"""Shared helpers for the Earth Chronicle site scripts. Reuses _RAG/vault.py without modifying it."""
from __future__ import annotations

import json
import re
import sys
import time
import unicodedata
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
ROOT = SITE.parent
sys.path.insert(0, str(ROOT / "_RAG"))
import vault  # noqa: E402  (reused, not modified)

DATA = SITE / "data"
IMAGES = SITE / "images"
CACHE = DATA / "cache"          # raw API responses, safe to delete

# Scope: everything except 00_Meta and _Templates (vault.SKIP_DIRS already drops _Templates/_RAG/Art-Talk-main).
EXCLUDE_TOP = {"00_Meta", "08_Canvas_Maps"}

CEILING = {
    "era": 5, "event": 5,
    "place": 4, "region": 4, "culture": 4,
    "person": 3, "theme": 3, "species": 3, "technology": 3,
    "observer-note": 1, "timeline": 1, "source": 1,
}
CONF = {"high": 3, "medium": 2, "low": 1}


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "note"


def load_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def save_json(path: Path, obj, indent=1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, indent=indent)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    for attempt in range(8):            # OneDrive / antivirus can briefly lock the target on Windows
        try:
            tmp.replace(path)
            return
        except PermissionError:
            time.sleep(0.5 * (attempt + 1))
    path.write_text(text, encoding="utf-8")
    tmp.unlink(missing_ok=True)


def load_notes():
    """Return a list of dicts: id, title, type, path, fm, body, out (resolved link ids). Adds inbound counts."""
    notes = []
    for p in vault.iter_notes():
        rel = p.relative_to(ROOT)
        if rel.parts[0] in EXCLUDE_TOP:
            continue
        fm, body = vault.parse_note(p)
        typ = fm.get("type")
        if typ not in CEILING:
            continue
        notes.append({"title": str(fm.get("title") or p.stem), "type": typ, "path": rel.as_posix(), "fm": fm, "body": body, "stem": p.stem})
    seen: dict[str, int] = {}
    for n in notes:
        s = slugify(n["title"])
        seen[s] = seen.get(s, 0) + 1
        n["slug"] = s if seen[s] == 1 else f"{s}-{seen[s]}"
        n["id"] = f'{n["type"]}/{n["slug"]}'
    by_title = {}
    for n in notes:
        by_title[n["stem"].lower()] = n
        by_title.setdefault(n["title"].lower(), n)
    for n in notes:
        targets = vault.links_in(n["body"]) + vault.links_in(n["fm"].get("related")) + vault.links_in(n["fm"].get("era")) + vault.links_in(n["fm"].get("region"))
        out = []
        for t in targets:
            m = by_title.get(t.lower())
            if m and m is not n and m["id"] not in out:
                out.append(m["id"])
        n["out"] = out
        n["unresolved"] = sorted({t for t in targets if t.lower() not in by_title})
    byid = {n["id"]: n for n in notes}
    for n in notes:
        n["inb"] = []
    for n in notes:
        for t in n["out"]:
            byid[t]["inb"].append(n["id"])
    return notes
