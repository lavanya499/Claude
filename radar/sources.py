"""Fetchers for public career-site APIs. Standard library only.

Every fetcher yields dicts with: id, title, location, url, posted (ISO date or None)
and optionally desc (plain-text job description). `want(title)` lets a fetcher skip
expensive detail calls for titles we will throw away anyway.
"""
import datetime as dt
import html
import json
import re
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")


def http(url, data=None, headers=None, timeout=30):
    h = {"User-Agent": UA, "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
         "Accept-Language": "en-GB,en;q=0.9"}
    h.update(headers or {})
    body = None
    if data is not None:
        if isinstance(data, (dict, list)):
            body = json.dumps(data).encode()
            h.setdefault("Content-Type", "application/json")
        else:
            body = data.encode() if isinstance(data, str) else data
    req = urllib.request.Request(url, data=body, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def get_json(url, **kw):
    return json.loads(http(url, **kw))


def text(s):
    """HTML (possibly entity-escaped twice) -> collapsed plain text."""
    if not s:
        return ""
    s = html.unescape(html.unescape(s))
    s = re.sub(r"<(br|/p|/li|/h\d)[^>]*>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    return re.sub(r"\n\s*\n+", "\n", s).strip()


def iso(v):
    if v in (None, ""):
        return None
    if isinstance(v, (int, float)):
        if v > 1e11:
            v /= 1000
        return dt.datetime.fromtimestamp(v, dt.timezone.utc).date().isoformat()
    m = re.search(r"\d{4}-\d{2}-\d{2}", str(v))
    if m:
        return m.group(0)
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%d %B %Y"):
        try:
            return dt.datetime.strptime(str(v).strip(), fmt).date().isoformat()
        except ValueError:
            pass
    return None


def _always(_title):
    return True


# --- ATS platforms -----------------------------------------------------------

def greenhouse(token, want=_always, **_):
    d = get_json(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs")
    for j in d.get("jobs", []):
        yield {"id": str(j["id"]), "title": j["title"],
               "location": (j.get("location") or {}).get("name", ""),
               "url": j.get("absolute_url"),
               "posted": iso(j.get("first_published") or j.get("updated_at")),
               "_detail": ("greenhouse", token, j["id"])}


def greenhouse_desc(token, job_id):
    d = get_json(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs/{job_id}")
    return text(d.get("content", ""))


def lever(company, want=_always, eu=False, **_):
    base = "https://api.eu.lever.co" if eu else "https://api.lever.co"
    for j in get_json(f"{base}/v0/postings/{company}?mode=json"):
        cats = j.get("categories") or {}
        locs = cats.get("allLocations") or [cats.get("location") or ""]
        desc = j.get("descriptionPlain") or ""
        for block in j.get("lists") or []:
            desc += "\n" + block.get("text", "") + "\n" + text(block.get("content", ""))
        yield {"id": j["id"], "title": j["text"], "location": "; ".join(locs),
               "url": j.get("hostedUrl"), "posted": iso(j.get("createdAt")),
               "desc": (desc + "\n" + (j.get("additionalPlain") or "")).strip()}


def ashby(org, want=_always, **_):
    d = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{org}")
    for j in d.get("jobs", []):
        if j.get("isListed") is False:
            continue
        locs = [j.get("location") or ""]
        locs += [s.get("location", "") for s in j.get("secondaryLocations") or []]
        country = (((j.get("address") or {}).get("postalAddress") or {})
                   .get("addressCountry"))
        if country:
            locs.append(country)
        if j.get("isRemote"):
            locs.append("Remote")
        yield {"id": j["id"], "title": j["title"],
               "location": "; ".join(x for x in locs if x),
               "url": j.get("jobUrl"), "posted": iso(j.get("publishedAt")),
               "desc": j.get("descriptionPlain") or text(j.get("descriptionHtml"))}


def smartrecruiters(company, want=_always, q="product manager", **_):
    offset, total = 0, None
    while total is None or offset < min(total, 600):
        qs = urllib.parse.urlencode({"q": q, "limit": 100, "offset": offset})
        d = get_json(f"https://api.smartrecruiters.com/v1/companies/{company}/postings?{qs}")
        total = d.get("totalFound", 0)
        for j in d.get("content", []):
            loc = j.get("location") or {}
            s = loc.get("fullLocation") or ", ".join(
                x for x in (loc.get("city"), loc.get("region"), loc.get("country")) if x)
            if loc.get("remote"):
                s += " (Remote)"
            yield {"id": j["id"], "title": j["name"], "location": s,
                   "url": f"https://jobs.smartrecruiters.com/{company}/{j['id']}",
                   "posted": iso(j.get("releasedDate")),
                   "_detail": ("smartrecruiters", company, j["id"])}
        offset += 100
        if not d.get("content"):
            break


def smartrecruiters_desc(company, job_id):
    d = get_json(f"https://api.smartrecruiters.com/v1/companies/{company}/postings/{job_id}")
    secs = ((d.get("jobAd") or {}).get("sections") or {}).values()
    return text("\n".join(s.get("text", "") for s in secs if isinstance(s, dict)))


def _workday_posted(s):
    if not s:
        return None
    today = dt.date.today()
    s = s.lower()
    if "today" in s:
        return today.isoformat()
    if "yesterday" in s:
        return (today - dt.timedelta(days=1)).isoformat()
    m = re.search(r"(\d+)\+?\s*days", s)
    return (today - dt.timedelta(days=int(m.group(1)))).isoformat() if m else None


def workday(host, tenant, site, want=_always, q="product manager", **_):
    base = f"https://{host}/wday/cxs/{tenant}/{site}"
    offset, total = 0, None
    while total is None or offset < min(total, 400):
        d = get_json(f"{base}/jobs", data={"appliedFacets": {}, "limit": 20,
                                           "offset": offset, "searchText": q})
        if total is None:
            total = d.get("total", 0)
        posts = d.get("jobPostings") or []
        for p in posts:
            path = p.get("externalPath", "")
            job = {"id": (p.get("bulletFields") or [path])[0], "title": p.get("title", ""),
                   "location": p.get("locationsText", ""),
                   "url": f"https://{host}/en-US/{site}{path}",
                   "posted": _workday_posted(p.get("postedOn"))}
            if want(job["title"]):
                try:
                    info = get_json(f"{base}{path}").get("jobPostingInfo", {})
                    locs = [info.get("location", "")] + (info.get("additionalLocations") or [])
                    job["location"] = "; ".join(x for x in locs if x) or job["location"]
                    job["desc"] = text(info.get("jobDescription", ""))
                    job["posted"] = iso(info.get("startDate")) or job["posted"]
                except Exception:
                    pass
            yield job
        offset += 20
        if not posts:
            break


# --- Company-specific sites ---------------------------------------------------

def amazon(countries, want=_always, q="product manager", **_):
    for cc in countries:
        for offset in range(0, 500, 100):
            qs = urllib.parse.urlencode({"base_query": q, "normalized_country_code[]": cc,
                                         "result_limit": 100, "offset": offset,
                                         "sort": "recent"})
            d = get_json(f"https://www.amazon.jobs/en/search.json?{qs}")
            jobs = d.get("jobs") or []
            for j in jobs:
                yield {"id": str(j.get("id_icims") or j.get("id")), "title": j["title"],
                       "location": j.get("normalized_location") or j.get("location", ""),
                       "url": "https://www.amazon.jobs" + j.get("job_path", ""),
                       "posted": iso(j.get("posted_date")),
                       "desc": text("\n".join(j.get(k) or "" for k in (
                           "description", "basic_qualifications", "preferred_qualifications")))}
            if len(jobs) < 100:
                break


def _js_array_after(src, start):
    """Return the JSON array literal beginning at the first '[' after `start`."""
    i = src.index("[", start)
    depth, in_str, esc = 0, False, False
    for k in range(i, len(src)):
        c = src[k]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return json.loads(src[i:k + 1])
    raise ValueError("unterminated array")


def _strings(node, out):
    if isinstance(node, str):
        out.append(node)
    elif isinstance(node, list):
        for x in node:
            _strings(x, out)
    return out


def google(locations, want=_always, q='"product manager"', max_pages=8, **_):
    for loc in locations:
        for page in range(1, max_pages + 1):
            qs = urllib.parse.urlencode({"q": q, "location": loc, "page": page})
            src = http(f"https://www.google.com/about/careers/applications/jobs/results/?{qs}",
                       headers={"Accept": "text/html"})
            m = re.search(r"AF_initDataCallback\(\{key: 'ds:1'.*?data:", src, re.S)
            if not m:
                break
            data = _js_array_after(src, m.end() - 1)
            rows = data[0] if data and isinstance(data[0], list) else []
            for r in rows:
                if not (isinstance(r, list) and len(r) > 2 and isinstance(r[1], str)):
                    continue
                locs = []
                for item in r:
                    if isinstance(item, list) and item and isinstance(item[0], list) \
                            and item[0] and isinstance(item[0][0], str) and "," in item[0][0]:
                        locs = [x[0] for x in item if isinstance(x, list) and x
                                and isinstance(x[0], str)]
                        break
                slug = re.sub(r"[^a-z0-9]+", "-", r[1].lower()).strip("-")
                yield {"id": str(r[0]), "title": r[1], "location": "; ".join(locs),
                       "url": "https://www.google.com/about/careers/applications/jobs/"
                              f"results/{r[0]}-{slug}",
                       "posted": None,
                       "desc": "\n".join(s for s in _strings(r[3:8], []) if len(s) > 30)[:6000]}
            if len(rows) < 20:
                break


def microsoft(locations, want=_always, q="product manager", **_):
    for loc in locations:
        for start in range(0, 200, 20):
            qs = urllib.parse.urlencode({"domain": "microsoft.com", "query": q,
                                         "location": loc, "start": start,
                                         "sort_by": "timestamp"})
            d = get_json(f"https://apply.careers.microsoft.com/api/pcsx/search?{qs}")
            pos = (d.get("data") or {}).get("positions") or []
            for p in pos:
                yield {"id": str(p.get("id")), "title": p.get("name", ""),
                       "location": "; ".join(p.get("locations") or []),
                       "url": "https://apply.careers.microsoft.com" + p["positionUrl"]
                       if str(p.get("positionUrl", "")).startswith("/")
                       else p.get("positionUrl") or
                       f"https://apply.careers.microsoft.com/careers/job/{p.get('id')}",
                       "posted": iso(p.get("postedTs"))}
            if len(pos) < 10:
                break


def eightfold(host, domain, want=_always, q="product manager", **_):
    for start in range(0, 300, 50):
        qs = urllib.parse.urlencode({"domain": domain, "query": q, "start": start, "num": 50})
        d = get_json(f"https://{host}/api/apply/v2/jobs?{qs}")
        pos = d.get("positions") or []
        for p in pos:
            yield {"id": str(p.get("id")), "title": p.get("name", ""),
                   "location": "; ".join(p.get("locations") or [p.get("location", "")]),
                   "url": p.get("canonicalPositionUrl") or f"https://{host}/careers/job/{p.get('id')}",
                   "posted": iso(p.get("t_create"))}
        if len(pos) < 50:
            break


def uber(want=_always, q="product manager", **_):
    for page in range(0, 6):
        d = get_json("https://www.uber.com/api/loadSearchJobsResults?localeCode=en",
                     data={"limit": 50, "page": page, "params": {"query": q}},
                     headers={"x-csrf-token": "x"})
        res = (d.get("data") or {}).get("results") or []
        for j in res:
            locs = j.get("allLocations") or [j.get("location") or {}]
            s = "; ".join(", ".join(x for x in (l.get("city"), l.get("countryName")) if x)
                          for l in locs)
            yield {"id": str(j["id"]), "title": j.get("title", ""), "location": s,
                   "url": f"https://www.uber.com/global/en/careers/list/{j['id']}/",
                   "posted": iso(j.get("creationDate")),
                   "desc": text(j.get("description", ""))}
        if len(res) < 50:
            break


def atlassian(want=_always, **_):
    for j in get_json("https://www.atlassian.com/endpoint/careers/listings"):
        yield {"id": str(j.get("id")), "title": j.get("title", ""),
               "location": "; ".join(j.get("locations") or []),
               "url": f"https://www.atlassian.com/company/careers/details/{j.get('id')}",
               "posted": None,
               "desc": text((j.get("overview") or "") + "\n" + (j.get("responsibilities") or "")
                            + "\n" + (j.get("qualifications") or ""))}


def linkedin(keywords, location, want=_always, hours=24, pages=1, **_):
    """LinkedIn's public (logged-out) job search. Covers every company."""
    for page in range(pages):
        qs = urllib.parse.urlencode({"keywords": keywords, "location": location,
                                     "f_TPR": f"r{hours * 3600}", "sortBy": "DD",
                                     "start": page * 25})
        src = http(f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?{qs}",
                   headers={"Accept": "text/html"})
        cards = src.split("<li")
        n = 0
        for c in cards:
            m = re.search(r"urn:li:jobPosting:(\d+)", c)
            if not m:
                continue
            g = lambda pat: (lambda mm: text(mm.group(1)) if mm else "")(re.search(pat, c, re.S))
            n += 1
            yield {"id": m.group(1),
                   "title": g(r'base-search-card__title">(.*?)</h3>'),
                   "company": g(r'base-search-card__subtitle">.*?>(.*?)</a>') or
                              g(r'base-search-card__subtitle">(.*?)</h4>'),
                   "location": g(r'job-search-card__location">(.*?)</span>'),
                   "url": f"https://www.linkedin.com/jobs/view/{m.group(1)}/",
                   "posted": g(r'<time[^>]*datetime="([^"]+)"')}
        if n < 25:
            break


def linkedin_desc(job_id):
    src = http(f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}",
               headers={"Accept": "text/html"})
    m = re.search(r'show-more-less-html__markup[^>]*>(.*?)</div>', src, re.S)
    return text(m.group(1)) if m else ""


FETCHERS = {
    "greenhouse": lambda c, w: greenhouse(c["token"], w),
    "lever": lambda c, w: lever(c["token"], w, eu=c.get("eu", False)),
    "ashby": lambda c, w: ashby(c["token"], w),
    "smartrecruiters": lambda c, w: smartrecruiters(c["token"], w),
    "workday": lambda c, w: workday(c["host"], c["tenant"], c["site"], w),
    "amazon": lambda c, w: amazon(c["countries"], w),
    "google": lambda c, w: google(c["locations"], w),
    "microsoft": lambda c, w: microsoft(c["locations"], w),
    "eightfold": lambda c, w: eightfold(c["host"], c["domain"], w),
    "uber": lambda c, w: uber(w),
    "atlassian": lambda c, w: atlassian(w),
}

DETAIL = {
    "greenhouse": greenhouse_desc,
    "smartrecruiters": smartrecruiters_desc,
}
