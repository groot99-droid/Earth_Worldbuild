"""Build (or incrementally update) the vault search index.

Chunks every note by `##` heading, embeds each chunk locally with fastembed, and stores chunks,
vectors, metadata, and an FTS5 keyword index in SQLite.

Usage:
    python _RAG/build_index.py            # incremental: only changed notes are re-embedded
    python _RAG/build_index.py --force    # rebuild everything
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vault import VAULT_ROOT, iter_notes, links_in, parse_note  # noqa: E402

RAG_DIR = Path(__file__).resolve().parent

SCHEMA = """
CREATE TABLE IF NOT EXISTS notes(
    path TEXT PRIMARY KEY, hash TEXT, title TEXT, type TEXT, era TEXT, region TEXT,
    themes TEXT, date_start INTEGER, date_end INTEGER, confidence TEXT, status TEXT, links TEXT);
CREATE TABLE IF NOT EXISTS chunks(
    id INTEGER PRIMARY KEY AUTOINCREMENT, path TEXT, title TEXT, heading TEXT, text TEXT, vec BLOB);
CREATE INDEX IF NOT EXISTS chunks_path ON chunks(path);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(title, heading, text, tokenize='porter unicode61');
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
"""

SECTION_RE = re.compile(r"^## +(.+?)\s*$", re.MULTILINE)
AUTO_RE = re.compile(r"<!-- /?AUTO:[^>]*-->")


def load_config() -> dict:
    return yaml.safe_load((RAG_DIR / "config.yaml").read_text(encoding="utf-8"))


def db_path(cfg: dict) -> Path:
    p = RAG_DIR / cfg["index"]["db_path"]
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def clean_wikilinks(text: str) -> str:
    """Replace [[Target|Alias]] with readable text so embeddings see words, not markup."""
    return re.sub(r"\[\[([^\]\|#]+)(?:#[^\]\|]*)?(?:\|([^\]]*))?\]\]", lambda m: m.group(2) or m.group(1), text)


def split_long(text: str, max_words: int, overlap: int) -> list[str]:
    """Split a long section on line boundaries into pieces of about max_words with overlap."""
    lines = text.splitlines()
    pieces, cur, count = [], [], 0
    for line in lines:
        w = len(line.split())
        if cur and count + w > max_words:
            pieces.append("\n".join(cur))
            # carry overlap: trailing lines totalling about `overlap` words
            carry, cw = [], 0
            for prev in reversed(cur):
                cw += len(prev.split())
                carry.insert(0, prev)
                if cw >= overlap:
                    break
            cur, count = carry, cw
        cur.append(line)
        count += w
    if cur:
        pieces.append("\n".join(cur))
    return [p for p in pieces if p.strip()]


def chunk_note(fm: dict, body: str, title: str, cfg: dict) -> list[tuple[str, str]]:
    """Return [(heading, text)] chunks for a note."""
    ch = cfg["chunking"]
    skip = tuple(ch.get("skip_section_prefixes", []))
    matches = list(SECTION_RE.finditer(body))
    sections: list[tuple[str, str]] = []
    if not matches:
        sections.append(("Overview", body))
    else:
        pre = body[: matches[0].start()].strip()
        if pre:
            sections.append(("Overview", pre))
        for i, m in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
            sections.append((m.group(1).strip(), body[m.end():end]))
    out = []
    for heading, text in sections:
        if heading.startswith(skip):
            continue
        text = clean_wikilinks(AUTO_RE.sub("", text)).strip()
        if not text:
            continue
        if len(text.split()) > ch["max_words"]:
            for piece in split_long(text, ch["max_words"], ch["overlap_words"]):
                out.append((heading, piece))
        else:
            out.append((heading, text))
    return out


def context_prefix(fm: dict, title: str) -> str:
    """Metadata header prepended to every chunk so retrieval keeps its bearings."""
    bits = [str(fm.get("type", ""))]
    for key in ("era", "region"):
        v = links_in(fm.get(key))
        if v:
            bits.append(v[0])
    return f"{title} ({'; '.join(b for b in bits if b)})"


def normalize(mat: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return (mat / norms).astype(np.float32)


def get_model(cfg: dict):
    import os

    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")  # Windows without Developer Mode
    from fastembed import TextEmbedding

    cache = RAG_DIR / cfg["embedding"]["cache_dir"]
    cache.mkdir(parents=True, exist_ok=True)
    return TextEmbedding(model_name=cfg["embedding"]["model"], cache_dir=str(cache))


def build(force: bool = False, verbose: bool = True) -> dict:
    cfg = load_config()
    conn = sqlite3.connect(db_path(cfg))
    conn.executescript(SCHEMA)

    model_name = cfg["embedding"]["model"]
    row = conn.execute("SELECT value FROM meta WHERE key='model'").fetchone()
    if force or (row and row[0] != model_name):
        conn.executescript("DELETE FROM notes; DELETE FROM chunks; DELETE FROM chunks_fts;")
    conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES('model', ?)", (model_name,))

    known = {r[0]: r[1] for r in conn.execute("SELECT path, hash FROM notes")}
    current: dict[str, Path] = {}
    for p in iter_notes():
        current[p.relative_to(VAULT_ROOT).as_posix()] = p

    removed = [k for k in known if k not in current]
    for k in removed:
        _delete_note(conn, k)

    todo = []
    for rel, p in current.items():
        h = hashlib.sha1(p.read_bytes()).hexdigest()
        if known.get(rel) != h:
            todo.append((rel, p, h))

    stats = {"notes_total": len(current), "notes_updated": len(todo), "notes_removed": len(removed), "chunks_added": 0}
    if not todo:
        conn.commit()
        conn.close()
        if verbose:
            print(f"Index up to date ({len(current)} notes).")
        return stats

    model = get_model(cfg)
    t0 = time.time()
    pending: list[tuple[str, dict, str, str, str]] = []  # rel, fm, title, heading, text
    note_rows = []
    for rel, p, h in todo:
        fm, body = parse_note(p)
        title = p.stem
        note_rows.append((rel, h, title, fm))
        for heading, text in chunk_note(fm, body, title, cfg):
            pending.append((rel, fm, title, heading, text))

    texts = [f"{context_prefix(fm, title)} > {heading}\n{text}" for rel, fm, title, heading, text in pending]
    if verbose:
        print(f"Embedding {len(texts)} chunks from {len(todo)} changed note(s)...")
    vecs = normalize(np.array(list(model.embed(texts, batch_size=32)), dtype=np.float32)) if texts else np.zeros((0, 384), np.float32)

    for rel, _, _ in todo:
        _delete_note(conn, rel)
    for rel, h, title, fm in note_rows:
        links = sorted({l for l in links_in([fm.get(k) for k in ("era", "region", "related", "sources")])})
        body_links = links_in(parse_note(current[rel])[1])
        links = sorted(set(links) | set(body_links))
        conn.execute(
            "INSERT INTO notes VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (rel, h, title, fm.get("type"),
             (links_in(fm.get("era")) or [None])[0], (links_in(fm.get("region")) or [None])[0],
             "," + ",".join(fm.get("themes") or []) + ",",
             fm.get("date_start"), fm.get("date_end"), fm.get("confidence"), fm.get("status"),
             json.dumps(links)),
        )
    for (rel, fm, title, heading, text), vec in zip(pending, vecs):
        cur = conn.execute("INSERT INTO chunks(path, title, heading, text, vec) VALUES(?,?,?,?,?)",
                           (rel, title, heading, text, vec.tobytes()))
        conn.execute("INSERT INTO chunks_fts(rowid, title, heading, text) VALUES(?,?,?,?)",
                     (cur.lastrowid, title, heading, text))
    conn.commit()
    conn.close()
    stats["chunks_added"] = len(pending)
    if verbose:
        print(f"Done in {time.time() - t0:.1f}s: {stats}")
    return stats


def _delete_note(conn: sqlite3.Connection, rel: str) -> None:
    ids = [r[0] for r in conn.execute("SELECT id FROM chunks WHERE path=?", (rel,))]
    conn.executemany("DELETE FROM chunks_fts WHERE rowid=?", [(i,) for i in ids])
    conn.execute("DELETE FROM chunks WHERE path=?", (rel,))
    conn.execute("DELETE FROM notes WHERE path=?", (rel,))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="rebuild the whole index")
    build(force=ap.parse_args().force)
