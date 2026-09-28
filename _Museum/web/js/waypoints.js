import * as THREE from 'three';

const TRAIL_COLOR = 0xd9a839;

// Manifest positions are authored in Blender's Z-up convention; the glTF
// export (export_yup=True) converts Blender (x, y, z) -> (x, z, -y). Convert
// every point pulled from the manifest before using it in the Three.js scene.
function blenderToThree([x, y, z]) {
  return new THREE.Vector3(x, z, -y);
}

export function createWaypointTrail(scene, manifest) {
  const roomsById = new Map(manifest.rooms.map((r) => [r.id, r]));
  let trailMesh = null;

  function findPath(fromId, toId) {
    if (!roomsById.has(fromId)) fromId = manifest.rooms[0].id;
    if (fromId === toId) return [fromId];
    const visited = new Set([fromId]);
    const queue = [[fromId]];
    while (queue.length) {
      const path = queue.shift();
      const last = path[path.length - 1];
      const room = roomsById.get(last);
      for (const n of room.connects_to || []) {
        if (n === toId) return [...path, n];
        if (!visited.has(n)) {
          visited.add(n);
          queue.push([...path, n]);
        }
      }
    }
    return [fromId, toId];
  }

  function pointsForPath(roomPath) {
    const pts = [];
    for (let i = 0; i < roomPath.length; i++) {
      const room = roomsById.get(roomPath[i]);
      if (!room) continue;
      pts.push(blenderToThree(room.position));
      if (i < roomPath.length - 1) {
        const nextId = roomPath[i + 1];
        const doorPos = room.doors && room.doors[nextId];
        if (doorPos) pts.push(blenderToThree(doorPos));
      }
    }
    return pts;
  }

  function clear() {
    if (trailMesh) {
      scene.remove(trailMesh);
      trailMesh.geometry.dispose();
      trailMesh.material.dispose();
      trailMesh = null;
    }
  }

  function showPathTo(fromRoomId, toRoomId) {
    clear();
    const roomPath = findPath(fromRoomId, toRoomId);
    const pts = pointsForPath(roomPath);
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

  return { showPathTo, clear, update };
}
