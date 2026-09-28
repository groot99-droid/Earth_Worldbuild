/* Explore tab: guided journeys, "connect two notes", surprise me, saved notes and (when present) the quiz. */
import { S } from "./state.js";
import { suggest } from "./search.js";
import { connection, forYou, noteOfTheDay } from "./recs.js";
import { cardHTML, railHTML } from "./views.js";
import { hist, marks } from "./store.js";
import { picture } from "./img.js";
import { $, $$, announce, debounce, esc, SINGULAR } from "./util.js";

export function renderExplore(main) {
  const j = S.featured?.journeys || [];
  const fy = forYou(8), today = noteOfTheDay(), saved = marks.list().map((id) => S.by[id]).filter(Boolean);
  let html = `<div class="rail-sec"><h2>Guided journeys</h2><p class="sub">Curated paths through the chronicle. Each stop is a real note; use the arrow keys to step through.</p><div class="ex-grid">${j.map((x) => `<a class="jcard" href="#/j/${esc(x.id)}/0"><h3>${esc(x.title)}</h3><p>${esc(x.blurb)}</p><p class="meta">${x.steps.length} stops · ${esc(S.by[x.steps[0]]?.title || "")} → ${esc(S.by[x.steps.at(-1)]?.title || "")}</p><div class="jstrip" aria-hidden="true">${x.steps.map(() => "<i></i>").join("")}</div></a>`).join("") || '<p class="meta">Journeys appear after the site data is rebuilt.</p>'}</div></div>`;
  html += `<div class="rail-sec"><h2>Connect two notes</h2><p class="sub">Pick any two notes and see the shortest chain of links between them.</p>
    <div class="connect"><div class="field"><label for="cA">From</label><input id="cA" autocomplete="off" placeholder="e.g. Hammurabi"><div class="suggest" hidden></div></div>
    <div class="field"><label for="cB">To</label><input id="cB" autocomplete="off" placeholder="e.g. Alan Turing"><div class="suggest" hidden></div></div>
    <button class="btn primary" data-action="connect">Find connection</button></div><div id="connect-out" aria-live="polite"></div></div>`;
  html += `<div class="rail-sec"><h2>Feeling curious?</h2><div class="row"><button class="btn primary" data-action="surprise">Surprise me</button>${today ? `<span class="meta">or read today’s pick: <a href="#/n/${esc(today.id)}">${esc(today.title)}</a></span>` : ""}</div></div>`;
  html += railHTML(fy.personal ? "Continue exploring" : "Start here", fy.personal ? "Suggested from what you have been reading" : "", fy.items);
  if (saved.length) html += railHTML("Saved notes", "Stored in this browser only", saved.map((r) => ({ rec: r })));
  if (hist.list().length) html += `<p><button class="link-btn" data-action="clear-history">Clear reading history</button></p>`;
  if (S.ai.quiz?.length) html += quizHTML();
  main.innerHTML = html;
  bindConnect(main);
}

/* ---------- connect two notes ---------- */
function bindConnect(main) {
  for (const inp of $$(".connect input", main)) {
    const box = inp.parentElement.querySelector(".suggest");
    const suggestSoon = debounce(() => {
      const hits = inp.value.trim() ? suggest(inp.value, 6) : [];
      box.innerHTML = hits.map((r) => `<button type="button" class="sg" data-id="${esc(r.id)}"><span><b>${esc(r.title)}</b><small>${esc(SINGULAR[r.type])}</small></span></button>`).join("");
      box.hidden = !hits.length;
    }, 90);
    inp.addEventListener("input", () => { inp.dataset.id = ""; suggestSoon(); });
    box.addEventListener("click", (e) => { const b = e.target.closest(".sg"); if (!b) return; inp.value = S.by[b.dataset.id].title; inp.dataset.id = b.dataset.id; box.hidden = true; inp.focus(); });
    inp.addEventListener("keydown", (e) => { if (e.key === "Escape") box.hidden = true; });
  }
}
export function doConnect() {
  const a = $("#cA"), b = $("#cB"), out = $("#connect-out"); if (!a || !b) return;
  const pick = (inp) => inp.dataset.id || suggest(inp.value, 1)[0]?.id;
  const ia = pick(a), ib = pick(b);
  if (!ia || !ib) { out.innerHTML = `<p class="meta">Choose a note from the suggestions in both boxes.</p>`; return; }
  const path = connection(ia, ib);
  if (!path) { out.innerHTML = `<p class="meta">No chain of links found between <strong>${esc(S.by[ia].title)}</strong> and <strong>${esc(S.by[ib].title)}</strong>. Try notes from nearer eras or regions.</p>`; return; }
  out.innerHTML = `<p class="meta"><strong>${esc(S.by[ia].title)}</strong> and <strong>${esc(S.by[ib].title)}</strong> are ${path.length - 1} link${path.length === 2 ? "" : "s"} apart.</p><div class="path">${path.map((id, i) => (i ? '<span class="arrow" aria-hidden="true">→</span>' : "") + cardHTML(S.by[id])).join("")}</div>`;
  announce(`${path.length - 1} links apart`);
}

