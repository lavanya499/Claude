"""Fast LinkedIn scanner: every PM posting from the last ~90 minutes, with minute-level times.

Runs every 15 minutes (.github/workflows/linkedin.yml). Keeps its own state in data/linkedin.json so it
never collides with the hourly company scan, writes LIVE.md (newest first), and pushes to ntfy:

  * an instant alert for each new role at a target company (tier 1-2) that scores >= push_min_score
  * one quiet hourly roll-up of every other new role, during waking hours only

Usage: python radar/linkedin_scan.py            (normal run)
       python radar/linkedin_scan.py --no-push  (scan and write files, send nothing)
"""
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import scan  # noqa: E402
import sources  # noqa: E402

ROOT, CFG, FAST = scan.ROOT, scan.CFG, scan.CFG["linkedin_fast"]
STATE = ROOT / "data/linkedin.json"
LIVE_MD = ROOT / "LIVE.md"
LIVE_URL = f"{scan.REPO_URL}/blob/{scan.BRANCH}/LIVE.md"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
VAGUE = re.compile(r"remote|anywhere|hybrid|emea|apac|asia|europe", re.I)


def stamp(t):
    return t.strftime("%Y-%m-%dT%H:%MZ")


def parse(s):
    return dt.datetime.strptime(s, "%Y-%m-%dT%H:%MZ").replace(tzinfo=dt.timezone.utc)


def ist(s):
    return parse(s).astimezone(IST).strftime("%d %b %H:%M")


