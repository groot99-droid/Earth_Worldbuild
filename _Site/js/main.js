/* Earth Chronicle: boot, controls and routing. Static site, no build step; serve the folder over HTTP. */
import { S, applyQuery, activeFilterCount, getNote, hashFor, isDefaultFilters, loadData, syncURL, themeTitle } from "./state.js";
import { filtered, suggestHTML } from "./search.js";
import { recentQ, hist, marks } from "./store.js";
import { installImageGuards, selfTest } from "./img.js";
import { renderTimeline, renderRegions, renderBrowse, showAllInRegion, skeleton } from "./views.js";
import { renderGraph, stopGraph, redrawGraph } from "./graph.js";
import { renderExplore, renderJourney, journeyKey, doConnect } from "./explore.js";
import { dlg, openNote, openLightbox, initLightbox } from "./note.js";
import { surprise } from "./recs.js";
import { $, $$, DEFAULT_TYPES, LABEL, TYPES, announce, debounce, esc, icon, store } from "./util.js";

const VIEWS = ["timeline", "regions", "graph", "browse", "explore"];
S.graphList = false;
const main = () => $("#main");

/* ---------- render ---------- */
function render({ focusMain = false, scrollTop = false } = {}) {
  stopGraph();
  syncControls();
  const m = main(), list = filtered();
  const label = S.view === "explore" ? "Explore" : `${list.length} of ${S.idx.length} notes`;
  $("#count").textContent = label;
  const fn = { timeline: renderTimeline, regions: renderRegions, browse: renderBrowse, graph: (mm, l) => renderGraph(mm, l, S.graphList), explore: renderExplore }[S.view] || renderTimeline;
  fn(m, list);
  S.renderedKey = hashFor(S.view) + (S.graphList ? "|list" : "");
  if (scrollTop) window.scrollTo({ top: 0 });
  if (focusMain) m.focus({ preventScroll: true });
}
function refresh() { S.browseN = 60; render(); syncURL(); }

/* ---------- controls ---------- */
function buildControls() {
  const chips = $("#typeChips");
  chips.innerHTML = `<button class="chip" data-type="all" aria-pressed="true">All notes</button>` + TYPES.map((t) => `<button class="chip" data-t="${t}" data-type="${t}" aria-pressed="false"><span class="dot" aria-hidden="true"></span>${LABEL[t]}</button>`).join("");
  chips.addEventListener("click", (e) => {
    const c = e.target.closest(".chip"); if (!c) return; const t = c.dataset.type;
    if (t === "all") S.types = new Set(DEFAULT_TYPES);
    else if (e.shiftKey || e.ctrlKey || e.metaKey) { S.types.has(t) ? (S.types.size > 1 && S.types.delete(t)) : S.types.add(t); }
    else if (S.types.size === 1 && S.types.has(t)) S.types = new Set(DEFAULT_TYPES);
    else S.types = new Set([t]);
    refresh();
  });
  const eras = S.idx.filter((r) => r.type === "era").sort((a, b) => (a.ds ?? 1e12) - (b.ds ?? 1e12));
  const regions = S.idx.filter((r) => r.type === "region").sort((a, b) => a.title.localeCompare(b.title));
  $("#fEra").innerHTML += eras.map((r) => `<option value="${esc(r.id)}">${esc(r.title)}</option>`).join("");
  $("#fRegion").innerHTML += regions.map((r) => `<option value="${esc(r.id)}">${esc(r.title)}</option>`).join("");
  $("#fTheme").innerHTML += S.meta.themes.map((t) => `<option value="${esc(t.slug)}">${esc(t.title)}</option>`).join("");
  for (const [id, key] of [["#fEra", "era"], ["#fRegion", "region"], ["#fTheme", "theme"], ["#fConf", "conf"]]) $(id).addEventListener("change", (e) => { S[key] = e.target.value; refresh(); });
  $("#tabs").addEventListener("click", (e) => { const t = e.target.closest(".tab"); if (t) location.hash = hashFor(t.dataset.view); });
  $("#tabs").addEventListener("keydown", (e) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) return;
    const tabs = $$(".tab"), i = tabs.indexOf(document.activeElement); if (i < 0) return;
    const n = e.key === "Home" ? 0 : e.key === "End" ? tabs.length - 1 : (i + (e.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
    tabs[n].focus(); location.hash = hashFor(tabs[n].dataset.view); e.preventDefault();
  });
  $("#filtersToggle").addEventListener("click", () => { const f = $("#filters"), open = f.hidden; f.hidden = !open; $("#filtersToggle").setAttribute("aria-expanded", String(open)); });
  $("#reset").addEventListener("click", resetFilters);
  $("#themeBtn").addEventListener("click", () => {
    const cur = document.documentElement.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const next = cur === "dark" ? "light" : "dark"; document.documentElement.dataset.theme = next; store.set("ec-theme", next); redrawGraph();
  });
  const saved = store.get("ec-theme"); if (saved) document.documentElement.dataset.theme = saved;
  bindSearch();
  new ResizeObserver(() => document.documentElement.style.setProperty("--head-h", $("#controls").offsetHeight + "px")).observe($("#controls"));
}
function resetFilters() { Object.assign(S, { era: "", region: "", theme: "", conf: "", q: "", focus: "", literal: false, types: new Set(DEFAULT_TYPES) }); refresh(); }

