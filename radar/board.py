"""Turn data/jobs.json into documents for the private Command Center page.

    python radar/board.py OUT_DIR [--known-jd FILE]

Writes OUT_DIR/board.json (the 'board/current' document) and OUT_DIR/jd/<id>.json for job
descriptions not listed in FILE (one doc id per line). Also writes OUT_DIR/batches/NN.json:
ready-made ArtifactData batch `writes` lists (<=50 each) that create the new jd documents.
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODES = [
    (r"london|greater london", "LON"), (r"dublin", "DUB"), (r"\bcork\b", "ORK"), (r"edinburgh", "EDI"),
    (r"manchester", "MAN"), (r"amsterdam", "AMS"), (r"berlin", "BER"), (r"munich|münchen", "MUC"),
    (r"hamburg", "HAM"), (r"frankfurt", "FRA"), (r"zurich|zürich", "ZRH"), (r"paris|clichy", "PAR"),
    (r"madrid", "MAD"), (r"barcelona", "BCN"), (r"lisbon", "LIS"), (r"stockholm", "STO"),
    (r"copenhagen", "CPH"), (r"warsaw|warszawa", "WAW"), (r"krak[oó]w", "KRK"), (r"prague", "PRG"),
    (r"tallinn", "TLL"), (r"budapest", "BUD"), (r"bucharest", "BUH"), (r"luxembourg", "LUX"),
    (r"düsseldorf|dusseldorf", "DUS"), (r"oslo", "OSL"), (r"sydney", "SYD"), (r"melbourne", "MEL"),
    (r"brisbane", "BNE"), (r"bangkok", "BKK"), (r"kuala lumpur|petaling jaya|cyberjaya", "KUL"),
    (r"penang", "PEN"), (r"singapore", "SIN"), (r"bengaluru|bangalore", "BLR"), (r"hyderabad", "HYD"),
    (r"gurugram|gurgaon|noida|delhi", "DEL"), (r"mumbai", "BOM"), (r"pune", "PNQ"), (r"chennai", "MAA"),
]
REGION_CODES = {"UK": "GBR", "Europe": "EUR", "Australia": "AUS", "Thailand": "THA",
                "Malaysia": "MYS", "Singapore": "SIN", "India": "IND"}
ORDER = ["UK", "Europe", "Australia", "Thailand", "Malaysia", "Singapore", "India"]


def code_for(job):
    loc = job.get("location", "").lower()
    hits = [(loc.find(m.group(0)), code) for rx, code in CODES for m in [re.search(rx, loc)] if m]
    # prefer an abroad city over an Indian one when a role lists both
    india = {"BLR", "HYD", "DEL", "BOM", "PNQ", "MAA"}
    for _, pos, code in sorted((code in india, pos, code) for pos, code in hits):
        return code
    return REGION_CODES.get(job["regions"][0], "—")


def doc_id(key):
    return re.sub(r"[^A-Za-z0-9_\-.~:@+]", "-", key)[:200]


def main():
    out = Path(sys.argv[1])
    known = set()
    if "--known-jd" in sys.argv:
        known = set(Path(sys.argv[sys.argv.index("--known-jd") + 1]).read_text().split())
    state = json.loads((ROOT / "data/jobs.json").read_text())
    active = [j for j in state["jobs"].values() if j.get("active")]
    active.sort(key=lambda j: (-j["score"], j["company"]))
    recent = sorted({j["first_seen"] for j in active}, reverse=True)[:2]
    picked = [j for j in active if j["score"] >= 45][:240]
    picked += [j for j in active if j["first_seen"] in recent and j not in picked]
    rows = []
    for j in picked:
        regs = sorted(j["regions"], key=ORDER.index)
        rows.append({"id": doc_id(j["key"]), "company": j["company"], "tier": j["tier"],
                     "title": j["title"], "location": j["location"][:90], "code": code_for(j),
                     "region": regs[0], "url": j["url"], "score": j["score"], "visa": j.get("visa", ""),
                     "posted": (j.get("posted") or "")[:10], "first_seen": j["first_seen"],
                     "level": j["level"], "hasJd": bool(j.get("desc")), "source": j.get("source", "")})
    board = {"updated": state.get("updated"), "total_open": len(active), "jobs": rows}
    (out / "jd").mkdir(parents=True, exist_ok=True)
    (out / "batches").mkdir(exist_ok=True)
    while len(json.dumps(board)) > 240_000:
        board["jobs"] = board["jobs"][:-10]
    (out / "board.json").write_text(json.dumps(board, ensure_ascii=False))
    writes = []
    by_id = {doc_id(j["key"]): j for j in picked}
    for r in board["jobs"]:
        j = by_id[r["id"]]
        if r["id"] in known or not j.get("desc"):
            continue
        f = out / "jd" / f"{r['id']}.json"
        f.write_text(json.dumps({"company": j["company"], "title": j["title"], "url": j["url"],
                                 "text": j["desc"][:3800]}, ensure_ascii=False))
        writes.append({"op": "set", "collection": "jd", "doc_id": r["id"], "file_path": os.path.relpath(f)})
    for i in range(0, len(writes), 45):
        (out / "batches" / f"{i // 45:02d}.json").write_text(json.dumps(writes[i:i + 45], indent=0))
    print(f"board: {len(board['jobs'])} roles ({len(json.dumps(board)) // 1024} KiB); "
          f"new job descriptions: {len(writes)} in {len(range(0, len(writes), 45))} batch file(s)")


if __name__ == "__main__":
    main()
