#!/usr/bin/env python3
"""Quality gate for the suggestion engine: hidden-link prediction.

Hides 20% of the note-to-note links, rebuilds the graph signal without them, and checks whether the hidden
partner appears in the top-k suggestions. Compares ablations, and fails if the shipped configuration drops
below the committed baseline (data/recs-baseline.json) by more than 0.01.

    python eval_recs.py            # report + gate
    python eval_recs.py --update   # rewrite the baseline (do this only after a deliberate change)
"""
from __future__ import annotations

import argparse
import sys

import recommend
from common import DATA, load_json, save_json


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--update", action="store_true")
    ap.add_argument("--tune", action="store_true", help="grid-search the fusion weights on the masked evaluation")
    args = ap.parse_args()
    index = load_json(DATA / "notes-index.json", [])
    edges = load_json(DATA / "graph.json", [])
    if not index:
        sys.exit("run build_site.py first")
    docs = {r["id"]: (r["title"] + " ") * 2 + r["search"] for r in index}
    _, _, eng = recommend.build(index, docs, [tuple(e) for e in edges])
    if args.tune:
        best = []
        for g in (0.6, 1.0, 1.5, 2.2):
            for s in (0.3, 0.6, 1.0):
                for t in (0.2, 0.4, 0.8):
                    w = {"text": 1.0, "graph": g, "struct": s, "time": t}
                    r = recommend.eval_hidden_links(eng, weights=w, mmr=False)
                    best.append((r["recall@10"] + r["mrr"], w, r))
        for sc, w, r in sorted(best, key=lambda x: -x[0])[:6]:
            print(round(sc, 3), w, r)
        return 0
    rows = {
        "shipped (fusion + MMR)": recommend.eval_hidden_links(eng),
        "fusion, no MMR": recommend.eval_hidden_links(eng, mmr=False),
        "graph only": recommend.eval_hidden_links(eng, weights={"graph": 1}, mmr=False),
        "text only": recommend.eval_hidden_links(eng, weights={"text": 1}, mmr=False),
        "struct only": recommend.eval_hidden_links(eng, weights={"struct": 1}, mmr=False),
        "time only": recommend.eval_hidden_links(eng, weights={"time": 1}, mmr=False),
    }
    print(f"{'configuration':26s} {'notes':>6s} {'recall@5':>9s} {'recall@10':>10s} {'MRR':>7s}")
    for name, r in rows.items():
        print(f"{name:26s} {r['notes']:6d} {r['recall@5']:9.3f} {r['recall@10']:10.3f} {r['mrr']:7.3f}")
    shipped = rows["shipped (fusion + MMR)"]
    base_path = DATA / "recs-baseline.json"
    if args.update or not base_path.exists():
        save_json(base_path, shipped)
        print("baseline written")
        return 0
    base = load_json(base_path, {})
    bad = [k for k in ("recall@5", "recall@10", "mrr") if shipped[k] < base.get(k, 0) - 0.01]
    print("gate:", "FAILED " + str(bad) if bad else "OK", "(baseline", base, ")")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