function syncControls() {
  $$("#typeChips .chip").forEach((c) => {
    const t = c.dataset.type; c.setAttribute("aria-pressed", String(t === "all" ? S.types.size === DEFAULT_TYPES.length && DEFAULT_TYPES.every((x) => S.types.has(x)) : S.types.has(t)));
  });
  $("#fEra").value = S.era; $("#fRegion").value = S.region; $("#fTheme").value = S.theme; $("#fConf").value = S.conf;
  const q = $("#q"); if (document.activeElement !== q) q.value = S.q;
  $$(".tab").forEach((t) => { const on = t.dataset.view === S.view; t.setAttribute("aria-selected", String(on)); t.tabIndex = on ? 0 : -1; });
  const n = activeFilterCount(), badge = $("#filtersToggle .n"); badge.textContent = n; badge.hidden = !n;
  const chips = [];
  if (S.q) chips.push(["q", `Search: ${S.q}`]);
  if (S.era) chips.push(["era", `Era: ${S.by[S.era]?.title}`]);
  if (S.region) chips.push(["region", `Region: ${S.by[S.region]?.title}`]);
  if (S.theme) chips.push(["theme", `Theme: ${themeTitle[S.theme] || S.theme}`]);
  if (S.conf) chips.push(["conf", `Confidence: ${S.conf}`]);
  if (!(S.types.size === DEFAULT_TYPES.length && DEFAULT_TYPES.every((x) => S.types.has(x)))) chips.push(["types", `Types: ${TYPES.filter((t) => S.types.has(t)).map((t) => LABEL[t]).join(", ")}`]);
  $("#active").innerHTML = chips.map(([k, l]) => `<span class="af">${esc(l)}<button type="button" data-action="clear" data-key="${k}" aria-label="Remove filter: ${esc(l)}">${icon.close}</button></span>`).join("");
}
function clearKey(key) {
  if (key === "types") S.types = new Set(DEFAULT_TYPES); else if (key === "q") S.q = ""; else S[key] = "";
  refresh();
}

