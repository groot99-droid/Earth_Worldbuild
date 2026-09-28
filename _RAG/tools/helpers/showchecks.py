"""Print a note's sources, fact_checks, Facts section and Open Questions.

Usage: python showchecks.py "Note Title" ["Another Title" ...]
"""
import re
import sys

import _paths  # noqa: F401
from vault import iter_notes, parse_note

names = sys.argv[1:]
for p in iter_notes():
    if p.stem in names:
        fm, body = parse_note(p)
        print("=====", p.stem, "| status", fm.get("status"), "| confidence", fm.get("confidence"))
        print("sources:", fm.get("sources"))
        for x in fm.get("fact_checks") or []:
            print("  FC:", x)
        m = re.search(r"## Facts\n(.*?)(?=\n## )", body, re.S)
        print("-- Facts:")
        print(m.group(1).strip() if m else "(none)")
        for sec in ("Open Questions",):
            m = re.search(rf"## {sec}\n(.*?)(?=\n## |\Z)", body, re.S)
            print(f"-- {sec}:")
            print(m.group(1).strip() if m else "(none)")
