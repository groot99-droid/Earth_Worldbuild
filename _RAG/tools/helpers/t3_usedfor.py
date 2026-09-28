"""Each source note's 'What It Is Used For' claims matched against its cached text; prints only atoms with a missing key.

Usage: python t3_usedfor.py TIER
"""
import re
import sys

import _paths  # noqa: F401
import fetch_source as fs

tier = int(sys.argv[1])
q = fs.load_queue()
notes = fs.source_notes()
for t in sorted(x for x, e in q.items() if e["tier"] == tier):
    slug = fs.pick_slug(t)
    if not fs.cache_paths(slug)[0].exists():
        print(f"## {t}: NOT CACHED")
        continue
    text, meta = fs.load_matchable(slug)
    tf = fs.fold(text)
    used = re.search(r"## What It Is Used For\s*(.*?)(?=\n## |\Z)", notes[t][2], re.S).group(1).strip()
    bad = []
    for atom in [a.strip() for a in re.split(r";|(?<=\.)\s+(?=[A-Z])|,\s+and\s+|, ", used) if a.strip()]:
        keys = fs.claim_keys(atom)
        if not keys:
            continue
        hits = fs.count_hits(keys, tf)
        miss = [k for _, k in keys if not hits[k]]
        if miss:
            bad.append(f"      - {atom[:120]}  MISSING: {', '.join(miss)}")
    print(f"## {t} [{meta['chars']:,} chars]" + ("" if not bad else "\n" + "\n".join(bad)))