/* ---------- search combobox ---------- */
function bindSearch() {
  const q = $("#q"), box = $("#suggest"); let active = -1;
  const setActive = (i) => { const o = $$(".sg", box); active = o.length ? (i + o.length) % o.length : -1; o.forEach((x, k) => x.setAttribute("aria-selected", String(k === active))); if (o[active]) { q.setAttribute("aria-activedescendant", o[active].id); o[active].scrollIntoView({ block: "nearest" }); } else q.removeAttribute("aria-activedescendant"); };
  const open = () => { box.innerHTML = suggestHTML(q.value); box.hidden = !box.innerHTML; q.setAttribute("aria-expanded", String(!box.hidden)); active = -1; };
  const close = () => { box.hidden = true; q.setAttribute("aria-expanded", "false"); q.removeAttribute("aria-activedescendant"); };
  const commit = (v) => { S.literal = false; S.q = v.trim(); q.value = S.q; if (S.q) recentQ.add(S.q); if (S.view === "explore" || location.hash.startsWith("#/j/")) { location.hash = hashFor("browse"); } else refresh(); close(); };
  const apply = debounce(() => { S.literal = false; S.q = q.value.trim(); if (S.view === "explore") { location.hash = hashFor("browse"); return; } refresh(); }, 260);
  const openSoon = debounce(open, 90);                      // scoring every note on each keystroke is wasted work once you're typing faster than ~90ms/key
  q.addEventListener("input", () => { openSoon(); apply(); });
  q.addEventListener("focus", open);
  q.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { if (box.hidden) open(); setActive(active + 1); e.preventDefault(); }
    else if (e.key === "ArrowUp") { setActive(active - 1); e.preventDefault(); }
    else if (e.key === "Enter") { const o = $$(".sg", box)[active]; if (o && !box.hidden) o.click(); else commit(q.value); e.preventDefault(); }
    else if (e.key === "Escape") { if (!box.hidden) { close(); e.preventDefault(); } else if (q.value) { q.value = ""; S.q = ""; refresh(); } }
  });
  box.addEventListener("mousedown", (e) => e.preventDefault());
  box.addEventListener("click", (e) => {
    const b = e.target.closest(".sg"); if (!b) return;
    if (b.dataset.id) { close(); location.hash = "#/n/" + b.dataset.id; } else commit(b.dataset.q);
  });
  document.addEventListener("click", (e) => { if (!e.target.closest(".searchbox")) close(); });
}

/* ---------- delegated actions ---------- */
document.addEventListener("click", (e) => {
  const a = e.target.closest("a.card, a.ghead, .tag-link, a[href^='#/n/']"); if (a && !dlg.contains(a)) S.trigger = a;
  const band = e.target.closest(".band");
  if (band) { const g = document.getElementById("g-" + band.dataset.go.replace("/", "-")); if (g) g.scrollIntoView({ behavior: "smooth", block: "start" }); else location.hash = "#/n/" + band.dataset.go; return; }
  if (e.target.closest("[data-close]")) { dlg.close(); return; }
  const lb = e.target.closest("[data-lb]"); if (lb) { openLightbox(+lb.dataset.lb); return; }
  const g = e.target.closest("[data-graph]"); if (g) { S.focus = g.dataset.graph; S.graphList = false; dlg.close(); location.hash = hashFor("graph"); return; }
  const act = e.target.closest("[data-action]"); if (!act) return;
  const d = act.dataset;
  switch (d.action) {
    case "reset": resetFilters(); break;
    case "clear": clearKey(d.key); break;
    case "clear-q": clearKey("q"); break;
    case "all-types": S.types = new Set(TYPES); refresh(); break;
    case "literal-q": S.literal = true; render(); break;
    case "more": showAllInRegion(act, filtered()); break;
    case "show-more": S.browseN += 60; render(); break;
    case "unfocus": S.focus = ""; location.hash = hashFor("graph"); break;
    case "graph-mode": S.graphList = !S.graphList; render(); break;
    case "surprise": { const r = surprise(); if (r) location.hash = "#/n/" + r.id; break; }
    case "connect": doConnect(); break;
    case "clear-history": hist.clear(); announce("Reading history cleared", true); render(); break;
    case "retry-note": openNote(d.id); break;
    case "copy-link": copyLink(); break;
    case "save": { const on = marks.toggle(d.id); act.setAttribute("aria-pressed", String(on)); act.textContent = on ? "Saved" : "Save"; announce(on ? "Saved to this browser" : "Removed from saved", true); break; }
    default: break;
  }
});
async function copyLink() {
  const url = location.href;
  try { await navigator.clipboard.writeText(url); announce("Link copied", true); }
  catch { const t = document.createElement("textarea"); t.value = url; document.body.appendChild(t); t.select(); try { document.execCommand("copy"); announce("Link copied", true); } catch { announce("Copy failed. The address bar has the link.", true); } t.remove(); }
}
document.addEventListener("click", (e) => {                 // quiz options (rendered by explore.js)
  const opt = e.target.closest(".quiz .opt"); if (!opt) return;
  const q = opt.closest(".q"), item = S.ai.quiz[+q.dataset.qi];
  $$(".opt", q).forEach((b, i) => { b.disabled = true; b.classList.toggle("right", i === item.answer); if (b === opt && i !== item.answer) b.classList.add("wrong"); });
  $(".meta", q).hidden = false; announce(+opt.dataset.oi === item.answer ? "Correct" : "Not quite. The correct answer is highlighted.");
});
document.addEventListener("keydown", (e) => {
  const band = e.target.closest?.(".band"); if (band && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); band.dispatchEvent(new MouseEvent("click", { bubbles: true })); return; }
  const m = location.hash.match(/^#\/j\/([^/]+)\/(\d+)/); if (m && !dlg.open && !/INPUT|SELECT|TEXTAREA/.test(e.target.tagName)) journeyKey(e, m[1], +m[2]);
});
dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });
dlg.addEventListener("close", () => {
  if (location.hash.startsWith("#/n/")) { history.replaceState(null, "", S.listHash); S.prevKind = "v"; }
  const t = S.trigger; if (t && t.isConnected) t.focus({ preventScroll: true }); else main().focus({ preventScroll: true });
});

