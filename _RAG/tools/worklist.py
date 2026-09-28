"""Live worklist for the fact-check/image sweep. Recompute every run, never cache.

Usage:
  python _RAG/tools/worklist.py factcheck [--type TYPE] [--limit N]   # notes missing fact_checks
  python _RAG/tools/worklist.py images [--type TYPE]                  # content notes with zero credited image
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RAG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAG))
from vault import VAULT_ROOT, iter_notes, parse_note  # noqa: E402

ENTITY_TYPES = ("event", "person", "place", "culture", "species", "technology", "era", "region")
IMAGE_TYPES = ("person", "place", "technology", "species")
SITE_DATA = VAULT_ROOT / "_Site" / "data"


def factcheck_gaps(only_type: str | None = None):
    out = []
    for p in iter_notes():
        fm, _ = parse_note(p)
        t = fm.get("type")
        if t not in ENTITY_TYPES:
            continue
        if only_type and t != only_type:
            continue
        if fm.get("fact_checks"):
            continue
        out.append({"type": t, "title": fm.get("title", p.stem), "path": str(p.relative_to(VAULT_ROOT)),
                    "mtime": p.stat().st_mtime})
    out.sort(key=lambda r: (r["type"], r["mtime"]))
    return out


def image_gaps(only_type: str | None = None):
    plan_path = SITE_DATA / "image-plan.json"
    credits_path = SITE_DATA / "image-credits.json"
    if not plan_path.exists() or not credits_path.exists():
        print("Run `python plan_images.py` in _Site/scripts first (image-plan.json missing/stale).", file=sys.stderr)
        return []
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    credits = json.loads(credits_path.read_text(encoding="utf-8"))
    # credits keys are "<type>/<slug>/<n>.jpg|png"; derive the note id (type/slug)
    have_ids = {k.rsplit("/", 1)[0] for k in credits}
    out = []
    for note_id, spec in plan.items():
        t = spec.get("type") if isinstance(spec, dict) else None
        if t is None:
            t = note_id.split("/", 1)[0]
        if t not in IMAGE_TYPES:
            continue
        if only_type and t != only_type:
            continue
        if note_id in have_ids:
            continue
        out.append({"id": note_id, "type": t})
    out.sort(key=lambda r: (r["type"], r["id"]))
    return out


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("factcheck", "images"):
        print(__doc__)
        return 2
    mode = sys.argv[1]
    only_type = None
    limit = None
    args = sys.argv[2:]
    for i, a in enumerate(args):
        if a == "--type" and i + 1 < len(args):
            only_type = args[i + 1]
        if a == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])
    rows = factcheck_gaps(only_type) if mode == "factcheck" else image_gaps(only_type)
    if limit:
        rows = rows[:limit]
    for r in rows:
        print(json.dumps(r, ensure_ascii=False))
    print(f"# total: {len(rows)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
