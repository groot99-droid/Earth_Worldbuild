"""Compact table of fetch results for a tier: level, route, size, and which hosts refused.

Usage: python status_table.py TIER
"""
import json
import sys
from collections import Counter

import _paths  # noqa: F401
import fetch_source as fs

tier = int(sys.argv[1]) if len(sys.argv) > 1 else 2
q = fs.load_queue()
rows = []
for t, e in sorted(q.items()):
    if e["tier"] != tier:
        continue
    slug = fs.pick_slug(t)
    mp = fs.cache_paths(slug)[1]
    if not mp.exists():
        rows.append((t, "-", "-", 0, "not fetched"))
        continue
    m = json.loads(mp.read_text(encoding="utf-8"))
    bad = sorted({f"{a['host'].split('.')[-2] if a.get('host') else '?'}:{a['status']}" for a in m.get("attempts", []) if a.get("status") not in (200,)})
    rows.append((t, m.get("level") or "FAILED", (m.get("route") or "-")[:34], m.get("chars", 0), " ".join(bad)))
print(Counter(r[1] for r in rows))
for r in rows:
    print(f"{r[1]:14} {r[2]:34} {r[3]:>7}  {r[0][:70]}  {r[4]}")