/* ---------- routing ---------- */
function route(initial = false) {
  const h = location.hash.replace(/^#\/?/, ""), [pathPart, qs] = h.split("?"), [kind, ...rest] = pathPart.split("/"), arg = rest.join("/");
  if (kind === "n" && S.by[arg]) {
    if (!S.rendered) { applyQuery(""); S.view = "timeline"; render(); S.listHash = hashFor("timeline"); }
    S.rendered = true; S.prevKind = "n"; openNote(arg); return;
  }
  if (dlg.open) dlg.close();
  if (kind === "g" && S.by[arg]) { S.focus = arg; S.view = "graph"; S.graphList = false; history.replaceState(null, "", hashFor("graph")); render({ scrollTop: true }); S.prevKind = "v"; return; }
  if (kind === "j") {
    const [jid, st] = arg.split("/"); S.view = "explore"; syncControls(); stopGraph(); renderJourney(main(), jid, +st || 0);
    S.renderedKey = "j:" + arg; S.prevKind = "j"; window.scrollTo({ top: 0 }); return;
  }
  const view = kind === "v" && VIEWS.includes(arg) ? arg : "timeline";
  const prevView = S.view;
  if (kind === "v") applyQuery(qs); else { applyQuery(""); }
  S.view = view;
  const key = hashFor(view) + (S.graphList ? "|list" : "");
  if (initial || key !== S.renderedKey) render({ focusMain: !initial && prevView !== view, scrollTop: !initial && prevView !== view });
  S.rendered = true; S.listHash = hashFor(view);
  if (kind !== "v") history.replaceState(null, "", S.listHash);
  S.prevKind = "v";
}
window.addEventListener("hashchange", () => route(false));

/* ---------- boot ---------- */
(async () => {
  installImageGuards(); initLightbox();
  main().innerHTML = skeleton(12);
  try {
    await loadData();
    buildControls();
    route(true);
    if (new URLSearchParams(location.search).get("selftest") === "images") selfTest(S);
  } catch (err) {
    console.error(err);
    main().innerHTML = `<div class="empty"><h2>Couldn’t load the chronicle</h2><p>${esc(err.message)}. Serve this folder over HTTP (for example <code>python -m http.server</code>) and make sure <code>python scripts/build_site.py</code> has been run.</p><div class="row"><button class="btn primary" onclick="location.reload()">Try again</button></div></div>`;
  }
})();
