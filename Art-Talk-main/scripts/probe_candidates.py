#!/usr/bin/env python3
"""Go/no-go image probe: does a candidate artist have enough freely licensed Commons files?

For each name this searches the Commons File namespace, runs every hit through the same
``license_ok()`` gate that ``fetch_images.py`` uses, drops files that are too small to be
useful, and guesses what each surviving file could be used for (a slot kind such as likeness,
primary document, venue). A candidate is GO when at least MIN_FILES files pass across at least
--min-kinds distinct slot kinds; otherwise NO-GO, and the caller should swap in a reserve.
Painters and sculptors need only enough files (--min-kinds 1, the default); composers, dancers,
dramatists and calligraphers rest on likeness/document/venue/instrument files, so use --min-kinds 3.

The slot kind is a filename heuristic, so treat it as a hint and eyeball the titles. Search hits
are only leads: a file can match the name and still depict someone else (Homer vs Winslow Homer).
Copy ``commons_file`` values verbatim from this output; never type a Commons filename from memory.

Usage:
    python scripts/probe_candidates.py "Hildegard of Bingen" "Wang Xizhi"
    python scripts/probe_candidates.py "Homer::Iliad manuscript"      # NAME::extra search terms
    python scripts/probe_candidates.py "Sophocles" --json probe.json  # also dump passing files
"""

from __future__ import annotations

import argparse
import json
import re
import sys

from fetch_images import file_info, get, license_ok, plain

COMMONS = "https://commons.wikimedia.org/w/api.php"
MIN_FILES = 8
MIN_WIDTH = 600
IMAGE_MIMES = {"image/jpeg", "image/png", "image/tiff", "image/webp"}

# First match wins, so the order runs from most to least specific.
KINDS = [
    ("document", r"manuscript|folio|codex|autograph|score|partitur|title ?page|first edition|playbill|"
                 r"poster|letter|handwritten|specimen|inscription|frontispiece|libretto|notation|leaf|page|"
                 r"帖|卷|書|书|經|经|墨[迹跡]|手札|写本|寫本"),
    ("instrument", r"instrument|costume|mask|dress|robe|kimono|violin|lute|harp|organ|piano|drum|flute|helmet"),
    ("venue", r"theat(?:er|re)|opera house|church|cathedral|mosque|temple|palace|hall|interior|exterior|"
              r"fa[cç]ade|building|castle|abbey|monastery|stage|amphitheat|故居|寺|廟|庙|宮|宫|殿|城"),
    ("likeness", r"portrait|bust|statue|monument|memorial|daguerreotype|carte de visite|photograph of|photo of|像|肖像"),
    ("depiction", r"illustration|engraving|lithograph|woodcut|scene|depict|print"),
    ("place", r"\bmap\b|view of|landscape|panorama|ruins"),
]


def slot_kind(title: str) -> str:
    for kind, pattern in KINDS:
        if re.search(pattern, title, re.I):
            return kind
    return "work"


def search_files(query: str, limit: int) -> list[str]:
    """Commons file names (without the File: prefix) matching a full-text query."""
    data = get(COMMONS, {
        "action": "query", "list": "search", "format": "json", "formatversion": "2",
        "srsearch": f"{query} filetype:bitmap", "srnamespace": "6", "srlimit": str(limit),
    }).json()
    return [hit["title"].removeprefix("File:") for hit in data.get("query", {}).get("search", [])]


def probe(name: str, extra: str, limit: int, min_kinds: int) -> dict:
    query = f'"{name}" {extra}'.strip()
    found = search_files(query, limit)
    infos = file_info(found) if found else {}
    passing, rejected = [], {}
    for f in found:
        info = infos.get(f)
        if not info:
            rejected["not found"] = rejected.get("not found", 0) + 1
            continue
        ok, lic = license_ok(info)
        if not ok:
            rejected[lic] = rejected.get(lic, 0) + 1
        elif info.get("mime") not in IMAGE_MIMES or (info.get("width") or 0) < MIN_WIDTH:
            rejected["too small or not a bitmap"] = rejected.get("too small or not a bitmap", 0) + 1
        else:
            passing.append({"file": info["title"].removeprefix("File:"), "license": plain(lic),
                            "width": info["width"], "height": info["height"], "kind": slot_kind(f)})
    kinds = sorted({p["kind"] for p in passing})
    go = len(passing) >= MIN_FILES and len(kinds) >= min_kinds
    return {"name": name, "query": query, "searched": len(found), "passing": passing,
            "kinds": kinds, "rejected": rejected, "go": go}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("names", nargs="+", help='candidate names, optionally "Name::extra search terms"')
    ap.add_argument("--limit", type=int, default=50, help="Commons search hits to examine (default 50)")
    ap.add_argument("--min-kinds", type=int, default=1, help="distinct slot kinds required for GO (3 for performing artists)")
    ap.add_argument("--show", type=int, default=30, help="passing files to print per candidate (default 30)")
    ap.add_argument("--json", metavar="PATH", help="also write the full results to this file")
    args = ap.parse_args()

    results = []
    for arg in args.names:
        name, _, extra = arg.partition("::")
        r = probe(name.strip(), extra.strip(), args.limit, args.min_kinds)
        results.append(r)
        verdict = "GO" if r["go"] else "NO-GO"
        print(f"\n{verdict}  {r['name']}: {len(r['passing'])} of {r['searched']} hits pass, "
              f"slot kinds: {', '.join(r['kinds']) or 'none'}")
        for p in r["passing"][: args.show]:
            print(f"    [{p['kind']:10s}] {p['file']}  ({p['license']}, {p['width']}x{p['height']})")
        if len(r["passing"]) > args.show:
            print(f"    ... and {len(r['passing']) - args.show} more (see --json)")
        if r["rejected"]:
            print("    rejected: " + "; ".join(f"{n}x {why}" for why, n in sorted(r["rejected"].items())))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=2, ensure_ascii=False)
    return 0 if all(r["go"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
