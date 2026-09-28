import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { blenderToThree, threeToBlender } from './coords.js';
import { createControls } from './controls.js';
import { createInteractions } from './interactions.js';
import { createWaypointTrail } from './waypoints.js';
import { readRenderOptions, configureRenderer, setupEnvironment, createPipeline, resolveModelUrl } from './render.js';
import { createLightRig, collectRooms, makeRoomAt } from './lights.js';
import { patchMaterials } from './materials.js';
import { createDebug, applyFraming } from './debug.js';
import { createGeoFactory, applyMezzaninePatch } from './procgeo.js';
import { createHud } from './hud.js';
import { createNavigate } from './navigate.js';
import { createTour } from './tour.js';
import { createUI } from './ui.js';
import { createTouchControls } from './touch.js';
import { createPersist } from './persist.js';
import { buildProceduralWing } from './procwing.js';

const MANIFEST_URL = '../data/museum-manifest.json';
const MODEL_URL = '../export/museum.gltf';
const MODEL_V2_URL = '../export/museum_v2.gltf'; // ?v2 (falls back to MODEL_URL)
const RENDER_OPTS = readRenderOptions(window.location.search); // ?classic ?exposure= ?debug ?view= ?test ...

const loadingEl = document.getElementById('loading');
const blockerEl = document.getElementById('blocker');
const roomLabelEl = document.getElementById('room-label');

export function buildManifestIndex(manifest) {
  const wings = manifest.wings && manifest.wings.length
    ? manifest.wings
    : [{ id: 'art-talk', name: 'Art-Talk Wing', image_base: 'Art-Talk-main/', rooms: manifest.rooms.map((r) => r.id) }];
  const wingsById = new Map(wings.map((w) => [w.id, w]));
  const byMeshName = new Map();
  const byWorkId = new Map();
  const flatWorks = [];
  for (const artist of manifest.artists) {
    for (const work of artist.works) {
      const meshName = `ART-${artist.slug}__${work.id}`;
      const entry = { artist, work, room: artist.room, wing: artist.wing || wings[0].id, meshName, index: flatWorks.length };
      byMeshName.set(meshName, entry);
      byWorkId.set(work.id, entry);
      flatWorks.push(entry);
    }
  }

  function suggestNext(entry) {
    const idx = flatWorks.indexOf(entry);
    if (idx === -1) return [];
    const suggestions = [];
    const next = flatWorks[(idx + 1) % flatWorks.length];
    suggestions.push(next);
    if (next.room === entry.room) {
      let j = idx + 1;
      while (j < flatWorks.length && flatWorks[j].room === entry.room) j++;
      if (j < flatWorks.length) suggestions.push(flatWorks[j]);
      else if (flatWorks.length) suggestions.push(flatWorks[0]);
    }
    return suggestions;
  }

  return { wings, wingsById, byMeshName, byWorkId, flatWorks, suggestNext };
}

