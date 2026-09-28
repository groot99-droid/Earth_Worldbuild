/* Note panel (modal drawer) and lightbox. */
import { S, getNote, getChunk, themeTitle } from "./state.js";
import { similar, prevNext } from "./recs.js";
import { hist, marks } from "./store.js";
import { picture } from "./img.js";
import { $, announce, esc, HUB_TYPES, icon, LABEL, SINGULAR, TYPES } from "./util.js";
import { byDate, cardHTML } from "./views.js";

export const dlg = $("#note");
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
const VOICE = { "epic-fantasy": "epic-fantasy", "horror-prose": "horror-prose", "essay-self-help": "essay", "confessional-poetry": "confessional-poetry" };
let currentImages = [], lbIdx = 0;

function groupTags(ids, label) {
  const recs = ids.map((i) => S.by[i]).filter(Boolean);
  if (!recs.length) return "";
  const g = {}; recs.forEach((r) => (g[r.type] ||= []).push(r));
  return `<h3>${label}</h3>` + TYPES.filter((t) => g[t]).map((t) => `<div class="grp">${LABEL[t]} (${g[t].length})</div><div class="tags">${g[t].sort(byDate).map((r) => `<a class="tag-link" data-t="${r.type}" href="#/n/${esc(r.id)}">${esc(r.title)}</a>`).join("")}</div>`).join("");
}

