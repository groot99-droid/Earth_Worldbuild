#!/usr/bin/env python3
"""Content suggestion engine for the Earth Chronicle site (stdlib only).

For every non-source note it ranks the other notes worth reading next and says why.

Signals (each turns into a ranking):
  text    TF-IDF cosine over title (x3), summary and facts. The "Context & Connections" section is left out:
          it is templated boilerplate that repeats era/region names.
  graph   direct wikilinks plus Adamic-Adar over shared neighbours (a shared neighbour that links to many
          notes, like an era or region hub, counts for less)
  struct  same era, same region (the generic "Planet-wide" region counts for little), shared themes
  time    closeness on a log scale of years before now
Fusion is weighted Reciprocal Rank Fusion, then MMR diversification (relevance vs similarity to what is
already picked) with a per-type cap, so a rail mixes people, events and places.

Outputs (via build(); build_site.py writes them):
  recs      {"ids": [...], "recs": {"<pos>": [[pos, "why,codes"], ...]}}
  featured  {"start": [ids], "journeys": [{id, title, blurb, steps: [ids]}]}
Importance (used for "start here" and journeys) = PageRank + richness + has-image.

Evaluated by eval_recs.py (hidden-link prediction); weights below were tuned against it.
"""
from __future__ import annotations

import math
import random
import re
from collections import Counter, defaultdict

NOW = 2026
K_RRF = 30
WEIGHTS = {"text": 1.0, "graph": 0.8, "struct": 0.5, "time": 0.3}   # tuned with eval_recs.py --tune; leans on text+graph, keeps era/time for context
TOP_N = 12
MMR_LAMBDA = 0.72
TYPE_CAP = 5
GENERIC_REGIONS = {"region/planet-wide"}

STOP = set("""a about above after again all also am an and any are as at be because been before being between both but by can could
did do does doing down during each few for from further had has have having he her here hers him his how i if in into is it its
just me more most my no nor not now of off on once only or other our out over own same she should so some such than that the their
theirs them then there these they this those through to too under until up very was we were what when where which while who whom
why will with would you your also may many often one two three first later around roughly about century century""".split())


def tokens(text: str) -> list[str]:
    text = re.sub(r"\[\[([^\]\|]+)(?:\|([^\]]*))?\]\]", lambda m: m.group(2) or m.group(1), text)
    out = []
    for t in re.findall(r"[a-z][a-z0-9]+", text.lower()):
        if t in STOP or len(t) < 3:
            continue
        if len(t) > 4 and t.endswith("ies"):
            t = t[:-3] + "y"
        elif len(t) > 4 and t.endswith("s") and not t.endswith("ss"):
            t = t[:-1]
        out.append(t)
    return out


def log_ybp(y) -> float | None:
    if not isinstance(y, (int, float)):
        return None
    return math.log10(max(0.0, NOW - y) + 1)


