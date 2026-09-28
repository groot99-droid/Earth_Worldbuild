"""Regenerate the auto-generated sections of hub notes and timelines from note frontmatter.

Fills (idempotently):
  * Era hubs     -> "## Notes in This Era"      (notes whose `era` points here)
  * Region hubs  -> "## Notes in This Region"   (notes whose `region` points here)
  * Theme hubs   -> "## Notes Tagged With This Theme" (notes whose `themes` includes the hub's `slug`)
  * Timelines    -> tables from `<!-- AUTO:timeline types=a,b min=N max=N -->` markers

Edit the source notes, never the generated blocks. Usage:  python _RAG/tools/update_hubs.py
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vault import VAULT_ROOT, iter_notes, links_in, parse_note  # noqa: E402

TYPE_LABEL = {
    "event": "Events", "person": "People", "place": "Places", "culture": "Peoples and cultures",
    "species": "Species", "technology": "Technologies", "era": "Eras", "observer-note": "Observer essays",
}
TYPE_ORDER = ["era", "event", "person", "culture", "place", "species", "technology", "observer-note"]
MEMBER_BLOCK = re.compile(r"<!-- AUTO:members -->.*?<!-- /AUTO:members -->", re.DOTALL)
TIMELINE_BLOCK = re.compile(r"<!-- AUTO:timeline([^>]*)-->.*?<!-- /AUTO:timeline -->", re.DOTALL)


def fmt_date(y) -> str:
    if y is None:
        return ""
    if y <= -1_000_000_000:
        return f"{-y / 1e9:g} Ga"
    if y <= -1_000_000:
        return f"{-y / 1e6:g} Ma"
    if y <= -10_000:
        return f"{-y / 1e3:g} ka"
    if y < 0:
        return f"{-y} BCE"
    return f"{y} CE"


def sort_key(item):
    fm = item[1]
    d = fm.get("date_start")
    return (d is None, d if d is not None else 0, item[0].stem)


def members_block(items) -> str:
    groups = defaultdict(list)
    for path, fm in items:
        groups[fm.get("type")].append((path, fm))
    lines = ["<!-- AUTO:members -->"]
    for t in TYPE_ORDER:
        if t not in groups:
            continue
        lines.append(f"**{TYPE_LABEL[t]}**")
        for path, fm in sorted(groups[t], key=sort_key):
            d = fmt_date(fm.get("date_start"))
            lines.append(f"- [[{path.stem}]]" + (f" ({d})" if d else ""))
        lines.append("")
    if len(lines) == 1:
        lines.append("_No notes yet._")
    lines.append("<!-- /AUTO:members -->")
    return "\n".join(lines)


def timeline_block(params: str, all_notes) -> str:
    kv = dict(p.split("=", 1) for p in params.split() if "=" in p)
    types = set(kv.get("types", "event").split(","))
    lo = int(kv["min"]) if "min" in kv else None
    hi = int(kv["max"]) if "max" in kv else None
    rows = []
    for path, fm in all_notes:
        if fm.get("type") not in types or fm.get("date_start") is None:
            continue
        d = fm["date_start"]
        if (lo is not None and d < lo) or (hi is not None and d > hi):
            continue
        rows.append((d, path, fm))
    rows.sort(key=lambda r: (r[0], r[1].stem))
    out = [f"<!-- AUTO:timeline{params}-->", "| Date | Note | Type | Era |", "|---|---|---|---|"]
    for d, path, fm in rows:
        end = fm.get("date_end")
        date = fmt_date(d) + (f" to {fmt_date(end)}" if end is not None and end != d else "")
        era = links_in(fm.get("era"))
        out.append(f"| {date} | [[{path.stem}]] | {fm.get('type')} | " + (f"[[{era[0]}]]" if era else "") + " |")
    out.append("<!-- /AUTO:timeline -->")
    return "\n".join(out)


def ensure_section(text: str, heading: str) -> str:
    if "<!-- AUTO:members -->" in text:
        return text
    return text.rstrip() + f"\n\n## {heading}\n<!-- AUTO:members -->\n<!-- /AUTO:members -->\n"


def main() -> int:
    all_notes = [(p, parse_note(p)[0]) for p in iter_notes()]
    by_era, by_region, by_theme = defaultdict(list), defaultdict(list), defaultdict(list)
    for p, fm in all_notes:
        for key, bucket in (("era", by_era), ("region", by_region)):
            tgt = links_in(fm.get(key))
            if tgt and fm.get("type") not in ("era", "region"):
                bucket[tgt[0].lower()].append((p, fm))
        for slug in fm.get("themes") or []:
            if fm.get("type") in TYPE_LABEL:
                by_theme[slug].append((p, fm))

    changed = 0
    for path, fm in all_notes:
        t = fm.get("type")
        text = path.read_text(encoding="utf-8")
        new = text
        if t == "era":
            new = ensure_section(new, "Notes in This Era")
            new = MEMBER_BLOCK.sub(lambda m: members_block(by_era[path.stem.lower()]), new)
        elif t == "region":
            new = ensure_section(new, "Notes in This Region")
            new = MEMBER_BLOCK.sub(lambda m: members_block(by_region[path.stem.lower()]), new)
        elif t == "theme":
            new = MEMBER_BLOCK.sub(lambda m: members_block(by_theme[fm.get("slug")]), new)
        elif t == "timeline":
            new = TIMELINE_BLOCK.sub(lambda m: timeline_block(m.group(1), all_notes), new)
        if new != text:
            path.write_text(new, encoding="utf-8", newline="\n")
            changed += 1
            print("updated", path.relative_to(VAULT_ROOT).as_posix())
    print(f"{changed} hub/timeline note(s) updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
