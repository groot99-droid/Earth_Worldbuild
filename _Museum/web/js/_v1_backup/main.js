import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { createControls } from './controls.js';
import { createInteractions } from './interactions.js';
import { createWaypointTrail } from './waypoints.js';

const MANIFEST_URL = '../data/museum-manifest.json';
const MODEL_URL = '../export/museum.gltf';

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

  window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });

  const hemi = new THREE.HemisphereLight(0x9a9488, 0x2a231a, 0.6);
  scene.add(hemi);

  let wallMeshes = [];
  let floorMeshes = [];
  let artMeshes = [];

  const gltf = await new GLTFLoader().loadAsync(MODEL_URL);
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

  loadingEl.classList.add('hidden');
  window.museumDebug = { camera, scene, wallMeshes, floorMeshes, artMeshes, manifest, get controls() { return controls; } };

  const waypointTrail = createWaypointTrail(scene, manifest);

  const controls = createControls(camera, renderer.domElement, () => ({
    walls: wallMeshes,
    floors: floorMeshes,
  }));

  function getCurrentRoomId() {
    let best = manifest.rooms[0].id;
    let bestDist = Infinity;
    for (const room of manifest.rooms) {
      const p = blenderToThree(room.position);
      const dx = camera.position.x - p.x;
      const dz = camera.position.z - p.z;
      const d = dx * dx + dz * dz;
      if (d < bestDist) {
        bestDist = d;
        best = room.id;
      }
    }
    return best;
  }

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

    renderer.render(scene, camera);
  }
  animate();
}

main().catch((err) => {
  console.error(err);
  loadingEl.textContent = 'Failed to load the museum: ' + err.message;
});