class Engine:
    def __init__(self, recs_index: list[dict], docs: dict[str, str], edges: list[tuple[str, str]], richness: dict[str, float]):
        self.ids = [r["id"] for r in recs_index]
        self.pos = {i: p for p, i in enumerate(self.ids)}
        self.meta = {r["id"]: r for r in recs_index}
        self.richness = richness
        self.adj: dict[str, set[str]] = defaultdict(set)
        for a, b in edges:
            if a in self.pos and b in self.pos and a != b:
                self.adj[a].add(b)
                self.adj[b].add(a)
        self._tfidf(docs)
        self.tm = {i: log_ybp(self.meta[i].get("ds")) for i in self.ids}

    # ---- text
    def _tfidf(self, docs):
        tf = {i: Counter(tokens(docs.get(i, ""))) for i in self.ids}
        df = Counter(t for c in tf.values() for t in c)
        n = len(self.ids)
        self.vec: dict[str, dict[str, float]] = {}
        self.post: dict[str, list[tuple[str, float]]] = defaultdict(list)
        for i, c in tf.items():
            w = {t: (1 + math.log(f)) * math.log((n + 1) / (df[t] + 0.5)) for t, f in c.items() if df[t] >= 2 or c[t] >= 2}
            norm = math.sqrt(sum(x * x for x in w.values())) or 1.0
            self.vec[i] = {t: x / norm for t, x in w.items()}
            for t, x in self.vec[i].items():
                self.post[t].append((i, x))

    def cos(self, a: str, b: str) -> float:
        va, vb = self.vec[a], self.vec[b]
        if len(va) > len(vb):
            va, vb = vb, va
        return sum(x * vb.get(t, 0.0) for t, x in va.items())

    def text_scores(self, i: str, mask: set[str] | None = None) -> dict[str, float]:
        acc: dict[str, float] = defaultdict(float)
        for t, x in self.vec[i].items():
            if mask and t in mask:
                continue
            for j, y in self.post[t]:
                if j != i:
                    acc[j] += x * y
        return acc

    # ---- graph
    def graph_scores(self, i: str, adj=None) -> tuple[dict[str, float], dict[str, int]]:
        adj = adj or self.adj
        acc: dict[str, float] = defaultdict(float)
        shared: dict[str, int] = defaultdict(int)
        for k in adj.get(i, ()):
            w = 1.0 / math.log(2 + len(adj[k]))
            for j in adj[k]:
                if j != i:
                    acc[j] += w
                    shared[j] += 1
        for j in adj.get(i, ()):
            acc[j] += 1.5                      # a direct link is strong evidence
        return acc, shared

    # ---- structure and time
    def struct_score(self, i: str, j: str) -> float:
        a, b = self.meta[i], self.meta[j]
        s = 0.0
        if a.get("era") and a["era"] == b.get("era"):
            s += 1.0
        if a.get("region") and a["region"] == b.get("region"):
            s += 0.3 if a["region"] in GENERIC_REGIONS else 0.9
        ta, tb = set(a.get("themes") or []), set(b.get("themes") or [])
        if ta and tb:
            s += len(ta & tb) / len(ta | tb)
        return s

    def time_score(self, i: str, j: str) -> float:
        a, b = self.tm[i], self.tm[j]
        if a is None or b is None:
            return 0.0
        return math.exp(-abs(a - b) / 0.35)

    # ---- ranking
    def rank(self, i: str, adj=None, weights=None, top_n=TOP_N, mmr=True, mask=None):
        w = weights or WEIGHTS
        text = self.text_scores(i, mask)
        graph, shared = self.graph_scores(i, adj)
        struct = {j: self.struct_score(i, j) for j in self.ids if j != i}
        time_ = {j: self.time_score(i, j) for j in self.ids if j != i}
        signals = {"text": text, "graph": graph, "struct": struct, "time": time_}
        fused: dict[str, float] = defaultdict(float)
        for name, sc in signals.items():
            if not w.get(name):
                continue
            ranked = sorted((j for j, v in sc.items() if v > 0), key=lambda j: -sc[j])[:80]
            for r, j in enumerate(ranked):
                fused[j] += w[name] / (K_RRF + r)
        if not fused:
            return []
        cand = sorted(fused, key=lambda j: -fused[j])[:60]
        top = fused[cand[0]]
        rel = {j: fused[j] / top for j in cand}
        for j in cand:                         # tiny tie-breaker toward notes that have images and are well developed
            rel[j] += 0.03 * (1 if self.meta[j].get("ni") else 0) + 0.02 * self.richness.get(j, 0)
        picked: list[str] = []
        types: Counter = Counter()
        pool = sorted(cand, key=lambda j: -rel[j])
        while pool and len(picked) < top_n:
            best, best_v = None, -1e9
            for j in pool:
                if types[self.meta[j]["type"]] >= TYPE_CAP:
                    continue
                pen = max((self.cos(j, p) for p in picked), default=0.0) if mmr else 0.0
                if mmr and picked:
                    same = sum(1 for p in picked if self.meta[p]["type"] == self.meta[j]["type"]) / len(picked)
                    pen = max(pen, 0.35 * same)
                v = MMR_LAMBDA * rel[j] - (1 - MMR_LAMBDA) * pen
                if v > best_v:
                    best, best_v = j, v
            if best is None:
                break
            picked.append(best)
            types[self.meta[best]["type"]] += 1
            pool.remove(best)
        out = []
        for j in picked:
            out.append((j, self.why(i, j, adj, shared, text)))
        return out

    def why(self, i, j, adj, shared, text) -> str:
        adj = adj or self.adj
        codes = []
        if j in adj.get(i, ()):
            codes.append("link")
        n = shared.get(j, 0)
        if n >= 2:
            codes.append(f"n:{n}")
        a, b = self.meta[i], self.meta[j]
        if a.get("era") and a["era"] == b.get("era"):
            codes.append("era")
        if a.get("region") and a["region"] == b.get("region") and a["region"] not in GENERIC_REGIONS:
            codes.append("region")
        if set(a.get("themes") or []) & set(b.get("themes") or []):
            codes.append("theme")
        if text.get(j, 0) >= 0.12:
            codes.append("text")
        if self.time_score(i, j) > 0.6 and "era" not in codes:
            codes.append("time")
        return ",".join(codes[:3]) or "text"

    # ---- importance and journeys
    def pagerank(self, iters=40, d=0.85) -> dict[str, float]:
        n = len(self.ids)
        pr = {i: 1 / n for i in self.ids}
        for _ in range(iters):
            new = {i: (1 - d) / n for i in self.ids}
            for i in self.ids:
                deg = len(self.adj[i])
                if deg:
                    share = d * pr[i] / deg
                    for j in self.adj[i]:
                        new[j] += share
                else:
                    for j in self.ids:
                        new[j] += d * pr[i] / n
            pr = new
        top = max(pr.values())
        return {i: v / top for i, v in pr.items()}


