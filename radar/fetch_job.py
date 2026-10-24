"""Print one Ashby posting (title, location, pay, full description). Usage: fetch_job.py ORG JOB_ID"""
import json
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import sources  # noqa: E402

org, jid = sys.argv[1], sys.argv[2]
if org == "li":  # LinkedIn search: "keywords|location|company id"; prints cards and matching descriptions
    import re
    kw, loc, cid = (jid.split("|") + ["", ""])[:3]
    want = re.compile(r"whatsapp|messag|business", re.I)
    shown = 0
    for r in sources.linkedin(kw, loc, hours=24 * 30, pages=3, company_id=cid or None,
                              geo_id=None if loc else "92000000"):
        print(r["id"], "|", r["title"], "|", r["company"], "|", r["location"], "|", r["posted"])
        if want.search(r["title"]) and shown < 3:
            shown += 1
            print("----- DESCRIPTION", r["id"], "-----")
            print(sources.linkedin_desc(r["id"]))
            print("-----")
    sys.exit(0)
if org == "url":  # any careers page: print its schema.org JobPosting, else the page text
    import re
    browser = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
               "Accept-Language": "en-US,en;q=0.9", "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate",
               "Sec-Fetch-Site": "none", "Sec-Fetch-User": "?1", "Upgrade-Insecure-Requests": "1"}
    try:
        src = sources.http(jid, headers=browser)
    except Exception as e:  # noqa: BLE001
        print("FETCH FAILED:", e)
        sys.exit(0)
    posts = []
    for blob in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', src, re.S):
        try:
            data = json.loads(blob)
        except ValueError:
            continue
        for x in data if isinstance(data, list) else [data]:
            if isinstance(x, dict) and x.get("@type") == "JobPosting":
                posts.append(x)
    for x in posts:
        print("TITLE:", x.get("title"), "| POSTED:", x.get("datePosted"), "| VALID THROUGH:", x.get("validThrough"))
        print("LOCATIONS:", json.dumps(x.get("jobLocation"))[:1200])
        for k in ("responsibilities", "qualifications", "skills", "baseSalary"):
            if x.get(k):
                print(k.upper() + ":", sources.text(x[k]) if isinstance(x[k], str) else json.dumps(x[k])[:3000])
        print("----- DESCRIPTION -----")
        print(sources.text(x.get("description", "")))
    if not posts:
        print("NO JobPosting JSON-LD; page length", len(src))
        print(sources.text(src)[:8000])
    sys.exit(0)
d = sources.get_json(f"https://api.ashbyhq.com/posting-api/job-board/{org}?includeCompensation=true")
jobs = d.get("jobs", [])
j = next((x for x in jobs if x.get("id") == jid), None)
if not j:
    print("NOT FOUND among", len(jobs), "open jobs. Open product titles:")
    for x in jobs:
        if "product" in x.get("title", "").lower():
            print(" -", x["id"], "|", x["title"], "|", x.get("location"))
    sys.exit(0)
print("TITLE:", j.get("title"))
print("LOCATION:", j.get("location"), "|", [s.get("location") for s in j.get("secondaryLocations") or []])
print("DEPARTMENT/TEAM:", j.get("department"), "|", j.get("team"), "| type:", j.get("employmentType"), "| remote:", j.get("isRemote"), "| workplace:", j.get("workplaceType"))
print("PUBLISHED:", j.get("publishedAt"), "| URL:", j.get("jobUrl"))
print("COMPENSATION:", json.dumps(j.get("compensation"))[:900] if j.get("compensation") else None)
print("----- DESCRIPTION -----")
print(j.get("descriptionPlain") or sources.text(j.get("descriptionHtml")))
