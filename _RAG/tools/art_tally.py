"""Tally the named-artist section against the expansion targets.

Reads every `person` note tagged `artist` straight from the vault (never cached), joins gender and
track from _RAG/handoff/art_expansion_ledger.csv (gender lives only in the ledger, never in
frontmatter), and prints have/target tables for the artists added by the expansion. The original 53
(ledger track `existing`) and the retro-tagged general People notes are reported separately so they
do not count toward the +150.

Usage:  PYTHONUTF8=1 _RAG/.venv/Scripts/python.exe _RAG/tools/art_tally.py
See _RAG/handoff/HANDOFF_Art_Section_Expansion.md for the plan these targets come from.
"""
from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from pathlib import Path

RAG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAG))
from vault import iter_notes, parse_note  # noqa: E402

LEDGER = RAG / "handoff" / "art_expansion_ledger.csv"

# Targets for the +150 new notes (illustrated + text-only), from the plan.
REGION_TARGET = {
    "Europe": 16, "Mediterranean Basin": 10, "Levant and Anatolia": 7, "Mesopotamia": 5, "Iranian Plateau": 7,
    "Arabian Peninsula": 2, "Central Asian Oases": 4, "Central Asian Steppe": 3, "Siberia and the Arctic": 2,
    "South Asia": 12, "East Asia": 16, "Southeast Asia": 9, "Nile Valley": 7, "Sub-Saharan Africa": 12,
    "Oceania": 7, "North America": 11, "Mesoamerica": 5, "Caribbean and Atlantic World": 5, "Andes": 5,
    "Amazon Basin and South American Lowlands": 5,
}
DISCIPLINE_TARGET = {
    "painting": 33, "literature": 32, "music": 27, "sculpture": 14, "architecture": 11, "theatre": 10, "dance": 8,
    "craft": 5, "calligraphy": 5, "design": 1, "photography": 2, "film": 2,
}
ERA_TARGET = {
    "Bronze Age": 3, "Iron Age": 2, "Classical Antiquity": 11, "Medieval Period": 29, "Early Modern Period": 27,
    "Industrial Age": 66, "Information Age": 12,
}
WOMEN_FLOOR = 60          # of 150
TEXT_ONLY_CAP = 20
TOTAL_TARGET = 150
NON_DISCIPLINE_TAGS = {"artist", "text-only"}


def strip_link(v) -> str:
    return re.sub(r"^\[\[|\]\]$", "", str(v or "")).strip()


def load_ledger() -> dict[str, dict]:
    if not LEDGER.exists():
        return {}
    with LEDGER.open(encoding="utf-8-sig", newline="") as fh:
        return {r["title"]: r for r in csv.DictReader(fh)}


def table(title: str, have: Counter, target: dict[str, int] | None = None) -> None:
    print(f"\n{title}")
    keys = list(target) if target else sorted(have, key=lambda k: -have[k])
    for extra in sorted(k for k in have if target and k not in target):
        keys.append(extra)
    for k in keys:
        h, t = have.get(k, 0), (target or {}).get(k)
        flag = ""
        if t is not None:
            flag = "  ok" if h == t else ("  over" if h > t else f"  needs {t - h}")
        print(f"  {k:44s} {h:4d}" + (f" / {t:<4d}{flag}" if t is not None else ""))


def main() -> int:
    ledger = load_ledger()
    section = []
    for p in iter_notes():
        fm, _ = parse_note(p)
        tags = fm.get("tags") or []
        if fm.get("type") == "person" and "artist" in tags:
            section.append(fm)

    original = [fm for fm in section if ledger.get(fm.get("title"), {}).get("track") == "existing"]
    retro = [fm for fm in section if ledger.get(fm.get("title"), {}).get("track") == "retro-tag"]
    new = [fm for fm in section if fm not in original and fm not in retro]

    def gender(fm) -> str:
        return ledger.get(fm.get("title"), {}).get("gender", "?")

    print(f"artist-tagged notes: {len(section)}  (original 53: {len(original)}, retro-tagged: {len(retro)}, "
          f"new: {len(new)} of {TOTAL_TARGET})")
    europe = sum(1 for fm in section if strip_link(fm.get("region")) in ("Europe", "Mediterranean Basin"))
    women_all = sum(1 for fm in section if gender(fm) == "F")
    print(f"whole section: Europe+Mediterranean {europe} ({europe / max(len(section), 1):.0%}), "
          f"women {women_all} ({women_all / max(len(section), 1):.0%})")

    table("REGION (new notes)", Counter(strip_link(fm.get("region")) for fm in new), REGION_TARGET)
    table("PRIMARY DISCIPLINE (new notes; first discipline tag)",
          Counter(next((t for t in fm.get("tags", []) if t not in NON_DISCIPLINE_TAGS), "?") for fm in new),
          DISCIPLINE_TARGET)
    table("ERA (new notes)", Counter(strip_link(fm.get("era")) for fm in new), ERA_TARGET)

    women = sum(1 for fm in new if gender(fm) == "F")
    unknown = sum(1 for fm in new if gender(fm) == "?")
    text_only = sum(1 for fm in new if "text-only" in (fm.get("tags") or []))
    share = women / max(len(new), 1)
    print(f"\nGENDER (new notes): women {women} of {len(new)} = {share:.0%}"
          f"  (floor {WOMEN_FLOOR}/{TOTAL_TARGET} = {WOMEN_FLOOR / TOTAL_TARGET:.0%})"
          + (f"  [{unknown} not in ledger]" if unknown else ""))
    if new and share < WOMEN_FLOOR / TOTAL_TARGET:
        print("  BELOW FLOOR: apply the pre-declared women swaps and replace dropouts women-first")
    print(f"TEXT-ONLY (new notes): {text_only} (cap {TEXT_ONLY_CAP})")

    if ledger:
        statuses = Counter(r["status"] for r in ledger.values() if r["track"] not in ("existing", "retro-tag"))
        print("\nLEDGER status (non-existing rows): " + ", ".join(f"{k} {v}" for k, v in sorted(statuses.items())))
        in_ledger = {t for t, r in ledger.items() if r["status"] in ("note_written", "validated")}
        missing = sorted(t for t in in_ledger if t not in {fm.get("title") for fm in section})
        if missing:
            print("  ledger says written but no artist-tagged note found: " + "; ".join(missing))
    return 0


if __name__ == "__main__":
    sys.exit(main())
