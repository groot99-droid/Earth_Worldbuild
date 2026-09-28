"""Validate the vault: frontmatter schema, folder placement, required sections, broken links, orphans.

Usage:  python _RAG/tools/validate_vault.py [--strict]
Exit code is 1 if any error is found (warnings do not fail unless --strict).
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vault import VAULT_ROOT, iter_notes, links_in, parse_note  # noqa: E402

CODE_RE = re.compile(r"```.*?```|`[^`\n]*`", re.DOTALL)

FOLDERS = {
    "era": "01_Eras", "region": "02_Regions",
    "event": "03_Entities/Events", "person": "03_Entities/People",
    "place": "03_Entities/Places", "culture": "03_Entities/Peoples-Cultures",
    "species": "03_Entities/Species", "technology": "03_Entities/Artifacts-Technologies",
    "theme": "04_Themes", "observer-note": "05_Observer_Notes",
    "timeline": "06_Timelines", "source": "07_Sources", "meta": "00_Meta",
}
ENTITY_TYPES = {"event", "person", "place", "culture", "species", "technology"}
THEMES = {"science", "technology", "religion", "war", "trade", "kinship", "language", "art", "earth-systems"}
PRECISION = {"exact", "year", "decade", "century", "approx", "deep-time"}
CONFIDENCE = {"high", "medium", "low"}
STATUS = {"seed", "draft", "reviewed"}
# How much of a source was actually read (source notes only). See Conventions.
ACCESS = ["full-text", "archived-copy", "reference-text", "abstract", "summary-only", "not-consulted"]
READ_LEVELS = {"full-text", "archived-copy", "reference-text", "abstract"}
ENTITY_SECTIONS = ["## Summary", "## Facts", "## Context & Connections", "## Observer's Reading", "## Open Questions"]
ESSAY_SECTIONS = ["## Question", "## What the Record Shows", "## Observer's Reading", "## Limits of This Reading"]
REQUIRED_BY_TYPE = {
    "era": ["title", "type", "date_start", "confidence", "status"],
    "region": ["title", "type", "confidence", "status"],
    "theme": ["title", "type", "slug", "status"],
    "observer-note": ["title", "type", "confidence", "status"],
    "timeline": ["title", "type", "status"],
    "source": ["title", "type", "citation", "status"],
    "meta": ["title", "type", "status"],
}
for t in ENTITY_TYPES:
    REQUIRED_BY_TYPE[t] = ["title", "type", "era", "region", "themes", "date_start", "date_precision", "confidence", "status"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    ap.add_argument("--list-access", action="store_true", help="list every verified source that has no access level")
    args = ap.parse_args()

    notes = {p: parse_note(p) for p in iter_notes()}
    titles = {p.stem.lower(): p for p in notes}
    by_type: dict[str, set[str]] = defaultdict(set)
    for p, (fm, _) in notes.items():
        by_type[str(fm.get("type"))].add(p.stem.lower())

    errors: list[str] = []
    warnings: list[str] = []
    inbound: dict[Path, int] = defaultdict(int)
    access_counts: dict[str, int] = defaultdict(int)
    no_access: list[str] = []

    def rel(p: Path) -> str:
        return p.relative_to(VAULT_ROOT).as_posix()

    for path, (fm, body) in notes.items():
        r = rel(path)
        if not fm:
            errors.append(f"{r}: missing or invalid frontmatter")
            continue
        ntype = fm.get("type")
        if ntype not in FOLDERS:
            errors.append(f"{r}: unknown type {ntype!r}")
            continue
        if fm.get("title") != path.stem:
            errors.append(f"{r}: title {fm.get('title')!r} does not match filename")
        if not r.startswith(FOLDERS[ntype] + "/"):
            errors.append(f"{r}: type '{ntype}' belongs in {FOLDERS[ntype]}/")
        for key in REQUIRED_BY_TYPE.get(ntype, []):
            if fm.get(key) in (None, "", []) and not (key == "themes" and fm.get("themes") == []):
                errors.append(f"{r}: missing required field '{key}'")
        if "confidence" in fm and fm["confidence"] not in CONFIDENCE:
            errors.append(f"{r}: bad confidence {fm['confidence']!r}")
        if "status" in fm and fm["status"] not in STATUS:
            errors.append(f"{r}: bad status {fm['status']!r}")
        if "date_precision" in fm and fm["date_precision"] not in PRECISION:
            errors.append(f"{r}: bad date_precision {fm['date_precision']!r}")
        for key in ("date_start", "date_end"):
            if fm.get(key) is not None and not isinstance(fm[key], int):
                errors.append(f"{r}: {key} must be an integer")
        if isinstance(fm.get("date_start"), int) and isinstance(fm.get("date_end"), int) and fm["date_end"] < fm["date_start"]:
            errors.append(f"{r}: date_end earlier than date_start")
        for th in fm.get("themes") or []:
            if th not in THEMES:
                errors.append(f"{r}: unknown theme slug {th!r}")

        # era / region must point at the right note type
        for field, want in (("era", "era"), ("region", "region")):
            if fm.get(field):
                tgt = links_in(fm[field])
                if not tgt:
                    errors.append(f"{r}: {field} is not a wikilink")
                elif tgt[0].lower() not in by_type[want]:
                    errors.append(f"{r}: {field} -> [[{tgt[0]}]] is not a '{want}' note")

        # sections
        if ntype in ENTITY_TYPES | {"era", "region", "theme"}:
            need = ENTITY_SECTIONS if ntype in ENTITY_TYPES | {"era", "region"} else ["## Summary", "## Observer's Reading"]
            for sec in need:
                if sec not in body:
                    errors.append(f"{r}: missing section '{sec}'")
        elif ntype == "observer-note":
            for sec in ESSAY_SECTIONS:
                if sec not in body:
                    errors.append(f"{r}: missing section '{sec}'")
        fc = fm.get("fact_checks")
        if fc is not None:
            if not isinstance(fc, list) or not all(isinstance(x, str) and x[:4].isdigit() and "[" in x for x in fc):
                errors.append(f"{r}: fact_checks must be a list of 'YYYY-MM-DD: claim [Source]' strings")
            else:
                for x in fc:
                    src = x[x.rfind("[") + 1:x.rfind("]")].split("; ")
                    for sname in src:
                        if sname.strip().lower() not in titles:
                            errors.append(f"{r}: fact_checks cites unknown source '{sname}'")
        if ntype in ENTITY_TYPES and fm.get("status") == "seed" and not fm.get("sources"):
            warnings.append(f"{r}: no sources listed")

        # source notes: how much of the source was actually read
        if ntype == "source":
            acc = fm.get("access")
            access_counts[acc if acc in ACCESS else "(not set)"] += 1
            if acc is not None and acc not in ACCESS:
                errors.append(f"{r}: bad access {acc!r} (expected one of {', '.join(ACCESS)})")
            elif acc is None and fm.get("verified") is True:
                no_access.append(r)
            elif acc == "not-consulted" and fm.get("verified") is True:
                warnings.append(f"{r}: access is not-consulted but verified is true")
            elif acc in READ_LEVELS and not fm.get("read_on"):
                warnings.append(f"{r}: access is {acc} but read_on is missing")

        # links (frontmatter + body)
        targets = links_in([fm.get(k) for k in ("era", "region", "related", "sources")]) + links_in(CODE_RE.sub('', body))
        for t in targets:
            key = t.lower()
            if key not in titles:
                errors.append(f"{r}: broken link [[{t}]]")
            elif titles[key] != path:
                inbound[titles[key]] += 1
        if ntype in ("source",):
            continue

    for path, (fm, _) in notes.items():
        if fm.get("type") in ENTITY_TYPES | {"observer-note"} and inbound[path] == 0:
            warnings.append(f"{rel(path)}: orphan (no inbound links)")

    content = [(p, fm) for p, (fm, _) in notes.items() if fm.get("type") in ENTITY_TYPES | {"era", "region"}]
    checked = [p for p, fm in content if fm.get("fact_checks")]
    print(f"Fact-check coverage: {len(checked)}/{len(content)} entity, era, and region notes have fact_checks.")
    print("Sources by access level: " + ", ".join(f"{k} {access_counts[k]}" for k in ACCESS + ["(not set)"] if access_counts[k]) + ".")
    if no_access:
        if args.list_access:
            warnings.extend(f"{r}: verified is true but no access level" for r in no_access)
        else:
            warnings.append(f"07_Sources: {len(no_access)} source(s) are verified but have no access level (--list-access lists them)")
    print(f"Checked {len(notes)} notes.")
    for w in warnings:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s).")
    return 1 if errors or (args.strict and warnings) else 0


if __name__ == "__main__":
    sys.exit(main())
