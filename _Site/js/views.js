/* Timeline, regions and browse views, plus cards, rails and the empty state. */
import { S } from "./state.js";
import { filtered } from "./search.js";
import { forYou } from "./recs.js";
import { picture } from "./img.js";
import { $, esc, LABEL, NOW, SINGULAR, TYPES, DEFAULT_TYPES } from "./util.js";
import { isDefaultFilters } from "./state.js";

export const byDate = (a, b) => (a.ds ?? 1e12) - (b.ds ?? 1e12) || a.title.localeCompare(b.title);

export function cardHTML(r, { why = "", eager = false } = {}) {
  return `<a class="card" data-t="${r.type}" href="#/n/${esc(r.id)}">${picture([r.imt, r.img], r.type, r.title[0], { eager, ai: r.ai })}
  <div class="cb"><div class="tl">${esc(SINGULAR[r.type])}${r.date ? ` · <span class="tnum">${esc(r.date)}</span>` : ""}</div><h3>${esc(r.title)}</h3><p class="sm">${esc(r.sum)}</p>${why ? `<p class="why">${esc(why)}</p>` : ""}</div></a>`;
}
export function railHTML(title, sub, items, id = "") {
  if (!items.length) return "";
  return `<section class="rail-sec" ${id ? `id="${id}"` : ""} aria-label="${esc(title)}"><h2>${esc(title)}</h2>${sub ? `<p class="sub">${esc(sub)}</p>` : ""}<div class="rail">${items.map((x) => cardHTML(x.rec || x, { why: x.why || "" })).join("")}</div></section>`;
}
export function skeleton(n = 12) {
  return `<div class="skeleton-grid" aria-hidden="true">${Array.from({ length: n }, () => `<div class="card"><div class="thumb"></div><div class="cb"><div class="sk-line" style="width:40%"></div><div class="sk-line" style="width:80%"></div><div class="sk-line"></div></div></div>`).join("")}</div>`;
}
export function emptyHTML() {
  const bits = [];
  if (S.q) bits.push(`<button class="btn" data-action="clear-q">Clear search “${esc(S.q)}”</button>`);
  if (S.era) bits.push(`<button class="btn" data-action="clear" data-key="era">Any era</button>`);
  if (S.region) bits.push(`<button class="btn" data-action="clear" data-key="region">Any region</button>`);
  if (S.theme) bits.push(`<button class="btn" data-action="clear" data-key="theme">Any theme</button>`);
  if (S.conf) bits.push(`<button class="btn" data-action="clear" data-key="conf">Any confidence</button>`);
  if (S.types.size < DEFAULT_TYPES.length || !S.types.has("source")) bits.push(`<button class="btn" data-action="all-types">Show every type</button>`);
  return `<div class="empty"><h2>No notes match</h2><p>Nothing fits these filters${S.q ? ` and the search “${esc(S.q)}”` : ""}. Loosen one of them, or start from a suggestion.</p><div class="row">${bits.join("")}<button class="btn primary" data-action="reset">Reset all filters</button></div></div>`;
}
const didYouMean = () => (S.didYouMean ? `<p class="meta" role="status">Showing results for <strong>${esc(S.didYouMean)}</strong>. <button class="link-btn" data-action="literal-q">Search for “${esc(S.q)}” instead</button></p>` : "");

/* ---------- timeline ---------- */
const xpos = (y, minY) => 1 - Math.log10(Math.max(0, NOW - y) + 1) / Math.log10(NOW - minY + 1);

