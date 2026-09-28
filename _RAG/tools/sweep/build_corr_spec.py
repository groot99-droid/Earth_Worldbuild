"""python build_corr_spec.py <corrections workflow .output> <spec out> <review out>
Validates each replacement (old occurs exactly once in the current note file, no frontmatter touch) and writes an apply_patch spec."""
import json
import re
import sys
from pathlib import Path

SRC, OUT, REVIEW = sys.argv[1:4]
VAULT = Path(r"C:\Users\utopi\OneDrive\Desktop\Earth _WorldBuilding")
raw = json.load(open(SRC, encoding="utf-8"))
results = raw["result"] if isinstance(raw, dict) else raw
FM_END = re.compile(r"\A---\r?\n.*?\r?\n---\r?\n", re.S)

# find note files by title
paths = {}
for p in VAULT.rglob("*.md"):
    if any(part in {"_RAG", "_Site", "_Museum", "_Rewrite", ".obsidian", ".claude", "Art-Talk-main", "_Templates"} for part in p.relative_to(VAULT).parts):
        continue
    paths[p.stem] = p

notes, lines, fm_issues = [], [], []
for r in results:
    t = r["title"]
    p = paths.get(t)
    if not p:
        lines.append(f"!! {t}: file not found")
        continue
    text = p.read_text(encoding="utf-8")
    m = FM_END.match(text)
    body = text[m.end():] if m else text
    reps = []
    for x in r.get("replacements", []):
        old, new = x["old"], x["new"]
        n_all = text.count(old)
        n_body = body.count(old)
        if n_all != 1 or n_body != 1:
            lines.append(f"!! {t}: old text found {n_all}x (body {n_body}x), skipped: {old[:80]}")
            continue
        if old == new:
            continue
        if "\u2014" in new or "\u2013" in new:
            lines.append(f"!! {t}: dash in replacement, skipped: {new[:80]}")
            continue
        reps.append([old, new])
        lines.append(f"[{t}]\n   - {old}\n   + {new}\n   ({x.get('why', '')[:140]})")
    if reps:
        notes.append({"note": t, "replace": reps})
    for f in r.get("frontmatter_issues", []):
        fm_issues.append(f"[{t}] {f}")
    for u in r.get("left_unchanged", []):
        lines.append(f"   ~ unchanged [{t}]: {u[:160]}")

Path(OUT).write_text(json.dumps({"date": "2026-09-27", "notes": notes}, ensure_ascii=False, indent=1), encoding="utf-8")
Path(REVIEW).write_text("\n".join(lines) + "\n\nFRONTMATTER ISSUES\n" + "\n".join(fm_issues) + "\n", encoding="utf-8")
print(f"{len(notes)} notes, {sum(len(n['replace']) for n in notes)} replacements; {len(fm_issues)} frontmatter issues")
