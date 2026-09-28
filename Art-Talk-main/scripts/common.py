"""Shared helpers for reading artist Markdown files.

Each file in ``artists/`` starts with YAML front matter (metadata and the
list of works) followed by a Markdown body split into ``## `` sections.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ARTISTS_DIR = ROOT / "artists"
IMAGES_DIR = ROOT / "images"
DATA_DIR = ROOT / "data"
RAG_DIR = ROOT / "rag"
CREDITS_FILE = DATA_DIR / "image-credits.json"

REQUIRED_SECTIONS = ["Overview", "Life", "Style & Technique", "Legacy", "Key Works", "Sources"]
PROSE_SECTIONS = ["Overview", "Life", "Style & Technique", "Legacy"]
MIN_WORKS = 5

WORKS_START = "<!-- works:start -->"
WORKS_END = "<!-- works:end -->"

_FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)


@dataclass
class Artist:
    path: Path
    meta: dict
    body: str
    sections: dict[str, str] = field(default_factory=dict)
    summary: str = ""

    @property
    def slug(self) -> str:
        return self.meta["slug"]

    @property
    def name(self) -> str:
        return self.meta["name"]

    @property
    def works(self) -> list[dict]:
        return self.meta.get("works", [])

    def image_path(self, work: dict) -> Path:
        return IMAGES_DIR / self.slug / f"{work['id']}.jpg"

    def image_rel(self, work: dict) -> str:
        """Image path relative to the repo root."""
        return f"images/{self.slug}/{work['id']}.jpg"

    def context(self) -> str:
        movements = ", ".join(self.meta.get("movements", []))
        return f"{self.name} ({self.meta['lifespan']}, {self.meta['country']}, {movements})"


def parse_sections(body: str) -> tuple[str, dict[str, str]]:
    """Split a body into the summary (text between the H1 and the first H2)
    and a mapping of ``## Heading`` -> section text."""
    sections: dict[str, str] = {}
    summary_lines: list[str] = []
    current: str | None = None
    buf: list[str] = []
    for line in body.splitlines():
        if line.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current = line[3:].strip()
            buf = []
        elif current is None:
            if not line.startswith("# "):
                summary_lines.append(line)
        else:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip()
    summary = "\n".join(summary_lines).strip()
    summary = re.sub(r"^>\s?", "", summary, flags=re.M).strip()
    return summary, sections


def load_artist(path: Path) -> Artist:
    text = path.read_text(encoding="utf-8")
    m = _FRONT_MATTER.match(text)
    if not m:
        raise ValueError(f"{path}: missing YAML front matter")
    meta = yaml.safe_load(m.group(1))
    body = text[m.end():]
    summary, sections = parse_sections(body)
    return Artist(path=path, meta=meta, body=body, sections=sections, summary=summary)


def load_artists() -> list[Artist]:
    artists = [load_artist(p) for p in sorted(ARTISTS_DIR.glob("*.md"))]
    artists.sort(key=lambda a: (a.meta["born"], a.name))
    return artists


def load_credits() -> dict:
    if CREDITS_FILE.exists():
        return json.loads(CREDITS_FILE.read_text(encoding="utf-8"))
    return {}


def save_credits(credits: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CREDITS_FILE.write_text(
        json.dumps(dict(sorted(credits.items())), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def strip_works_block(text: str) -> str:
    """Remove the generated works block, leaving only hand-written prose."""
    return re.sub(
        re.escape(WORKS_START) + r".*?" + re.escape(WORKS_END), "", text, flags=re.S
    ).strip()