export function renderTimeline(main, list) {
  if (!list.length) { main.innerHTML = emptyHTML(); return; }
  const eras = S.idx.filter((r) => r.type === "era" && r.ds != null).sort(byDate);
  const groups = new Map();
  list.forEach((r) => { if (r.type === "era") { if (!groups.has(r.id)) groups.set(r.id, []); } else { const k = r.era || "_none"; if (!groups.has(k)) groups.set(k, []); groups.get(k).push(r); } });
  const ordered = [...groups.keys()].sort((a, b) => (a === "_none") - (b === "_none") || ((S.by[a]?.ds ?? 1e12) - (S.by[b]?.ds ?? 1e12)));
  let html = didYouMean();
  if (isDefaultFilters()) {
    const fy = forYou(8);
    html += railHTML(fy.personal ? "Continue exploring" : "Start here", fy.personal ? "Suggested from what you have been reading" : "A spread of well-connected notes across time and place", fy.items, "home-rail");
  }
  html += `<div class="ruler" id="ruler"></div><p class="sr-only">Log-scaled ruler of ${eras.length} eras from the formation of the Earth to now. The era sections below list the same notes; each era bar is a button that jumps to its section.</p>`;
  let first = true;
  for (const k of ordered) {
    const items = groups.get(k).sort(byDate), era = S.by[k];
    const head = era
      ? `<a class="ghead" data-t="era" href="#/n/${esc(era.id)}"><div class="cover">${picture([era.imt, era.img], "era", era.title[0], { ai: era.ai })}</div><div class="gb"><div class="meta tnum">${esc(era.date)}</div><h2>${esc(era.title)}</h2><p>${esc(era.sum)}</p><p class="meta">${items.length} note${items.length === 1 ? "" : "s"} in view</p></div></a>`
      : `<div class="ghead" style="--c:var(--muted);grid-template-columns:1fr"><div class="gb"><h2>Not placed in an era</h2><p>Regions, themes, observer notes and other notes that span eras.</p></div></div>`;
    html += `<section class="group" id="g-${era ? era.id.replace("/", "-") : "none"}" aria-label="${esc(era ? era.title : "Not placed in an era")}">${head}${items.length ? `<div class="grid">${items.map((r) => { const c = cardHTML(r, { eager: first }); first = false; return c; }).join("")}</div>` : ""}</section>`;
  }
  main.innerHTML = html;
  const ruler = $("#ruler", main); drawRuler(ruler, eras, list); ruler._redo = () => drawRuler(ruler, eras, list);
}
function drawRuler(box, eras, list) {
  const W = box.clientWidth || 900, lanes = [], H = 96, laneH = 13;
  const minY = Math.min(...eras.map((e) => e.ds));
  const svg = [`<svg width="${W}" height="${H}" role="group" aria-label="Timeline ruler, logarithmic scale, planetary formation to now">`];
  const items = eras.map((e) => ({ e, a: xpos(e.ds, minY) * W, b: xpos(e.de ?? e.ds, minY) * W })).sort((p, q) => p.a - q.a);
  for (const it of items) {
    let l = lanes.findIndex((end) => end < it.a - 1); if (l < 0) { l = lanes.length; lanes.push(0); }
    lanes[l] = Math.max(it.b, it.a + 3);
    const w = Math.max(3, it.b - it.a), y = 4 + l * (laneH + 2);
    const inView = list.some((r) => r.id === it.e.id || r.era === it.e.id);
    svg.push(`<g class="band" role="button" tabindex="0" data-go="${esc(it.e.id)}" aria-label="Jump to ${esc(it.e.title)}, ${esc(it.e.date)}"><title>${esc(it.e.title)} (${esc(it.e.date)})</title><rect x="${it.a.toFixed(1)}" y="${y}" width="${w.toFixed(1)}" height="${laneH}" rx="3" fill="var(--c-era)" opacity="${inView ? .9 : .28}" stroke="var(--bg)"/>${w > 62 ? `<text x="${(it.a + 4).toFixed(1)}" y="${y + 10}" style="fill:var(--on-c)">${esc(it.e.title.replace(/ (Period|Epoch|Era|Eon)$/, ""))}</text>` : ""}</g>`);
  }
  const base = H - 26;
  svg.push(`<line class="axis" x1="0" x2="${W}" y1="${base}" y2="${base}"/>`);
  for (const [ybp, lab] of [[10, "10 y"], [100, "100 y"], [1e3, "1 ka"], [1e4, "10 ka"], [1e5, "100 ka"], [1e6, "1 Ma"], [1e7, "10 Ma"], [1e8, "100 Ma"], [1e9, "1 Ga"]]) {
    const x = xpos(NOW - ybp, minY) * W; if (x < 10 || x > W - 10) continue;
    svg.push(`<line class="axis" x1="${x}" x2="${x}" y1="${base}" y2="${base + 5}"/><text x="${x}" y="${base + 16}" text-anchor="middle">${lab}</text>`);
  }
  svg.push(`<text x="0" y="${H - 2}">planet forms</text><text x="${W}" y="${H - 2}" text-anchor="end">now</text>`);
  for (const r of list) { if (r.ds == null || r.type === "era") continue; const x = xpos(r.ds, minY) * W; svg.push(`<rect x="${x.toFixed(1)}" y="${base - 6}" width="1.5" height="6" fill="var(--c-${r.type})" opacity=".7"/>`); }
  svg.push("</svg>");
  box.innerHTML = svg.join("");
}
window.addEventListener("resize", () => { const r = $(".ruler"); if (r && r._redo) { clearTimeout(window._rt); window._rt = setTimeout(r._redo, 150); } });