def richness_map(index_by_id: dict[str, dict], docs: dict[str, str]) -> dict[str, float]:
    lens = {i: len(docs.get(i, "")) for i in index_by_id}
    m = max(lens.values()) or 1
    return {i: lens[i] / m for i in lens}


JOURNEYS = [
    {"id": "deep-time", "title": "From a molten planet to the Information Age",
     "blurb": "One stop per stretch of log-scaled time, from planetary formation to now.",
     "types": {"event", "species", "culture", "technology", "era"}, "k": 14, "bins": "log", "themes": None},
    {"id": "minds-and-makers", "title": "Minds and makers",
     "blurb": "Thinkers, scientists, artists and inventors, in the order they lived.",
     "types": {"person"}, "k": 12, "bins": "linear", "themes": {"science", "art", "language"}},
    {"id": "cities-and-sacred-places", "title": "Cities and sacred places",
     "blurb": "Places where people gathered, built and worshipped, oldest first.",
     "types": {"place"}, "k": 12, "bins": "linear", "themes": None},
    {"id": "power-and-war", "title": "Power, conflict and collapse",
     "blurb": "Wars, empires and breakdowns that redrew the map.",
     "types": {"event", "culture", "person"}, "k": 12, "bins": "linear", "themes": {"war"}},
]


def build_journeys(eng: Engine, importance: dict[str, float]) -> list[dict]:
    out = []
    for j in JOURNEYS:
        cands = []
        for i in eng.ids:
            m = eng.meta[i]
            if m["type"] not in j["types"] or m.get("ds") is None:
                continue
            if j["themes"] and not (set(m.get("themes") or []) & j["themes"]):
                continue
            cands.append(i)
        if len(cands) < j["k"]:
            continue
        key = (lambda i: eng.tm[i]) if j["bins"] == "log" else (lambda i: eng.meta[i]["ds"])
        ordered = sorted(cands, key=key)
        steps = []
        if j["bins"] == "log":                     # equal spans of log-time
            lo, hi = key(ordered[0]), key(ordered[-1])
            groups = [[i for i in ordered if lo + (hi - lo) * b / j["k"] <= key(i) <= lo + (hi - lo) * (b + 1) / j["k"]] for b in range(j["k"])]
        else:                                      # equal counts, so dense periods do not swallow the journey
            size = len(ordered) / j["k"]
            groups = [ordered[int(b * size):int((b + 1) * size)] for b in range(j["k"])]
        for g in groups:
            g = [i for i in g if i not in steps]
            if g:
                steps.append(max(g, key=lambda i: importance[i] + 0.15 * (1 if eng.meta[i].get("ni") else 0)))
        steps.sort(key=lambda i: eng.meta[i]["ds"])
        out.append({"id": j["id"], "title": j["title"], "blurb": j["blurb"], "steps": steps})
    return out


