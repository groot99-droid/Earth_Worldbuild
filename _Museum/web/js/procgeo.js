// Procedural geometry helpers. Pieces are authored in BLENDER extents (Z-up metres,
// see coords.js) and added as children of the loaded glTF scene, named by the viewer's
// classification contract (V2_CONTRACT.md §2): names containing `wall`/`outer` collide,
// `floor`/`landing`/`step` are walkable, `GEO-<room>_floor` defines a room, nothing
// decorative may contain those words.
import * as THREE from 'three';

export function createGeoFactory(gltfScene) {
  const materials = new Map();
  gltfScene.traverse((o) => {
    if (!o.isMesh) return;
    const ms = Array.isArray(o.material) ? o.material : [o.material];
    for (const m of ms) if (m && m.name && !materials.has(m.name)) materials.set(m.name, m);
  });
  const fallback = new THREE.MeshStandardMaterial({ name: 'MAT-proc_fallback', color: 0xd8cdb4, roughness: 0.8 });
  function mat(name) {
    return (name && materials.get(name)) || fallback;
  }
  // ext = { x: [a, b], y: [a, b], z: [a, b] } in Blender coords.
  function box(name, ext, materialName) {
    const sx = ext.x[1] - ext.x[0];
    const sy = ext.y[1] - ext.y[0];
    const sz = ext.z[1] - ext.z[0];
    const geo = new THREE.BoxGeometry(sx, sz, sy); // three width = x, height = Blender z, depth = Blender y
    const mesh = new THREE.Mesh(geo, mat(materialName));
    mesh.name = name;
    mesh.position.set((ext.x[0] + ext.x[1]) / 2, (ext.z[0] + ext.z[1]) / 2, -(ext.y[0] + ext.y[1]) / 2);
    mesh.userData.procedural = true;
    gltfScene.add(mesh);
    return mesh;
  }
  return { materials, mat, box, root: gltfScene };
}

export const V1_MATERIALS = {
  wall: 'MAT-wall_plaster_cream',
  floor: 'MAT-floor_parquet_warm',
  ceiling: 'MAT-ceiling_plaster_white',
  trim: 'MAT-trim_gold',
  stone: 'MAT-stair_stone',
};

// The v1 export leaves the stair hall's upper level as a 1.5 m strip at its east end
// (GEO-stairhall_landing, x 96.5-98) while the upper spine floor stops at x=84, so the
// top of the stairs never meets the mezzanine. This adds the missing balcony ring
// around the stairwell, balustrades along its edge, and closes the stair hall's open
// west side (|y| > 3) that the v1 walls leave to the void.
export function applyMezzaninePatch(f) {
  const M = V1_MATERIALS;
  const out = [];
  out.push(f.box('GEO-stairhall_landing_n', { x: [84.0, 96.5], y: [1.6, 6.0], z: [6.9, 7.1] }, M.floor));
  out.push(f.box('GEO-stairhall_landing_s', { x: [84.0, 96.5], y: [-6.0, -1.6], z: [6.9, 7.1] }, M.floor));
  out.push(f.box('GEO-stairhall_landing_w', { x: [84.0, 85.85], y: [-1.6, 1.6], z: [6.9, 7.1] }, M.floor));
  // balustrades: top at z 8.5 (1.4 m above the 7.1 landing top) so the feet+1.2 collision ray hits them (names contain 'wall')
  out.push(f.box('GEO-stairhall_wall_balustrade_n', { x: [85.85, 96.5], y: [1.6, 1.7], z: [7.0, 8.5] }, M.trim));
  out.push(f.box('GEO-stairhall_wall_balustrade_s', { x: [85.85, 96.5], y: [-1.7, -1.6], z: [7.0, 8.5] }, M.trim));
  out.push(f.box('GEO-stairhall_wall_balustrade_w', { x: [85.85, 85.95], y: [-1.6, 1.6], z: [7.0, 8.5] }, M.trim));
  // close the open west side of the stair hall outside the spine opening (both levels)
  out.push(f.box('GEO-stairhall_wallW_0', { x: [83.8, 84.2], y: [3.0, 6.2], z: [0.0, 14.0] }, M.wall));
  out.push(f.box('GEO-stairhall_wallW_1', { x: [83.8, 84.2], y: [-6.2, -3.0], z: [0.0, 14.0] }, M.wall));
  return out;
}
