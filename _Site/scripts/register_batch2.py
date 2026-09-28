#!/usr/bin/env python3
"""Register the second Higgsfield batch: one new lead (AI) image for each of the 58 notes that came out of the
image audit with no image, or only weak/not-lead images. Existing images (if any) are pushed back one position.

    python register_batch2.py <dir-of-00.png..57.png> <ids.json> <prompts.json> <jobids.json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from ai_assets import DATE, MODEL, STYLE, _shift_up
from common import DATA, IMAGES, load_json, save_json
from fetch_images import prep_image, save_img


def main() -> int:
    src_dir, ids_path, prompts_path, jobids_path = (Path(a) for a in sys.argv[1:5])
    ids = json.loads(ids_path.read_text(encoding="utf-8"))
    prompts = json.loads(prompts_path.read_text(encoding="utf-8"))["prompts"]
    jobids = json.loads(jobids_path.read_text(encoding="utf-8"))
    credits = load_json(DATA / "image-credits.json", {})
    done = 0
    for i, nid in enumerate(ids):
        f = src_dir / f"{i:02d}.png"
        if not f.exists():
            print(f"missing {f}")
            continue
        img = prep_image(f.read_bytes())
        typ, slug = nid.split("/")
        rel_dir = f"{typ}/{slug}"
        job = jobids[str(i)]
        if any(c.get("job_id") == job for c in credits.values()):
            continue
        _shift_up(rel_dir)
        credits = load_json(DATA / "image-credits.json", {})
        rel = f"{rel_dir}/1.jpg"
        save_img(img, IMAGES / rel)
        credits[rel] = {"ai": True, "model": MODEL, "prompt": STYLE + prompts[nid], "job_id": job, "generated": DATE,
                         "caption": "AI illustration: " + prompts[nid].split(",")[0].split(".")[0].capitalize(),
                         "license": "AI-generated image (no third-party source); Higgsfield terms apply",
                         "license_url": None, "source": None, "author": None, "via": "higgsfield-ai",
                         "w": img.size[0], "h": img.size[1]}
        save_json(DATA / "image-credits.json", credits)
        done += 1
    print(f"registered {done} AI images")
    return 0


if __name__ == "__main__":
    sys.exit(main())
