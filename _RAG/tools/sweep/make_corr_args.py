"""python make_corr_args.py <factcheck workflow .output> <corr.json out>
Writes {title: [discrepancies]} to corr.json and prints the Workflow args JSON for corrections_wf.js."""
import json
import sys

src, out = sys.argv[1], sys.argv[2]
raw = json.load(open(src, encoding="utf-8"))
res = raw["result"] if isinstance(raw, dict) else raw
corr = {r["title"]: r["corrections"] for r in res if r.get("corrections")}
json.dump(corr, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
items = [{"title": r["title"], "path": r["_path"]} for r in res if r.get("corrections")]
print(json.dumps({"file": out.replace("/", "\\"), "items": items}, ensure_ascii=False))
