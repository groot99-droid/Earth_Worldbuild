// Guided tour: walks the visitor from work to work (manifest order = chronological),
// routing room -> door -> door -> room through the manifest graph (waypoints.routePoints),
// smoothly along a Catmull-Rom path, looks at each work, opens its placard, dwells, moves on.
// Space pauses, N/P skip, Esc ends. Collision is off while travelling (the path is legal).
import * as THREE from 'three';
import { findPath, routePoints } from './waypoints.js';

export function createTour({ manifestIndex, roomsById, camera, controls, interactions, getCurrentRoomId, roomAt = null, opts = {} }) {
  const SPEED = opts.speed || 2.5;          // m/s
  const DEFAULT_DWELL = opts.dwell ?? 6;    // s at each work
  const LOOK_TAU = 0.6, ARRIVE_TAU = 0.35, ARRIVE_DIST = 5, Y_TAU = 0.15;
  const EYE = controls.EYE_HEIGHT;

  let works = [];
  let index = -1;
  let phase = 'idle'; // idle | travel | dwell | paused
  let resumePhase = null;
  let curve = null, length = 0, s = 0, dwellLeft = 0, dwell = DEFAULT_DWELL, lookHold = 0;
  let entry = null;
  let lookTarget = new THREE.Vector3();

  const statusEl = document.createElement('div');
  statusEl.id = 'tour-status';
  statusEl.hidden = true;
  document.body.appendChild(statusEl);

  const _p = new THREE.Vector3(), _t = new THREE.Vector3(), _look = new THREE.Vector3();
  const _m = new THREE.Matrix4(), _q = new THREE.Quaternion();

  function startRoom() {
    const r = roomAt ? roomAt(camera.position) : null;
    if (r && roomsById.has(r.manifestId)) return r.manifestId;
    return getCurrentRoomId();
  }

  function buildLeg(e) {
    const spot = interactions.spotFor(e);
    if (!spot) return false;
    const path = findPath(roomsById, startRoom(), e.room);
    const pts = routePoints(roomsById, path, { fromPoint: camera.position.clone(), toPoint: spot.position });
    const flat = pts.map((p) => new THREE.Vector3(p.x, 0, p.z));
    // extra points 0.8 m either side of interior corners (the corner itself stays on the path)
    const dense = [];
    for (let i = 0; i < flat.length; i++) {
      const p = flat[i];
      if (i > 0 && i < flat.length - 1) {
        const a = flat[i - 1], b = flat[i + 1];
        const da = p.distanceTo(a), db = p.distanceTo(b);
        if (da > 1.6) dense.push(p.clone().lerp(a, 0.8 / da));
        dense.push(p);
        if (db > 1.6) dense.push(p.clone().lerp(b, 0.8 / db));
      } else dense.push(p);
    }
    const clean = dense.filter((p, i) => i === 0 || p.distanceTo(dense[i - 1]) > 0.05);
    if (clean.length < 2) clean.push(clean[0].clone().add(new THREE.Vector3(0.01, 0, 0)));
    curve = new THREE.CatmullRomCurve3(clean, false, 'centripetal');
    length = curve.getLength();
    s = 0;
    entry = e;
    lookTarget = spot.lookAt.clone();
    return true;
  }

  function status() {
    if (!entry) { statusEl.hidden = true; return; }
    const w = entry.work, a = entry.artist;
    const title = w.title && w.title !== a.name ? `${w.title} — ${a.name}` : a.name;
    const state = phase === 'paused' ? 'paused' : phase === 'dwell' ? 'viewing' : 'walking';
    statusEl.textContent = `Guided tour ${index + 1} / ${works.length} · ${title} · ${state} · Space pause · N/P skip · Esc end`;
    statusEl.hidden = false;
  }

  function next() {
    interactions.closePlacard();
    index++;
    while (index < works.length && !buildLeg(works[index])) index++;
    if (index >= works.length) { stop(); return; }
    phase = 'travel';
    status();
  }
  function prev() {
    index = Math.max(-1, index - 2);
    next();
  }

  function start({ works: list = manifestIndex.flatWorks, from = 0, dwell: d = DEFAULT_DWELL } = {}) {
    works = list;
    dwell = d;
    index = from - 1;
    const blocker = document.getElementById('blocker');
    if (blocker) blocker.classList.add('hidden');
    controls.engage({ pointerLock: false });
    controls.setCollision(false);
    next();
  }

  function stop() {
    phase = 'idle';
    entry = null;
    curve = null;
    controls.setCollision(true);
    controls.syncLook();
    const g = controls.groundY(camera.position.x, camera.position.z, camera.position.y - EYE, { up: 1.0, down: 2.0 });
    if (g !== null) camera.position.y = g + EYE;
    statusEl.hidden = true;
  }
  function pause() {
    if (phase === 'travel' || phase === 'dwell') { resumePhase = phase; phase = 'paused'; status(); }
  }
  function resume() {
    if (phase === 'paused') { phase = resumePhase || 'travel'; status(); }
  }
  function togglePause() { if (phase === 'paused') resume(); else pause(); }
  function active() { return phase !== 'idle'; }

  function aimAt(target, dt, tau = LOOK_TAU) {
    _m.lookAt(camera.position, target, camera.up);
    _q.setFromRotationMatrix(_m);
    camera.quaternion.slerp(_q, 1 - Math.exp(-dt / tau));
  }

  function followFloor(dt) {
    const g = controls.groundY(camera.position.x, camera.position.z, camera.position.y - EYE, { up: 1.0, down: 1.5 });
    if (g === null) return;
    const ty = g + EYE;
    camera.position.y += (ty - camera.position.y) * (1 - Math.exp(-dt / Y_TAU));
  }

  function update(dt) {
    if (phase === 'travel') {
      s = Math.min(length, s + SPEED * dt);
      const u = length > 0 ? s / length : 1;
      curve.getPointAt(u, _p);
      camera.position.x = _p.x;
      camera.position.z = _p.z;
      followFloor(dt);
      if (length - s < ARRIVE_DIST) {
        aimAt(lookTarget, dt, ARRIVE_TAU); // settle on the work well before arrival
      } else {
        curve.getTangentAt(u, _t);
        _t.y = 0;
        if (_t.lengthSq() > 1e-6) aimAt(_look.copy(camera.position).add(_t), dt);
      }
      if (s >= length) {
        phase = 'dwell';
        dwellLeft = dwell;
        lookHold = 1.0;
        controls.syncLook();
        interactions.openPlacard(entry.meshName);
        status();
      }
    } else if (phase === 'dwell') {
      followFloor(dt);
      if (lookHold > 0) { lookHold -= dt; aimAt(lookTarget, dt, ARRIVE_TAU); controls.syncLook(); }
      dwellLeft -= dt;
      if (dwellLeft <= 0) next();
    }
  }

  function state() {
    return {
      active: active(), phase, index, total: works.length,
      progress: length ? +(s / length).toFixed(3) : 0,
      work: entry ? entry.work.id : null, room: entry ? entry.room : null,
    };
  }

  return { start, stop, pause, resume, togglePause, next, prev, active, state, update };
}
