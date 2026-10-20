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

GH = ["stripe", "airbnb", "monzo", "deliveroo", "n26", "adyen", "datadog", "cloudflare",
      "databricks", "mongodb", "elastic", "figma", "miro", "realtimeboardglobal", "celonis",
      "getyourguide", "skyscanner", "checkoutcom", "coinbase", "intercom", "hubspot",
      "anthropic", "dropbox", "pinterest", "reddit", "twilio", "okta", "gitlab", "rippling",
      "deepmind", "canva", "agoda", "grab", "wise", "transferwise", "airwallex", "cultureamp",
      "booking", "bookingcom", "klarna", "glovo", "traderepublic", "pleo", "mollie",
      "hellofresh", "trivago", "spotify", "xero", "safetyculture", "lmwn", "traveloka",
      "zalando", "personio", "bolt", "wayve", "synthesia", "postman", "doordash", "instacart",
      "remote", "taxfix", "contentful", "sumup", "gocardless", "marshmallow", "cleo", "tide",
      "paddle", "multiverse", "onfido", "truelayer", "snyk", "thoughtmachine", "zopa",
      "employmenthero", "linktree", "carousell", "xendit", "ninjavan", "shopback", "2c2p"]
LEVER = ["palantir", "spotify", "mistral", "lmwn", "binance", "kraken", "gojek", "traveloka",
         "safetyculture", "canva", "klarna", "grab", "airwallex", "netflix", "shopback",
         "carousell", "ninjavan", "xendit", "employmenthero", "linktree", "ledger",
         "cultureamp", "atlassian", "wise", "zeller", "blinkist"]
ASHBY = ["notion", "openai", "deel", "ramp", "linear", "synthesia", "elevenlabs", "cohere",
         "posthog", "airwallex", "rippling", "revolut", "wise", "multiverse", "lovable",
         "n8n", "pennylane", "qonto", "alan", "mistral", "perplexity", "harvey"]
SR = ["Visa", "ServiceNow", "DeliveryHero", "Canva", "Wise", "Grab", "BoschGroup",
      "BookingCom", "Booking", "Ubisoft", "LinkedIn3", "Sky", "Experian", "Equinix",
      "Lazada", "Shopee", "foodpanda", "Agoda", "Atlassian"]
WD = [("salesforce.wd12.myworkdayjobs.com", "salesforce", "External_Career_Site"),
      ("adobe.wd5.myworkdayjobs.com", "adobe", "external_experienced"),
      ("paypal.wd1.myworkdayjobs.com", "paypal", "jobs"),
      ("mastercard.wd1.myworkdayjobs.com", "mastercard", "CorporateCareers"),
      ("nvidia.wd5.myworkdayjobs.com", "nvidia", "NVIDIAExternalCareerSite"),
      ("workday.wd5.myworkdayjobs.com", "workday", "Workday"),
      ("autodesk.wd1.myworkdayjobs.com", "autodesk", "Ext"),
      ("expedia.wd108.myworkdayjobs.com", "expedia", "search"),
      ("bookingholdings.wd5.myworkdayjobs.com", "bookingholdings", "BookingHoldings"),
      ("klarna.wd3.myworkdayjobs.com", "klarna", "Klarna_Careers"),
      ("ebay.wd5.myworkdayjobs.com", "ebay", "apply"),
      ("visa.wd5.myworkdayjobs.com", "visa", "Visa"),
      ("wise.wd3.myworkdayjobs.com", "wise", "Wise_Careers"),
      ("intuit.wd1.myworkdayjobs.com", "intuit", "Intuit"),
      ("zendesk.wd1.myworkdayjobs.com", "zendesk", "zendesk"),
      ("thomsonreuters.wd5.myworkdayjobs.com", "thomsonreuters", "External_Career_Site"),
      ("hp.wd5.myworkdayjobs.com", "hp", "ExternalCareerSite"),
      ("cisco.wd5.myworkdayjobs.com", "cisco", "Cisco_Careers"),
      ("dell.wd1.myworkdayjobs.com", "dell", "External"),
      ("spgi.wd5.myworkdayjobs.com", "spgi", "SPGI_Careers")]

