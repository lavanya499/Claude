"""SPM job radar: scan target companies + LinkedIn, keep a deduped list, push alerts.

Usage: python radar/scan.py            (normal run, used by the hourly workflow)
       python radar/scan.py --no-push  (scan and write files, send nothing)
"""
import concurrent.futures as cf
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import sources  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "radar/config.json").read_text())
COMPANIES = json.loads((ROOT / "radar/companies.json").read_text())
STATE = ROOT / "data/jobs.json"
HEALTH = ROOT / "data/health.json"
REPORT = ROOT / "JOBS.md"
REPO_URL = "https://github.com/" + os.environ.get("GITHUB_REPOSITORY", "lavanya499/Claude")
BRANCH = os.environ.get("GITHUB_REF_NAME", "main")

NOW = dt.datetime.now(dt.timezone.utc)
TODAY = NOW.date().isoformat()

T = {k: re.compile(v, re.I) for k, v in CFG["titles"].items()}
REGIONS = {k: re.compile(v, re.I) for k, v in CFG["regions"].items()}
DOMAIN = re.compile(CFG["profile"]["domain"], re.I)
YEARS = re.compile(r"(\d{1,2})\+?\s*(?:\+\s*)?(?:years?|yrs)\b[^.]{0,60}?experience", re.I)
PENALTY = re.compile(CFG["titles"].get("penalty", "$^"), re.I)
VISA_YES = re.compile(r"visa sponsorship (is )?(available|provided|offered)|we (can|will|do) sponsor|"
                      r"sponsorship (is )?available|relocation (support|package|assistance|bonus)|"
                      r"help(ing)? you relocate|relocate to", re.I)
VISA_NO = re.compile(r"(unable|not able|cannot|can't|can not|do not|don't|won't|will not|no) "
                     r"(to )?(offer |provide |support )?(visa |work permit )?sponsor|"
                     r"must (already )?(have|hold) (the )?(full )?right to work|"
                     r"without (the need for )?(visa )?sponsorship|not eligible for (visa )?sponsorship", re.I)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def seniority(title):
    t = title.lower()
    if not T["must"].search(t) or T["exclude"].search(t):
        return None
    if T["stretch"].search(t):
        return "stretch"
    if T["reach"].search(t):
        return "reach"
    if T["senior"].search(t):
        return "senior"
    if T["mid"].search(t):
        return "mid"
    return "unlevelled"


def region(location):
    hits = []
    for part in re.split(r";|\||/| or |\n", location or ""):
        part = part.strip()
        for name, rx in REGIONS.items():
            if part and rx.search(part) and name not in hits:
                hits.append(name)
    return hits


def visa_flag(desc):
    if not desc:
        return ""
    if VISA_NO.search(desc):
        return "no"
    if VISA_YES.search(desc):
        return "yes"
    return ""


def score(job):
    lp = CFG["profile"]["level_points"]
    lvl = job["level"]
    if lvl == "unlevelled" and job["tier"] == 1:
        lvl = "unlevelled_tier1"  # big tech titles like Google "Product Manager" (L5) fit ~5 yrs PM
    s = lp.get(lvl, 24)
    s += {1: 25, 2: 18}.get(job["tier"], 5)
    desc = job.get("desc") or ""
    m = YEARS.search(desc)
    if m:  # required years of experience vs ~5 yrs PM / 9+ total
        n = int(m.group(1))
        s += 5 if n <= 6 else -12 if n >= 10 else 0
    title_hits = len(set(x.lower() for x in DOMAIN.findall(job["title"])))
    desc_hits = len(set(x.lower() for x in DOMAIN.findall(desc[:4000])))
    s += min(12, 4 * title_hits + 2 * min(desc_hits, 3))
    s += max([CFG["region_points"].get(r, 0) for r in job["regions"]] or [0])
    s += {"yes": 10, "no": -15}.get(job.get("visa"), 0)
    if PENALTY.search(job["title"]):
        s -= 20
    posted = job.get("posted") or job.get("first_seen")
    try:
        age = (NOW.date() - dt.date.fromisoformat(posted[:10])).days
        s += 10 if age <= 2 else 5 if age <= 7 else 0
    except (TypeError, ValueError):
        pass
    return max(0, min(100, s))


# --- collection ----------------------------------------------------------------

