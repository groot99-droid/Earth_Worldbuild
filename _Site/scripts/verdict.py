#!/usr/bin/env python3
"""Record visual-review verdicts: python verdict.py <sheet> "<tile>=<code>:<reason>" ...
codes: D duplicate | O off-topic or misleading | Q unusable quality | W weak (keep, not as lead) | L not lead material (map/diagram/flag) | X wrong subject (person/place mix-up)"""
import json, sys
from pathlib import Path
from common import DATA
sheet = sys.argv[1].zfill(2)
mp = json.loads((DATA / "audit" / "sheets" / f"sheet-{sheet}.json").read_text(encoding="utf-8"))
vf = DATA / "audit" / "verdicts.json"
v = json.loads(vf.read_text(encoding="utf-8")) if vf.exists() else {}
for a in sys.argv[2:]:
    tile, rest = a.split("=", 1)
    code, _, reason = rest.partition(":")
    rel = mp[tile.zfill(2)]
    v[rel] = {"code": code, "reason": reason}
vf.write_text(json.dumps(v, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"sheet {sheet}: {len(sys.argv) - 2} verdicts recorded; total {len(v)}")
