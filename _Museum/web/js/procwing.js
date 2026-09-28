// The procedural Earth Chronicle "People" wing. _Museum/build_people_wing.py writes
// data/people-wing.json (every wall/floor/ceiling/trim box and every hang position, in
// Blender coords); this module turns it into meshes named by the viewer's classification
// contract and adds them under the glTF scene before main.js classifies meshes, so
// collision, floor-following, lights, minimap, placards and the tour treat the wing
// exactly like the exported galleries. Portrait textures stream in by room distance.
import * as THREE from 'three';
import { blenderToThree } from './coords.js';
import { createGeoFactory, V1_MATERIALS } from './procgeo.js';

export const LAYOUT_URL = '../data/people-wing.json';
const PLACEHOLDER = 0xefe6d2;   // cream canvas until the portrait arrives
const LOAD_RADIUS = 45;         // m: rooms closer than this get their textures
const UNLOAD_RADIUS = 70;       // m: rooms farther than this drop them again
const CONCURRENCY = 4;
const REEVAL = 1.0;             // s between distance checks

export async function buildProceduralWing(manifest, gltfScene, { camera, renderer, imageRoot = '../../', layoutUrl = LAYOUT_URL } = {}) {
  const wing = (manifest.wings || []).find((w) => w.id === 'people');
  if (!wing) return null;
  let layout;
  try {
    const r = await fetch(layoutUrl);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    layout = await r.json();
  } catch (e) {
    console.warn('[museum] People wing layout unavailable:', e.message);
    return null;
  }

  const factory = createGeoFactory(gltfScene);
  const hidden = new Set(layout.hidden || []);
  gltfScene.traverse((o) => { if (hidden.has(o.name)) o.visible = false; });

  const MAT = { wall: V1_MATERIALS.wall, floor: V1_MATERIALS.floor, ceiling: V1_MATERIALS.ceiling, trim: V1_MATERIALS.trim };
  const boxes = (layout.boxes || []).map((b) => factory.box(b.name, b, MAT[b.material] || V1_MATERIALS.wall));

  // work id -> {artist, work} for this wing
  const byWork = new Map();
  for (const artist of manifest.artists) {
    if ((artist.wing || 'art-talk') !== wing.id) continue;
    for (const work of artist.works) byWork.set(work.id, { artist, work });
  }

  const artMeshes = [];
  const perRoom = new Map();   // room id -> meshes
  const _n = new THREE.Vector3();
  for (const [id, h] of Object.entries(layout.hangs || {})) {
    const entry = byWork.get(id);
    if (!entry) { console.warn('[museum] hang without a manifest work:', id); continue; }
    const geo = new THREE.PlaneGeometry(h.w, h.h);
    const mat = new THREE.MeshStandardMaterial({ name: `MAT-ART-${entry.artist.slug}__${id}`, color: PLACEHOLDER, roughness: 0.55, metalness: 0 });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.name = `ART-${entry.artist.slug}__${id}`;
    mesh.position.copy(blenderToThree(h.pos));
    _n.copy(blenderToThree(h.normal)); // linear, so it converts directions too
    mesh.lookAt(mesh.position.clone().add(_n)); // PlaneGeometry faces +z
    mesh.userData.workId = id;
    mesh.userData.room = h.room;
    mesh.userData.procedural = true;
    mesh.userData.thumbUrl = imageRoot + (wing.image_base || '') + (entry.work.thumb || entry.work.image);
    gltfScene.add(mesh);
    artMeshes.push(mesh);
    if (!perRoom.has(h.room)) perRoom.set(h.room, []);
    perRoom.get(h.room).push(mesh);
  }

  // ---- texture streaming by room distance ------------------------------------------
  const centers = new Map();
  for (const [rid, r] of Object.entries(layout.rooms || {})) {
    centers.set(rid, new THREE.Vector3((r.x[0] + r.x[1]) / 2, (r.z0 || 0) + 1.5, -(r.y[0] + r.y[1]) / 2));
  }
  const loader = new THREE.TextureLoader();
  const maxAniso = renderer ? renderer.capabilities.getMaxAnisotropy() : 1;
  const status = new Map();    // room id -> 'unloaded' | 'loading' | 'loaded'
  const promises = new Map();  // room id -> Promise resolved when its textures are on
  const queue = [];
  let active = 0;
  const stats = { loads: 0, unloads: 0, failures: 0 };

  function pump() {
    while (active < CONCURRENCY && queue.length) {
      const job = queue.shift();
      active++;
      job().catch(() => {}).finally(() => { active--; pump(); });
    }
  }
  function loadMesh(mesh) {
    if (mesh.material.map || mesh.userData.loading) return Promise.resolve();
    mesh.userData.loading = true;
    return new Promise((resolve) => {
      queue.push(() => loader.loadAsync(mesh.userData.thumbUrl).then((tex) => {
        tex.colorSpace = THREE.SRGBColorSpace;
        tex.anisotropy = maxAniso;
        if (mesh.userData.wantTexture === false) { tex.dispose(); return; } // unloaded meanwhile
        mesh.material.map = tex;
        mesh.material.color.set(0xffffff);
        mesh.material.needsUpdate = true;
        stats.loads++;
      }).catch((e) => {
        stats.failures++;
        console.warn('[museum] portrait failed to load:', mesh.userData.thumbUrl, e && e.message);
      }).finally(() => { mesh.userData.loading = false; resolve(); }));
      pump();
    });
  }
  function loadRoom(rid) {
    if (status.get(rid) === 'loaded' || status.get(rid) === 'loading') return promises.get(rid);
    status.set(rid, 'loading');
    const meshes = perRoom.get(rid) || [];
    for (const m of meshes) m.userData.wantTexture = true;
    const p = Promise.all(meshes.map(loadMesh)).then(() => { if (status.get(rid) === 'loading') status.set(rid, 'loaded'); });
    promises.set(rid, p);
    return p;
  }
  function unloadRoom(rid) {
    if (!status.get(rid) || status.get(rid) === 'unloaded') return;
    for (const m of perRoom.get(rid) || []) {
      m.userData.wantTexture = false;
      if (m.material.map) {
        m.material.map.dispose();
        m.material.map = null;
        m.material.color.set(PLACEHOLDER);
        m.material.needsUpdate = true;
        stats.unloads++;
      }
    }
    status.set(rid, 'unloaded');
    promises.delete(rid);
  }

  let acc = REEVAL; // evaluate on the first update
  function update(dt) {
    acc += dt;
    if (acc < REEVAL) return;
    acc = 0;
    for (const [rid, c] of centers) {
      const d = Math.hypot(camera.position.x - c.x, camera.position.z - c.z);
      const s = status.get(rid) || 'unloaded';
      if (d < LOAD_RADIUS && s === 'unloaded') loadRoom(rid);
      else if (d > UNLOAD_RADIUS && s === 'loaded') unloadRoom(rid);
    }
  }
  function whenLoaded(rid) { return loadRoom(rid) || Promise.resolve(); }
  function state() {
    const rooms = {};
    for (const rid of centers.keys()) rooms[rid] = status.get(rid) || 'unloaded';
    return { ...stats, active, queued: queue.length, rooms };
  }

  return { wing, layout, rooms: [...centers.keys()], artMeshes, boxes, hidden: [...hidden], update, whenLoaded, loadRoom, unloadRoom, state };
}
