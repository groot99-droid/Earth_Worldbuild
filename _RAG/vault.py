"""Shared helpers: vault discovery, frontmatter parsing, wikilink extraction."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

VAULT_ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {"_RAG", ".obsidian", "_Templates", ".git", "node_modules", ".trash", "Art-Talk-main", "_Site", "_Museum", "_Rewrite", ".claude"}  # Art-Talk-main, _Site, _Museum and _Rewrite are standalone projects/working folders, not vault notes

FM_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.DOTALL)
WIKILINK_RE = re.compile(r"\[\[([^\]\|#]+)(?:#[^\]\|]*)?(?:\|[^\]]*)?\]\]")


def iter_notes(root: Path = VAULT_ROOT):
    """Yield every markdown note path in the vault, skipping tooling folders."""
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        yield path


def parse_note(path: Path):
    """Return (frontmatter dict, body str). Frontmatter is {} if absent or invalid."""
    text = path.read_text(encoding="utf-8")
    m = FM_RE.match(text)
    if not m:
        return {}, text
    try:
        fm = yaml.safe_load(m.group(1)) or {}
        if not isinstance(fm, dict):
            fm = {}
    except yaml.YAMLError:
        fm = {}
    return fm, text[m.end():]


def links_in(value) -> list[str]:
    """Extract wikilink targets from a string or list (frontmatter values or body text)."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        out = []
        for v in value:
            out.extend(links_in(v))
        return out
    return [m.group(1).strip() for m in WIKILINK_RE.finditer(str(value))]


def title_index(root: Path = VAULT_ROOT) -> dict[str, Path]:
    """Map lowercase note title (filename stem) -> path."""
    return {p.stem.lower(): p for p in iter_notes(root)}
