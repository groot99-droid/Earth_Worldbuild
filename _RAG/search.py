"""Hybrid search over the vault index: vector similarity + FTS5 BM25, fused with reciprocal-rank fusion.

CLI examples:
    python _RAG/search.py "when did humans first control fire"
    python _RAG/search.py "trade networks" --type event --era "Classical Antiquity" -k 5
    python _RAG/search.py "plague" --from -1000 --to 1500 --expand
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_index import RAG_DIR, db_path, get_model, load_config  # noqa: E402
from vault import VAULT_ROOT  # noqa: E402

STOP = {"the", "a", "an", "of", "and", "or", "to", "in", "on", "for", "is", "was", "were", "are", "what",
        "when", "did", "do", "does", "how", "why", "who", "which", "with", "by", "at", "from", "as", "it"}


def fmt_date(y) -> str:
    if y is None:
        return ""
    if y <= -1_000_000_000:
        return f"{-y / 1e9:g} Ga"
    if y <= -1_000_000:
        return f"{-y / 1e6:g} Ma"
    if y <= -10_000:
        return f"{-y / 1e3:g} ka"
    return f"{-y} BCE" if y < 0 else f"{y} CE"


class VaultSearch:
    def __init__(self) -> None:
        self.cfg = load_config()
        self._model = None
        self.reload()

    # ---- loading -------------------------------------------------------------------------
    def reload(self) -> None:
        path = db_path(self.cfg)
        if not path.exists():
            raise RuntimeError("Index not found. Run: python _RAG/build_index.py")
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        rows = self.conn.execute("SELECT id, path, title, heading, text, vec FROM chunks ORDER BY id").fetchall()
        self.ids = [r["id"] for r in rows]
        self.idx_of = {cid: i for i, cid in enumerate(self.ids)}
        self.chunks = [dict(id=r["id"], path=r["path"], title=r["title"], heading=r["heading"], text=r["text"]) for r in rows]
        self.mat = (np.vstack([np.frombuffer(r["vec"], dtype=np.float32) for r in rows])
                    if rows else np.zeros((0, 384), np.float32))
        self.notes = {r["path"]: dict(r) for r in self.conn.execute("SELECT * FROM notes")}
        self.by_title = {n["title"].lower(): n for n in self.notes.values()}

    @property
    def model(self):
        if self._model is None:
            self._model = get_model(self.cfg)
        return self._model

    # ---- filters -------------------------------------------------------------------------
    def _mask(self, type=None, era=None, region=None, theme=None, date_from=None, date_to=None) -> np.ndarray:
        ok = np.ones(len(self.chunks), dtype=bool)
        if not any(v is not None for v in (type, era, region, theme, date_from, date_to)):
            return ok
        for i, c in enumerate(self.chunks):
            n = self.notes[c["path"]]
            if type and n["type"] != type:
                ok[i] = False
            elif era and (n["era"] or "").lower() != era.lower():
                ok[i] = False
            elif region and (n["region"] or "").lower() != region.lower():
                ok[i] = False
            elif theme and f",{theme}," not in (n["themes"] or ""):
                ok[i] = False
            elif date_from is not None and (n["date_start"] is None or n["date_start"] < date_from):
                ok[i] = False
            elif date_to is not None and (n["date_start"] is None or n["date_start"] > date_to):
                ok[i] = False
        return ok

    # ---- retrieval -----------------------------------------------------------------------
    def search(self, query: str, k: int | None = None, expand: bool = False, **filters) -> list[dict]:
        s = self.cfg["search"]
        k = k or s["default_k"]
        ok = self._mask(**filters)
        if not ok.any():
            return []
        cand = s["candidates"]

        qv = np.array(list(self.model.query_embed(query))[0], dtype=np.float32)
        qv /= (np.linalg.norm(qv) or 1.0)
        sims = self.mat @ qv
        sims[~ok] = -np.inf
        vec_rank = [int(i) for i in np.argsort(-sims)[:cand] if np.isfinite(sims[i])]

        toks = [t for t in re.findall(r"\w+", query.lower()) if t not in STOP]
        bm_rank: list[int] = []
        if toks:
            fts_q = " OR ".join(f'"{t}"' for t in toks)
            try:
                rows = self.conn.execute(
                    "SELECT rowid FROM chunks_fts WHERE chunks_fts MATCH ? ORDER BY bm25(chunks_fts, 5.0, 2.0, 1.0) LIMIT ?",
                    (fts_q, cand * 2)).fetchall()
                bm_rank = [self.idx_of[r[0]] for r in rows if r[0] in self.idx_of and ok[self.idx_of[r[0]]]][:cand]
            except sqlite3.OperationalError:
                bm_rank = []

        score: dict[int, float] = {}
        for ranking in (vec_rank, bm_rank):
            for r, i in enumerate(ranking):
                score[i] = score.get(i, 0.0) + 1.0 / (s["rrf_k"] + r + 1)

        hw = s.get("heading_weights", {})
        for i in score:
            score[i] *= hw.get(self.chunks[i]["heading"], 1.0)

        results, per_note = [], {}
        for i, sc in sorted(score.items(), key=lambda kv: -kv[1]):
            c = self.chunks[i]
            if per_note.get(c["path"], 0) >= 2:
                continue
            per_note[c["path"]] = per_note.get(c["path"], 0) + 1
            n = self.notes[c["path"]]
            results.append({
                "rank": len(results) + 1, "score": round(sc, 5), "title": c["title"], "path": c["path"],
                "type": n["type"], "era": n["era"], "region": n["region"],
                "date": fmt_date(n["date_start"]), "confidence": n["confidence"], "status": n["status"],
                "heading": c["heading"], "text": c["text"],
            })
            if len(results) >= k:
                break
        if expand:
            seen = set()
            for r in results[:3]:
                for nb in self.neighbors(r["title"])["outgoing"]:
                    if nb.get("type") not in ("source", "meta"):  # bibliography is noise here
                        seen.add(nb["title"])
            listed = {r["title"] for r in results}
            for r in results[:1]:
                r["neighbors"] = [self.brief(t) for t in sorted(seen) if t not in listed][:10]
        return results

    # ---- graph & lookup ------------------------------------------------------------------
    def resolve(self, name: str) -> dict | None:
        name = name.strip().strip("[]")
        if name.lower() in self.by_title:
            return self.by_title[name.lower()]
        norm = name.replace("\\", "/").lstrip("./")
        return self.notes.get(norm) or self.notes.get(norm + ".md")

    def brief(self, title: str) -> dict:
        n = self.resolve(title)
        if not n:
            return {"title": title, "type": None}
        summ = next((c["text"] for c in self.chunks if c["path"] == n["path"] and c["heading"] == "Summary"), "")
        return {"title": n["title"], "type": n["type"], "date": fmt_date(n["date_start"]),
                "path": n["path"], "summary": summ[:240]}

    def neighbors(self, name: str) -> dict:
        n = self.resolve(name)
        if not n:
            return {"error": f"note not found: {name}", "outgoing": [], "incoming": []}
        out = [self.brief(t) for t in json.loads(n["links"]) if self.resolve(t) and self.resolve(t)["path"] != n["path"]]
        inc = [self.brief(m["title"]) for m in self.notes.values()
               if m["path"] != n["path"] and n["title"] in json.loads(m["links"])]
        return {"title": n["title"], "outgoing": out, "incoming": inc}

    def read_note(self, name: str) -> str:
        n = self.resolve(name)
        if not n:
            return f"Note not found: {name}"
        return (VAULT_ROOT / n["path"]).read_text(encoding="utf-8")

    def timeline(self, start: int | None = None, end: int | None = None, theme: str | None = None,
                 types: tuple[str, ...] = ("event",)) -> list[dict]:
        out = []
        for n in self.notes.values():
            d = n["date_start"]
            if d is None or n["type"] not in types:
                continue
            if (start is not None and d < start) or (end is not None and d > end):
                continue
            if theme and f",{theme}," not in (n["themes"] or ""):
                continue
            out.append({"date": fmt_date(d), "year": d, "title": n["title"], "type": n["type"],
                        "era": n["era"], "region": n["region"], "path": n["path"]})
        return sorted(out, key=lambda r: (r["year"], r["title"]))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query")
    ap.add_argument("-k", type=int, default=None)
    ap.add_argument("--type")
    ap.add_argument("--era")
    ap.add_argument("--region")
    ap.add_argument("--theme")
    ap.add_argument("--from", dest="date_from", type=int)
    ap.add_argument("--to", dest="date_to", type=int)
    ap.add_argument("--expand", action="store_true", help="add linked neighbor notes for the top hit")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    vs = VaultSearch()
    res = vs.search(a.query, k=a.k, expand=a.expand, type=a.type, era=a.era, region=a.region,
                    theme=a.theme, date_from=a.date_from, date_to=a.date_to)
    if a.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return
    for r in res:
        print(f"{r['rank']}. {r['title']}  [{r['type']}]  {r['date']}  ({r['heading']})  score={r['score']}")
        print("   " + r["text"].replace("\n", " ")[:220])
        for nb in r.get("neighbors", []):
            print(f"   ~ neighbor: {nb['title']} [{nb['type']}]")
    if not res:
        print("No results.")


if __name__ == "__main__":
    main()