def query_plan(now):
    """(location, keywords, pages) in a rotation, so a partial run never starves the same markets."""
    plan = []
    for loc in FAST["locations"]:
        big = loc in FAST["big"]
        for kw in FAST["keywords"] + (FAST["big_keywords"] if big else []):
            plan.append((loc, kw, FAST["big_pages"] if big else FAST["pages"]))
    off = (int(now.timestamp() // 900) * 7) % len(plan)
    return (plan[off:] + plan[:off])[:FAST["max_calls"]]


def card_regions(card, search_loc):
    regs = scan.region(card["location"])
    if not regs and (not card["location"] or VAGUE.search(card["location"])):
        regs = scan.region(search_loc)
    return regs


def ats_fingerprints():
    try:
        jobs = json.loads((ROOT / "data/jobs.json").read_text())["jobs"].values()
    except (OSError, ValueError, KeyError):
        return set()
    return {(scan.slug(j["company"]), scan.slug(j["title"])) for j in jobs if j.get("source") != "linkedin"}


def collect(state, now):
    jobs, health = state["jobs"], {"calls": 0, "errors": 0, "cards": 0, "new": 0}
    plan = query_plan(now)
    new = []
    for loc, kw, pages in plan:
        health["calls"] += 1
        try:
            cards = list(sources.linkedin(kw, loc, seconds=FAST["seconds"], pages=pages))
        except Exception as e:  # noqa: BLE001
            health["errors"] += 1
            health["last_error"] = f"{type(e).__name__}: {str(e)[:120]}"
            print("query failed:", loc, kw, health["last_error"])
            if "429" in str(e) or "rate-limited" in str(e):
                health["rate_limited"] = True
                state["blocked_until"] = stamp(now + dt.timedelta(minutes=40))
                break
            continue
        health["cards"] += len(cards)
        for c in cards:
            lvl = scan.seniority(c["title"])
            regs = card_regions(c, loc) if lvl else []
            if not (lvl and regs):
                continue
            rec = jobs.get(c["id"])
            if rec is None:
                rec = jobs[c["id"]] = {"id": c["id"], "first_seen_at": stamp(now)}
                new.append(rec)
            co = scan.company_for(c["company"])
            rec.update({"company": co["name"] if co else c["company"] or "Unknown",
                        "tier": co.get("tier", 2) if co else 3, "title": c["title"],
                        "location": c["location"], "url": c["url"], "level": lvl, "regions": regs,
                        "posted": c["posted"]})
            if c["posted_ts"] and not rec.get("posted_ts"):
                rec["posted_ts"] = c["posted_ts"]
    health["new"] = len(new)
    return new, health


def rescore(rec):
    rec["visa"] = scan.visa_flag(rec.get("desc", ""))
    rec["score"] = scan.score(rec | {"first_seen": (rec.get("posted") or rec["first_seen_at"])[:10]})


def enrich(new):
    """Pull the description for the best new roles: it sharpens the visa flag and the score."""
    budget = FAST["detail_limit"]
    for rec in new:
        rescore(rec)
    for rec in sorted(new, key=lambda r: (r["tier"], -r["score"])):
        if budget <= 0 or rec["tier"] > 2:
            break
        budget -= 1
        try:
            rec["desc"] = sources.linkedin_desc(rec["id"])[:3500]
        except Exception as e:  # noqa: BLE001
            print("detail failed", rec["id"], e)
            break
        rescore(rec)


def age_label(rec, now):
    ts = rec.get("posted_ts") or rec["first_seen_at"]
    mins = int((now - parse(ts)).total_seconds() // 60)
    return f"{mins} min ago" if mins < 90 else f"{mins // 60} h ago"


def alert(new, state, now, baseline, push):
    seen_on_site = ats_fingerprints()
    for rec in new:
        rec["dup"] = (scan.slug(rec["company"]), scan.slug(rec["title"])) in seen_on_site
    fresh = [r for r in new if not r["dup"]]
    hot = sorted((r for r in fresh if r["tier"] in (1, 2) and r["level"] != "mid"
                  and r["score"] >= CFG["push_min_score"]), key=lambda r: (r["tier"], -r["score"]))
    if baseline:
        state["last_rollup"] = stamp(now)
        if push:
            scan.ntfy("LinkedIn live scanner is on",
                      f"Watching {len(FAST['locations'])} countries every 15 minutes. "
                      f"{len(new)} PM roles from the last 90 minutes are in the live list. "
                      "Roles at your target companies ping you the moment they appear.",
                      click=LIVE_URL, tags=["rocket"],
                      actions=[{"action": "view", "label": "Live list", "url": LIVE_URL}])
        return
    if push:
        for r in hot[:6]:
            note = {"yes": " · sponsorship/relocation mentioned", "no": " · says no sponsorship"}.get(r["visa"], "")
            scan.ntfy(f"{r['company']}: {r['title']}"[:250],
                      f"{r['location'][:120]}\nPosted {age_label(r, now)} · score {r['score']}{note}",
                      click=r["url"], priority=5 if r["tier"] == 1 else 4,
                      tags=["star"] if r["tier"] == 1 else ["briefcase"],
                      actions=[{"action": "view", "label": "Live list", "url": LIVE_URL}])
    for r in hot[:6]:
        r["alerted"] = True

    lo, hi = FAST["rollup_hours_utc"]
    since = state.get("last_rollup") or "0"
    due = (not state.get("last_rollup")) or now - parse(state["last_rollup"]) >= dt.timedelta(minutes=55)
    if push and due and lo <= now.hour <= hi:
        rest = sorted((r for r in state["jobs"].values()
                       if r["first_seen_at"] > since and not r.get("alerted") and not r.get("dup")),
                      key=lambda r: (r["tier"], -r.get("score", 0)))
        if rest:
            lines = [f"{r['company']}: {r['title']} ({(r['regions'] or [''])[0]})" for r in rest[:8]]
            scan.ntfy(f"{len(rest)} new PM roles on LinkedIn this hour", "\n".join(lines),
                      click=LIVE_URL, priority=2, tags=["mag"],
                      actions=[{"action": "view", "label": "Live list", "url": LIVE_URL}])
        state["last_rollup"] = stamp(now)


def write_live(state, now):
    cutoff = stamp(now - dt.timedelta(hours=48))
    rows = sorted((r for r in state["jobs"].values()
                   if r["first_seen_at"] >= cutoff and not r.get("dup") and "score" in r),
                  key=lambda r: r.get("posted_ts") or r["first_seen_at"], reverse=True)

    def table(items):
        out = ["| Posted (IST) | Company | Role | Where | Level | Score |", "|---|---|---|---|---|---|"]
        for r in items[:120]:
            title = r["title"].replace("|", "/")
            when = ist(r.get("posted_ts") or r["first_seen_at"])
            if not r.get("posted_ts"):
                when = "~" + when
            out.append(f"| {when} | {'⭐ ' if r['tier'] == 1 else ''}{r['company'].replace('|', '/')} | "
                       f"[{title}]({r['url']}) | {r['location'][:50].replace('|', '/')} | "
                       f"{r['level']} | {r['score']} |")
        return out

    targets = [r for r in rows if r["tier"] in (1, 2)]
    others = [r for r in rows if r["tier"] > 2 and r["level"] != "mid"]
    md = [f"# Live LinkedIn roles (last 48 hours, newest first)", "",
          f"Updated {ist(stamp(now))} IST. Scanned every 15 minutes across {len(FAST['locations'])} countries. "
          "A leading `~` means LinkedIn only gave a day, so the time shown is when we first saw it.", "",
          f"## Target companies ({len(targets)})", ""] + table(targets) + \
         ["", f"## Everyone else, senior level and above ({len(others)})", ""] + table(others) + [""]
    LIVE_MD.write_text("\n".join(md))


def main():
    push = "--no-push" not in sys.argv
    now = dt.datetime.now(dt.timezone.utc).replace(second=0, microsecond=0)
    state = json.loads(STATE.read_text()) if STATE.exists() else {"jobs": {}}
    baseline = not state["jobs"]
    before = json.dumps(state, sort_keys=True)
    if state.get("blocked_until") and stamp(now) < state["blocked_until"]:
        print("LinkedIn backoff until", state["blocked_until"])
        health = {"skipped": "backoff", "until": state["blocked_until"]}
        new = []
    else:
        state.pop("blocked_until", None)
        new, health = collect(state, now)
        enrich(new)
        alert(new, state, now, baseline, push)
    cutoff = stamp(now - dt.timedelta(days=FAST["keep_days"]))
    old_desc = stamp(now - dt.timedelta(days=3))
    for k, r in list(state["jobs"].items()):
        if r["first_seen_at"] < cutoff:
            del state["jobs"][k]
        elif r["first_seen_at"] < old_desc:
            r.pop("desc", None)
    state["health"] = health
    prev = json.loads(before)
    changed = bool(new) or any(state.get(k) != prev.get(k) for k in ("blocked_until", "last_rollup"))
    if changed:
        state["updated"] = stamp(now)
        STATE.write_text(json.dumps(state, indent=0, ensure_ascii=False, sort_keys=True))
        write_live(state, now)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"changed={'true' if changed else 'false'}\n")
    print(f"{len(state['jobs'])} tracked, {len(new)} new, health {health}")


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        sys.exit(1)
