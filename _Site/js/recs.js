/* Runtime suggestions: precomputed similarity lists (scripts/recommend.py) blended with what this reader has viewed. */
import { S } from "./state.js";
import { hist } from "./store.js";
import { HUB_TYPES } from "./util.js";

const pos = (id) => S.recPos?.get(id);

export function whyText(codes, toRec) {
  const era = toRec?.era && S.by[toRec.era]?.title, reg = toRec?.region && S.by[toRec.region]?.title;
  return codes.split(",").filter(Boolean).map((c) => {
    if (c === "link") return "Directly linked";
    if (c.startsWith("n:")) return `${c.slice(2)} notes in common`;
    if (c === "era") return era ? `Same era: ${era}` : "Same era";
    if (c === "region") return reg ? `Same region: ${reg}` : "Same region";
    if (c === "theme") return "Shared theme";
    if (c === "text") return "Similar topics";
    if (c === "time") return "Close in time";
    return "";
  }).filter(Boolean).slice(0, 2).join(" · ");
}

/* Suggestions for one note: [{rec, why}] */
export function similar(id, n = 8) {
  const p = pos(id); if (p == null || !S.recs) return [];
  return (S.recs.recs[p] || []).slice(0, n).map(([j, why]) => { const rec = S.by[S.recs.ids[j]]; return { rec, why: whyText(why, rec) }; }).filter((x) => x.rec);
}

/* "Continue exploring": recency-decayed blend of the similarity lists of recently viewed notes, minus what was seen. */
export function forYou(n = 10) {
  const start = () => ({ personal: false, items: (S.featured?.start || []).map((id) => ({ rec: S.by[id], why: "A good place to start" })).filter((x) => x.rec).slice(0, n) });
  const h = hist.ids().filter((id) => S.by[id]).slice(0, 8);
  if (!h.length || !S.recs) return start();
  const seen = new Set(hist.ids()), score = new Map(), src = new Map();
  h.forEach((id, age) => {
    const p = pos(id); if (p == null) return;
    const w = Math.pow(0.75, age);
    (S.recs.recs[p] || []).forEach(([j], r) => {
      const jid = S.recs.ids[j]; if (seen.has(jid)) return;
      const s = w / (1 + r); score.set(jid, (score.get(jid) || 0) + s);
      if (!src.has(jid) || s > src.get(jid).s) src.set(jid, { s, from: id });
    });
  });
  const items = [], types = {};
  for (const jid of [...score.keys()].sort((a, b) => score.get(b) - score.get(a))) {
    const rec = S.by[jid]; if (!rec || (types[rec.type] || 0) >= 4) continue;
    types[rec.type] = (types[rec.type] || 0) + 1;
    items.push({ rec, why: `Because you viewed ${S.by[src.get(jid).from].title}` });
    if (items.length >= n) break;
  }
  return items.length ? { personal: true, items } : start();
}

export function noteOfTheDay() {
  const l = S.featured?.start || []; if (!l.length) return null;
  const day = Math.floor(Date.now() / 86400000);
  return S.by[l[day % l.length]] || null;
}

let adj = null;
function adjacency() {
  if (adj) return adj;
  adj = new Map();
  for (const [a, b] of S.edges) {
    (adj.get(a) || adj.set(a, new Set()).get(a)).add(b);
    (adj.get(b) || adj.set(b, new Set()).get(b)).add(a);
  }
  return adj;
}
/* Shortest chain of links between two notes. Prefers chains that avoid hub notes (eras, regions, themes), which
   connect everything and say little; falls back to any chain. */
export function connection(a, b) {
  const g = adjacency();
  const bfs = (allowHubs) => {
    const prev = new Map([[a, null]]); const q = [a];
    while (q.length) {
      const cur = q.shift(); if (cur === b) break;
      for (const nx of g.get(cur) || []) {
        if (prev.has(nx)) continue;
        if (!allowHubs && nx !== b && HUB_TYPES.has(S.by[nx]?.type)) continue;
        prev.set(nx, cur); q.push(nx);
      }
    }
    if (!prev.has(b)) return null;
    const path = []; for (let c = b; c; c = prev.get(c)) path.push(c);
    return path.reverse();
  };
  return a === b ? [a] : bfs(false) || bfs(true);
}

let chrono = null;
export function prevNext(id) {
  if (!chrono) chrono = S.idx.filter((r) => r.type !== "source" && r.ds != null && r.type !== "era").sort((x, y) => x.ds - y.ds || x.title.localeCompare(y.title));
  const i = chrono.findIndex((r) => r.id === id);
  return i < 0 ? {} : { prev: chrono[i - 1], next: chrono[i + 1] };
}

export function surprise() {
  const seen = new Set(hist.ids());
  const pool = S.idx.filter((r) => r.type !== "source" && r.img && !seen.has(r.id) && !["region", "theme", "timeline", "observer-note"].includes(r.type));
  const list = pool.length ? pool : S.idx.filter((r) => r.type !== "source");
  const w = list.map((r) => Math.log(r.nl + 2)); let x = Math.random() * w.reduce((a, b) => a + b, 0);
  for (let i = 0; i < list.length; i++) { x -= w[i]; if (x <= 0) return list[i]; }
  return list[0];
}
