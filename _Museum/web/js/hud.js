// Floor-plan minimap and the large map (M): rooms come from the geometry (lights.js
// collectRooms boxes, which include the corridors the manifest lacks), doors from the
// manifest, art dots from the ART meshes. Only the player's level is drawn. Clicking a
// room on the large map teleports there.
import * as THREE from 'three';
import { blenderToThree, yawToward } from './coords.js';
import { artCenter, roomArtCentroid } from './artgeom.js';

const CORRIDOR_NAMES = { spine1: 'Spine Hall', spine2: 'Upper Spine Hall', stairhall: 'Staircase Hall', futurewing: 'Vestibule' };

export function createHud({ camera, rooms, roomsById, manifest, artMeshes, controls, lights = null, onTeleport = null, redrawHz = 10 }) {
  const roomList = [...rooms.values()];
  let artPts = artMeshes.map((m) => artCenter(m, new THREE.Vector3()));
  const fadeEl = document.getElementById('fade');

  // ---- DOM ----------------------------------------------------------------------------
  const mini = document.createElement('canvas');
  mini.id = 'minimap';
  mini.width = 440; mini.height = 440; // 2x for crisp lines at 220 css px
  mini.title = 'Floor plan (M for the full map)';
  const large = document.createElement('div');
  large.id = 'map-large';
  const largeCanvas = document.createElement('canvas');
  const caption = document.createElement('div');
  caption.className = 'map-caption';
  caption.textContent = 'Floor plan · click a room to go there · M / Esc to close';
  large.appendChild(largeCanvas);
  large.appendChild(caption);
  document.body.appendChild(mini);
  document.body.appendChild(large);

  let mapOpen = false;
  let acc = 0;
  let fadeLevel = 0; // teleport blackout, decayed by update(dt) so it needs no timers or CSS transitions
  let largeView = null; // {ox, oy, scale, level rooms} of the last large draw, for hit-testing

  const feetY = () => camera.position.y - controls.EYE_HEIGHT;
  const levelRooms = (feet) => roomList.filter((r) => feet >= r.floorY - 3 && feet <= r.ceilY - 1);
  const roomName = (r) => {
    const m = roomsById.get(r.manifestId);
    return m ? m.name : (CORRIDOR_NAMES[r.id] || r.id);
  };

  function heading() {
    const { yaw } = controls.getLook();
    return { hx: -Math.sin(yaw), hy: Math.cos(yaw) }; // Blender x/y components of the view direction
  }

  // Draw the level's plan. `view` = {cx, cy (Blender centre), scale (px/m), W, H, labels}
  function drawPlan(ctx, view, current) {
    const { W, H, scale } = view;
    const sx = (bx) => W / 2 + (bx - view.cx) * scale;
    const sy = (by) => H / 2 - (by - view.cy) * scale;
    const feet = feetY();
    ctx.clearRect(0, 0, W, H);
    ctx.lineWidth = Math.max(1, scale * 0.12);
    for (const r of levelRooms(feet)) {
      const x0 = sx(r.box.min.x), x1 = sx(r.box.max.x);
      const y0 = sy(-r.box.min.z), y1 = sy(-r.box.max.z); // Blender y = -three z
      const isCur = current && r.id === current.id;
      ctx.fillStyle = isCur ? 'rgba(202, 162, 77, 0.28)' : 'rgba(242, 234, 217, 0.10)';
      ctx.strokeStyle = isCur ? '#caa24d' : 'rgba(202, 162, 77, 0.55)';
      ctx.beginPath();
      ctx.rect(Math.min(x0, x1), Math.min(y0, y1), Math.abs(x1 - x0), Math.abs(y1 - y0));
      ctx.fill();
      ctx.stroke();
      if (view.labels) {
        ctx.fillStyle = isCur ? '#f2ead9' : '#b9ac8f';
        ctx.font = `${Math.max(10, Math.min(16, scale * 1.6))}px Georgia, serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        const name = roomName(r);
        const w = Math.abs(x1 - x0) - 6;
        const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
        if (ctx.measureText(name).width <= w) {
          ctx.fillText(name, cx, cy);
        } else {
          // wrap long names onto up to three lines that fit the room box
          const words = name.split(/\s+/);
          const lines = [];
          let cur = '';
          for (const word of words) {
            const t = cur ? `${cur} ${word}` : word;
            if (ctx.measureText(t).width <= w || !cur) cur = t;
            else { lines.push(cur); cur = word; }
          }
          if (cur) lines.push(cur);
          const lh = Math.max(11, Math.min(17, scale * 1.7));
          if (lines.length <= 3 && lines.every((l) => ctx.measureText(l).width <= w) && lines.length * lh <= Math.abs(y1 - y0)) {
            lines.forEach((l, i) => ctx.fillText(l, cx, cy + (i - (lines.length - 1) / 2) * lh));
          }
        }
      }
    }
    // doors (manifest, same level)
    ctx.fillStyle = '#e0b95e';
    for (const room of manifest.rooms) {
      for (const d of Object.values(room.doors || {})) {
        if (Math.abs(d[2] - feet) > 3) continue;
        const s = Math.max(2, scale * 0.9);
        ctx.fillRect(sx(d[0]) - s / 2, sy(d[1]) - s / 2, s, s);
      }
    }
    // art dots
    ctx.fillStyle = 'rgba(242, 234, 217, 0.85)';
    const dot = Math.max(1, scale * 0.25);
    for (const p of artPts) {
      if (Math.abs(p.y - (feet + 1.5)) > 3.5) continue;
      ctx.fillRect(sx(p.x) - dot / 2, sy(-p.z) - dot / 2, dot, dot);
    }
    // player
    const { hx, hy } = heading();
    const px = sx(camera.position.x), py = sy(-camera.position.z);
    const len = Math.max(6, scale * 1.6);
    ctx.fillStyle = '#ffd27a';
    ctx.strokeStyle = '#1b1712';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(px + hx * len, py - hy * len);
    ctx.lineTo(px - hy * len * 0.5 - hx * len * 0.6, py - hx * len * 0.5 + hy * len * 0.6);
    ctx.lineTo(px + hy * len * 0.5 - hx * len * 0.6, py + hx * len * 0.5 + hy * len * 0.6);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
  }

  function currentGeoRoom() {
    const feet = feetY();
    let best = null;
    for (const r of roomList) {
      const b = r.box;
      if (camera.position.x < b.min.x - 0.3 || camera.position.x > b.max.x + 0.3 || camera.position.z < b.min.z - 0.3 || camera.position.z > b.max.z + 0.3) continue;
      if (r.floorY > feet + 0.8 || feet > r.ceilY) continue;
      if (!best || r.floorY > best.floorY + 0.01 || (Math.abs(r.floorY - best.floorY) < 0.01 && r.area < best.area)) best = r;
    }
    return best;
  }

  function drawMini() {
    const ctx = mini.getContext('2d');
    const W = mini.width, H = mini.height;
    drawPlan(ctx, { W, H, scale: W / 60, cx: camera.position.x, cy: -camera.position.z, labels: false }, currentGeoRoom());
  }

  function drawLarge() {
    const level = levelRooms(feetY());
    if (!level.length) return;
    const box = new THREE.Box3();
    for (const r of level) box.union(r.box);
    const spanX = box.max.x - box.min.x + 8;
    const spanY = box.max.z - box.min.z + 8;
    const maxW = Math.floor(window.innerWidth * 0.86), maxH = Math.floor(window.innerHeight * 0.8);
    const scale = Math.min(maxW / spanX, maxH / spanY);
    const W = Math.max(200, Math.round(spanX * scale)), H = Math.max(200, Math.round(spanY * scale));
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    largeCanvas.width = W * dpr; largeCanvas.height = H * dpr;
    largeCanvas.style.width = `${W}px`; largeCanvas.style.height = `${H}px`;
    const ctx = largeCanvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const view = { W, H, scale, cx: (box.min.x + box.max.x) / 2, cy: -(box.min.z + box.max.z) / 2, labels: true };
    drawPlan(ctx, view, currentGeoRoom());
    largeView = { ...view, level };
  }

  function draw() {
    drawMini();
    if (mapOpen) drawLarge();
  }

  function applyFade() {
    if (fadeEl) fadeEl.style.opacity = fadeLevel > 0.001 ? String(fadeLevel) : '0';
  }
  function fade() {
    fadeLevel = 1;
    applyFade();
  }
  function update(dt) {
    if (fadeLevel > 0) {
      fadeLevel = Math.max(0, fadeLevel - dt / 0.45);
      applyFade();
    }
    acc += dt;
    if (acc < 1 / redrawHz) return;
    acc = 0;
    draw();
  }

  function findGeoRoomAt(pos) {
    const feet = pos.y - controls.EYE_HEIGHT;
    let best = null;
    for (const r of roomList) {
      const b = r.box;
      if (pos.x < b.min.x - 0.3 || pos.x > b.max.x + 0.3 || pos.z < b.min.z - 0.3 || pos.z > b.max.z + 0.3) continue;
      if (Math.abs(r.floorY - feet) > 1.5) continue;
      if (!best || r.area < best.area) best = r;
    }
    return best;
  }

  // Teleport to a manifest room (spawn ?? position) or a geometry room (box centre).
  function teleportToRoom(id) {
    const man = roomsById.get(id);
    let pos;
    if (man) {
      pos = blenderToThree(man.spawn || man.position);
      pos.y += controls.EYE_HEIGHT;
    } else {
      const g = rooms.get(id);
      if (!g) return false;
      pos = new THREE.Vector3(g.center.x, g.floorY + controls.EYE_HEIGHT, g.center.z);
    }
    const g = findGeoRoomAt(pos);
    const centroid = g ? roomArtCentroid(artMeshes, g.box, g.floorY) : null;
    fade();
    if (centroid && centroid.distanceTo(pos) > 1.5) {
      controls.teleport(pos, { lookAt: new THREE.Vector3(centroid.x, pos.y, centroid.z) });
    } else {
      controls.teleport(pos, { yaw: yawToward(1, 0) });
    }
    if (lights) lights.update(camera, 0, true);
    if (onTeleport) onTeleport(id);
    draw();
    return true;
  }

  function roomAtScreen(clientX, clientY) {
    if (!largeView) return null;
    const rect = largeCanvas.getBoundingClientRect();
    const x = clientX - rect.left, y = clientY - rect.top;
    const bx = largeView.cx + (x - largeView.W / 2) / largeView.scale;
    const by = largeView.cy - (y - largeView.H / 2) / largeView.scale;
    let best = null;
    for (const r of largeView.level) {
      if (bx < r.box.min.x || bx > r.box.max.x || -by < r.box.min.z || -by > r.box.max.z) continue;
      if (!best || r.area < best.area) best = r;
    }
    return best;
  }

  function openMap() { mapOpen = true; large.classList.add('open'); drawLarge(); }
  function closeMap() { mapOpen = false; large.classList.remove('open'); }
  function toggleMap() { if (mapOpen) closeMap(); else openMap(); }
  function isMapOpen() { return mapOpen; }

  mini.addEventListener('click', (e) => { e.stopPropagation(); toggleMap(); });
  largeCanvas.addEventListener('click', (e) => {
    e.stopPropagation();
    const r = roomAtScreen(e.clientX, e.clientY);
    if (!r) return;
    closeMap();
    teleportToRoom(roomsById.has(r.manifestId) ? r.manifestId : r.id);
  });
  large.addEventListener('click', (e) => { if (e.target === large) closeMap(); });

  function setArtMeshes(list) { artPts = list.map((m) => artCenter(m, new THREE.Vector3())); }

  draw();
  return { update, draw, toggleMap, openMap, closeMap, isMapOpen, teleportToRoom, setArtMeshes, roomAtScreen, currentGeoRoom, fade };
}
