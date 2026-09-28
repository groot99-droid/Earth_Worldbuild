"""Side-by-side: each source's abstract (or opening text) and every fact_check that cites it.

Usage: python t2_report.py TIER LO HI [WIDTH]   (LO:HI slices the tier's titles, sorted)
"""
import json
import re
import sys

import _paths  # noqa: F401
import fetch_source as fs
from vault import iter_notes, parse_note

tier = int(sys.argv[1])
lo, hi = int(sys.argv[2]), int(sys.argv[3])
width = int(sys.argv[4]) if len(sys.argv) > 4 else 1100
q = fs.load_queue()
titles = sorted(t for t, e in q.items() if e["tier"] == tier)[lo:hi]
notes = {p: parse_note(p) for p in iter_notes()}
for t in titles:
    slug = fs.pick_slug(t)
    tp, mp = fs.cache_paths(slug)
    print("=" * 100)
    if not mp.exists() or not tp.exists():
        print(f"## {t}\n   (no text)")
    else:
        m = json.loads(mp.read_text(encoding="utf-8"))
        text = tp.read_text(encoding="utf-8")
        mm = re.search(r"## Abstract\n(.*?)(?=\n## |\Z)", text, re.S)
        if mm:
            body = mm.group(1).strip()
        else:
            body = re.sub(r"^\[[^\]]*\][^\n]*\n", "", text, flags=re.M)
            body = "\n".join(l for l in body.split("\n") if len(l) > 120)[:width]
        print(f"## {t}  [{m['level']} via {m['route']}, {m['chars']:,} chars]")
        print("   ABSTRACT/OPENING:", re.sub(r"\s+", " ", body)[:width])
    for p, (fm, body) in notes.items():
        if fm.get("type") == "source":
            continue
        for x in fm.get("fact_checks") or []:
            mm = re.search(r"\[([^\]]+)\]\s*$", str(x))
            if mm and t in [s.strip() for s in mm.group(1).split(";")]:
                print(f"   CHECK in [{p.stem}]: {re.sub(r'^[0-9-]+: ', '', str(x))[:420]}")
        if any(f"[[{t}]]" in str(s) for s in (fm.get("sources") or [])) and not any(
                t in str(x) for x in (fm.get("fact_checks") or [])):
            print(f"   (listed in sources of [{p.stem}] with no check)")
