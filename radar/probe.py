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


def main():
    ok, bad = [], []
    with cf.ThreadPoolExecutor(12) as ex:
        for lab, n, npm, sample, err in ex.map(run, CANDIDATES):
            (bad if err or n == 0 else ok).append((lab, n, npm, sample, err))
    print("\n=== WORKING ===")
    for lab, n, npm, sample, _ in sorted(ok):
        print(f"OK  {lab:55s} jobs={n:5d} pm={npm:4d}  " + " || ".join(sample)[:400])
    print("\n=== FAILED / EMPTY ===")
    for lab, n, npm, sample, err in sorted(bad):
        print(f"BAD {lab:55s} {err or 'empty'}")

    print("\n=== LINKEDIN GUEST ===")
    for loc in ["United Kingdom", "Thailand"]:
        try:
            rows = list(sources.linkedin("Senior Product Manager", loc))
            print(f"OK  linkedin {loc}: {len(rows)} cards")
            for r in rows[:5]:
                print("   ", json.dumps(r)[:300])
            if rows:
                d = sources.linkedin_desc(rows[0]["id"])
                print(f"    desc chars={len(d)} :: {d[:200]!r}")
        except Exception as e:  # noqa: BLE001
            print(f"BAD linkedin {loc}: {type(e).__name__}: {e}")
            traceback.print_exc()

    print("\n=== GOOGLE RAW ===")
    try:
        src = sources.http("https://www.google.com/about/careers/applications/jobs/results/?"
                           "q=%22product%20manager%22&location=United%20Kingdom")
        i = src.find("AF_initDataCallback({key: 'ds:1'")
        print("len", len(src), "ds1 at", i)
        print(src[i:i + 3000])
    except Exception as e:  # noqa: BLE001
        print("google raw failed", e)

    print("\n=== MICROSOFT legacy ===")
    try:
        print(sources.http("https://gcsservices.careers.microsoft.com/search/api/v1/search?"
                           "q=product%20manager&lc=United%20Kingdom&l=en_us&pg=1&pgSz=20&o=Recent")[:1500])
    except Exception as e:  # noqa: BLE001
        print("ms legacy failed", e)
    try:
        print(sources.http("https://apply.careers.microsoft.com/api/pcsx/search?"
                           "domain=microsoft.com&query=product%20manager&location=United%20Kingdom")[:1500])
    except Exception as e:  # noqa: BLE001
        print("ms pcsx failed", e)

    print("\n=== NTFY reachability ===")
    try:
        print(sources.http("https://ntfy.sh/v1/health")[:200])
    except Exception as e:  # noqa: BLE001
        print("ntfy failed", e)


if __name__ == "__main__":
    main()
