import * as THREE from 'three';

const IMAGE_BASE = '../../Art-Talk-main/';
const REWRITE_URL = '../data/placard-rewrite.json';   // AI rewrite layer, built by _Rewrite/rewrite_layer.py
const VOICE = { 'epic-fantasy': 'epic-fantasy', 'horror-prose': 'horror-prose', 'essay-self-help': 'essay', 'confessional-poetry': 'confessional-poetry' };

function escapeHtml(t) {
  return t.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}
// Placard text is plain prose with *italic* and blank-line paragraph breaks.
function placardHtml(t) {
  return escapeHtml(t).split(/\n\s*\n/).map((p) => p.replace(/\*([^*\n]+)\*/g, '<em>$1</em>')).join('<br><br>');
}

const PICK_DISTANCE = 6;

export function createInteractions(camera, manifestIndex, waypointTrail, isLockedFn, getCurrentRoomId) {
  const raycaster = new THREE.Raycaster();
  const center = new THREE.Vector2(0, 0);
  let artMeshes = [];

  function setArtMeshes(meshes) { artMeshes = meshes; }

  function pickArt() {
    raycaster.setFromCamera(center, camera);
    raycaster.far = PICK_DISTANCE;
    const hits = raycaster.intersectObjects(artMeshes, false);
    return hits.length ? hits[0].object : null;
  }

  const placard = document.getElementById('placard');
  const closeBtn = document.getElementById('placard-close');
  const titleEl = document.getElementById('placard-title');
  const metaEl = document.getElementById('placard-meta');
  const artistEl = document.getElementById('placard-artist');
  const descEl = document.getElementById('placard-description');
  const creditEl = document.getElementById('placard-credit');
  const voiceEl = document.getElementById('placard-voice');
  let rewrites = {};
  fetch(REWRITE_URL).then((r) => (r.ok ? r.json() : {})).then((j) => { rewrites = j || {}; }).catch(() => {});
  const imgEl = document.getElementById('placard-image');
  const suggestedList = document.getElementById('suggested-list');

  function renderSuggestions(entry) {
    suggestedList.innerHTML = '';
    const suggestions = manifestIndex.suggestNext(entry);
    for (const s of suggestions) {
      const div = document.createElement('div');
      div.className = 'suggested-item';
      const img = document.createElement('img');
      img.src = IMAGE_BASE + s.work.image;
      img.alt = s.work.title || '';
      const label = document.createElement('span');
      label.textContent = s.work.title || s.artist.name;
      div.appendChild(img);
      div.appendChild(label);
      div.addEventListener('click', () => {
        const fromRoom = getCurrentRoomId();
        waypointTrail.showPathTo(fromRoom, s.room);
      });
      suggestedList.appendChild(div);
    }
  }

  function openPlacard(meshName) {
    const entry = manifestIndex.byMeshName.get(meshName);
    if (!entry) return;
    const { artist, work } = entry;
    titleEl.textContent = work.title || 'Untitled';
    const metaBits = [work.year, work.medium, work.location].filter(Boolean);
    metaEl.textContent = metaBits.join(' · ');
    artistEl.textContent = artist.lifespan ? `${artist.name} (${artist.lifespan})` : artist.name;
    const rw = rewrites[work.id];
    descEl.innerHTML = placardHtml(rw ? rw.description : (work.description || ''));
    voiceEl.textContent = rw ? `AI rewrite · ${VOICE[rw.mode] || rw.mode} voice, retold from the gallery text` : '';
    voiceEl.hidden = !rw;
    if (work.credit) {
      const c = work.credit;
      const link = c.source
        ? `<a href="${c.source}" target="_blank" rel="noopener">Wikimedia Commons</a>`
        : 'Wikimedia Commons';
      creditEl.innerHTML = `Image: ${link} · ${c.author || 'Unknown'} · ${c.license || ''}`;
    } else {
      creditEl.textContent = '';
    }
    imgEl.src = IMAGE_BASE + work.image;
    imgEl.alt = work.title || '';

    renderSuggestions(entry);

    placard.classList.remove('hidden');
    placard.classList.add('visible');
  }

  function closePlacard() {
    placard.classList.remove('visible');
    placard.classList.add('hidden');
    waypointTrail.clear();
  }

  closeBtn.addEventListener('click', closePlacard);

  function onClick() {
    if (!isLockedFn()) return;
    const hit = pickArt();
    if (hit) openPlacard(hit.name);
  }

  document.addEventListener('click', onClick);

  return { setArtMeshes, closePlacard };
}