export async function openNote(id) {
  const r = S.by[id]; if (!r) return;
  if (!dlg.open) dlg.showModal();
  dlg.innerHTML = `<div class="np"><div class="np-top"><span class="meta">Loading…</span><button class="btn" data-close>Close</button></div><div class="np-body"><div class="sk-line" style="width:30%"></div><div class="sk-line" style="width:70%;height:28px"></div><div class="sk-line"></div><div class="sk-line" style="width:90%"></div></div></div>`;
  let d;
  try { d = await getNote(id); } catch (e) { dlg.innerHTML = `<div class="np"><div class="np-top"><span></span><button class="btn" data-close>Close</button></div><div class="np-body"><div class="empty"><h2>Couldn’t load this note</h2><p>Check your connection and try again.</p><div class="row"><button class="btn primary" data-action="retry-note" data-id="${esc(id)}">Retry</button></div></div></div></div>`; return; }
  let sourceRecs = [];
  if (d.sources.length) { const chunk = await getChunk("source"); sourceRecs = d.sources.map((s) => chunk[s]).filter(Boolean); }
  if (location.hash !== "#/n/" + id) return;              // navigated away while loading
  hist.add(id);
  currentImages = d.images;
  const era = r.era && S.by[r.era], reg = r.region && S.by[r.region];
  const themes = d.themes.map((t) => (t.id ? `<a class="badge" href="#/n/${esc(t.id)}">${esc(themeTitle[t.slug] || t.slug)}</a>` : `<span class="badge">${esc(t.slug)}</span>`)).join("");
  const alts = (i) => d.images.filter((_, k) => k !== i).flatMap((im) => [im.thumb, im.src]);
  const gallery = d.images.length ? `<div class="gallery n${Math.min(d.images.length, 3)}">${d.images.slice(0, 5).map((im, i) => `<button type="button" data-lb="${i}" aria-label="Open image ${i + 1} of ${d.images.length}: ${esc(im.caption || r.title)}">${picture([i ? (im.thumb || im.src) : im.src, im.src, im.thumb, ...alts(i).slice(0, 1)], r.type, r.title[0], { eager: i === 0, alt: im.caption || r.title, ai: im.ai })}</button>`).join("")}</div>` : "";
  let members = "";
  if (r.type === "era") members = groupTags(S.idx.filter((x) => x.era === id).map((x) => x.id), "Notes in this era");
  else if (r.type === "region") members = groupTags(S.idx.filter((x) => x.region === id).map((x) => x.id), "Notes in this region");
  else if (r.type === "theme") { const slug = (S.meta.themes.find((t) => t.id === id) || {}).slug; members = groupTags(S.idx.filter((x) => x.themes.includes(slug)).map((x) => x.id), "Notes tagged with this theme"); }
  const badged = new Set([era?.id, reg?.id, ...d.themes.map((t) => t.id)].filter(Boolean));
  const outIds = d.out.filter((x) => S.by[x] && !badged.has(x) && !(["era", "region", "theme"].includes(r.type) && (S.by[x].era === id || S.by[x].region === id)));
  const connIds = [...new Set([...outIds, ...d.inb.filter((x) => S.by[x] && !badged.has(x) && x !== id)])];
  let srcHtml = "";
  if (r.type === "source") {
    const s = d.source || {};
    srcHtml = `<div class="src">${s.citation ? `<p>${esc(s.citation)}</p>` : ""}<p class="meta">${[s.source_kind, s.reliability && "reliability: " + s.reliability, s.verified && "verified: " + s.verified, s.checked_on && "checked " + s.checked_on].filter(Boolean).map(esc).join(" · ")}</p>${s.url ? `<p><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.url)}</a></p>` : ""}</div>` + groupTags(d.cited_by || [], "Cited by");
  } else if (sourceRecs.length) {
    srcHtml = `<h3>Sources</h3>` + sourceRecs.map((s) => `<div class="src"><a href="#/n/${esc(s.id)}"><strong>${esc(s.title)}</strong></a>${s.source && s.source.url ? ` · <a href="${esc(s.source.url)}" target="_blank" rel="noopener">link ↗</a>` : ""}<div class="meta">${esc([s.source && s.source.source_kind, s.source && s.source.reliability && "reliability: " + s.source.reliability].filter(Boolean).join(" · "))}</div></div>`).join("");
  }
  const credits = d.images.length ? `<div class="credits"><strong>Image credits</strong><ol>${d.images.map((im) => `<li>${esc(im.caption)}${im.ai ? ` <span class="badge ai">AI illustration</span> ${esc(im.model || "")}` : ""}${im.author ? " — " + esc(im.author) : ""}${im.license ? ". " + (im.license_url ? `<a href="${esc(im.license_url)}" target="_blank" rel="noopener">${esc(im.license)}</a>` : esc(im.license)) : ""}${im.source ? ` · <a href="${esc(im.source)}" target="_blank" rel="noopener">source</a>` : ""}${im.via && /borrowed/.test(im.via) ? ` · <em>${esc(im.via)}</em>` : ""}</li>`).join("")}</ol></div>` : "";
  const sim = r.type === "source" ? [] : similar(id, 8);
  const { prev, next } = prevNext(id);
  const brief = S.ai.briefs?.[id]?.text;
  const v = d.voice;
  const rewrite = v ? `<p class="rw"><span class="badge ai">AI rewrite</span>${esc(cap(VOICE[v.mode] || v.mode))} voice${v.observer_mode && d.observer ? `; Observer's Reading in the ${esc(VOICE[v.observer_mode] || v.observer_mode)} voice` : ""}. Retold from the vault note, with its names, numbers and links checked.</p>` : "";
  const saved = marks.has(id);
  const crumbs = [`<a href="#/v/browse?t=${r.type}">${esc(LABEL[r.type])}</a>`, era && r.type !== "era" ? `<a href="#/n/${esc(era.id)}">${esc(era.title)}</a>` : "", reg && r.type !== "region" ? `<a href="#/n/${esc(reg.id)}">${esc(reg.title)}</a>` : ""].filter(Boolean);
  dlg.innerHTML = `<div class="np" data-t="${r.type}"><div class="np-top"><nav class="crumbs" aria-label="Breadcrumb">${crumbs.join(" › ")}</nav><span class="acts"><button class="btn" data-action="save" data-id="${esc(id)}" aria-pressed="${saved}">${saved ? "Saved" : "Save"}</button><button class="btn" data-action="copy-link">Copy link</button><button class="btn" data-graph="${esc(id)}">Show in graph</button><button class="btn" data-close>Close</button></span></div>
  <div class="np-body">
    <div class="badges"><span class="badge type">${esc(SINGULAR[r.type])}</span>${r.date ? `<span class="badge tnum">${esc(r.date)}</span>` : ""}${era ? `<a class="badge" href="#/n/${esc(era.id)}">${esc(era.title)}</a>` : ""}${reg ? `<a class="badge" href="#/n/${esc(reg.id)}">${esc(reg.title)}</a>` : ""}${themes}${r.conf ? `<span class="badge conf-${esc(r.conf)}" title="Confidence in the facts">confidence: ${esc(r.conf)}</span>` : ""}</div>
    <h2 class="title" id="noteTitle" tabindex="-1">${esc(r.title)}</h2>${gallery}
    ${brief ? `<div class="brief"><span class="badge ai">In brief · AI-written</span>${esc(brief)}</div>` : ""}
    ${rewrite}<div class="prose">${d.summary ? `<h3>${r.type === "source" ? "What it is used for" : "Summary"}</h3>${d.summary}` : ""}
    ${d.facts.length ? `<h3>Facts</h3><ul class="facts">${d.facts.map((f) => `<li>${f}</li>`).join("")}</ul>` : ""}
    ${d.context ? `<h3>Context &amp; connections</h3>${d.context}` : ""}
    ${d.observer ? `<aside class="observer" aria-label="Observer's Reading, interpretation"><div class="tag">Interpretation · not established fact</div><h3>Observer's Reading</h3>${d.observer}</aside>` : ""}
    ${d.questions.length ? `<div class="questions"><h3>Open questions</h3><ul>${d.questions.map((q) => `<li>${q}</li>`).join("")}</ul></div>` : ""}
    ${d.extra.map((x) => `<h3>${esc(x.title)}</h3>${x.html}`).join("")}
    </div>
    ${sim.length ? `<h3>You might also like</h3><div class="rail">${sim.map((x) => cardHTML(x.rec, { why: x.why })).join("")}</div>` : ""}
    ${prev || next ? `<nav class="pn" aria-label="Previous and next in time">${prev ? `<a href="#/n/${esc(prev.id)}"><small>← Earlier</small>${esc(prev.title)}</a>` : "<span></span>"}${next ? `<a href="#/n/${esc(next.id)}" style="text-align:right"><small>Later →</small>${esc(next.title)}</a>` : ""}</nav>` : ""}
    ${members}${groupTags(connIds, "Connections")}${srcHtml}
    ${d.fact_checks.length ? `<details class="fc"><summary>Fact checks (${d.fact_checks.length})</summary><ul>${d.fact_checks.map((f) => `<li>${esc(f)}</li>`).join("")}</ul></details>` : ""}
    ${credits}
  </div></div>`;
  dlg.scrollTop = 0;
  $("#noteTitle", dlg)?.focus({ preventScroll: true });
  announce(`${r.title}, ${SINGULAR[r.type]}`);
}

/* ---------- lightbox ---------- */
const lbEl = $("#lb");
export function openLightbox(i) { lbIdx = i; showLb(); if (!lbEl.open) lbEl.showModal(); }
function showLb() {
  const im = currentImages[lbIdx]; if (!im) return;
  const img = $("img", lbEl); img.onerror = () => { if (im.thumb && img.src.indexOf(im.thumb) < 0) img.src = im.thumb; };
  img.src = im.src; img.alt = im.caption || "";
  $(".cap", lbEl).innerHTML = `${im.ai ? '<span class="badge ai">AI illustration</span> ' : ""}${esc(im.caption)}<br>${im.author ? esc(im.author) + " · " : ""}${im.license_url ? `<a href="${esc(im.license_url)}" target="_blank" rel="noopener">${esc(im.license)}</a>` : esc(im.license || "")}${im.source ? ` · <a href="${esc(im.source)}" target="_blank" rel="noopener">source</a>` : ""}<br>${lbIdx + 1} / ${currentImages.length}`;
  $(".prev", lbEl).style.display = $(".next", lbEl).style.display = currentImages.length > 1 ? "" : "none";
  const nxt = currentImages[(lbIdx + 1) % currentImages.length]; if (nxt) new Image().src = nxt.src;   // preload the neighbour
}
const lbStep = (d) => { lbIdx = (lbIdx + d + currentImages.length) % currentImages.length; showLb(); };
export function initLightbox() {
  lbEl.innerHTML = `<button class="x" aria-label="Close image viewer">${icon.close}</button><button class="prev" aria-label="Previous image">${icon.prev}</button><button class="next" aria-label="Next image">${icon.next}</button><img alt=""><div class="cap" aria-live="polite"></div>`;
  lbEl.addEventListener("click", (e) => { if (e.target.closest(".prev")) lbStep(-1); else if (e.target.closest(".next")) lbStep(1); else if (e.target === lbEl || e.target.closest(".x")) lbEl.close(); });
  document.addEventListener("keydown", (e) => { if (!lbEl.open) return; if (e.key === "ArrowLeft") lbStep(-1); else if (e.key === "ArrowRight") lbStep(1); });
}
