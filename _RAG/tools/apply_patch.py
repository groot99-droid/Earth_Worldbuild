"""Apply fact-check patches to vault notes safely (the only way source and cited notes are edited in bulk).

Usage:  python _RAG/tools/apply_patch.py spec.json [--dry]

Guards: a note is written only if every 'old' text matches exactly once, every cited source exists, the new
frontmatter still parses, and the file did not change on disk while the patch was prepared (another writer).
Each written file is first copied to _RAG/source_cache/patch_backups/<run>/.

Spec (all keys optional except where noted):
{
  "date": "2026-09-25",                       # defaults to today
  "sources_new": [ {title, citation, url, kind, reliability, used, caveats, [access, access_route, read_on]} ],
  "source_updates": [ {
      "title": "Britannica on Timur",          # required, an existing 07_Sources note
      "set": {"access": "archived-copy", "access_route": "...", "read_on": "2026-09-25"},   # frontmatter fields
      "citation": "...",                       # replaces frontmatter citation and the ## Citation section
      "used": "...",                           # replaces the ## What It Is Used For section
      "caveats": "...",                        # replaces the ## Caveats section
      "replace": [[old, new]],                 # exact-once replacements anywhere in the note
      "mark": "done"                           # queue status (pending|fetched|done|blocked)
  } ],
  "notes": [ {
      "note": "Timur",                         # required
      "replace": [[old, new]],                 # exact-once text replacements (body or frontmatter)
      "checks": ["claim [Source A; Source B]"],          # appended to fact_checks, dated `date`
      "replace_checks": [["substring of one existing check", "new claim [Source]"]],
      "drop_checks": ["substring of one existing check"],
      "sources": ["Source Title"]              # added to the sources: list if missing
  } ],
  "discrepancies": [ {note, source, was, text_says, action} ]   # appended to source_cache/discrepancies.md
}
"""
from __future__ import annotations

import difflib
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import yaml

RAG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAG))
from vault import FM_RE, VAULT_ROOT, iter_notes  # noqa: E402

CACHE = RAG / "source_cache"
ACCESS = {"full-text", "archived-copy", "reference-text", "abstract", "summary-only", "not-consulted"}

SRC_T = """---
title: "{title}"
type: source
themes: []
related: []
sources: []
confidence: {confidence}
status: draft
tags: []
citation: "{citation}"
url: "{url}"
source_kind: {kind}
reliability: {reliability}
verified: true
checked_on: {date}
{access_lines}---

## Citation
{citation}

## What It Is Used For
{used}

## Caveats
{caveats}
"""


class Abort(Exception):
    pass