/* ---------- regions ---------- */
export function renderRegions(main, list) {
  const regions = S.idx.filter((r) => r.type === "region").sort((a, b) => a.title.localeCompare(b.title));
  const secs = [...regions, { id: "_none", title: "No single region", sum: "Notes not tied to one region." }];
  let html = didYouMean(), shown = 0;
  for (const reg of secs) {
    const items = list.filter((r) => r.type !== "region" && (reg.id === "_none" ? !r.region : r.region === reg.id));
    if (!items.length) continue; shown++;
    const head = reg.id === "_none"
      ? `<div class="ghead" style="--c:var(--muted);grid-template-columns:1fr"><div class="gb"><div class="meta">${items.length} notes</div><h2>${esc(reg.title)}</h2><p>${esc(reg.sum)}</p></div></div>`
      : `<a class="ghead" data-t="region" href="#/n/${esc(reg.id)}"><div class="cover">${picture([reg.imt, reg.img], "region", reg.title[0], { ai: reg.ai })}</div><div class="gb"><div class="meta">${items.length} notes</div><h2>${esc(reg.title)}</h2><p>${esc(reg.sum)}</p></div></a>`;
    const by = {}; items.forEach((r) => (by[r.type] ||= []).push(r));
    let body = "";
    for (const t of TYPES) {
      if (!by[t]) continue;
      const rows = by[t].sort(byDate);
      body += `<h3 class="sub">${LABEL[t]} (${rows.length})</h3><div class="grid" data-more="${esc(reg.id)}|${t}">${rows.slice(0, 12).map((r) => cardHTML(r)).join("")}</div>${rows.length > 12 ? `<button class="link-btn" data-action="more" data-region="${esc(reg.id)}" data-type="${t}">Show all ${rows.length}</button>` : ""}`;
    }
    html += `<section class="rsec" aria-label="${esc(reg.title)}">${head}${body}</section>`;
  }
  main.innerHTML = shown ? html : emptyHTML();
}
export function showAllInRegion(btn, list) {
  const { region, type } = btn.dataset;
  const rows = list.filter((r) => r.type === type && (region === "_none" ? !r.region : r.region === region)).sort(byDate);
  btn.previousElementSibling.innerHTML = rows.map((r) => cardHTML(r)).join(""); btn.remove();
}

/* ---------- browse ---------- */
export function renderBrowse(main, list) {
  if (!list.length) { main.innerHTML = emptyHTML(); return; }
  const rows = S.q ? list : [...list].sort((a, b) => a.title.localeCompare(b.title));
  const shown = rows.slice(0, S.browseN);
  main.innerHTML = didYouMean() + `<div class="grid">${shown.map((r, i) => cardHTML(r, { eager: i < 4 })).join("")}</div>` +
    (rows.length > shown.length ? `<button class="btn more" data-action="show-more" style="display:block;margin:22px auto">Show ${Math.min(60, rows.length - shown.length)} more (${rows.length - shown.length} left)</button>` : "");
}

export { filtered };
