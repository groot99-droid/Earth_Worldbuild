/* Application state, data loading and URL <-> state sync. The URL is the source of truth for view and filters,
   so any view can be shared, bookmarked and restored with the back button. */
import { DEFAULT_TYPES, TYPES, fetchJson } from "./util.js";

export const S = {
  idx: [], by: {}, edges: [], meta: null, recs: null, featured: null, ai: {},
  view: "timeline", types: new Set(DEFAULT_TYPES), era: "", region: "", theme: "", conf: "", q: "", focus: "", browseN: 60,
  didYouMean: "", noteDepth: 0, cameFromList: false, listHash: "#/v/timeline", trigger: null,
};
export const themeTitle = {};
const detailCache = {}, rewriteCache = {};

/* A note's fields, overlaid with its AI rewrite (data/rewrite-<type>.json, built by _Rewrite/rewrite_layer.py) when one exists. */
export async function getNote(id) {
  const t = id.split("/")[0];
  detailCache[t] ||= fetchJson(`data/notes-${t}.json`);
  rewriteCache[t] ||= fetchJson(`data/rewrite-${t}.json`, 1).catch(() => ({}));
  const [notes, rw] = await Promise.all([detailCache[t], rewriteCache[t]]);
  const d = notes[id];
  return d && rw[id] ? { ...d, ...rw[id] } : d;
}
export async function getChunk(type) { detailCache[type] ||= fetchJson(`data/notes-${type}.json`); return detailCache[type]; }

export async function loadData() {
  const [idx, edges, meta, recs, featured] = await Promise.all([
    fetchJson("data/notes-index.json"), fetchJson("data/graph.json"), fetchJson("data/meta.json"),
    fetchJson("data/recs.json").catch(() => null), fetchJson("data/featured.json").catch(() => null),
  ]);
  S.idx = idx; S.edges = edges; S.meta = meta; S.recs = recs; S.featured = featured;
  S.ai = await fetchJson("data/ai-text.json", 1).catch(() => ({}));   // optional AI-written extras
  const rw = await fetchJson("data/rewrite-index.json", 1).catch(() => ({}));   // card blurbs from the AI rewrite layer
  idx.forEach((r) => { S.by[r.id] = r; if (rw[r.id]?.sum) r.sum = rw[r.id].sum; });
  meta.themes.forEach((t) => (themeTitle[t.slug] = t.title));
  if (recs) { S.recPos = new Map(recs.ids.map((id, i) => [id, i])); }
}
export const themeIdOf = (slug) => (S.meta.themes.find((t) => t.slug === slug) || {}).id;

/* ----- URL ----- */
const sameSet = (a, b) => a.size === b.length && b.every((x) => a.has(x));
export function isDefaultFilters() {
  return sameSet(S.types, DEFAULT_TYPES) && !S.era && !S.region && !S.theme && !S.conf && !S.q;
}
export function activeFilterCount() {
  return (sameSet(S.types, DEFAULT_TYPES) ? 0 : 1) + (S.era ? 1 : 0) + (S.region ? 1 : 0) + (S.theme ? 1 : 0) + (S.conf ? 1 : 0);
}
export function hashFor(view = S.view) {
  const p = new URLSearchParams();
  if (!sameSet(S.types, DEFAULT_TYPES)) p.set("t", TYPES.filter((t) => S.types.has(t)).join(","));
  if (S.era) p.set("era", S.era);
  if (S.region) p.set("region", S.region);
  if (S.theme) p.set("theme", S.theme);
  if (S.conf) p.set("conf", S.conf);
  if (S.q) p.set("q", S.q);
  if (view === "graph" && S.focus) p.set("focus", S.focus);
  const qs = p.toString();
  return `#/v/${view}` + (qs ? "?" + qs : "");
}
export function applyQuery(qs) {
  const p = new URLSearchParams(qs || "");
  const t = (p.get("t") || "").split(",").filter((x) => TYPES.includes(x));
  S.types = new Set(t.length ? t : DEFAULT_TYPES);
  S.era = S.by[p.get("era")] ? p.get("era") : "";
  S.region = S.by[p.get("region")] ? p.get("region") : "";
  S.theme = p.get("theme") || "";
  S.conf = ["high", "medium", "low"].includes(p.get("conf")) ? p.get("conf") : "";
  S.q = p.get("q") || "";
  S.focus = S.by[p.get("focus")] ? p.get("focus") : "";
}
export function syncURL() {
  const h = hashFor(S.view);
  S.listHash = h;
  if (location.hash !== h) history.replaceState(history.state, "", h);
}
