/* Images that always resolve to something: retry once, then fall back to the next candidate, then a typed placeholder.
   Boxes reserve their space (aspect-ratio) so nothing shifts while images load. */
import { esc } from "./util.js";

export function picture(urls, type, initial, { alt = "", eager = false, ai = false } = {}) {
  const [src, ...alts] = urls.filter(Boolean);
  const badge = ai ? '<span class="ai-badge">AI illustration</span>' : "";
  if (!src) return `<div class="thumb none" data-t="${esc(type)}"><span class="ph" aria-hidden="true">${esc(initial)}</span></div>`;
  return `<div class="thumb" data-t="${esc(type)}"><img src="${esc(src)}" data-alts="${esc(JSON.stringify(alts))}" alt="${esc(alt)}" ${eager ? 'loading="eager" fetchpriority="high"' : 'loading="lazy"'} decoding="async"><span class="ph" aria-hidden="true">${esc(initial)}</span>${badge}</div>`;
}

const isThumbImg = (el) => el && el.tagName === "IMG" && el.parentElement && el.parentElement.classList.contains("thumb");

function onLoad(e) { if (isThumbImg(e.target)) e.target.parentElement.classList.add("loaded"); }
function onError(e) {
  const img = e.target; if (!isThumbImg(img)) return;
  const tries = +(img.dataset.tries || 0);
  if (tries === 0) {                                    // one retry with a cache-buster (transient failures, OneDrive hydration)
    img.dataset.tries = "1"; const u = img.getAttribute("src");
    setTimeout(() => (img.src = u + (u.includes("?") ? "&" : "?") + "r=" + Date.now()), 400);
    return;
  }
  let alts = []; try { alts = JSON.parse(img.dataset.alts || "[]"); } catch { /* ignore */ }
  if (alts.length) { const next = alts.shift(); img.dataset.alts = JSON.stringify(alts); img.dataset.tries = "0"; img.src = next; return; }
  img.parentElement.classList.add("failed");
}
export function installImageGuards() {
  document.addEventListener("load", onLoad, true);
  document.addEventListener("error", onError, true);
}

/* ---------- self test (?selftest=images): every image URL must load and decode; the fallback chain must work ---------- */
export async function selfTest(S) {
  const box = document.createElement("div"); box.className = "selftest"; box.setAttribute("role", "status");
  box.textContent = "Image self-test running…"; document.body.appendChild(box);
  const urls = new Set();
  S.idx.forEach((r) => { if (r.img) urls.add(r.img); if (r.imt) urls.add(r.imt); });
  const types = [...new Set(S.idx.map((r) => r.type))];
  for (const t of types) {
    const chunk = await fetch(`data/notes-${t}.json`).then((r) => r.json());
    Object.values(chunk).forEach((d) => d.images.forEach((im) => { urls.add(im.src); if (im.thumb) urls.add(im.thumb); }));
  }
  const list = [...urls], failed = []; let ok = 0, i = 0;
  const worker = async () => {
    while (i < list.length) {
      const u = list[i++];
      try {
        const r = await fetch(u, { cache: "no-store" }); if (!r.ok) throw new Error("HTTP " + r.status);
        const b = await r.blob(); if (!b.type.startsWith("image/") || b.size < 500) throw new Error("not an image");
        await createImageBitmap(b); ok++;
      } catch (e) { failed.push(`${u} (${e.message})`); }
      if (i % 200 === 0) box.textContent = `Image self-test: ${i}/${list.length}…`;
    }
  };
  await Promise.all(Array.from({ length: 12 }, worker));
  // fallback chain: bad -> bad -> good must end up loaded; bad -> bad must end up as a placeholder
  const good = S.idx.find((r) => r.imt)?.imt;
  const host = document.createElement("div"); host.style.cssText = "position:fixed;left:0;top:0;width:200px;opacity:.01;pointer-events:none;z-index:-1"; // in the viewport: lazy images off-screen would never load
  host.innerHTML = picture(["images/__nope1.jpg", "images/__nope2.jpg", good], "event", "T") + picture(["images/__nope3.jpg", "images/__nope4.jpg"], "event", "T");
  document.body.appendChild(host);
  await new Promise((res) => setTimeout(res, 3500));
  const [a, b] = host.querySelectorAll(".thumb");
  const chain = { recovers: a.classList.contains("loaded") && !a.classList.contains("failed"), placeholder: b.classList.contains("failed") };
  host.remove();
  const res = { total: list.length, ok, failed: failed.length, failures: failed.slice(0, 50), fallbackChain: chain };
  window.__selftest = res; console.log("IMAGE SELFTEST", JSON.stringify(res));
  const pass = !failed.length && chain.recovers && chain.placeholder;
  box.innerHTML = `<strong>Image self-test: ${pass ? "PASS" : "FAIL"}</strong><br>${ok}/${list.length} images loaded and decoded, ${failed.length} failed.<br>Fallback chain: recovers=${chain.recovers}, placeholder=${chain.placeholder}.` + (failed.length ? `<ul>${failed.slice(0, 20).map((f) => `<li>${esc(f)}</li>`).join("")}</ul>` : "");
  return res;
}