/* ---------- journey player ---------- */
export function renderJourney(main, jid, step) {
  const j = (S.featured?.journeys || []).find((x) => x.id === jid);
  if (!j) { main.innerHTML = `<div class="empty"><h2>Journey not found</h2><div class="row"><a class="btn primary" href="#/v/explore">All journeys</a></div></div>`; return; }
  const n = j.steps.length, i = Math.max(0, Math.min(n - 1, step)), r = S.by[j.steps[i]];
  const narration = S.ai.journeys?.[jid]?.steps?.[r.id];
  main.innerHTML = `<div class="player"><p class="meta"><a href="#/v/explore">← All journeys</a></p><h2 style="font-family:var(--serif);margin:.2em 0">${esc(j.title)}</h2>
    <p class="meta">Stop ${i + 1} of ${n}</p><div class="progress" role="progressbar" aria-valuemin="1" aria-valuemax="${n}" aria-valuenow="${i + 1}" aria-label="Journey progress"><div style="width:${((i + 1) / n) * 100}%"></div></div>
    <a class="card" data-t="${r.type}" href="#/n/${esc(r.id)}">${picture([r.img, r.imt], r.type, r.title[0], { eager: true, ai: r.ai, alt: r.title })}<div class="cb"><div class="tl">${esc(SINGULAR[r.type])}${r.date ? ` · <span class="tnum">${esc(r.date)}</span>` : ""}</div><h3 style="font-size:1.5rem">${esc(r.title)}</h3><p>${esc(r.sum)}</p>${narration ? `<p class="why"><span class="badge ai">AI-written</span> ${esc(narration)}</p>` : ""}</div></a>
    <div class="row" style="justify-content:space-between;margin-top:14px"><a class="btn" href="#/j/${esc(jid)}/${Math.max(0, i - 1)}" ${i === 0 ? 'aria-disabled="true" tabindex="-1"' : ""}>← Previous</a><a class="btn" href="#/n/${esc(r.id)}">Open note</a><a class="btn primary" href="#/j/${esc(jid)}/${Math.min(n - 1, i + 1)}" ${i === n - 1 ? 'aria-disabled="true" tabindex="-1"' : ""}>Next →</a></div></div>`;
  announce(`Stop ${i + 1} of ${n}: ${r.title}`);
  hist.add(r.id);
}
export function journeyKey(e, jid, step) {
  const j = (S.featured?.journeys || []).find((x) => x.id === jid); if (!j) return;
  if (e.key === "ArrowRight" && step < j.steps.length - 1) location.hash = `#/j/${jid}/${step + 1}`;
  else if (e.key === "ArrowLeft" && step > 0) location.hash = `#/j/${jid}/${step - 1}`;
}

/* ---------- quiz (questions written by Gemini from each note's Summary and Facts; see scripts/ai_assets.py) ---------- */
function quizHTML() {
  const qs = S.ai.quiz.slice(0, 20);
  return `<div class="rail-sec quiz"><h2>Test yourself <span class="badge ai">AI-written questions</span></h2><p class="sub">Each answer can be checked against the note it comes from.</p>${qs.map((q, qi) => `<div class="q" data-qi="${qi}"><p><strong>${esc(q.q)}</strong></p><div class="opts">${q.options.map((o, oi) => `<button type="button" class="opt" data-oi="${oi}">${esc(o)}</button>`).join("")}</div><p class="meta" hidden>Check: <a href="#/n/${esc(q.id)}">${esc(S.by[q.id]?.title || q.id)}</a></p></div>`).join("")}</div>`;
}
