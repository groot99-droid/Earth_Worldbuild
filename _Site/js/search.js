/* Filtering, ranked search, typo tolerance and suggestions. Everything runs in the browser over the note index. */
import { S, themeIdOf } from "./state.js";
import { recentQ } from "./store.js";
import { esc, SINGULAR } from "./util.js";

const norm = (s) => String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
export const tokenize = (q) => norm(q).split(/[^a-z0-9]+/).filter(Boolean);

let prepared = false, vocab = null;
function prepare() {
  if (prepared) return;
  vocab = new Map();
  for (const r of S.idx) {
    r._t = norm(r.title);
    r._s = norm(r.search);
    for (const w of r._s.split(/[^a-z0-9]+/)) if (w.length >= 3) vocab.set(w, (vocab.get(w) || 0) + 1);
  }
  prepared = true;
}

function dl(a, b, max) {                                  // Damerau-Levenshtein with early exit
  if (Math.abs(a.length - b.length) > max) return max + 1;
  const d = Array.from({ length: a.length + 1 }, (_, i) => [i, ...Array(b.length).fill(0)]);
  for (let j = 1; j <= b.length; j++) d[0][j] = j;
  for (let i = 1; i <= a.length; i++) for (let j = 1; j <= b.length; j++) {
    const c = a[i - 1] === b[j - 1] ? 0 : 1;
    d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + c);
    if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) d[i][j] = Math.min(d[i][j], d[i - 2][j - 2] + 1);
  }
  return d[a.length][b.length];
}
export function correctToken(t) {
  prepare();
  if (vocab.has(t) || t.length < 4) return t;
  const max = t.length > 6 ? 2 : 1;
  let best = null, bd = max + 1, bf = 0;
  for (const [w, f] of vocab) {
    if (Math.abs(w.length - t.length) > max || w[0] !== t[0] && w[1] !== t[1]) continue;
    const d = dl(t, w, max);
    if (d < bd || (d === bd && f > bf)) { best = w; bd = d; bf = f; }
  }
  return best && bd <= max ? best : t;
}

function baseMatch(r) {
  if (!S.types.has(r.type)) return false;
  if (S.era && r.era !== S.era && r.id !== S.era) return false;
  if (S.region && r.region !== S.region && r.id !== S.region) return false;
  if (S.theme && !r.themes.includes(S.theme) && r.id !== themeIdOf(S.theme)) return false;
  if (S.conf && r.conf !== S.conf) return false;
  return true;
}
export function scoreNote(r, toks) {
  let s = 0;
  for (const t of toks) {
    if (r._t.includes(t)) s += 5 + (new RegExp("(^|[^a-z0-9])" + t).test(r._t) ? 2 : 0);
    const occ = r._s.split(t).length - 1; s += Math.min(4, occ);
  }
  return s + 0.02 * r.nl + (r.img ? 0.3 : 0);
}
/* The filtered list; when a search finds nothing, retry with spelling-corrected words and remember the correction. */
export function filtered() {
  prepare();
  S.didYouMean = "";
  const base = S.idx.filter(baseMatch);
  if (!S.q) return base;
  let toks = tokenize(S.q);
  let out = base.filter((r) => toks.every((t) => r._s.includes(t)));
  if (!out.length && toks.length && !S.literal) {
    const fixed = toks.map(correctToken);
    if (fixed.join(" ") !== toks.join(" ")) {
      const alt = base.filter((r) => fixed.every((t) => r._s.includes(t)));
      if (alt.length) { out = alt; S.didYouMean = fixed.join(" "); toks = fixed; }
    }
  }
  return out.map((r) => [r, scoreNote(r, toks)]).sort((a, b) => b[1] - a[1]).map((x) => x[0]);
}

/* ---------- suggestions (title-first autocomplete) ---------- */
export function suggest(q, limit = 8) {
  prepare();
  const toks = tokenize(q); if (!toks.length) return [];
  const nq = norm(q).trim();
  const scored = [];
  for (const r of S.idx) {
    const t = r._t; let s = 0;
    if (t === nq) s = 100;
    else if (t.startsWith(nq)) s = 80;
    else if (toks.every((k) => t.split(/[^a-z0-9]+/).some((w) => w.startsWith(k)))) s = 62;
    else if (t.includes(nq)) s = 46;
    else if (toks.every((k) => t.includes(k))) s = 34;
    else if (toks.every((k) => r._s.includes(k))) s = 12;
    else if (toks.length === 1 && toks[0].length >= 4 && t.split(/[^a-z0-9]+/).some((w) => dl(toks[0], w, 1) <= 1)) s = 9;
    if (!s) continue;
    s += Math.min(5, r.nl / 20) + (r.img ? 1 : 0) - (r.type === "source" ? 6 : 0);
    scored.push([r, s]);
  }
  return scored.sort((a, b) => b[1] - a[1]).slice(0, limit).map((x) => x[0]);
}

export function suggestHTML(q) {
  const opt = (r, i) => `<button type="button" class="sg" role="option" id="sg-${i}" aria-selected="false" data-id="${esc(r.id)}"><span class="sgt">${r.imt ? `<img src="${esc(r.imt)}" alt="" loading="lazy" decoding="async">` : ""}</span><span><b>${esc(r.title)}</b><small>${esc(SINGULAR[r.type])}${r.date ? " · " + esc(r.date) : ""}</small></span></button>`;
  let i = 0, html = "";
  if (!q.trim()) {
    const recent = recentQ.list();
    if (recent.length) html += `<div class="grp">Recent searches</div>` + recent.map((x) => `<button type="button" class="sg" role="option" id="sg-${i++}" aria-selected="false" data-q="${esc(x)}"><span><b>${esc(x)}</b></span></button>`).join("");
    const starters = (S.featured?.start || []).slice(0, 5).map((id) => S.by[id]).filter(Boolean);
    if (starters.length) html += `<div class="grp">Try these</div>` + starters.map((r) => opt(r, i++)).join("");
    return html;
  }
  const hits = suggest(q);
  if (hits.length) html += `<div class="grp">Notes</div>` + hits.map((r) => opt(r, i++)).join("");
  html += `<button type="button" class="sg" role="option" id="sg-${i++}" aria-selected="false" data-q="${esc(q.trim())}"><span><b>Search all notes for “${esc(q.trim())}”</b><small>Full-text search across summaries and facts</small></span></button>`;
  if (!hits.length) {
    const fixed = tokenize(q).map(correctToken).join(" ");
    if (fixed && fixed !== tokenize(q).join(" ")) html += `<button type="button" class="sg" role="option" id="sg-${i++}" aria-selected="false" data-q="${esc(fixed)}"><span><b>Did you mean “${esc(fixed)}”?</b></span></button>`;
  }
  return html;
}
