"""Print the passages of cached sources that match given terms.

Reads stdin lines of the form  Source title||term1|term2|...  (terms are regexes; '#' starts a comment line) and
prints, for each term, the number of matching segments of that source's cached text and the first two snippets.

Usage: printf 'Britannica on Timur||1370|Husayn\n' | python probe.py
"""
import re
import sys

import _paths  # noqa: F401
import fetch_source as fs

width = 230
top = 2
cache = {}
for line in sys.stdin.read().splitlines():
    if not line.strip() or line.startswith("#"):
        continue
    src, terms = line.strip("\r").split("||", 1)
    if src not in cache:
        text, meta = fs.load_matchable(fs.pick_slug(src))
        segs = fs.segments(text)
        cache[src] = (segs, [fs.fold(s) for s in segs])
    segs, sf = cache[src]
    for term in [x.strip() for x in terms.split("|")]:
        rx = re.compile(fs.fold(term), re.I)
        hits = [segs[i] for i, s in enumerate(sf) if rx.search(s)]
        print(f"--- [{src.replace('Britannica on ', '')}] '{term}': {len(hits)} hit(s)")
        for h in hits[:top]:
            m = rx.search(fs.fold(h))
            st = max(0, (m.start() if m else 0) - 90)
            print("    > " + re.sub(r"\s+", " ", h)[st:st + width])
