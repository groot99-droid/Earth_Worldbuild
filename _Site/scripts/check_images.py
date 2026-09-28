#!/usr/bin/env python3
"""Static image gate (site/_hero holds the AI hero banner, credited in data/hero.json). Fails (exit 1) if any referenced image cannot be shown, or lacks a credit.

Checks: every credit's file exists, opens and fully decodes; short side >= 180 px and long side >= 300 px;
no file over 700 KB; a 480 px thumbnail exists; licence and source are recorded (AI images: model); no orphan files;
every image path in data/notes-*.json exists; and reports (does not fail on) exact duplicates across notes.

    python check_images.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict

from PIL import Image

from common import DATA, IMAGES, load_json

MAX_BYTES = 700_000


def main() -> int:
    credits = load_json(DATA / "image-credits.json", {})
    bad: list[str] = []
    seen: dict[str, list[str]] = defaultdict(list)
    for rel, c in sorted(credits.items()):
        p = IMAGES / rel
        if not p.exists():
            bad.append(f"missing file {rel}")
            continue
        try:
            with Image.open(p) as im:
                im.load()
                w, h = im.size
        except Exception as exc:  # noqa: BLE001
            bad.append(f"cannot decode {rel}: {exc}")
            continue
        if min(w, h) < 180 or max(w, h) < 300:
            bad.append(f"too small {rel}: {w}x{h}")
        if p.stat().st_size > MAX_BYTES:
            bad.append(f"too heavy {rel}: {p.stat().st_size // 1024} KB")
        if not (IMAGES / "_t" / rel).exists():
            bad.append(f"no thumbnail for {rel} (run make_thumbs.py)")
        if c.get("ai"):
            if not (c.get("model") and c.get("prompt")):
                bad.append(f"AI image without model/prompt {rel}")
        else:
            if not c.get("license"):
                bad.append(f"no licence {rel}")
            if not (c.get("source") or c.get("borrowed_from")):
                bad.append(f"no source {rel}")
        if not c.get("borrowed_from"):
            seen[hashlib.md5(p.read_bytes()).hexdigest()].append(rel)
    on_disk = {p.relative_to(IMAGES).as_posix() for p in IMAGES.rglob("*.jpg") if p.relative_to(IMAGES).parts[0] not in ("_t", "_hero")}
    hero = load_json(DATA / "hero.json", None)
    if hero and not ((IMAGES / "_hero" / "hero.jpg").exists() and hero.get("ai") and hero.get("model") and hero.get("prompt")):
        bad.append("hero banner missing or without AI credit")
    for orphan in sorted(on_disk - set(credits)):
        bad.append(f"orphan file without credit {orphan}")
    for f in DATA.glob("notes-*.json"):
        if f.name == "notes-index.json":
            continue
        for nid, d in json.loads(f.read_text(encoding="utf-8")).items():
            for im in d.get("images", []):
                if not (DATA.parent / im["src"]).exists():
                    bad.append(f"{nid}: image path missing {im['src']}")
    dupes = [v for v in seen.values() if len(v) > 1]
    print(f"{len(credits)} credited images, {len(on_disk)} files, {len(dupes)} exact-duplicate groups across notes (informational)")
    for b in bad[:60]:
        print("  FAIL:", b)
    print("check_images:", f"FAILED ({len(bad)})" if bad else "OK")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
