/* Link graph: force layout on a canvas, plus a keyboard/screen-reader alternative (arrow keys, and a plain list view). */
import { S } from "./state.js";
import { announce, esc, HUB_TYPES, reducedMotion, SINGULAR, $ } from "./util.js";

const G = { nodes: [], links: [], raf: 0, tx: 0, ty: 0, k: 1, hover: null, canvas: null, tip: null, alpha: 1, userMoved: false, kb: -1, order: [], W: 0, H: 0, colors: null };
const posCache = new Map();                                // node positions persist across renderGraph() calls, so revisiting a view doesn't restart the layout dance
export function stopGraph() { cancelAnimationFrame(G.raf); G.raf = 0; }
function computeColors() {                                 // read theme colors once per render/theme-change instead of every animation frame
  const cs = getComputedStyle(document.documentElement), c = new Map();
  for (const n of G.nodes) { const t = n.r.type; if (!c.has(t)) c.set(t, cs.getPropertyValue("--c-" + t).trim() || "#888"); }
  c.set("__line", cs.getPropertyValue("--line").trim()); c.set("__accent", cs.getPropertyValue("--accent").trim());
  c.set("__focus", cs.getPropertyValue("--focus").trim()); c.set("__text", cs.getPropertyValue("--text").trim());
  return c;
}

