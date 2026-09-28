"""Run `fetch_source.py claims` (best snippet per check) for a slice of a tier's sources.

Usage: python t3_claims.py TIER LO HI
"""
import subprocess
import sys

import _paths
import fetch_source as fs

tier, lo, hi = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
q = fs.load_queue()
for t in sorted(x for x, e in q.items() if e["tier"] == tier)[lo:hi]:
    if not fs.cache_paths(fs.pick_slug(t))[0].exists():
        print(f"\n######## {t}: NOT CACHED")
        continue
    out = subprocess.run([sys.executable, str(_paths.TOOLS / "fetch_source.py"), "claims", t, "--top", "1", "--width", "190"],
                         capture_output=True, text=True, encoding="utf-8").stdout
    print(f"\n######## {t}\n" + "\n".join(l for l in out.split("\n") if l.strip()))