async function main() {
  const manifest = await fetch(MANIFEST_URL).then((r) => r.json());
  const manifestIndex = buildManifestIndex(manifest);
  const roomsById = new Map(manifest.rooms.map((r) => [r.id, r]));

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0a0806);

  const camera = new THREE.PerspectiveCamera(70, window.innerWidth / window.innerHeight, 0.05, 500);
  const startRoom = roomsById.get('rotunda');
  const startPos = blenderToThree(startRoom.position);
  camera.position.set(startPos.x, 1.7, startPos.z + 3);

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  document.body.appendChild(renderer.domElement);
  // v2 look: AgX + soft shadows + PMREM environment + composer (MSAA HalfFloat, bloom, OutputPass).
  // ?classic keeps the v1 look (plain renderer.render, hemisphere light only).
  configureRenderer(renderer, RENDER_OPTS);
  const pipeline = createPipeline(renderer, scene, camera, RENDER_OPTS);
  const envInfo = await setupEnvironment(renderer, scene, RENDER_OPTS);

  window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2)); // DPR changes (monitor switch, zoom)
    renderer.setSize(window.innerWidth, window.innerHeight);
    pipeline.setSize(window.innerWidth, window.innerHeight);
  });

  const hemi = new THREE.HemisphereLight(0x9a9488, 0x2a231a, 0.6);
  if (RENDER_OPTS.classic) scene.add(hemi); // otherwise lights.js owns the fill light

  const wallMeshes = [];
  const floorMeshes = [];
  const artMeshes = [];

  let modelUrl = await resolveModelUrl(RENDER_OPTS, MODEL_URL, MODEL_V2_URL);
  let gltf;
  try {
    gltf = await new GLTFLoader().loadAsync(modelUrl);
  } catch (err) {
    if (modelUrl === MODEL_URL) throw err;
    console.warn(`[museum] ${modelUrl} failed to load (${err.message}); falling back to ${MODEL_URL}`);
    modelUrl = MODEL_URL;
    gltf = await new GLTFLoader().loadAsync(modelUrl);
  }
  scene.add(gltf.scene);

  // Procedural geometry is added under gltf.scene BEFORE the classification below, so
  // collision, floor-following, materials, lights and placards treat it like exported geometry.
  const geoFactory = createGeoFactory(gltf.scene);
  if (!RENDER_OPTS.nopatch) applyMezzaninePatch(geoFactory);
  const procwing = RENDER_OPTS.wing ? await buildProceduralWing(manifest, gltf.scene, { camera, renderer }) : null; // ?wing=0 skips it
  gltf.scene.updateMatrixWorld(true);

  gltf.scene.traverse((obj) => {
    if (!obj.isMesh || !obj.visible) return;
    const name = obj.name || '';
    if (name.startsWith('ART-')) {
      artMeshes.push(obj);
    } else if (name.includes('wall') || name.includes('outer')) {
      wallMeshes.push(obj);
    } else if (name.includes('floor') || name.includes('landing') || name.includes('step')) {
      floorMeshes.push(obj);
    }
  });

  const geoRooms = collectRooms(gltf.scene);
  const roomAt = makeRoomAt(geoRooms);
  const materialStats = RENDER_OPTS.classic
    ? null
    : patchMaterials(gltf.scene, renderer, { envIntensity: RENDER_OPTS.envIntensity });
  const lights = RENDER_OPTS.classic
    ? null
    : createLightRig(scene, renderer, { root: gltf.scene, lightGain: RENDER_OPTS.lightGain, rooms: geoRooms });

  const waypointTrail = createWaypointTrail(scene, manifest, camera);

  const controls = createControls(camera, renderer.domElement, () => ({
    walls: wallMeshes,
    floors: floorMeshes,
  }));

  function getCurrentRoomId() {
    // Level-aware: the room whose floor mesh is under the camera when it is a manifest room;
    // otherwise the nearest manifest room on the camera's floor. (Plain 2-D nearest picked
    // upper-floor Gallery F while standing in Gallery A.)
    const r = roomAt(camera.position);
    if (r && roomsById.has(r.manifestId)) return r.manifestId;
    const feetY = camera.position.y - controls.EYE_HEIGHT;
    let best = manifest.rooms[0].id;
    let bestDist = Infinity;
    for (const room of manifest.rooms) {
      const p = blenderToThree(room.position);
      const dx = camera.position.x - p.x;
      const dz = camera.position.z - p.z;
      const d = dx * dx + dz * dz + (Math.abs(p.y - feetY) > 3 ? 1e4 : 0);
      if (d < bestDist) {
        bestDist = d;
        best = room.id;
      }
    }
    return best;
  }

  const debug = createDebug({
    renderer, scene, camera, pipeline, lights, controls, manifest,
    roomAt,
    opts: RENDER_OPTS,
    info: { model: modelUrl.split('/').pop(), materials: materialStats, ...envInfo },
  });

  const interactions = createInteractions(camera, manifestIndex, waypointTrail, controls.isLocked, getCurrentRoomId, {
    domElement: renderer.domElement,
    walls: () => wallMeshes,
    groundY: controls.groundY,
  });
  interactions.setArtMeshes(artMeshes);

  function enter({ pointerLock = true } = {}) {
    blockerEl.classList.add('hidden');
    controls.engage({ pointerLock });
  }
  blockerEl.addEventListener('click', (e) => {
    if (e.target.closest('button')) return;
    enter();
  });
  const exploreBtn = document.getElementById('btn-explore');
  if (exploreBtn) exploreBtn.addEventListener('click', () => enter());

  const hud = createHud({ camera, rooms: geoRooms, roomsById, manifest, artMeshes, controls, lights });
  const navigate = createNavigate({
    manifest, manifestIndex, camera, controls, interactions, waypointTrail, getCurrentRoomId,
    teleportToRoom: hud.teleportToRoom, lights, fade: hud.fade,
  });
  const tour = createTour({ manifestIndex, roomsById, camera, controls, interactions, getCurrentRoomId, roomAt, opts: { dwell: RENDER_OPTS.tourDwell } });
  const persist = createPersist({ camera, controls, enabled: !RENDER_OPTS.test });
  const ui = createUI({ manifest, manifestIndex, controls, interactions, hud, navigate, tour, persist, enter });
  const touch = createTouchControls({ domElement: renderer.domElement, controls, interactions });

  // ---- simulation / rendering -------------------------------------------------------------
  let lastRoomId = null;
  let roomLabelTimer = 0;

  function simulate(delta) {
    if (tour.active()) tour.update(delta);
    else if (controls.isLocked()) controls.update(delta);
    camera.updateMatrixWorld(); // raycasts below (look prompt, picks, tests) see this frame's pose, not the last rendered one
    waypointTrail.update(delta);
    interactions.update(delta);
    hud.update(delta);
    persist.tick(delta);
    ui.update(delta);
    if (procwing) procwing.update(delta);

    const currentRoomId = getCurrentRoomId();
    if (currentRoomId !== lastRoomId) {
      lastRoomId = currentRoomId;
      const room = roomsById.get(currentRoomId);
      roomLabelEl.textContent = room ? room.name : '';
      roomLabelEl.classList.add('visible');
      roomLabelTimer = 2.5;
    }
    if (roomLabelTimer > 0) {
      roomLabelTimer -= delta;
      if (roomLabelTimer <= 0) roomLabelEl.classList.remove('visible');
    }
    if (lights) lights.update(camera, delta);
  }

  function frame(delta) {
    simulate(delta);
    pipeline.render(delta);
    debug.update(delta);
  }

  function renderOnce() {
    if (lights) lights.update(camera, 0, true);
    pipeline.render(0);
    hud.draw();
    debug.update(0);
  }
  debug.setRenderOnce(renderOnce);

  function snapshot() {
    const p = camera.position;
    const look = controls.getLook();
    const geo = roomAt(camera.position);
    return {
      pos: [p.x, p.y, p.z], blender: threeToBlender(p), yaw: look.yaw, pitch: look.pitch,
      room: getCurrentRoomId(), geoRoom: geo ? geo.id : null,
    };
  }
  function step(dt = 1 / 60, n = 1) {
    for (let i = 0; i < n; i++) simulate(dt);
    return snapshot();
  }
  function probeArt() {
    const hit = interactions.pickArt();
    return hit ? hit.name : null;
  }

  let autoLoop = !RENDER_OPTS.test;
  const clock = new THREE.Clock();
  function animate() {
    if (!autoLoop) return;
    requestAnimationFrame(animate);
    frame(Math.min(clock.getDelta(), 0.1));
  }
  function setAutoLoop(on) {
    const was = autoLoop;
    autoLoop = !!on;
    if (autoLoop && !was) { clock.getDelta(); animate(); }
  }

  window.museumDebug = {
    THREE, camera, scene, wallMeshes, floorMeshes, artMeshes, manifest, manifestIndex, roomsById,
    rooms: geoRooms, roomAt, controls, renderer, pipeline, lights, renderOnce, renderOptions: RENDER_OPTS,
    materialStats, modelUrl, interactions, waypointTrail, geoFactory, hud, navigate, tour, persist, ui, touch, procwing,
    simulate, frame, step, snapshot, probeArt, setAutoLoop, getCurrentRoomId, enter,
    setView: (name) => debug.setView(name).then((ok) => { renderOnce(); return ok; }),
    applyFraming: (f) => { applyFraming(camera, f); controls.syncLook(); if (lights) lights.update(camera, 0, true); renderOnce(); },
    measure: debug.measure, probe: debug.probe, tune: debug.tune,
    ready: false,
  };

  await interactions.rewritesReady; // the placard overlay is small and local; ready means fully loaded
  loadingEl.classList.add('hidden');
  // Deep links: ?work=<id> / ?room=<id> / ?resume=1 skip the blocker.
  if (RENDER_OPTS.work && navigate.goToWork(RENDER_OPTS.work)) enter({ pointerLock: false });
  else if (RENDER_OPTS.room && hud.teleportToRoom(RENDER_OPTS.room)) enter({ pointerLock: false });
  else if (RENDER_OPTS.resume && persist.restore()) enter({ pointerLock: false });
  window.museumDebug.ready = true;
  if (autoLoop) animate();
  else renderOnce();
  if (RENDER_OPTS.view) window.museumDebug.setView(RENDER_OPTS.view);
}

main().catch((err) => {
  console.error(err);
  loadingEl.textContent = 'Failed to load the museum: ' + err.message;
});
