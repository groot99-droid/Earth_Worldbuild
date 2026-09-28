#!/usr/bin/env python3
"""Create a 480 px thumbnail for every image: images/_t/<type>/<slug>/<n>.jpg (incremental).

Cards and the timeline use the thumbnails (about 25-40 KB); the note panel and lightbox use the 960 px originals.
    python make_thumbs.py [--force]
"""
from __future__ import annotations

import sys

from PIL import Image

from common import IMAGES

MAX_SIDE = 480


def main() -> int:
    force = "--force" in sys.argv
    made = skipped = bad = 0
    tdir = IMAGES / "_t"
    for src in sorted(IMAGES.rglob("*.jpg")):
        if tdir in src.parents:
            continue
        dest = tdir / src.relative_to(IMAGES)
        if dest.exists() and not force and dest.stat().st_mtime >= src.stat().st_mtime:
            skipped += 1
            continue
        try:
            with Image.open(src) as im:
                im = im.convert("RGB")
                im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
                dest.parent.mkdir(parents=True, exist_ok=True)
                im.save(dest, "JPEG", quality=76, optimize=True, progressive=True)
            made += 1
        except Exception as exc:  # noqa: BLE001
            bad += 1
            print(f"cannot thumbnail {src}: {exc}", file=sys.stderr)
    print(f"thumbnails: {made} made, {skipped} up to date, {bad} failed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