def start_here(eng: Engine, importance: dict[str, float], n=12) -> list[str]:
    """Most central, well-developed notes, spread over types and eras."""
    score = {i: importance[i] + 0.1 * eng.richness.get(i, 0) + 0.1 * (1 if eng.meta[i].get("ni") else 0)
             for i in eng.ids if eng.meta[i]["type"] in ("event", "person", "place", "culture", "species", "technology")}
    picked, types, eras = [], Counter(), Counter()
    for i in sorted(score, key=lambda i: -score[i]):
        m = eng.meta[i]
        if types[m["type"]] >= 3 or (m.get("era") and eras[m["era"]] >= 2):
            continue
        picked.append(i)
        types[m["type"]] += 1
        eras[m.get("era")] += 1
        if len(picked) >= n:
            break
    return picked


def build(index: list[dict], docs: dict[str, str], edges: list[tuple[str, str]]):
    rec_index = [r for r in index if r["type"] != "source"]
    by_id = {r["id"]: r for r in rec_index}
    eng = Engine(rec_index, docs, edges, richness_map(by_id, docs))
    recs = {}
    for i in eng.ids:
        recs[str(eng.pos[i])] = [[eng.pos[j], why] for j, why in eng.rank(i)]
    imp = eng.pagerank()
    featured = {"start": start_here(eng, imp), "journeys": build_journeys(eng, imp)}
    return {"ids": eng.ids, "recs": recs}, featured, eng


def eval_hidden_links(eng: Engine, frac=0.2, seed=7, ks=(5, 10), weights=None, mmr=True, mask_leak=True) -> dict:
    """Hide a fraction of links, rebuild the graph signal without them, and see whether the hidden partner
    shows up in the top-k. A note's text usually names the notes it links to, so with mask_leak the query
    terms that are the title words of the note or of its hidden partners are dropped from the text signal;
    otherwise "text only" would win by reading the answer."""
    rnd = random.Random(seed)
    edges = sorted({tuple(sorted((a, b))) for a in eng.adj for b in eng.adj[a]})
    hidden = set(rnd.sample(edges, int(len(edges) * frac)))
    reduced: dict[str, set[str]] = defaultdict(set)
    for a, b in edges:
        if (a, b) not in hidden:
            reduced[a].add(b)
            reduced[b].add(a)
    targets: dict[str, set[str]] = defaultdict(set)
    for a, b in hidden:
        targets[a].add(b)
        targets[b].add(a)
    hits = {k: 0 for k in ks}
    rr = 0.0
    n = 0
    for i, ts in targets.items():
        mask = None
        if mask_leak:
            mask = set(tokens(eng.meta[i]["title"]))
            for t in ts:
                mask |= set(tokens(eng.meta[t]["title"]))
        ranked = [j for j, _ in eng.rank(i, adj=reduced, weights=weights, top_n=max(ks), mmr=mmr, mask=mask)]
        n += 1
        first = next((r for r, j in enumerate(ranked, 1) if j in ts), None)
        if first:
            rr += 1 / first
        for k in ks:
            if any(j in ts for j in ranked[:k]):
                hits[k] += 1
    return {"notes": n, **{f"recall@{k}": round(hits[k] / max(1, n), 4) for k in ks}, "mrr": round(rr / max(1, n), 4)}
