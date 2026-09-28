import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { createControls } from './controls.js';
import { createInteractions } from './interactions.js';
import { createWaypointTrail } from './waypoints.js';
import { readRenderOptions, configureRenderer, setupEnvironment, createPipeline, resolveModelUrl } from './render.js';
import { createLightRig } from './lights.js';
import { patchMaterials } from './materials.js';
import { createDebug } from './debug.js';

const MANIFEST_URL = '../data/museum-manifest.json';
const MODEL_URL = '../export/museum.gltf';
const MODEL_V2_URL = '../export/museum_v2.gltf'; // ?v2 (falls back to MODEL_URL)
const RENDER_OPTS = readRenderOptions(window.location.search); // ?classic ?exposure= ?debug ?view= ...

// The manifest's positions/doors are authored in Blender's Z-up convention
// (x, y-north/south, z-height). The glTF export used export_yup=True, which
// converts Blender (x, y, z) -> glTF/Three.js (x, z, -y). Every position
// pulled from the manifest must go through this before use in the Three.js
// scene, or it lands nowhere near the actual geometry.
function blenderToThree([x, y, z]) {
  return new THREE.Vector3(x, z, -y);
}

const loadingEl = document.getElementById('loading');
const blockerEl = document.getElementById('blocker');
const roomLabelEl = document.getElementById('room-label');

function buildManifestIndex(manifest) {
  const byMeshName = new Map();
  const flatWorks = [];
  for (const artist of manifest.artists) {
    for (const work of artist.works) {
      const meshName = `ART-${artist.slug}__${work.id}`;
      const entry = { artist, work, room: artist.room, meshName };
      byMeshName.set(meshName, entry);
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

  return { byMeshName, flatWorks, suggestNext };
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

  let wallMeshes = [];
  let floorMeshes = [];
  let artMeshes = [];

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

  gltf.scene.traverse((obj) => {
    if (!obj.isMesh) return;
    const name = obj.name || '';
    if (name.startsWith('ART-')) {
      artMeshes.push(obj);
    } else if (name.includes('wall') || name.includes('outer')) {
      wallMeshes.push(obj);
    } else if (name.includes('floor') || name.includes('landing') || name.includes('step')) {
      floorMeshes.push(obj);
    }
  });

  const materialStats = RENDER_OPTS.classic
    ? null
    : patchMaterials(gltf.scene, renderer, { envIntensity: RENDER_OPTS.envIntensity });
  const lights = RENDER_OPTS.classic
    ? null
    : createLightRig(scene, renderer, { root: gltf.scene, lightGain: RENDER_OPTS.lightGain });

  loadingEl.classList.add('hidden');
  window.museumDebug = { camera, scene, wallMeshes, floorMeshes, artMeshes, manifest, get controls() { return controls; } };

  const waypointTrail = createWaypointTrail(scene, manifest);

  const controls = createControls(camera, renderer.domElement, () => ({
    walls: wallMeshes,
    floors: floorMeshes,
  }));

  function getCurrentRoomId() {
    // Level-aware: the room whose floor mesh is under the camera (light rig) when it is a
    // manifest room; otherwise the nearest manifest room on the camera's floor. (Plain 2-D
    // nearest picked upper-floor Gallery F while standing in Gallery A.)
    if (lights) {
      const r = lights.roomAt(camera.position);
      if (r && roomsById.has(r.manifestId)) return r.manifestId;
    }
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
    roomAt: lights ? lights.roomAt : null,
    opts: RENDER_OPTS,
    info: { model: modelUrl.split('/').pop(), materials: materialStats, ...envInfo },
  });
  function renderOnce() {
    if (lights) lights.update(camera, 0, true);
    pipeline.render(0);
    debug.update(0);
  }
  debug.setRenderOnce(renderOnce);
  Object.assign(window.museumDebug, {
    renderer, pipeline, lights, renderOnce, renderOptions: RENDER_OPTS, materialStats, modelUrl,
    setView: (name) => debug.setView(name).then((ok) => { renderOnce(); return ok; }),
    measure: debug.measure, probe: debug.probe, tune: debug.tune,
  });

  const interactions = createInteractions(camera, manifestIndex, waypointTrail, controls.isLocked, getCurrentRoomId);
  interactions.setArtMeshes(artMeshes);

  blockerEl.addEventListener('click', () => {
    blockerEl.classList.add('hidden');
    controls.engage();
  });

  let lastRoomId = null;
  let roomLabelTimer = 0;

  const clock = new THREE.Clock();
  function animate() {
    requestAnimationFrame(animate);
    const delta = Math.min(clock.getDelta(), 0.1);

    if (controls.isLocked()) {
      controls.update(delta);
    }
    waypointTrail.update(delta);

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
    pipeline.render(delta);
    debug.update(delta);
  }
  animate();
  if (RENDER_OPTS.view) window.museumDebug.setView(RENDER_OPTS.view);
}

main().catch((err) => {
  console.error(err);
  loadingEl.textContent = 'Failed to load the museum: ' + err.message;
});