EU = ["United Kingdom", "Ireland", "Netherlands", "Germany", "Australia", "Singapore",
      "Malaysia", "Thailand", "India"]

CANDIDATES = (
    [{"ats": "greenhouse", "token": t} for t in GH]
    + [{"ats": "lever", "token": t} for t in LEVER]
    + [{"ats": "lever", "token": t, "eu": True} for t in LEVER]
    + [{"ats": "ashby", "token": t} for t in ASHBY]
    + [{"ats": "smartrecruiters", "token": t} for t in SR]
    + [{"ats": "workday", "host": h, "tenant": t, "site": s} for h, t, s in WD]
    + [{"ats": "amazon", "countries": ["GBR", "IRL", "DEU", "AUS", "SGP", "IND"]},
       {"ats": "google", "locations": ["United Kingdom", "Singapore", "Australia"]},
       {"ats": "microsoft", "locations": ["United Kingdom", "Ireland", "Australia", "India"]},
       {"ats": "eightfold", "host": "explore.jobs.netflix.net", "domain": "netflix.com"},
       {"ats": "uber"},
       {"ats": "atlassian"}]
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

    print("\n=== EXPERIMENTS: companies without a known public API ===")
    raw("apple-html", "https://jobs.apple.com/en-gb/search?search=product%20manager&sort=newest&location=united-kingdom-GBR",
        find="hydration")
    raw("apple-api", "https://jobs.apple.com/api/v1/search", data={"query": "product manager", "filters": {"locations": ["postLocation-GBR"]}, "page": 1, "locale": "en-gb", "sort": "newest"}, find="")
    raw("meta-html", "https://www.metacareers.com/jobs?q=product%20manager&offices[0]=London%2C%20UK", find="Product Manager")
    raw("revolut", "https://www.revolut.com/careers/?query=product%20owner", find="__NEXT_DATA__")
    raw("revolut-api", "https://www.revolut.com/api/careers/positions", find="")
    raw("booking-jibe", "https://jobs.booking.com/api/jobs?keywords=product%20manager&page=1", find="")
    raw("booking-careers", "https://jobs.booking.com/booking/jobs?keywords=product%20manager", find="Product Manager")
    raw("zalando", "https://jobs.zalando.com/api/jobs/?limit=20&offset=0&query=product%20manager", find="")
    raw("uber-html", "https://www.uber.com/global/en/careers/list/?query=product%20manager", find="Product Manager")
    raw("canva-sr-titles", "https://api.smartrecruiters.com/v1/companies/Canva/postings?limit=100", find="product", n=600)
    raw("shopee", "https://careers.shopee.sg/api/v1/job/list?keyword=product%20manager&limit=20&offset=0", find="")
    for site in ["Klarna", "klarna", "External", "Klarna_Careers_External"]:
        raw(f"klarna-wd-{site}", f"https://klarna.wd3.myworkdayjobs.com/wday/cxs/klarna/{site}/jobs",
            data={"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": "product"}, find="", n=300)
    for t in ["skyscanner", "linemanwongnai", "lmwn", "canva", "klarna", "revolut", "uber", "booking", "zalando", "shopee"]:
        for ats, url in [("ashby", f"https://api.ashbyhq.com/posting-api/job-board/{t}"),
                         ("lever", f"https://api.lever.co/v0/postings/{t}?mode=json&limit=1"),
                         ("gh", f"https://boards-api.greenhouse.io/v1/boards/{t}/jobs")]:
            try:
                src = sources.http(url)
                print(f"OK  {ats}:{t} len={len(src)} {src[:120]!r}")
            except Exception as e:  # noqa: BLE001
                pass
    print("\n=== LINKEDIN ===")
    try:
        rows = list(sources.linkedin("Senior Product Manager", "United Kingdom"))
        print("linkedin ok", len(rows))
    except Exception as e:  # noqa: BLE001
        print("linkedin", type(e).__name__, e)


if __name__ == "__main__":
    main()
