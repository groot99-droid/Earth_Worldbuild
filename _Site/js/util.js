/* Shared constants and helpers. */
export const $ = (s, r = document) => r.querySelector(s);
export const $$ = (s, r = document) => [...r.querySelectorAll(s)];
export const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
export const TYPES = ["era", "event", "person", "place", "culture", "technology", "species", "region", "theme", "observer-note", "timeline", "source"];
export const DEFAULT_TYPES = TYPES.filter((t) => t !== "source");
export const LABEL = { era: "Eras", event: "Events", person: "People", place: "Places", culture: "Peoples & cultures", technology: "Artifacts & tech", species: "Species", region: "Regions", theme: "Themes", "observer-note": "Observer notes", timeline: "Timelines", source: "Sources" };
export const SINGULAR = { era: "Era", event: "Event", person: "Person", place: "Place", culture: "People & culture", technology: "Artifact / tech", species: "Species", region: "Region", theme: "Theme", "observer-note": "Observer note", timeline: "Timeline", source: "Source" };
export const HUB_TYPES = new Set(["era", "region", "theme", "timeline", "observer-note"]);
export const NOW = 2026;

/* localStorage can throw (private mode, blocked site data): every access is guarded and falls back to memory. */
const mem = new Map();
export const store = {
  get(k) { try { return localStorage.getItem(k); } catch { return mem.get(k) ?? null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { mem.set(k, v); } },
  getJSON(k, d) { try { const v = this.get(k); return v ? JSON.parse(v) : d; } catch { return d; } },
  setJSON(k, v) { this.set(k, JSON.stringify(v)); },
};

export async function fetchJson(url, tries = 2) {
  let err;
  for (let i = 0; i < tries; i++) {
    try { const r = await fetch(url); if (!r.ok) throw new Error(`${url} ${r.status}`); return await r.json(); }
    catch (e) { err = e; await new Promise((res) => setTimeout(res, 300 * (i + 1))); }
  }
  throw err;
}
export const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };
export const reducedMotion = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

export function announce(msg, visible = false) {
  const live = $("#live"); if (live) { live.textContent = ""; setTimeout(() => (live.textContent = msg), 30); }
  if (visible) {
    const t = $("#toast"); if (!t) return; t.textContent = msg; t.hidden = false;
    clearTimeout(announce._t); announce._t = setTimeout(() => (t.hidden = true), 3500);
  }
}
export const icon = {
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>',
  close: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg>',
  prev: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m15 5-7 7 7 7"/></svg>',
  next: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m9 5 7 7-7 7"/></svg>',
  moon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>',
};
