import * as THREE from 'three';
import { viewingSpot } from './artgeom.js';

const IMAGE_ROOT = '../../';                  // the server is rooted at the project root
const DEFAULT_IMAGE_BASE = 'Art-Talk-main/';  // wings without an image_base (the Art-Talk wing)
const REWRITE_URL = '../data/placard-rewrite.json';   // AI rewrite layer, built by _Rewrite/rewrite_layer.py
const VOICE = { 'epic-fantasy': 'epic-fantasy', 'horror-prose': 'horror-prose', 'essay-self-help': 'essay', 'confessional-poetry': 'confessional-poetry' };

function escapeHtml(t) {
  return String(t).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}
// Placard text is plain prose with *italic* and blank-line paragraph breaks.
function placardHtml(t) {
  return escapeHtml(t).split(/\n\s*\n/).map((p) => p.replace(/\*([^*\n]+)\*/g, '<em>$1</em>')).join('<br><br>');
}

const PICK_DISTANCE = 6;

export function createInteractions(camera, manifestIndex, waypointTrail, isLockedFn, getCurrentRoomId,
  { domElement = null, walls = () => [], groundY = null } = {}) {
  const raycaster = new THREE.Raycaster();
  const ndc = new THREE.Vector2(0, 0);
  let artMeshes = [];
  let current = null;       // the entry whose placard is open
  let hovered = null;       // the entry under the crosshair
  let teleporter = null;    // fn(entry) provided by navigate.js
  let frame = 0;

  function setArtMeshes(meshes) { artMeshes = meshes; }
  function setTeleporter(fn) { teleporter = fn; }

  function pickArt(x = 0, y = 0) {
    ndc.set(x, y);
    raycaster.setFromCamera(ndc, camera);
    raycaster.far = PICK_DISTANCE;
    const hits = raycaster.intersectObjects(artMeshes, false);
    return hits.length ? hits[0].object : null;
  }

  function imageUrl(entry, rel) {
    const wing = manifestIndex.wingsById && manifestIndex.wingsById.get(entry.wing);
    const base = wing && wing.image_base ? wing.image_base : DEFAULT_IMAGE_BASE;
    return IMAGE_ROOT + base + rel;
  }

  const placard = document.getElementById('placard');
  const closeBtn = document.getElementById('placard-close');
  const titleEl = document.getElementById('placard-title');
  const metaEl = document.getElementById('placard-meta');
  const artistEl = document.getElementById('placard-artist');
  const descEl = document.getElementById('placard-description');
  const creditEl = document.getElementById('placard-credit');
  const voiceEl = document.getElementById('placard-voice');
  const imgEl = document.getElementById('placard-image');
  const suggestedList = document.getElementById('suggested-list');
  const prevBtn = document.getElementById('placard-prev');
  const nextBtn = document.getElementById('placard-next');
  const promptEl = document.getElementById('look-prompt');
  const crosshair = document.getElementById('crosshair');
  let rewrites = {};
  const rewritesReady = fetch(REWRITE_URL).then((r) => (r.ok ? r.json() : {})).then((j) => { rewrites = j || {}; return rewrites; }).catch(() => rewrites);

  function artistLine(artist) {
    const bits = [artist.lifespan ? `${artist.name} (${artist.lifespan})` : artist.name];
    if (artist.era && artist.era.title) bits.push(artist.era.title);
    if (artist.wing === 'people' && artist.region) bits.push(artist.region);
    return bits.join(' · ');
  }

  function creditHtml(c) {
    if (!c) return '';
    const link = c.source
      ? `<a href="${escapeHtml(c.source)}" target="_blank" rel="noopener">Wikimedia Commons</a>`
      : 'Wikimedia Commons';
    const license = c.license
      ? (c.license_url ? `<a href="${escapeHtml(c.license_url)}" target="_blank" rel="noopener">${escapeHtml(c.license)}</a>` : escapeHtml(c.license))
      : '';
    const bits = [`Image: ${link}`, escapeHtml(c.author || 'Unknown')];
    if (license) bits.push(license);
    if (c.ai) bits.push(`AI illustration${c.model ? ` (${escapeHtml(c.model)})` : ''}`);
    return bits.join(' · ');
  }

  function renderSuggestions(entry) {
    suggestedList.innerHTML = '';
    const suggestions = manifestIndex.suggestNext(entry);
    for (const s of suggestions) {
      const div = document.createElement('div');
      div.className = 'suggested-item';
      const img = document.createElement('img');
      img.src = imageUrl(s, s.work.thumb || s.work.image);
      img.alt = s.work.title || '';
      const label = document.createElement('span');
      label.textContent = s.work.title || s.artist.name;
      const actions = document.createElement('div');
      actions.className = 'suggested-actions';
      const guide = document.createElement('button');
      guide.type = 'button';
      guide.textContent = 'Guide me';
      guide.title = 'Draw the trail to this work';
      guide.addEventListener('click', (e) => {
        e.stopPropagation();
        waypointTrail.showPathTo(getCurrentRoomId(), s.room, camera.position);
      });
      const tp = document.createElement('button');
      tp.type = 'button';
      tp.textContent = 'Teleport';
      tp.title = 'Jump to this work';
      tp.addEventListener('click', (e) => {
        e.stopPropagation();
        if (teleporter) teleporter(s);
      });
      actions.appendChild(guide);
      actions.appendChild(tp);
      div.appendChild(img);
      div.appendChild(label);
      div.appendChild(actions);
      div.addEventListener('click', () => {
        waypointTrail.showPathTo(getCurrentRoomId(), s.room, camera.position);
      });
      suggestedList.appendChild(div);
    }
  }

  function openPlacard(meshName) {
    const entry = manifestIndex.byMeshName.get(meshName);
    if (!entry) return null;
    const { artist, work } = entry;
    titleEl.textContent = work.title || 'Untitled';
    const metaBits = [work.year, work.medium, work.location].filter(Boolean);
    if (artist.themes && artist.themes.length) metaBits.push(artist.themes.map((t) => t.title || t.slug || t).join(', '));
    metaEl.textContent = metaBits.join(' · ');
    artistEl.textContent = artistLine(artist);
    const rw = rewrites[work.id];
    descEl.innerHTML = placardHtml(rw ? rw.description : (work.description || ''));
    voiceEl.textContent = rw ? `AI rewrite · ${VOICE[rw.mode] || rw.mode} voice, retold from the gallery text` : '';
    voiceEl.hidden = !rw;
    creditEl.innerHTML = creditHtml(work.credit);
    imgEl.src = imageUrl(entry, work.image);
    imgEl.alt = work.title || '';

    renderSuggestions(entry);
    const n = manifestIndex.flatWorks.length;
    if (prevBtn) prevBtn.disabled = !(teleporter && n > 1);
    if (nextBtn) nextBtn.disabled = !(teleporter && n > 1);

    current = entry;
    placard.classList.remove('hidden');
    placard.classList.add('visible');
    return entry;
  }

  function closePlacard() {
    current = null;
    placard.classList.remove('visible');
    placard.classList.add('hidden');
    waypointTrail.clear();
  }
  function isOpen() { return current !== null; }

  function stepWork(dir) {
    if (!current || !teleporter) return;
    const list = manifestIndex.flatWorks;
    const idx = list.indexOf(current);
    if (idx === -1) return;
    teleporter(list[(idx + dir + list.length) % list.length]);
  }

  closeBtn.addEventListener('click', closePlacard);
  if (prevBtn) prevBtn.addEventListener('click', () => stepWork(-1));
  if (nextBtn) nextBtn.addEventListener('click', () => stepWork(1));

  function openAtCrosshair() {
    const hit = pickArt();
    return hit ? openPlacard(hit.name) : null;
  }
  function openAtScreen(x, y) {
    const hit = pickArt(x, y);
    return hit ? openPlacard(hit.name) : null;
  }

  function onClick(e) {
    if (domElement && e.target !== domElement) return; // clicks on panels/buttons are theirs
    if (!isLockedFn()) return;
    openAtCrosshair();
  }
  document.addEventListener('click', onClick);

  // Look-at prompt under the crosshair (every 3rd frame).
  function update() {
    frame++;
    if (frame % 3) return;
    const hit = isLockedFn() ? pickArt() : null;
    const entry = hit ? manifestIndex.byMeshName.get(hit.name) || null : null;
    if (entry === hovered) return;
    hovered = entry;
    if (!promptEl) return;
    if (entry) {
      const t = entry.work.title || '';
      const a = entry.artist.name || '';
      promptEl.textContent = `${t && t !== a ? `${t} — ${a}` : a} · click / E to read`;
      promptEl.hidden = false;
      if (crosshair) crosshair.classList.add('hot');
    } else {
      promptEl.hidden = true;
      if (crosshair) crosshair.classList.remove('hot');
    }
  }

  // Where to stand to look at an entry's work (used by navigate.js / tour.js).
  function spotFor(entry, distance = 2.2) {
    const mesh = artMeshes.find((m) => m.name === entry.meshName);
    if (!mesh) return null;
    return viewingSpot(mesh, { walls: walls(), groundY, distance });
  }

  return {
    setArtMeshes, setTeleporter, openPlacard, closePlacard, isOpen, openAtCrosshair, openAtScreen,
    current: () => current, hovered: () => hovered, update, imageUrl, spotFor, pickArt, rewritesReady,
  };
}
