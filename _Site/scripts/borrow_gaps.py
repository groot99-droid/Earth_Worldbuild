#!/usr/bin/env python3
"""Give non-source notes that ended with no image of their own a related note's image (flagged as borrowed).

Uses fetch_images.borrow(): the donor must be a note this one links to; least-reused, most-linked donor first.
    python borrow_gaps.py
"""
import fetch_images as fi
from common import DATA, load_json, load_notes

fi.BORROW_TYPES = {"observer-note", "timeline", "theme", "region", "event", "era", "place", "culture", "technology", "species", "person"}
notes = load_notes()
state = fi.State()
plan = load_json(DATA / "image-plan.json", {})
byid = {n["id"]: n for n in notes}
before = sum(1 for c in state.credits.values() if c.get("borrowed_from"))
fi.borrow(state, notes, byid, plan)
after = sum(1 for c in state.credits.values() if c.get("borrowed_from"))
fi.write_gaps(state, notes, plan)
print(f"borrowed images: {before} -> {after}")
