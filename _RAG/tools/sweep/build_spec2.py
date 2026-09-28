"""Turn a factcheck workflow result (JSON with "result": [...]) into an apply_patch spec.

python build_spec2.py <workflow .output file> <spec out.json> [--no-verify]
Prints corrections and problems for human review.
"""
import json
import re
import sys
import urllib.request
import urllib.error

SRC, OUT = sys.argv[1], sys.argv[2]
VERIFY = "--no-verify" not in sys.argv
UA = "EarthChronicleVault/1.0 (personal history vault fact-check; contact via vault owner)"


def fix_quotes(s):
    return re.sub(r'"([^"]*)"', r"'\1'", s).replace('"', "'")


def url_status(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


raw = json.load(open(SRC, encoding="utf-8"))
results = raw["result"] if isinstance(raw, dict) else raw

sources = {}
for r in results:
    for s in r.get("sources_new", []):
        sources.setdefault(s["title"], dict(s))

bad_sources = set()
if VERIFY:
    for t, s in sources.items():
        st = url_status(s["url"])
        if st == 404:
            bad_sources.add(t)
            print(f"DROP source (404): {t} {s['url']}")
        elif st not in (200, 403, 429, 0):
            print(f"NOTE source status {st}: {t} {s['url']}")

for t, s in sources.items():
    s["citation"] = fix_quotes(s["citation"])
    s["title"] = fix_quotes(s["title"]) if '"' in s["title"] else s["title"]
    if s.get("access") == "reference-text" and re.search(r"snippet|403|search result", s.get("access_route", ""), re.I):
        s["access"] = "summary-only"
    s.setdefault("read_on", "2026-09-27")

notes = []
for r in results:
    title = r["title"]
    checks = []
    for c in r.get("checks", []):
        c = fix_quotes(c)
        m = re.search(r"\[([^\]]+)\]$", c)
        if not m:
            print(f"DROP check (no trailing [Source]) for {title}: {c[:70]}")
            continue
        cited = [x for x in m.group(1).split("; ") if x not in bad_sources]
        if not cited:
            print(f"DROP check (all sources bad) for {title}: {c[:70]}")
            continue
        c = c[: m.start()] + "[" + "; ".join(cited) + "]"
        checks.append(c)
    if len(checks) < 2:
        print(f"SKIP note {title}: only {len(checks)} valid checks")
        continue
    notes.append({"note": title, "checks": checks})
    for corr in r.get("corrections", []):
        print(f"CORRECTION [{title}]: {corr}")

keep_sources = [s for t, s in sources.items() if t not in bad_sources]
json.dump({"date": "2026-09-27", "sources_new": keep_sources, "notes": notes},
          open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"wrote {OUT}: {len(keep_sources)} sources, {len(notes)} notes")