def linkedin_plan():
    """LinkedIn throttles bursts, so each hourly run takes the next few queries in a fixed rotation."""
    li = CFG["linkedin"]
    plan = [f"co:{c['name']}" for c in COMPANIES
            if c["ats"] == "linkedin_company" or c.get("fallback", {}).get("ats") == "linkedin_company"]
    plan += [f"loc:{loc}|{kw}" for loc in li["locations"] for kw in li["keywords"]]
    n = li.get("per_run", 6)
    slot = int(NOW.timestamp() // 3600) if "--all-linkedin" not in sys.argv else 0
    if "--all-linkedin" in sys.argv:
        return set(plan)
    return {plan[(slot * n + i) % len(plan)] for i in range(min(n, len(plan)))}


LI_PLAN = linkedin_plan()


def want(title):
    return seniority(title) is not None


def scan_company(c):
    via = c["ats"]
    skip = {"ok": True, "via": "linkedin_company", "skipped": True}
    try:
        if via == "linkedin_company" and f"co:{c['name']}" not in LI_PLAN:
            return c, [], skip
        rows = list(sources.FETCHERS[via](c, want))
    except Exception as e:  # noqa: BLE001
        if not c.get("fallback"):
            return c, [], {"ok": False, "via": via, "error": f"{type(e).__name__}: {str(e)[:160]}"}
        via = c["fallback"]["ats"]
        if via == "linkedin_company" and f"co:{c['name']}" not in LI_PLAN:
            return c, [], skip | {"ok": False, "error": f"{type(e).__name__}: {str(e)[:120]} (LinkedIn fallback queued)"}
        try:
            rows = list(sources.FETCHERS[via](c | c["fallback"], want))
        except Exception as e2:  # noqa: BLE001
            return c, [], {"ok": False, "via": via,
                           "error": f"{type(e).__name__}: {str(e)[:80]} / fallback {type(e2).__name__}: {str(e2)[:80]}"}
    if via == "linkedin_company":
        for r in rows:
            r["_detail"] = ("linkedin", r["id"])
    out = []
    for r in rows:
        lvl = seniority(r["title"])
        regs = region(r.get("location", ""))
        if lvl and regs:
            out.append(r | {"level": lvl, "regions": regs})
    return c, out, {"ok": True, "via": via, "total": len(rows), "matched": len(out)}


ALIASES = {}
for _c in COMPANIES:
    for _a in [_c["name"]] + _c.get("aliases", []):
        ALIASES[slug(_a)] = _c


def company_for(name):
    s = slug(name or "")
    if s in ALIASES:
        return ALIASES[s]
    for a, c in ALIASES.items():
        if len(a) > 3 and (s.startswith(a + "-") or s == a):
            return c
    return None


def scan_linkedin():
    li = CFG["linkedin"]
    found, health = [], {"ok": True, "calls": 0, "errors": 0, "cards": 0}
    for loc in li["locations"]:
        for kw in li["keywords"]:
            if f"loc:{loc}|{kw}" not in LI_PLAN:
                continue
            health["calls"] += 1
            try:
                rows = list(sources.linkedin(kw, loc, hours=li.get("hours", 24)))
            except Exception as e:  # noqa: BLE001
                health["errors"] += 1
                health["last_error"] = f"{type(e).__name__}: {str(e)[:120]}"
                if "429" in str(e) or "rate-limited" in str(e):
                    health.update(ok=False, rate_limited=True)
                    return found, health
                continue
            health["cards"] += len(rows)
            for r in rows:
                lvl = seniority(r["title"])
                regs = region(r["location"]) or region(loc)
                if lvl and regs:
                    found.append(r | {"level": lvl, "regions": regs})
    health["ok"] = health["errors"] == 0
    return found, health


# --- output --------------------------------------------------------------------

def ntfy(title, message, click=None, priority=3, tags=None, email=False):
    topic = os.environ.get("NTFY_TOPIC") or CFG["ntfy_topic"]
    body = {"topic": topic, "title": title[:250], "message": message[:3800],
            "priority": priority, "tags": tags or ["briefcase"]}
    if email and os.environ.get("NTFY_EMAIL"):
        body["email"] = os.environ["NTFY_EMAIL"]
    if click:
        body["click"] = click
    body["actions"] = [{"action": "view", "label": "All jobs",
                        "url": f"{REPO_URL}/blob/{BRANCH}/JOBS.md"}]
    try:
        sources.http("https://ntfy.sh/", data=body, timeout=20)
    except Exception as e:  # noqa: BLE001
        print("ntfy failed:", e)


def md_row(j):
    visa = {"yes": "✅ sponsor/relocation", "no": "⛔ no sponsorship"}.get(j.get("visa"), "")
    title = j["title"].replace("|", "/")
    return (f"| {j['score']} | {'⭐ ' if j['tier'] == 1 else ''}{j['company']} | "
            f"[{title}]({j['url']}) | {j['location'][:60].replace('|', '/')} | "
            f"{visa} | {j.get('posted') or j['first_seen']} |")


def write_report(jobs, health, new_keys):
    open_jobs = [j for j in jobs if j["active"]]
    head = "| Score | Company | Role | Location | Visa | Posted |\n|---:|---|---|---|---|---|"
    recent = sorted((j for j in open_jobs if j["first_seen"] >= (NOW - dt.timedelta(days=1)).date().isoformat()),
                    key=lambda j: -j["score"])
    lines = [
        "# SPM Job Radar",
        "",
        f"_Updated {NOW:%Y-%m-%d %H:%M} UTC · {len(open_jobs)} open matches · "
        f"{len(recent)} new in the last 24h · {sum(1 for h in health.values() if h.get('ok'))}/"
        f"{len(health)} sources healthy_",
        "",
        "Score = level fit (up to 40) + company tier (25/18) + target country (15) + visa/relocation signal (±10) "
        "+ freshness (10) + required experience (±) + domain fit with your background (up to 12). ⭐ = Tier-1 big tech. Full data: [`data/jobs.json`](data/jobs.json). "
        "How to use it: [PLAYBOOK.md](PLAYBOOK.md).",
        "",
        "## New in the last 24 hours",
        "",
        head, *([md_row(j) for j in recent[:80]] or ["| – | – | nothing new yet | – | – | – |"]),
        "",
    ]
    order = ["UK", "Europe", "Australia", "Thailand", "Malaysia", "Singapore", "India"]
    for reg in order:
        rows = sorted((j for j in open_jobs if j["regions"][0] == reg), key=lambda j: -j["score"])
        if not rows:
            continue
        lines += [f"## {reg} — {len(rows)} open", "", head, *[md_row(j) for j in rows[:60]], ""]
        if len(rows) > 60:
            lines += [f"_…and {len(rows) - 60} more in data/jobs.json_", ""]
    lines += ["<details><summary>Source health</summary>", "",
              "| Source | Status | Jobs scanned | Matches |", "|---|---|---:|---:|"]
    for name, h in sorted(health.items()):
        status = "ok" if h.get("ok") else f"⚠️ {h.get('error') or h.get('last_error', 'error')}"
        lines.append(f"| {name} | {status} | {h.get('total', h.get('cards', ''))} | {h.get('matched', '')} |")
    lines += ["", "</details>", ""]
    REPORT.write_text("\n".join(lines))


def main():
    push = "--no-push" not in sys.argv
    STATE.parent.mkdir(parents=True, exist_ok=True)
    state = json.loads(STATE.read_text()) if STATE.exists() else {"jobs": {}}
    before = json.dumps(state["jobs"], sort_keys=True)
    known = state["jobs"]
    first_run = not known

    health, found = {}, []
    with cf.ThreadPoolExecutor(10) as ex:
        for c, rows, h in ex.map(scan_company, COMPANIES):
            health[c["name"]] = h
            for r in rows:
                found.append((c, r))
    li_rows, health["LinkedIn (all companies)"] = scan_linkedin()

    ok_companies = {n for n, h in health.items() if h.get("ok") and not h.get("skipped")}
    baselined = set(state.get("baselined", []))
    fresh_sources = {n for n in ok_companies if n not in baselined and n != "LinkedIn (all companies)"}
    by_fingerprint = {}
    for c, r in found:
        from_li = r.get("_detail", ("",))[0] == "linkedin"
        key = f"linkedin:{r['id']}" if from_li else f"{slug(c['name'])}:{r['id']}"
        by_fingerprint[(slug(c["name"]), slug(r["title"]))] = key
        rec = known.get(key) or {"first_seen": TODAY, "key": key}
        rec.update({"company": c["name"], "tier": c.get("tier", 2), "title": r["title"],
                    "location": r.get("location", ""), "url": r["url"],
                    "source": "linkedin" if from_li else c["ats"],
                    "posted": r.get("posted") or rec.get("posted"), "level": r["level"],
                    "regions": r["regions"], "last_seen": TODAY, "active": True})
        if r.get("desc") and not rec.get("desc"):
            rec["desc"] = r["desc"][:5000]
        rec["_detail"] = r.get("_detail")
        known[key] = rec
    for r in li_rows:
        c = company_for(r.get("company"))
        cname = c["name"] if c else r.get("company") or "Unknown"
        if (slug(cname), slug(r["title"])) in by_fingerprint:
            continue  # already have it straight from the company's own site
        key = f"linkedin:{r['id']}"
        rec = known.get(key) or {"first_seen": TODAY, "key": key}
        rec.update({"company": cname, "tier": c.get("tier", 2) if c else 3, "title": r["title"],
                    "location": r["location"], "url": r["url"], "source": "linkedin",
                    "posted": r.get("posted") or rec.get("posted"), "level": r["level"],
                    "regions": r["regions"], "last_seen": TODAY, "active": True,
                    "_detail": ("linkedin", r["id"])})
        known[key] = rec

    # Close jobs that vanished from a healthy source; LinkedIn rows age out after 14 days.
    for key, rec in list(known.items()):
        if rec["last_seen"] == TODAY:
            continue
        if rec["source"] == "linkedin":
            rec["active"] = (NOW.date() - dt.date.fromisoformat(rec["first_seen"])).days <= 14
        elif rec["company"] in ok_companies:
            rec["active"] = False
        if (NOW.date() - dt.date.fromisoformat(rec["last_seen"])).days > CFG["keep_days"]:
            del known[key]

    new_keys = [k for k, r in known.items() if r["first_seen"] == TODAY and not r.get("notified")]
    for k in new_keys:  # first successful scan of a source = baseline, not news
        if known[k]["company"] in fresh_sources and known[k]["source"] != "linkedin":
            known[k]["notified"] = True
    state["baselined"] = sorted(baselined | fresh_sources)

    # Pull descriptions for new rows that lack one (visa/relocation signal + tailoring later).
    budget, li_budget = CFG["detail_fetch_limit"], CFG.get("linkedin_detail_limit", 15)
    for key in sorted(new_keys, key=lambda k: (known[k]["tier"], -score(known[k]))):
        rec = known[key]
        d = rec.pop("_detail", None)
        if rec.get("desc") or not d or budget <= 0 or (d[0] == "linkedin" and li_budget <= 0):
            continue
        budget -= 1
        try:
            if d[0] == "linkedin":
                li_budget -= 1
                rec["desc"] = sources.linkedin_desc(d[1])[:5000]
            else:
                rec["desc"] = sources.DETAIL[d[0]](d[1], d[2])[:5000]
        except Exception as e:  # noqa: BLE001
            print("detail failed", key, e)
    for rec in known.values():
        rec.pop("_detail", None)
        rec["visa"] = visa_flag(rec.get("desc", ""))
        rec["score"] = score(rec)

    jobs = sorted(known.values(), key=lambda j: (-j["active"], -j["score"], j["company"]))
    write_report(jobs, health, new_keys)
    HEALTH.write_text(json.dumps(health, indent=1, sort_keys=True))

    fresh = sorted((known[k] for k in new_keys if known[k]["active"] and not known[k].get("notified")),
                   key=lambda j: -j["score"])
    if push and first_run:
        ntfy("SPM radar is live", f"Tracking {len(jobs)} open SPM roles across "
             f"{len(ok_companies)} sources. You'll get a ping when a new one appears.",
             click=f"{REPO_URL}/blob/{BRANCH}/JOBS.md", tags=["rocket"])
    elif push:
        hot = [j for j in fresh if j["tier"] in (1, 2) and j["score"] >= CFG["push_min_score"]]
        for j in hot[:6]:
            ntfy(f"{j['company']}: {j['title']}"[:250],
                 f"{j['location'][:120]}\nScore {j['score']}"
                 + (f" · posted {j['posted'][:10]}" if j.get("posted") else "")
                 + {"yes": " · sponsorship/relocation mentioned", "no": " · says no sponsorship"}
                 .get(j["visa"], ""),
                 click=j["url"], priority=5 if j["tier"] == 1 else 4,
                 tags=["star"] if j["tier"] == 1 else ["briefcase"])
        if len(hot) > 6:
            ntfy(f"+{len(hot) - 6} more new roles at target companies", "Open the list to see them all.",
                 click=f"{REPO_URL}/blob/{BRANCH}/JOBS.md")
        if NOW.hour == CFG["digest_hour_utc"]:
            today = sorted((j for j in jobs if j["active"] and j["first_seen"] >=
                            (NOW - dt.timedelta(days=1)).date().isoformat()), key=lambda j: -j["score"])
            msg = "\n".join(f"{j['score']} · {j['company']} — {j['title']} ({j['regions'][0]})"
                            for j in today[:10]) or "Quiet day. Use tonight for referrals + interview prep."
            ntfy(f"Tonight's shortlist: {len(today)} new roles in 24h", msg,
                 click=f"{REPO_URL}/blob/{BRANCH}/JOBS.md", priority=4, tags=["calendar"], email=True)
    for k in new_keys:
        known[k]["notified"] = True

    changed = json.dumps(dict(sorted(known.items())), sort_keys=True) != before or NOW.hour == CFG["digest_hour_utc"]
    STATE.write_text(json.dumps({"updated": NOW.isoformat(timespec="minutes"),
                                 "baselined": state["baselined"],
                                 "jobs": dict(sorted(known.items()))}, indent=1, ensure_ascii=False))
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"changed={'true' if changed else 'false'}\n")
    print(f"{len(jobs)} tracked, {sum(j['active'] for j in jobs)} open, {len(fresh)} new; "
          f"healthy sources {len(ok_companies)}/{len(health)}")
    for n, h in sorted(health.items()):
        if not h.get("ok"):
            print("  unhealthy:", n, h)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        if NOW.hour == CFG["digest_hour_utc"]:  # at most one error ping a day
            ntfy("Job radar hit an error", f"{type(exc).__name__}: {exc}"[:500], priority=2, tags=["warning"])
        sys.exit(1)
