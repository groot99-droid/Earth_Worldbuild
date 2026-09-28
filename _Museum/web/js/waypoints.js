import * as THREE from 'three';
import { blenderToThree } from './coords.js';

const TRAIL_COLOR = 0xd9a839;

// BFS over the manifest's room graph (room.connects_to).
export function findPath(roomsById, fromId, toId) {
  if (!roomsById.has(fromId)) fromId = roomsById.keys().next().value;
  if (fromId === toId) return [fromId];
  const visited = new Set([fromId]);
  const queue = [[fromId]];
  while (queue.length) {
    const path = queue.shift();
    const last = path[path.length - 1];
    const room = roomsById.get(last);
    for (const n of (room && room.connects_to) || []) {
      if (n === toId) return [...path, n];
      if (!visited.has(n)) {
        visited.add(n);
        queue.push([...path, n]);
      }
    }
  }
  return [fromId, toId];
}

// Points (three.js coords) that walk a room path without cutting through walls:
//   start -> [A's door to B -> B's door to A] -> B's interior -> ... -> end.
// Both doors of a shared doorway are pushed (they differ when the doorway is a
// corridor segment, e.g. gallery-a (20,3) -> gallery-b (36,-3) along the spine).
// Intermediate rooms contribute room.through["prev>next"] (or the reverse of
// "next>prev") when present, nothing when they are a spine/corridor (kind 'spine'),
// else their centre. fromPoint/toPoint replace the first/last room centres.
export function routePoints(roomsById, roomPath, { fromPoint = null, toPoint = null } = {}) {
  const pts = [];
  const push = (v) => {
    if (!pts.length || pts[pts.length - 1].distanceTo(v) > 0.05) pts.push(v);
  };
  for (let i = 0; i < roomPath.length; i++) {
    const room = roomsById.get(roomPath[i]);
    if (!room) continue;
    const prevId = i > 0 ? roomPath[i - 1] : null;
    const nextId = i < roomPath.length - 1 ? roomPath[i + 1] : null;
    if (i === 0) {
      push(fromPoint ? fromPoint.clone() : blenderToThree(room.position));
    } else if (i === roomPath.length - 1) {
      push(toPoint ? toPoint.clone() : blenderToThree(room.position));
    } else {
      const th = room.through || {};
      const key = `${prevId}>${nextId}`;
      const rkey = `${nextId}>${prevId}`;
      if (th[key]) th[key].forEach((p) => push(blenderToThree(p)));
      else if (th[rkey]) [...th[rkey]].reverse().forEach((p) => push(blenderToThree(p)));
      else if (room.kind !== 'spine') push(blenderToThree(room.position));
    }
    if (nextId) {
      const next = roomsById.get(nextId);
      const d1 = room.doors && room.doors[nextId];
      if (d1) push(blenderToThree(d1));
      const d2 = next && next.doors && next.doors[roomPath[i]];
      if (d2) push(blenderToThree(d2));
    }
  }
  return pts;
}

export function createWaypointTrail(scene, manifest, camera = null) {
  const roomsById = new Map(manifest.rooms.map((r) => [r.id, r]));
  let trailMesh = null;

  function clear() {
    if (trailMesh) {
      scene.remove(trailMesh);
      trailMesh.geometry.dispose();
      trailMesh.material.dispose();
      trailMesh = null;
    }
  }

  function showPathTo(fromRoomId, toRoomId, fromPoint = null) {
    clear();
    const roomPath = findPath(roomsById, fromRoomId, toRoomId);
    let start = fromPoint || (camera ? camera.position : null);
    if (start) {
      const feet = camera ? camera.position.y - 1.7 : start.y;
      start = new THREE.Vector3(start.x, feet + 0.05, start.z);
    }
    const pts = routePoints(roomsById, roomPath, { fromPoint: start });
    if (pts.length < 2) return;

    const curve = new THREE.CatmullRomCurve3(pts, false, 'catmullrom', 0.15);
    const segments = Math.max(16, pts.length * 8);
    const tubeGeo = new THREE.TubeGeometry(curve, segments, 0.09, 8, false);
    const mat = new THREE.MeshBasicMaterial({
      color: TRAIL_COLOR,
      transparent: true,
      opacity: 0.85,
      depthWrite: false,
    });
    trailMesh = new THREE.Mesh(tubeGeo, mat);
    trailMesh.renderOrder = 10;
    scene.add(trailMesh);
  }

  function update() {
    if (trailMesh) {
      const pulse = 0.5 + 0.5 * Math.sin(performance.now() * 0.004);
      trailMesh.material.opacity = 0.55 + 0.35 * pulse;
    }
  }

  return { showPathTo, clear, update, hasTrail: () => trailMesh !== null, findPath: (a, b) => findPath(roomsById, a, b) };
}
