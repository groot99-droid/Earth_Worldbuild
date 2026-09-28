/* Reading history, saved notes and recent searches (all local to this browser). */
import { store } from "./util.js";

const HKEY = "ec-hist", MKEY = "ec-marks", QKEY = "ec-recentq";
export const hist = {
  list() { return store.getJSON(HKEY, []); },
  add(id) { const l = this.list().filter((x) => x.id !== id); l.unshift({ id, t: Date.now() }); store.setJSON(HKEY, l.slice(0, 80)); },
  ids() { return this.list().map((x) => x.id); },
  clear() { store.setJSON(HKEY, []); },
};
export const marks = {
  list() { return store.getJSON(MKEY, []); },
  has(id) { return this.list().includes(id); },
  toggle(id) { const l = this.list(); const i = l.indexOf(id); if (i >= 0) l.splice(i, 1); else l.unshift(id); store.setJSON(MKEY, l); return i < 0; },
};
export const recentQ = {
  list() { return store.getJSON(QKEY, []); },
  add(q) { q = q.trim(); if (q.length < 2) return; const l = this.list().filter((x) => x !== q); l.unshift(q); store.setJSON(QKEY, l.slice(0, 6)); },
  clear() { store.setJSON(QKEY, []); },
};