export function renderGraph(main, list, listMode = false) {
  let ids;
  if (S.focus && S.by[S.focus]) {
    const nb = new Map([[S.focus, 0]]);
    const hub = (id) => HUB_TYPES.has(S.by[id].type);
    for (let d = 1; d <= 2; d++) for (const [a, b] of S.edges) {
      if (nb.get(a) === d - 1 && !nb.has(b) && (d === 1 || !hub(a))) nb.set(b, d);
      if (nb.get(b) === d - 1 && !nb.has(a) && (d === 1 || !hub(b))) nb.set(a, d);
    }
    ids = [...nb.keys()];
  } else ids = list.filter((r) => r.type !== "source").map((r) => r.id);
  const set = new Set(ids);
  const links = S.edges.filter(([a, b]) => set.has(a) && set.has(b));
  const deg = new Map(ids.map((i) => [i, 0])); links.forEach(([a, b]) => { deg.set(a, deg.get(a) + 1); deg.set(b, deg.get(b) + 1); });
  const bar = `<div class="graph-bar"><span class="pill">${ids.length} notes · ${links.length} links</span>${S.focus ? `<span class="pill">Focus: ${esc(S.by[S.focus].title)}</span><button class="btn" data-action="unfocus">Show all</button>` : ""}<button class="btn" data-action="graph-mode" aria-pressed="${listMode}">${listMode ? "Show graph" : "View as list"}</button></div>`;
  if (!ids.length) { main.innerHTML = `<div class="empty"><h2>No notes to graph</h2><p>Nothing matches these filters.</p><div class="row"><button class="btn primary" data-action="reset">Reset all filters</button></div></div>`; return; }
  if (listMode) {                                           // accessible alternative: every note with its strongest neighbours
    const nbrs = new Map(ids.map((i) => [i, []])); links.forEach(([a, b]) => { nbrs.get(a).push(b); nbrs.get(b).push(a); });
    const rows = [...ids].sort((a, b) => deg.get(b) - deg.get(a)).slice(0, 300);
    main.innerHTML = `<div class="rail-sec"><div class="row" style="margin-bottom:12px">${bar.replace('class="graph-bar"', 'class="row"')}</div><ul class="glist">${rows.map((id) => { const r = S.by[id]; const n = nbrs.get(id).filter((x) => !HUB_TYPES.has(S.by[x].type)).slice(0, 4).map((x) => S.by[x].title); return `<li data-t="${r.type}"><a href="#/n/${esc(id)}"><strong>${esc(r.title)}</strong></a> <small>${esc(SINGULAR[r.type])} · ${deg.get(id)} links${n.length ? " · " + esc(n.join(", ")) : ""}</small></li>`; }).join("")}</ul>${ids.length > 300 ? `<p class="meta">Showing the 300 best-connected of ${ids.length} notes. Use the filters to narrow the list.</p>` : ""}</div>`;
    return;
  }
  main.innerHTML = `<div class="graph-wrap"><canvas tabindex="0" role="img" aria-label="Network graph of ${ids.length} notes and ${links.length} links. Use left and right arrow keys to move between notes, Enter to open one, or choose View as list."></canvas><div class="graph-tip"></div>${bar}</div>`;
  const wrap = $(".graph-wrap", main); G.canvas = $("canvas", wrap); G.tip = $(".graph-tip", wrap);
  const W = wrap.clientWidth, H = wrap.clientHeight;
  let newCount = 0;
  G.nodes = ids.map((id, i) => {
    const r = S.by[id], cached = posCache.get(id), a = i * 2.399963, rad = 14 * Math.sqrt(i + 1);
    if (!cached) newCount++;
    return { id, r, x: cached ? cached.x : W / 2 + Math.cos(a) * rad, y: cached ? cached.y : H / 2 + Math.sin(a) * rad, vx: 0, vy: 0, deg: deg.get(id), rad: 2.5 + Math.sqrt(deg.get(id)) * 0.6 + (id === S.focus ? 5 : 0) };
  });
  const ix = new Map(G.nodes.map((n, i) => [n.id, i]));
  G.links = links.map(([a, b]) => ({ s: ix.get(a), t: ix.get(b) }));
  G.order = [...G.nodes].sort((a, b) => b.deg - a.deg);
  G.tx = 0; G.ty = 0; G.k = 1; G.userMoved = false; G.kb = -1; G.hover = null;
  G.alpha = ids.length && newCount === 0 ? 0.2 : 1;         // a fully-cached view only needs a gentle settle, not a full re-layout from scratch
  sizeCanvas(); G.colors = computeColors(); bindGraph();
  if (reducedMotion() || (ids.length && newCount === 0)) { for (let i = 0; i < 90 && G.alpha > 0.02; i++) step(); fitGraph(); drawGraph(); } else tick();
}
function sizeCanvas() { const c = G.canvas, dpr = devicePixelRatio || 1; G.W = c.clientWidth; G.H = c.clientHeight; c.width = G.W * dpr; c.height = G.H * dpr; }
function step() {
  const N = G.nodes, W = G.W, H = G.H;
  for (let it = 0; it < 4; it++) {
    const a = G.alpha;
    for (let i = 0; i < N.length; i++) for (let j = i + 1; j < N.length; j++) {
      let dx = N[j].x - N[i].x, dy = N[j].y - N[i].y, d2 = dx * dx + dy * dy;
      if (d2 > 250000) continue; if (d2 < 1) { dx = Math.random() - .5; dy = Math.random() - .5; d2 = 1; }
      const f = (2600 * a) / d2, d = Math.sqrt(d2); dx = (dx / d) * f; dy = (dy / d) * f;
      N[i].vx -= dx; N[i].vy -= dy; N[j].vx += dx; N[j].vy += dy;
    }
    for (const l of G.links) { const s = N[l.s], t = N[l.t]; const dx = t.x - s.x, dy = t.y - s.y, d = Math.sqrt(dx * dx + dy * dy) || 1; const f = (d - 60) * 0.02 * a; s.vx += (dx / d) * f; s.vy += (dy / d) * f; t.vx -= (dx / d) * f; t.vy -= (dy / d) * f; }
    for (const n of N) { n.vx += (W / 2 - n.x) * 0.0025 * a; n.vy += (H / 2 - n.y) * 0.0025 * a; n.vx = Math.max(-25, Math.min(25, n.vx)); n.vy = Math.max(-25, Math.min(25, n.vy)); n.x += n.vx; n.y += n.vy; n.vx *= 0.8; n.vy *= 0.8; }
    G.alpha *= 0.985;
  }
  for (const n of N) posCache.set(n.id, { x: n.x, y: n.y });
}
function tick() {
  if (G.alpha > 0.02) step();
  if (!G.userMoved && (G.alpha < 0.3 || G.alpha === 1)) fitGraph();
  drawGraph();
  G.raf = G.alpha > 0.02 ? requestAnimationFrame(tick) : 0;
}
function fitGraph() {
  const N = G.nodes; if (!N.length) return;
  let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
  for (const n of N) { x0 = Math.min(x0, n.x); x1 = Math.max(x1, n.x); y0 = Math.min(y0, n.y); y1 = Math.max(y1, n.y); }
  const W = G.W, H = G.H, k = Math.min(3, 0.92 * Math.min(W / Math.max(1, x1 - x0), H / Math.max(1, y1 - y0)));
  G.k = k; G.tx = W / 2 - ((x0 + x1) / 2) * k; G.ty = H / 2 - ((y0 + y1) / 2) * k;
}
export function drawGraph() {
  const c = G.canvas; if (!c || !c.isConnected) return; const ctx = c.getContext("2d"), dpr = devicePixelRatio || 1;
  const col = G.colors || (G.colors = computeColors());
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.clearRect(0, 0, c.width, c.height);
  ctx.setTransform(dpr * G.k, 0, 0, dpr * G.k, dpr * G.tx, dpr * G.ty);
  const hv = G.hover || (G.kb >= 0 ? G.order[G.kb] : null), hs = new Set();
  if (hv) { hs.add(hv.id); G.links.forEach((l) => { if (G.nodes[l.s] === hv) hs.add(G.nodes[l.t].id); if (G.nodes[l.t] === hv) hs.add(G.nodes[l.s].id); }); }
  ctx.lineWidth = 0.6 / G.k; ctx.strokeStyle = col.get("__line");
  ctx.globalAlpha = hv ? 0.25 : 0.55; ctx.beginPath();
  for (const l of G.links) { const s = G.nodes[l.s], t = G.nodes[l.t]; ctx.moveTo(s.x, s.y); ctx.lineTo(t.x, t.y); }
  ctx.stroke();
  if (hv) { ctx.globalAlpha = 1; ctx.strokeStyle = col.get("__accent"); ctx.lineWidth = 1.2 / G.k; ctx.beginPath(); for (const l of G.links) { const s = G.nodes[l.s], t = G.nodes[l.t]; if (s === hv || t === hv) { ctx.moveTo(s.x, s.y); ctx.lineTo(t.x, t.y); } } ctx.stroke(); }
  for (const n of G.nodes) { ctx.globalAlpha = hv && !hs.has(n.id) ? 0.25 : 1; ctx.fillStyle = col.get(n.r.type) || "#888"; ctx.beginPath(); ctx.arc(n.x, n.y, n.rad, 0, 6.2832); ctx.fill(); }
  ctx.globalAlpha = 1;
  if (hv) { ctx.strokeStyle = col.get("__focus"); ctx.lineWidth = 2.5 / G.k; ctx.beginPath(); ctx.arc(hv.x, hv.y, hv.rad + 3 / G.k, 0, 6.2832); ctx.stroke(); }
  ctx.fillStyle = col.get("__text"); ctx.font = `${11 / G.k}px sans-serif`;
  for (const n of G.nodes) if ((hv && hs.has(n.id)) || n.id === S.focus || (G.k > 1.8 && n.deg > 12) || n.deg > 70) ctx.fillText(n.r.title, n.x + n.rad + 2, n.y + 3);
}
export function redrawGraph() { if (G.nodes.length) G.colors = computeColors(); drawGraph(); }
function nodeAt(e) {
  const b = G.canvas.getBoundingClientRect(), x = (e.clientX - b.left - G.tx) / G.k, y = (e.clientY - b.top - G.ty) / G.k;
  let best = null, bd = 1e9; for (const n of G.nodes) { const d = (n.x - x) ** 2 + (n.y - y) ** 2; if (d < (n.rad + 4 / G.k) ** 2 && d < bd) { best = n; bd = d; } } return best;
}
function bindGraph() {
  const c = G.canvas; let drag = null, moved = false;
  c.onpointerdown = (e) => { drag = { x: e.clientX, y: e.clientY, tx: G.tx, ty: G.ty }; moved = false; c.setPointerCapture(e.pointerId); c.style.cursor = "grabbing"; };
  c.onpointermove = (e) => {
    if (drag) { const dx = e.clientX - drag.x, dy = e.clientY - drag.y; if (Math.abs(dx) + Math.abs(dy) > 3) { moved = true; G.userMoved = true; } G.tx = drag.tx + dx; G.ty = drag.ty + dy; drawGraph(); return; }
    const n = nodeAt(e); if (n !== G.hover) { G.hover = n; drawGraph(); }
    if (n) { G.tip.style.display = "block"; G.tip.textContent = `${n.r.title} · ${SINGULAR[n.r.type]}`; const b = c.getBoundingClientRect(); G.tip.style.left = e.clientX - b.left + 12 + "px"; G.tip.style.top = e.clientY - b.top + 12 + "px"; } else G.tip.style.display = "none";
  };
  c.onpointerup = (e) => { c.style.cursor = "grab"; if (drag && !moved) { const n = nodeAt(e); if (n) location.hash = "#/n/" + n.id; } drag = null; };
  c.onwheel = (e) => { e.preventDefault(); G.userMoved = true; const b = c.getBoundingClientRect(), mx = e.clientX - b.left, my = e.clientY - b.top, k2 = Math.min(6, Math.max(0.3, G.k * (e.deltaY < 0 ? 1.15 : 1 / 1.15))); G.tx = mx - ((mx - G.tx) / G.k) * k2; G.ty = my - ((my - G.ty) / G.k) * k2; G.k = k2; drawGraph(); };
  c.onkeydown = (e) => {                                   // keyboard: arrows move through notes by connectedness, Enter opens
    const n = G.order.length; if (!n) return;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") G.kb = (G.kb + 1) % n;
    else if (e.key === "ArrowLeft" || e.key === "ArrowUp") G.kb = (G.kb - 1 + n) % n;
    else if (e.key === "Enter" && G.kb >= 0) { location.hash = "#/n/" + G.order[G.kb].id; return; }
    else return;
    e.preventDefault(); const cur = G.order[G.kb]; G.hover = null; drawGraph();
    announce(`${cur.r.title}, ${SINGULAR[cur.r.type]}, ${cur.deg} links. Press Enter to open.`);
  };
}
window.addEventListener("resize", () => { if (G.canvas && G.canvas.isConnected) { sizeCanvas(); drawGraph(); } });
