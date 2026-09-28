#!/usr/bin/env python3
"""Audit every credited image: duplicates, quality, and whether it plausibly belongs to its note.

Automated signals (a human/visual pass decides; nothing is deleted here):
  dup-exact / dup-near   same pixels or near-identical (dHash) in the same note or across notes
  same-file              the same Commons/Met/NASA file used by several notes
  small / extreme-ratio  low resolution or a strip-like aspect
  flat / diagram         few dominant colours (map, flag, chart, seal, logo, scan)
  blank / dark           almost no detail
  caption:<kind>         the credit caption says flag / coat of arms / logo / map / chart / cover / page / signature ...
  off-topic?             neither the caption nor the Commons description shares words with the note's title or text
                         (people: no name word at all)
Writes data/audit/image-audit.json and prints a summary.

    python audit_images.py
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict

import numpy as np
from PIL import Image, ImageFilter

from common import DATA, IMAGES, load_json, load_notes, save_json
from fetch_images import sig_tokens

KIND = [
    ("flag", r"\bflag\b|\bbanner\b|\bstandard of\b"), ("arms", r"coat of arms|\bblazon\b|\bemblem\b|heraldic|\bseal\b"),
    ("logo", r"\blogo\b|\bwordmark\b|\bicon\b|\bsymbol\b"), ("map", r"\bmap\b|\bmaps\b|locator|atlas|\bchart of\b|\bplan of\b|\bterritor"),
    ("chart", r"\bchart\b|\bgraph\b|diagram|\btable\b|timeline|distribution|phylogen|cladogram|\bcurve\b|schematic|infographic"),
    ("doc", r"\bcover\b|title page|\bpage\b|manuscript|\bletter\b|newspaper|\bscan\b|\bstamp\b|banknote|\bcoin\b|signature|autograph|\bposter\b|\bbook\b"),
    ("screenshot", r"screenshot|screen shot|\bui\b|\bwebsite\b"),
]
PHOTOISH_OK = {"map": {"region", "culture", "place", "event", "era"}}   # maps can legitimately illustrate these, but never as the lead


def dhash(img: Image.Image, n=8) -> int:
    g = np.asarray(img.convert("L").resize((n + 1, n), Image.LANCZOS), dtype=np.int16)
    bits = (g[:, 1:] > g[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def features(path) -> dict:
    with Image.open(path) as im:
        im = im.convert("RGB")
        w, h = im.size
        small = im.resize((96, 96), Image.BILINEAR)
        a = np.asarray(small, dtype=np.uint8)
        q = (a // 32).reshape(-1, 3)
        codes = q[:, 0] * 64 + q[:, 1] * 8 + q[:, 2]
        top = np.bincount(codes, minlength=512)
        flat = float(np.sort(top)[-6:].sum() / codes.size)               # share of the 6 most common colours (of 512)
        lum = np.asarray(small.convert("L"), dtype=np.float32)
        edges = np.asarray(small.convert("L").filter(ImageFilter.FIND_EDGES), dtype=np.float32)
        sat = np.asarray(small.convert("HSV"), dtype=np.float32)[..., 1].mean() / 255
        return {"w": w, "h": h, "flat": round(flat, 3), "std": round(float(lum.std()), 1), "mean": round(float(lum.mean()), 1),
                "edge": round(float(edges.mean()), 2), "white": round(float((lum > 235).mean()), 3), "sat": round(float(sat), 3),
                "dh": dhash(im), "dh16": dhash(im, 16)}


def ham(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def main() -> int:
    credits = load_json(DATA / "image-credits.json", {})
    notes = {n["id"]: n for n in load_notes()}
    fileinfo = load_json(DATA / "cache" / "fileinfo.json", {})
    desc_by_title = {v["title"]: v.get("desc", "") for v in fileinfo.values() if v}
    out: dict[str, dict] = {}
    for rel, c in sorted(credits.items()):
        p = IMAGES / rel
        f = features(p)
        f["md5"] = hashlib.md5(p.read_bytes()).hexdigest()
        typ, slug, _ = rel.split("/")
        nid = f"{typ}/{slug}"
        f.update({"note": nid, "type": typ, "n": int(rel.split("/")[-1].split(".")[0]), "caption": c.get("caption", ""), "file": c.get("file"),
                  "via": c.get("via", ""), "ai": bool(c.get("ai")), "borrowed": bool(c.get("borrowed_from"))})
        out[rel] = f

    # ---- duplicates
    flags: dict[str, list[str]] = defaultdict(list)
    by_md5 = defaultdict(list)
    for rel, f in out.items():
        if not f["borrowed"]:
            by_md5[f["md5"]].append(rel)
    for grp in by_md5.values():
        if len(grp) > 1:
            for r in grp:
                flags[r].append("dup-exact:" + ",".join(x for x in grp if x != r)[:120])
    items = [(r, f) for r, f in out.items() if not f["borrowed"]]
    dh = np.array([f["dh"] for _, f in items], dtype=object)
    for i in range(len(items)):
        ri, fi_ = items[i]
        for j in range(i + 1, len(items)):
            rj, fj = items[j]
            if fi_["md5"] == fj["md5"]:
                continue
            if abs(fi_["w"] / fi_["h"] - fj["w"] / fj["h"]) > 0.25:
                continue
            d = ham(fi_["dh"], fj["dh"])
            d16 = ham(fi_["dh16"], fj["dh16"])
            if (d <= 4 and d16 <= 34) or (d <= 9 and d16 <= 52):
                tag = ("dup-near-same-note" if fi_["note"] == fj["note"] else "dup-near-cross-note") + ("" if d <= 4 else "(loose)")
                flags[ri].append(f"{tag}:{rj}")
                flags[rj].append(f"{tag}:{ri}")
    by_file = defaultdict(list)
    for rel, f in out.items():
        if f["file"] and not f["borrowed"] and not f["ai"]:
            by_file[f["file"]].append(rel)
    for grp in by_file.values():
        notes_in = {out[r]["note"] for r in grp}
        if len(notes_in) > 1:
            for r in grp:
                flags[r].append("same-file-many-notes:" + ",".join(sorted(notes_in - {out[r]["note"]}))[:120])

    # ---- quality and kind
    for rel, f in out.items():
        if f["ai"]:
            continue
        t = f["type"]
        if min(f["w"], f["h"]) < 320:
            flags[rel].append("small")
        r = f["w"] / f["h"]
        if r > 3.2 or r < 0.35:
            flags[rel].append("extreme-ratio")
        if f["flat"] > 0.93 and f["edge"] > 2:
            flags[rel].append("flat/diagram")
        if f["std"] < 14 or f["edge"] < 1.2:
            flags[rel].append("blank")
        if f["mean"] < 22:
            flags[rel].append("dark")
        cap = f["caption"].lower()
        for k, rx in KIND:
            if re.search(rx, cap):
                if k == "map" and t in PHOTOISH_OK["map"]:
                    flags[rel].append("caption:map(ok-not-lead)")
                else:
                    flags[rel].append("caption:" + k)
        # ---- relevance to the note
        n = notes.get(f["note"])
        if not n or f["borrowed"] or f["type"] == "source":
            continue
        words = sig_tokens(f["caption"] + " " + desc_by_title.get(f["file"], "") + " " + (f.get("file") or ""))
        title_t = sig_tokens(n["title"])
        body = n["body"][:1500]
        text_t = sig_tokens(body)
        if title_t & words:
            continue
        if f["type"] == "person":
            flags[rel].append("off-topic?:no-name-word")
        elif len(text_t & words) < 2:
            flags[rel].append("off-topic?:no-shared-words")

    for rel in out:
        out[rel]["flags"] = flags.get(rel, [])
        del out[rel]["dh16"]
        out[rel]["dh"] = str(out[rel]["dh"])
    save_json(DATA / "audit" / "image-audit.json", out)
    cnt = Counter(fl.split(":")[0] for f in out.values() for fl in f["flags"])
    print(f"{len(out)} images audited; images with at least one flag: {sum(1 for f in out.values() if f['flags'])}")
    for k, v in cnt.most_common():
        print(f"  {k:28s}{v:5d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
