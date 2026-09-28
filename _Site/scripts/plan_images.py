#!/usr/bin/env python3
"""Decide how many images (1..ceiling) each note should get, scaled by richness percentile.

Output: data/image-plan.json   Usage: python plan_images.py [--dry]
"""
from __future__ import annotations

import argparse
import collections
import re

from common import CEILING, CONF, DATA, load_notes, save_json


def richness(n) -> float:
    body = n["body"]
    facts = re.search(r"^## Facts\s*\n(.*?)(?=^## |\Z)", body, re.M | re.S)
    bullets = len(re.findall(r"^\s*[-*] ", facts.group(1), re.M)) if facts else 0
    conf = CONF.get(str(n["fm"].get("confidence")).lower(), 1)
    # weights chosen so no single signal dominates: bullets 0-10, length 0-10, links 0-10, confidence 0-3
    return (min(bullets, 10) + min(len(body) / 400, 10) + min((len(n["out"]) + len(n["inb"])) / 3, 10) + conf)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    notes = load_notes()
    bytype = collections.defaultdict(list)
    for n in notes:
        n["rich"] = richness(n)
        bytype[n["type"]].append(n)
    plan, dist = {}, collections.defaultdict(collections.Counter)
    for typ, items in bytype.items():
        ceil = CEILING[typ]
        items.sort(key=lambda n: n["rich"])
        for rank, n in enumerate(items):
            pct = rank / max(1, len(items) - 1)
            count = 1 + int(pct * ceil - 1e-9) if ceil > 1 else 1   # 1..ceil, roughly uniform over percentile
            count = max(1, min(ceil, count))
            plan[n["id"]] = {"title": n["title"], "type": typ, "slug": n["slug"], "count": count,
                             "richness": round(n["rich"], 2), "path": n["path"]}
            dist[typ][count] += 1
    print(f"{'type':14s}{'notes':>6s}  distribution (images: notes)   total")
    grand = 0
    for typ in CEILING:
        d = dist[typ]
        tot = sum(k * v for k, v in d.items())
        grand += tot
        print(f"{typ:14s}{len(bytype[typ]):6d}  {dict(sorted(d.items()))}   {tot}")
    print(f"notes {len(notes)}  planned images {grand}")
    if not args.dry:
        save_json(DATA / "image-plan.json", plan)
        print("wrote data/image-plan.json")


if __name__ == "__main__":
    main()