def yaml_scalar(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    if s.lower() not in ("true", "false", "yes", "no", "on", "off", "null", "y", "n") and (
            re.fullmatch(r"\d{4}-\d{2}-\d{2}", s) or re.fullmatch(r"[a-z]+(-[a-z]+)*", s)):
        return s                                   # dates and simple enum words stay unquoted, like existing notes
    return json.dumps(s, ensure_ascii=False)       # a JSON string is a valid YAML double-quoted scalar


def split_note(text: str) -> tuple[str, str]:
    m = FM_RE.match(text)
    if not m:
        raise Abort("no frontmatter")
    return text[: m.end()], text[m.end():]


def set_field(text: str, key: str, value) -> str:
    fm, body = split_note(text)
    line = f"{key}: {yaml_scalar(value)}"
    pat = re.compile(rf"^{re.escape(key)}:.*$", re.M)
    if pat.search(fm):
        fm = pat.sub(lambda _: line, fm, count=1)
    else:                                          # insert before the closing ---
        idx = fm.rstrip().rfind("---")
        fm = fm[:idx] + line + "\n" + fm[idx:]
    return fm + body


def replace_section(text: str, heading: str, new_body: str) -> str:
    m = re.search(rf"^## {re.escape(heading)}[ \t]*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    if not m:
        raise Abort(f"no '## {heading}' section")
    more = m.end(1) < len(text)                    # another section follows: keep one blank line before it
    return text[: m.start(1)] + new_body.strip() + ("\n\n" if more else "\n") + text[m.end(1):]


def parse_list_line(fm: str, key: str) -> tuple[re.Match | None, list]:
    m = re.search(rf"^{key}: \[(.*)\]$", fm, re.M)
    if not m:
        return None, []
    return m, yaml.safe_load(f"[{m.group(1)}]") or []


def emit_list(key: str, items: list[str]) -> str:
    line = f"{key}: [" + ", ".join(json.dumps(x, ensure_ascii=False) for x in items) + "]"
    assert yaml.safe_load(line)[key] == items, "list did not round-trip"
    return line


def edit_note(text: str, n: dict, date: str, known: set[str]) -> str:
    for old, new in n.get("replace", []):
        if text.count(old) != 1:
            raise Abort(f"text not found exactly once ({text.count(old)}x): {old[:70]}...")
        text = text.replace(old, new)
    if any(k in n for k in ("checks", "replace_checks", "drop_checks")):
        fm, body = split_note(text)
        m, items = parse_list_line(fm, "fact_checks")
        if m is None and (n.get("replace_checks") or n.get("drop_checks")):
            raise Abort("no single-line fact_checks")
        for old, new in n.get("replace_checks", []):
            hits = [i for i, x in enumerate(items) if old in x]
            if len(hits) != 1:
                raise Abort(f"check substring matched {len(hits)} entries: {old[:60]}")
            items[hits[0]] = f"{date}: {new}"
        for old in n.get("drop_checks", []):
            hits = [i for i, x in enumerate(items) if old in x]
            if len(hits) != 1:
                raise Abort(f"drop_checks substring matched {len(hits)} entries: {old[:60]}")
            del items[hits[0]]
        for c in n.get("checks", []):
            items.append(f"{date}: {c}")
        for x in [c for c in n.get("checks", [])] + [c for _, c in n.get("replace_checks", [])]:
            if '"' in x or not re.search(r"\[[^\]]+\]$", x):
                raise Abort(f"check must end with [Source] and contain no double quotes: {x[:60]}")
            for src in re.findall(r"\[([^\]]+)\]", x)[-1].split("; "):
                if src not in known:
                    raise Abort(f"check cites unknown source: {src}")
        if m is None:                                  # note had no fact_checks line at all: insert one
            idx = fm.rstrip().rfind("---")
            fm = fm[:idx] + emit_list("fact_checks", items) + "\n" + fm[idx:]
        else:
            fm = fm[: m.start()] + emit_list("fact_checks", items) + fm[m.end():]
        text = fm + body
    if n.get("sources"):
        fm, body = split_note(text)
        m, items = parse_list_line(fm, "sources")
        if m is None:
            raise Abort("no single-line sources")
        for s in n["sources"]:
            if s not in known:
                raise Abort(f"unknown source {s}")
            if f"[[{s}]]" not in items:
                items.append(f"[[{s}]]")
        fm = fm[: m.start()] + emit_list("sources", items) + fm[m.end():]
        text = fm + body
    return text


def edit_source(text: str, u: dict) -> str:
    text = edit_note(text, {"replace": u.get("replace", [])}, "", set())
    for k, v in (u.get("set") or {}).items():
        if k == "access" and v not in ACCESS:
            raise Abort(f"bad access value {v!r}")
        text = set_field(text, k, v)
    if "citation" in u:
        text = set_field(text, "citation", u["citation"])
        text = replace_section(text, "Citation", u["citation"])
    if "used" in u:
        text = replace_section(text, "What It Is Used For", u["used"])
    if "caveats" in u:
        text = replace_section(text, "Caveats", u["caveats"])
    return text


def validate_text(text: str, title: str) -> None:
    parsed = yaml.safe_load(FM_RE.match(text).group(1))
    if not isinstance(parsed, dict) or parsed.get("title") != title:
        raise Abort("frontmatter no longer parses or title changed")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    dry = "--dry" in sys.argv
    date = spec.get("date") or datetime.now().date().isoformat()
    existing = {p.stem: p for p in iter_notes()}
    new_titles = {s["title"] for s in spec.get("sources_new", [])}
    known = set(existing) | new_titles
    run = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = CACHE / "patch_backups" / run
    bad = 0
    written: list[str] = []

    def write(path: Path, before: str | None, after: str, mtime: float | None) -> None:
        if dry:
            if before is not None:
                diff = list(difflib.unified_diff(before.splitlines(), after.splitlines(), "before", "after", n=0, lineterm=""))
                for ln in diff[:60]:
                    print("    " + (ln[:220] + ("..." if len(ln) > 220 else "")))
            return
        if before is not None:
            if path.stat().st_mtime != mtime:
                raise Abort("file changed on disk while patching (another writer); rerun")
            dest = backup_dir / path.relative_to(VAULT_ROOT)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
        path.write_text(after, encoding="utf-8", newline="\n")

    for s in spec.get("sources_new", []):
        if '"' in s["title"] + s["citation"]:
            print(f"ABORT source {s['title']}: double quote in title or citation")
            bad += 1
            continue
        if s["title"] in existing:
            print("source exists, skipping:", s["title"])
            continue
        lines = "".join(f"{k}: {yaml_scalar(s[k])}\n" for k in ("access", "access_route", "read_on") if k in s)
        s = {"confidence": "medium", "kind": "reference", "reliability": "medium", **s, "date": date, "access_lines": lines}
        try:
            write(VAULT_ROOT / "07_Sources" / (s["title"] + ".md"), None, SRC_T.format(**s), None)
            print("source created:", s["title"])
        except Abort as e:
            print(f"ABORT source {s['title']}: {e}")
            bad += 1

    for u in spec.get("source_updates", []):
        p = existing.get(u["title"])
        if p is None or p.parent.name != "07_Sources":
            print("SOURCE NOT FOUND", u["title"])
            bad += 1
            continue
        try:
            before, mtime = p.read_text(encoding="utf-8"), p.stat().st_mtime
            after = edit_source(before, u)
            validate_text(after, u["title"])
            print("source updated:", u["title"])
            write(p, before, after, mtime)
            written.append(u["title"])
        except Abort as e:
            print(f"ABORT source {u['title']}: {e}")
            bad += 1

    for n in spec.get("notes", []):
        p = existing.get(n["note"])
        if p is None:
            print("NOTE NOT FOUND", n["note"])
            bad += 1
            continue
        try:
            before, mtime = p.read_text(encoding="utf-8"), p.stat().st_mtime
            after = edit_note(before, n, date, known)
            validate_text(after, n["note"])
            print("patched:", n["note"])
            write(p, before, after, mtime)
            written.append(n["note"])
        except Abort as e:
            print(f"ABORT {n['note']}: {e}")
            bad += 1

    if not dry:
        if spec.get("discrepancies"):
            CACHE.mkdir(parents=True, exist_ok=True)
            log = CACHE / "discrepancies.md"
            with log.open("a", encoding="utf-8", newline="\n") as f:
                if not log.stat().st_size:
                    f.write("# Discrepancies found while re-reading sources\n")
                f.write(f"\n## {date}\n")
                for d in spec["discrepancies"]:
                    f.write(f"- **{d.get('note', '?')}** vs [{d.get('source', '?')}]: was: {d.get('was', '')} | source text: "
                            f"{d.get('text_says', '')} | action: {d.get('action', '')}\n")
        qp = CACHE / "queue.json"
        marks = {u["title"]: u["mark"] for u in spec.get("source_updates", []) if u.get("mark") and u["title"] in written}
        if marks and qp.exists():
            q = json.loads(qp.read_text(encoding="utf-8"))
            for t, st in marks.items():
                if t in q:
                    q[t]["status"] = st
                    q[t]["done_on"] = date
                    q[t]["access"] = next((u["set"].get("access") for u in spec["source_updates"] if u["title"] == t and u.get("set")), q[t].get("access"))
                    q[t]["discrepancies"] = [d for d in spec.get("discrepancies", []) if d.get("source") == t] or q[t].get("discrepancies", [])
            qp.write_text(json.dumps(q, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print("DONE", "with problems" if bad else "clean", "(dry run)" if dry else f"({len(written)} notes written; backups in {backup_dir})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
