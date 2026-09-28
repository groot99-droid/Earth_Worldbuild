#!/usr/bin/env python3
"""Labelled contact sheets for the visual review (5 x 8 tiles). Writes data/audit/sheets/sheet-NN.jpg and sheet-NN.json.

    python audit_sheets.py [--only-flagged] [--types person place] [--per 40]
"""
import argparse
import json
from PIL import Image, ImageDraw, ImageFont

from common import DATA, IMAGES, load_json, load_notes

ap = argparse.ArgumentParser()
ap.add_argument("--only-flagged", action="store_true")
ap.add_argument("--types", nargs="*")
ap.add_argument("--per", type=int, default=40)
ap.add_argument("--prefix", default="sheet")
args = ap.parse_args()

audit = load_json(DATA / "audit" / "image-audit.json", {})
titles = {n["id"]: n["title"] for n in load_notes()}
order = ["era", "event", "person", "place", "culture", "technology", "species", "region", "theme", "observer-note", "timeline", "source"]
rels = [r for r, f in audit.items() if not f["ai"] and (not args.types or f["type"] in args.types) and (not args.only_flagged or f["flags"])]
rels.sort(key=lambda r: (order.index(audit[r]["type"]), titles.get(audit[r]["note"], "").lower(), audit[r]["n"]))
out = DATA / "audit" / "sheets"
out.mkdir(parents=True, exist_ok=True)
for old in out.glob(f"{args.prefix}-*"):
    old.unlink()
font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 12)
bold = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 12)
big = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 15)
TW, TH, LH, cols = 240, 150, 52, 5
short = {"dup-exact": "DUP", "dup-near-same-note": "dupN", "dup-near-cross-note": "dupX", "same-file-many-notes": "sameF", "small": "small", "extreme-ratio": "ratio",
         "flat/diagram": "flat", "blank": "blank", "dark": "dark", "off-topic?": "off?", "caption": "cap"}
def clip(s, n): return s if len(s) <= n else s[: n - 1] + "…"
for si in range(0, len(rels), args.per):
    chunk = rels[si: si + args.per]
    rows = (len(chunk) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * TW, rows * (TH + LH)), "white")
    d = ImageDraw.Draw(sheet)
    mapping = {}
    for i, rel in enumerate(chunk):
        f = audit[rel]
        t = IMAGES / "_t" / rel
        im = Image.open(t if t.exists() else IMAGES / rel).convert("RGB")
        im.thumbnail((TW - 4, TH - 4))
        x, y = (i % cols) * TW, (i // cols) * (TH + LH)
        sheet.paste(im, (x + 2 + (TW - 4 - im.size[0]) // 2, y + 2))
        d.rectangle([x, y, x + 30, y + 20], fill="black"); d.text((x + 4, y + 1), f"{i:02d}", fill="yellow", font=big)
        title = titles.get(f["note"], f["note"])
        fl = sorted({short.get(x.split(":")[0].split("(")[0], x.split(":")[0]) for x in f["flags"]})
        d.text((x + 3, y + TH), f"{clip(title, 30)} #{f['n']}", fill="black", font=bold)
        d.text((x + 3, y + TH + 16), clip(f["caption"].replace("AI illustration: ", ""), 40), fill=(60, 60, 60), font=font)
        d.text((x + 3, y + TH + 32), " ".join(fl), fill=(200, 30, 30), font=font)
        d.rectangle([x, y, x + TW - 1, y + TH + LH - 1], outline=(200, 200, 200))
        mapping[f"{i:02d}"] = rel
    n = si // args.per + 1
    sheet.save(out / f"{args.prefix}-{n:02d}.jpg", quality=82)
    (out / f"{args.prefix}-{n:02d}.json").write_text(json.dumps(mapping, indent=0), encoding="utf-8")
print(len(rels), "images ->", (len(rels) + args.per - 1) // args.per, "sheets in", out)
