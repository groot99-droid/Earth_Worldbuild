"""Recompute the counts shown in `00_Meta/Project Status Overview.md`.

The overview's figures live in two generated blocks, `<!-- AUTO:status-exists -->` and
`<!-- AUTO:status-standing -->`. This script recomputes them from the files on disk (vault notes,
canvases, the site data, the museum manifest and the rewrite store) and never reads a cache.
Edit the prose outside the blocks by hand; never edit inside them.

Usage:
    python _RAG/tools/status_overview.py            # print the two blocks (writes nothing)
    python _RAG/tools/status_overview.py --write    # rewrite the blocks in the overview note

Standard library only, plus the vault's own `_RAG/vault.py` parser (which uses PyYAML, as every
`_RAG/tools/` script does). The validator is run as a subprocess and only its summary line is kept.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

RAG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAG))
from vault import VAULT_ROOT, iter_notes, links_in, parse_note  # noqa: E402

NOTE = VAULT_ROOT / "00_Meta" / "Project Status Overview.md"
ENTITY_TYPES = ("event", "person", "culture", "place", "species", "technology")
LAYERS = [  # (label, folder, type)
    ("Eras", "01_Eras", "era"), ("Regions", "02_Regions", "region"),
    ("Events", "03_Entities/Events", "event"), ("People", "03_Entities/People", "person"),
    ("Peoples and Cultures", "03_Entities/Peoples-Cultures", "culture"),
    ("Places", "03_Entities/Places", "place"), ("Species", "03_Entities/Species", "species"),
    ("Technologies", "03_Entities/Artifacts-Technologies", "technology"),
    ("Themes", "04_Themes", "theme"), ("Observer essays", "05_Observer_Notes", "observer-note"),
    ("Timelines", "06_Timelines", "timeline"), ("Sources", "07_Sources", "source"),
    ("Meta", "00_Meta", "meta"),
]
ACCESS = ["full-text", "archived-copy", "reference-text", "abstract", "summary-only", "not-consulted"]
BLOCK = "<!-- AUTO:{name} -->\n{body}\n<!-- /AUTO:{name} -->"
BLOCK_RE = r"<!-- AUTO:{name} -->.*?<!-- /AUTO:{name} -->"
AUTO_RE = re.compile(r"<!--\s*AUTO:([\w-]+)[^>]*-->.*?<!--\s*/AUTO:\1\s*-->", re.S)
WORD_RE = re.compile(r"[A-Za-z0-9À-ɏ'’-]+")
WIKILINK_RE = re.compile(r"\[\[[^\]]+\]\]")


def n(x: int) -> str:
    return f"{x:,}"


def load_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def validator_line() -> str:
    try:
        r = subprocess.run([sys.executable, str(RAG / "tools" / "validate_vault.py")], capture_output=True,
                           text=True, encoding="utf-8", timeout=600)
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"could not run ({e.__class__.__name__})"
    lines = [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]
    return lines[-1].rstrip(".") if lines else "no output"


def rewrite_counts() -> dict | None:
    """Fresh / stale / not-yet-rewritten counts, computed the way `_Rewrite/rewrite_layer.py status` does."""
    sys.path.insert(0, str(VAULT_ROOT / "_Rewrite"))
    try:
        import rewrite_layer as rl  # noqa: PLC0415
    except Exception:  # noqa: BLE001 - the layer is optional
        return None
    out = {}
    for target in rl.TARGETS:
        sources = rl.SOURCES[target]()
        store = rl.load_json(rl.store_path(target), {}) or {}
        fresh = sum(1 for i, s in sources.items() if store.get(i, {}).get("src") == s["src"])
        stale = sum(1 for i, s in sources.items() if i in store and store[i].get("src") != s["src"])
        out[target] = (len(sources), fresh, stale, len(sources) - fresh - stale)
    return out


def compute() -> tuple[str, str]:
    notes = {p: parse_note(p) for p in iter_notes() if p != NOTE}
    by_type: dict[str, list] = defaultdict(list)
    words = links = 0
    for p, (fm, body) in notes.items():
        by_type[str(fm.get("type"))].append((p, fm))
        text = AUTO_RE.sub("", body)
        words += len(WORD_RE.findall(re.sub(r"\[\[([^\]|]+\|)?([^\]]+)\]\]", r"\2", text)))
        links += len(WIKILINK_RE.findall(text))

    # ---------------------------------------------------------------- what exists
    rows = ["| Layer | Folder | Notes |", "|---|---|---|"]
    for label, folder, t in LAYERS:
        cnt = sum(1 for p, _ in by_type[t] if p.relative_to(VAULT_ROOT).as_posix().startswith(folder + "/"))
        rows.append(f"| {label} | `{folder}/` | {n(cnt)} |")
    eras = sorted(((fm.get("date_start") if isinstance(fm.get("date_start"), int) else 0, p.stem)
                   for p, fm in by_type["era"]))
    per_era = Counter()
    for t in ENTITY_TYPES:
        for _, fm in by_type[t]:
            tgt = links_in(fm.get("era"))
            per_era[tgt[0] if tgt else "(none)"] += 1
    era_cells = [f"[[{title}]] {per_era.get(title, 0)}" for _, title in eras if per_era.get(title, 0)]
    empty = [f"[[{title}]]" for _, title in eras if not per_era.get(title, 0)]
    entity_total = sum(len(by_type[t]) for t in ENTITY_TYPES)
    exists = [
        f"Counted on {date.today().isoformat()} by `_RAG/tools/status_overview.py` (regenerate it; do not edit by hand). "
        f"Earth Chronicle holds {n(len(notes))} notes, not counting this one, with about {n(round(words, -3))} words of body "
        f"text and {n(links)} wikilinks in note bodies (generated hub lists and timelines left out of both counts).",
        "",
        *rows,
        "",
        f"Entity notes by primary era ({n(entity_total)} in all), oldest era first: " + ", ".join(era_cells) + ".",
    ]
    if empty:
        exists.append(f"Eras with no entity note of their own: {', '.join(empty)}.")
    artists = [fm for _, fm in by_type["person"] if "artist" in (fm.get("tags") or [])]
    illustrated = sum(1 for fm in artists if fm.get("art_talk"))
    exists.append(f"The named-artist section (person notes tagged `artist`) has {len(artists)} notes, "
                  f"{illustrated} of them with an Art-Talk profile.")

    # ---------------------------------------------------------------- where things stand
    content = [(p, fm) for t in (*ENTITY_TYPES, "era", "region") for p, fm in by_type[t]]
    checked = [fm for _, fm in content if fm.get("fact_checks")]
    checks = [c for fm in checked for c in fm["fact_checks"] if isinstance(c, str)]
    by_day = Counter(c[:10] for c in checks)
    gaps = Counter(str(fm.get("type")) for _, fm in content if not fm.get("fact_checks"))
    status = Counter(str(fm.get("status")) for t, lst in by_type.items() if t not in ("source", "meta")
                     for _, fm in lst)
    srcs = [fm for _, fm in by_type["source"]]
    verified = sum(1 for fm in srcs if fm.get("verified") is True)
    acc = Counter(fm.get("access") if fm.get("access") in ACCESS else "(not set)" for fm in srcs)
    unverified = sorted(fm.get("title") for fm in srcs if fm.get("verified") is not True)
    summaries = sum(1 for fm in srcs if "(Search Summaries)" in str(fm.get("title")))
    generic = Counter()
    for c in checks:
        for s in c[c.rfind("[") + 1:c.rfind("]")].split("; "):
            if s.strip() in ("Encyclopaedia Britannica", "English Wikipedia"):
                generic[s.strip()] += 1

    standing = [
        f"- **Validator:** {validator_line()}.",
        f"- **Fact-checking:** {len(checked)} of {len(content)} era, region and entity notes carry dated `fact_checks`, "
        f"{n(len(checks))} in all ("
        + ", ".join(f"{d} {by_day[d]}" for d in sorted(by_day)) + "). "
        f"Notes without any: " + ", ".join(f"{t} {c}" for t, c in gaps.most_common()) + ". "
        f"{generic['Encyclopaedia Britannica']} checks cite the generic [[Encyclopaedia Britannica]] note and "
        f"{generic['English Wikipedia']} the generic [[English Wikipedia]] note, both `not-consulted`.",
        "- **Status:** " + ", ".join(f"{c} `{s}`" for s, c in status.most_common())
        + " (all notes except sources and meta notes). Under [[Conventions]] a note stays `seed` until every claim is checked.",
        f"- **Sources:** {len(srcs)} source notes, {verified} marked `verified: true`. By access level: "
        + ", ".join(f"{k} {acc[k]}" for k in ACCESS + ["(not set)"] if acc[k]) + f". {summaries} are \"(Search Summaries)\" "
        f"notes. Not verified ({len(unverified)}): " + ", ".join(f"[[{t}]]" for t in unverified) + ".",
    ]
    canvas = load_json(VAULT_ROOT / "08_Canvas_Maps" / "Themes and Essays Map.canvas") or {}
    on_map = {Path(nd.get("file", "")).stem for nd in canvas.get("nodes", []) if nd.get("type") == "file"}
    essays = sorted(p.stem for p, _ in by_type["observer-note"])
    missing = [e for e in essays if e not in on_map]
    standing.append(f"- **Canvas maps:** `08_Canvas_Maps/Themes and Essays Map.canvas` shows {len(essays) - len(missing)} "
                    f"of the {len(essays)} Observer essays"
                    + (f"; missing: {', '.join(f'[[{e}]]' for e in missing)}." if missing else "."))
    site = load_json(VAULT_ROOT / "_Site" / "data" / "build-report.json") or {}
    if site:
        standing.append(f"- **Site (`_Site/`):** the last build holds {n(site.get('notes', 0))} notes, "
                        f"{n(site.get('images', 0))} images ({n(site.get('with_image', 0))} notes with an image) and "
                        f"{n(site.get('edges', 0))} edges; {len(site.get('unresolved_wikilinks', []))} unresolved link(s).")
    manifest = load_json(VAULT_ROOT / "_Museum" / "data" / "museum-manifest.json") or {}
    if manifest:
        works = sum(len(a.get("works", [])) for a in manifest.get("artists", []))
        standing.append(f"- **Museum (`_Museum/`):** {len(manifest.get('rooms', []))} scenes (the hub and "
                        f"{len(manifest.get('rooms', [])) - 1} rooms), {len(manifest.get('artists', []))} artists and people, "
                        f"{n(works)} works.")
    rw = rewrite_counts()
    if rw:
        standing.append("- **Rewrite layer (`_Rewrite/`):** " + "; ".join(
            f"{t} {n(fresh)} of {n(total)} rewritten, {n(stale)} stale, {n(todo)} not yet rewritten"
            for t, (total, fresh, stale, todo) in rw.items()) + ".")
    return "\n".join(exists), "\n".join(standing)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="rewrite the generated blocks in the overview note")
    args = ap.parse_args()
    exists, standing = compute()
    blocks = {"status-exists": exists, "status-standing": standing}
    if not args.write:
        for name, body in blocks.items():
            print(BLOCK.format(name=name, body=body), end="\n\n")
        return 0
    text = NOTE.read_text(encoding="utf-8")
    for name, body in blocks.items():
        pat = re.compile(BLOCK_RE.format(name=name), re.S)
        if not pat.search(text):
            print(f"{NOTE.name}: no <!-- AUTO:{name} --> block; add the markers first", file=sys.stderr)
            return 1
        text = pat.sub(lambda _m: BLOCK.format(name=name, body=body), text)
    NOTE.write_text(text, encoding="utf-8", newline="\n")
    print(f"updated {NOTE.relative_to(VAULT_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
