"""One-off health check: which career-site endpoints answer, and how many PM roles each has.

Run on GitHub Actions (job sites are reachable there): python radar/probe.py
"""
import concurrent.futures as cf
import itertools
import json
import re
import sys
import traceback

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import sources  # noqa: E402

PM = re.compile(r"product manager|product lead|head of product", re.I)

# Round 3 candidates: customer-experience / conversational-AI / insurtech companies.
GH = ["polyai", "parloa", "cognigy", "lemonade", "wefox", "zego", "bolttech", "covergenius",
      "freshworks", "sprinklr", "uniphore", "observeai", "yellowai", "gupshup", "haptik", "koreai",
      "zendesk", "talkdesk", "dixa", "ada", "forethought", "sierra", "decagon", "cresta", "gorgias",
      "kustomer", "helpscout", "aircall", "ringcentral", "five9", "genesys", "twilio", "sinch",
      "infobip", "messagebird", "bird", "trengo", "chatbase", "assembled", "playvox", "zopa",
      "acko", "digit", "insurify", "getsafe", "alan", "hiscox", "bupa", "ondo"]
LEVER = ["polyai", "parloa", "cognigy", "covergenius", "bolttech", "yellowai", "yellow", "observeai",
         "uniphore", "gupshup", "haptik", "freshworks", "dixa", "talkdesk", "aircall", "zego",
         "wefox", "getsafe", "acko", "infobip", "sinch", "verloop", "leena", "sprinklr"]
ASHBY = ["polyai", "parloa", "cognigy", "zego", "lemonade", "wefox", "dixa", "aircall", "sierra",
         "decagon", "cresta", "assembled", "gorgias", "kustomer", "getsafe", "covergenius", "bolttech",
         "talkdesk", "trengo", "yellowai", "observeai", "ada", "forethought", "intercom"]
SR = ["Freshworks", "Sprinklr", "Talkdesk", "Infobip", "Sinch", "Genesys", "NICE", "Five9",
      "Bolttech", "CoverGenius", "Uniphore", "Zendesk", "Gupshup", "Bupa", "Aviva", "Allianz"]
WD = [("zendesk.wd1.myworkdayjobs.com", "zendesk", "zendesk"),
      ("genesys.wd1.myworkdayjobs.com", "genesys", "Genesys"),
      ("sprinklr.wd1.myworkdayjobs.com", "sprinklr", "careers"),
      ("nice.wd3.myworkdayjobs.com", "nice", "NICE_Careers"),
      ("five9.wd5.myworkdayjobs.com", "five9", "Five9"),
      ("ringcentral.wd1.myworkdayjobs.com", "ringcentral", "RingCentral_Careers")]

EU = ["United Kingdom", "Ireland", "Netherlands", "Germany", "Australia", "Singapore",
      "Malaysia", "Thailand", "India"]

CANDIDATES = (
    [{"ats": "greenhouse", "token": t} for t in GH]
    + [{"ats": "lever", "token": t} for t in LEVER]
    + [{"ats": "lever", "token": t, "eu": True} for t in LEVER]
    + [{"ats": "ashby", "token": t} for t in ASHBY]
    + [{"ats": "smartrecruiters", "token": t} for t in SR]
    + [{"ats": "workday", "host": h, "tenant": t, "site": s} for h, t, s in WD]
)


def label(c):
    return c["ats"] + ":" + str(c.get("token") or c.get("tenant") or c.get("host")
                                or "") + (":eu" if c.get("eu") else "")


def run(c):
    try:
        jobs = list(itertools.islice(sources.FETCHERS[c["ats"]](c, lambda t: False), 4000))
        pm = [j for j in jobs if PM.search(j["title"])]
        return label(c), len(jobs), len(pm), [f'{j["title"]} | {j["location"]}' for j in pm[:4]], None
    except Exception as e:  # noqa: BLE001
        return label(c), 0, 0, [], f"{type(e).__name__}: {str(e)[:120]}"


def raw(label, url, data=None, headers=None, find=None, n=1500):
    try:
        src = sources.http(url, data=data, headers=headers)
        i = src.find(find) if find else 0
        print(f"OK  {label}: len={len(src)} find={i}\n    {src[max(i, 0):max(i, 0) + n]!r}")
    except Exception as e:  # noqa: BLE001
        print(f"BAD {label}: {type(e).__name__}: {str(e)[:150]}")


def main():
    if "--companies" in sys.argv:  # health-check the configured top-50 list
        cands = json.load(open(__file__.rsplit("/", 1)[0] + "/companies.json"))
    elif "--experiments" in sys.argv:
        cands = []
    else:
        cands = CANDIDATES
    ok, bad = [], []
    with cf.ThreadPoolExecutor(12) as ex:
        for lab, n, npm, sample, err in ex.map(run, cands):
            (bad if err or n == 0 else ok).append((lab, n, npm, sample, err))
    for lab, n, npm, sample, _ in sorted(ok):
        print(f"OK  {lab:55s} jobs={n:5d} pm={npm:4d}  " + " || ".join(sample)[:300])
    for lab, n, npm, sample, err in sorted(bad):
        print(f"BAD {lab:55s} {err or 'empty'}")

    print("\n=== EXPERIMENTS ===")
    for i, body in enumerate([
        {"query": "product manager", "filters": {}, "page": 1, "locale": "en-gb", "sort": "newest"},
        {"query": "product manager", "filters": {"postingpostLocation": ["postLocation-GBR"]}, "page": 1, "locale": "en-gb", "sort": "newest"},
        {"query": "product manager", "filters": {"locations": ["postLocation-GBR"]}, "page": 1, "locale": "en-gb", "sort": "newest", "format": {"longDate": "MMMM D, YYYY", "mediumDate": "MMM D, YYYY"}},
    ]):
        raw(f"apple-v1-{i}", "https://jobs.apple.com/api/v1/search", data=body, n=700)
    raw("apple-role", "https://jobs.apple.com/api/role/search", data={"query": "product manager", "filters": {"postingpostLocation": ["postLocation-GBR"]}, "page": 1, "locale": "en-gb", "sort": "newest"}, n=400)
    for q in ["", "keywords=product&", "keywords=product%20manager&internal=false&", "q=product%20manager&"]:
        raw(f"booking-{q[:12]}", f"https://jobs.booking.com/api/jobs?{q}page=1&limit=5&sortBy=relevance&descending=false", n=500)
    raw("booking-sub", "https://jobs.booking.com/booking/api/jobs?keywords=product&page=1", n=300)
    print("\n=== LINKEDIN ===")
    try:
        rows = list(sources.linkedin("Senior Product Manager", "United Kingdom"))
        print("linkedin ok", len(rows))
    except Exception as e:  # noqa: BLE001
        print("linkedin", type(e).__name__, e)


if __name__ == "__main__":
    main()
