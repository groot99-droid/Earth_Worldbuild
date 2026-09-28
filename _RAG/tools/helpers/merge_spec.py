"""Merge the builder output (tierN_auto.json) and the hand-written extras (tierN_extra.json) into one apply_patch spec.

Usage: python merge_spec.py TIER   -> specs/tierN.json
source_updates from the extras (for example the generic homepage note) are appended to the builder's.
"""
import json
import sys

import _paths

tier = int(sys.argv[1])
auto = json.loads((_paths.WORK / f"tier{tier}_auto.json").read_text(encoding="utf-8"))
extra = json.loads((_paths.WORK / f"tier{tier}_extra.json").read_text(encoding="utf-8"))
spec = {"date": auto["date"],
        "sources_new": extra.get("sources_new", []),
        "source_updates": auto["source_updates"] + extra.get("source_updates", []),
        "notes": extra.get("notes", []),
        "discrepancies": extra.get("discrepancies", [])}
out = _paths.WORK / f"tier{tier}.json"
out.write_text(json.dumps(spec, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"{out.name}: {len(spec['sources_new'])} new sources, {len(spec['source_updates'])} source updates, "
      f"{len(spec['notes'])} note patches, {len(spec['discrepancies'])} discrepancies")
