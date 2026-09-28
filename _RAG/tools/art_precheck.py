"""Pre-write safety checks for the artist-section expansion. Run again immediately before each write.

Other sessions edit this vault live, so a title that was free ten minutes ago may not be free now.

  art_precheck.py batch N            check the ledger rows assigned to batch N
  art_precheck.py names "A" "B"      check ad-hoc titles
  art_precheck.py file NOTE.md ...   check drafted vault notes: title free, every wikilink target exists
  art_precheck.py lock ["message"]   take the advisory write lock (refuses if another holder is fresh)
  art_precheck.py unlock             release it

Name checks (case-insensitive): the title and every ledger alias must not match an existing note title;
the slug must be free in Art-Talk-main/artists/ (illustrated tracks); and a looser warning lists existing
notes whose title shares the candidate's last word, in case the person exists under another spelling.
Exit status is 1 on any hard failure, 0 otherwise.
"""
from __future__ import annotations

import csv
import re
import sys
import time
import unicodedata
from pathlib import Path

RAG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAG))
from vault import VAULT_ROOT, iter_notes, links_in, parse_note  # noqa: E402

LEDGER = RAG / "handoff" / "art_expansion_ledger.csv"
LOCK = RAG / "handoff" / "art_expansion.lock"
LOCK_STALE_SECONDS = 60 * 60
ARTISTS = VAULT_ROOT / "Art-Talk-main" / "artists"


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def existing_titles() -> dict[str, Path]:
    """Lowercased note title -> path, computed fresh (never cached)."""
    return {p.stem.lower(): p for p in iter_notes()}


def load_ledger() -> list[dict]:
    with LEDGER.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def check_name(title: str, aliases: str, slug: str, track: str, titles: dict[str, Path]) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    variants = [title] + [a.strip() for a in aliases.split(";") if a.strip()]
    for v in variants:
        hit = titles.get(v.lower())
        if hit:
            errors.append(f"{'title' if v == title else 'alias'} {v!r} already exists: {hit.relative_to(VAULT_ROOT)}")
    if slug and track in ("ill", "tierP") and (ARTISTS / f"{slug}.md").exists():
        errors.append(f"slug {slug!r} already used in Art-Talk-main/artists/")
    surname = norm(re.sub(r"\(.*?\)", "", title)).split(" ")[-1] if norm(title) else ""
    if len(surname) > 3:
        near = sorted(t for t in titles if surname in norm(t).split(" ") and t != title.lower())
        if near:
            warnings.append(f"possible existing note(s) sharing {surname!r}: " + "; ".join(near[:6]))
    return errors, warnings


def cmd_names(rows: list[dict]) -> int:
    titles = existing_titles()
    failed = 0
    for r in rows:
        errors, warnings = check_name(r["title"], r.get("aliases", ""), r.get("slug", ""), r.get("track", "ill"), titles)
        mark = "FAIL" if errors else "ok  "
        print(f"{mark} {r['title']}")
        for e in errors:
            print(f"       ERROR   {e}")
        for w in warnings:
            print(f"       warning {w}")
        failed += bool(errors)
    print(f"\n{len(rows) - failed} clear, {failed} blocked")
    return 1 if failed else 0


def cmd_files(paths: list[str]) -> int:
    titles = existing_titles()
    failed = 0
    for raw in paths:
        p = Path(raw)
        fm, body = parse_note(p)
        title = fm.get("title") or p.stem
        errors = []
        clash = titles.get(str(title).lower())
        if clash and clash.resolve() != p.resolve():
            errors.append(f"title {title!r} already exists at {clash.relative_to(VAULT_ROOT)}")
        if p.stem != title:
            errors.append(f"file name {p.stem!r} does not match title {title!r}")
        targets = links_in(fm.get("era")) + links_in(fm.get("region")) + links_in(fm.get("related")) \
            + links_in(fm.get("sources")) + links_in(body)
        for t in sorted(set(targets)):
            if t.lower() not in titles and t.lower() != str(title).lower():
                errors.append(f"wikilink target does not exist: [[{t}]]")
        print(("FAIL " if errors else "ok   ") + str(title))
        for e in errors:
            print(f"       ERROR   {e}")
        failed += bool(errors)
    return 1 if failed else 0


def cmd_lock(message: str) -> int:
    if LOCK.exists():
        age = time.time() - LOCK.stat().st_mtime
        if age < LOCK_STALE_SECONDS:
            print(f"lock held ({int(age // 60)} min old): {LOCK.read_text(encoding='utf-8').strip()}")
            return 1
        print(f"taking over a stale lock ({int(age // 60)} min old)")
    LOCK.write_text(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message or 'art expansion write'}\n", encoding="utf-8")
    print("lock taken")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "batch" and args:
        rows = [r for r in load_ledger() if r["batch"] == args[0]]
        if not rows:
            print(f"no ledger rows with batch={args[0]}")
            return 2
        return cmd_names(rows)
    if cmd == "names" and args:
        return cmd_names([{"title": a, "aliases": "", "slug": "", "track": "text-only"} for a in args])
    if cmd == "file" and args:
        return cmd_files(args)
    if cmd == "lock":
        return cmd_lock(" ".join(args))
    if cmd == "unlock":
        LOCK.unlink(missing_ok=True)
        print("lock released")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
