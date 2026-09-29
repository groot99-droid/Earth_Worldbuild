#!/usr/bin/env node
// Browser walk-through tests for the Chronicle Museum viewer.
//
//   node _Museum/tools/walk_test.mjs [--out DIR] [--grep NAME] [--no-shots] [--headed] [--list]
//
// Starts a static server on the project root, opens the viewer in headless Chromium
// (software WebGL is fine) with ?test (no animation loop) and drives it through
// window.museumDebug: deterministic steps, walks, teleports, door clicks, placards, the
// tour. Every scene has its own origin (rooms: hall door at (0, 0) on the south wall), so
// assertions are scene-local Blender metres (x east, y north, z up). Screenshots and
// report.json go to --out (default _Museum/tools/out, git-ignored). The first test runs the
// Python lint (build_manifest.py --lint, fetch_models.py --check).
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
function loadPlaywright() {
  try { return require('playwright'); } catch (e) { /* fall through */ }
  for (const p of ['/opt/node22/lib/node_modules/playwright', '/usr/lib/node_modules/playwright']) {
    try { return require(p); } catch (e) { /* next */ }
  }
  throw new Error('playwright not found: npm i -g playwright (or set NODE_PATH)');
}
const { chromium } = loadPlaywright();

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '../..');
const args = process.argv.slice(2);
const opt = {
  out: path.join(__dirname, 'out'), grep: null, shots: true, headed: false, list: false,
  chromium: process.env.CHROMIUM || '/opt/pw-browsers/chromium', timeout: 180000,
};
for (let i = 0; i < args.length; i++) {
  const a = args[i];
  if (a === '--out') opt.out = path.resolve(args[++i]);
  else if (a === '--grep') opt.grep = args[++i];
  else if (a === '--no-shots') opt.shots = false;
  else if (a === '--headed') opt.headed = true;
  else if (a === '--list') opt.list = true;
  else if (a === '--chromium') opt.chromium = args[++i];
}
if (!fs.existsSync(opt.chromium)) opt.chromium = undefined; // let Playwright find its own

const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8', '.json': 'application/json; charset=utf-8', '.gltf': 'model/gltf+json',
  '.bin': 'application/octet-stream', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
  '.svg': 'image/svg+xml', '.webp': 'image/webp', '.txt': 'text/plain; charset=utf-8', '.md': 'text/plain; charset=utf-8',
  '.glb': 'model/gltf-binary', '.wasm': 'application/wasm',
};

function startServer() {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      let p;
      try { p = decodeURIComponent(new URL(req.url, 'http://x').pathname); } catch (e) { res.writeHead(400); res.end(); return; }
      const file = path.normalize(path.join(ROOT, p));
      if (!file.startsWith(ROOT)) { res.writeHead(403); res.end(); return; }
      fs.stat(file, (err, st) => {
        if (err || !st.isFile()) { res.writeHead(404); res.end('not found'); return; }
        res.writeHead(200, { 'Content-Type': MIME[path.extname(file).toLowerCase()] || 'application/octet-stream', 'Content-Length': st.size, 'Cache-Control': 'no-store' });
        if (req.method === 'HEAD') { res.end(); return; }
        fs.createReadStream(file).pipe(res);
      });
    });
    server.listen(0, '127.0.0.1', () => resolve({ server, port: server.address().port }));
  });
}

// ---- page helpers (run inside the browser through page.evaluate) -----------------------
const H = {
  // Blender heading in degrees (0 = east/+x, 90 = north/+y) -> three yaw
  at: ([bx, by, bz, heading]) => {
    const D = window.museumDebug;
    const t = (heading * Math.PI) / 180;
    const yaw = Math.atan2(-Math.cos(t), Math.sin(t));
    D.controls.setPosition(bx, bz + 1.7, -by);
    D.controls.setLook(yaw, 0);
    D.controls.setKeys({});
    D.controls.setCollision(true);
    D.enter({ pointerLock: false });
    return D.step(1 / 60, 2);
  },
  walk: ([dir, seconds]) => {
    const D = window.museumDebug;
    D.controls.setKeys({ [dir]: true });
    const s = D.step(1 / 60, Math.round(seconds * 60));
    D.controls.setKeys({});
    return s;
  },
  snap: () => window.museumDebug.snapshot(),
};

const ignoreConsole = (t) => /favicon\.ico/.test(t);

class Ctx {
  constructor(browser, base) { this.browser = browser; this.base = base; this.page = null; this.errors = []; this.query = null; this.context = null; }
  async load(query = 'test', { fresh = false } = {}) {
    if (!fresh && this.page && this.query === query) return this.page;
    if (this.page) await this.page.close();
    if (!this.context) this.context = await this.browser.newContext({ viewport: { width: 1280, height: 720 } }); // one context: localStorage survives reloads
    this.errors = [];
    this.query = query;
    const page = await this.context.newPage();
    page.on('console', (m) => {
      if (m.type() !== 'error') return;
      const loc = m.location && m.location();
      const url = (loc && loc.url) || '';
      if (ignoreConsole(`${m.text()} ${url}`)) return;
      this.errors.push(`${m.text()}${url ? ` (${url})` : ''}`);
    });
    page.on('pageerror', (e) => this.errors.push(String(e)));
    await page.goto(`${this.base}/_Museum/web/index.html?${query}`, { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => window.museumDebug && window.museumDebug.ready, null, { timeout: opt.timeout });
    this.page = page;
    return page;
  }
  async at(bx, by, bz, heading = 0) { return this.page.evaluate(H.at, [bx, by, bz, heading]); }
  async walk(dir, seconds) { return this.page.evaluate(H.walk, [dir, seconds]); }
  async snap() { return this.page.evaluate(H.snap); }
  async ev(fn, arg) { return this.page.evaluate(fn, arg); }
  async shot(name) {
    if (!opt.shots) return null;
    await this.page.evaluate(() => { window.museumDebug.step(1 / 60, 30); window.museumDebug.renderOnce(); }); // half a second: teleport fade clears
    await this.page.waitForTimeout(450); // let CSS transitions (placard, panels) finish
    const file = path.join(opt.out, `${name}.png`);
    await this.page.screenshot({ path: file, timeout: 120000 });
    shots.push(file);
    return file;
  }
}

const tests = [];
const shots = [];
function test(name, fn) { tests.push({ name, fn }); }
function assert(cond, msg) { if (!cond) throw new Error(msg); }
const near = (v, target, tol) => Math.abs(v - target) <= tol;
const between = (v, lo, hi) => v >= lo && v <= hi;
const fmt = (b) => `(${b.map((v) => v.toFixed(2)).join(', ')})`;
const feet = (s) => s.blender[2] - 1.7;

import { spawnSync } from 'node:child_process';

// ---- shared browser helpers ---------------------------------------------------------------
const B = {
  // Stand 2 m in front of a door leaf, look at it, step, return the probe + prompt.
  faceDoor: (name) => {
    const D = window.museumDebug, T = D.THREE;
    const d = D.lists.doors.find((m) => m.name === name);
    if (!d) return { probe: null, prompt: `no ${name}` };
    const c = d.userData.center, f = d.userData.facing;
    D.controls.setCollision(true);
    D.controls.teleport(new T.Vector3(c.x + f.x * 2.0, 1.7, c.z + f.z * 2.0), { lookAt: new T.Vector3(c.x, 1.5, c.z) });
    D.enter({ pointerLock: false });
    D.step(1 / 60, 3);
    return { probe: D.probeArt(), prompt: document.getElementById('look-prompt').textContent };
  },
  // Wait for a scene switch to finish and its textures/models to arrive.
  settle: async () => {
    const D = window.museumDebug;
    await new Promise((r) => setTimeout(r, 30));
    while (D.scenes.isSwitching()) await new Promise((r) => setTimeout(r, 30));
    await D.scenes.world().whenLoaded();
    D.step(1 / 60, 5);
    return D.snapshot();
  },
  counts: () => {
    const D = window.museumDebug;
    return { scene: D.scenes.currentId(), art: D.lists.art.length, walls: D.lists.walls.length, floors: D.lists.floors.length,
      doors: D.lists.doors.length, pickables: D.lists.pickables.length, rooms: D.rooms.size, room: D.getCurrentRoomId(),
      geoRoom: D.snapshot().geoRoom, pipeline: D.pipeline.mode };
  },
};
const worksInRoom = (manifest, room) => manifest.artists.filter((a) => a.room === room).reduce((n, a) => n + a.works.length, 0);
const ROOM_IDS = ['gallery-a', 'gallery-b', 'gallery-c', 'gallery-d', 'gallery-e', 'gallery-f', 'people-bronze-age', 'people-iron-age',
  'people-classical-antiquity', 'people-medieval-period-1', 'people-medieval-period-2', 'people-early-modern-period-1',
  'people-early-modern-period-2', 'people-industrial-age-1', 'people-industrial-age-2', 'people-information-age'];
const SHOT_ROOMS = new Set(['gallery-c', 'gallery-f', 'people-industrial-age-2', 'people-medieval-period-1']);

// ---- 0. python lint --------------------------------------------------------------------------
test('lint_prestep', async () => {
  const py = process.env.PYTHON || 'python3';
  const a = spawnSync(py, [path.join(ROOT, '_Museum', 'build_manifest.py'), '--lint'], { encoding: 'utf-8' });
  assert(a.status === 0, `build_manifest.py --lint failed:\n${(a.stdout || '').slice(-1500)}\n${(a.stderr || '').slice(-800)}`);
  const b = spawnSync(py, [path.join(ROOT, '_Museum', 'fetch_models.py'), '--check'], { encoding: 'utf-8' });
  assert(b.status === 0, `fetch_models.py --check failed:\n${(b.stdout || '').slice(-800)}\n${(b.stderr || '').slice(-800)}`);
  const dims = JSON.parse(fs.readFileSync(path.join(ROOT, '_Museum', 'data', 'work-dimensions.json'), 'utf-8'));
  const manifest = JSON.parse(fs.readFileSync(path.join(ROOT, '_Museum', 'data', 'museum-manifest.json'), 'utf-8'));
  const missing = manifest.artists.flatMap((ar) => ar.works).filter((w) => !dims.works[w.id]).length;
  assert(missing === 0, `${missing} works have no entry in work-dimensions.json`);
  return { lint: a.stdout.trim().split('\n').slice(-1)[0], dims: Object.keys(dims.works).length };
});

// ---- 1. the hub ----------------------------------------------------------------------------
test('load', async (c) => {
  await c.load('test');
  const n = await c.ev(B.counts);
  assert(n.scene === 'hub' && n.room === 'hub', `expected to start in the hub, got ${JSON.stringify(n)}`);
  assert(n.doors === 16, `expected 16 doors, got ${n.doors}`);
  assert(n.art === 0, `the hub hangs no works, got ${n.art}`);
  assert(n.walls >= 30 && n.floors >= 2, `hub geometry: ${JSON.stringify(n)}`);
  const sub = await c.ev(() => document.getElementById('blocker-subtitle').textContent);
  assert(/53 artists, 299 works/.test(sub) && /203 people, 387 portraits/.test(sub), `subtitle: ${sub}`);
  const layout = await c.ev(() => Object.keys(window.museumDebug.layout.scenes).length);
  assert(layout === 17, `layout scenes: ${layout}`);
  const sky = await c.ev(() => { const b = window.museumDebug.scene.background; return b && b.isTexture ? [b.image.width, b.image.height] : null; });
  assert(sky && sky[0] === 2 * sky[1], `assets/sky.jpg should be the equirectangular background, got ${JSON.stringify(sky)}`);
  assert(c.errors.length === 0, `console errors: ${c.errors.join(' | ')}`);
  await c.ev(async () => { await window.museumDebug.scenes.world().whenLoaded(); window.museumDebug.renderOnce(); });
  await c.shot('view_hub_spawn');
  return n;
});

test('hub_walk_and_walls', async (c) => {
  await c.load('test');
  await c.ev(async () => { await window.museumDebug.scenes.world().whenLoaded(); }); // benches and pedestals (colliders) arrive with the models
  let s = await c.at(0, 2.2, 0, 0);   // beside the centre line: the benches stand on it
  s = await c.walk('forward', 8);
  assert(s.blender[0] > 25 && s.geoRoom === 'hub', `walked east along the hall: ${fmt(s.blender)} in ${s.geoRoom}`);
  await c.at(16, 0, 0, 0);
  s = await c.walk('forward', 2);
  assert(s.blender[0] < 19.6, `the bench at x=20 should block the centre line: ${fmt(s.blender)}`);
  await c.at(30, 0, 0, 90);
  s = await c.walk('forward', 3);
  assert(s.blender[1] < 3.95, `the north wall should block at y=4: ${fmt(s.blender)}`);
  await c.at(30, 0, 0, 270);
  s = await c.walk('forward', 3);
  assert(s.blender[1] > -3.95, `the south wall should block at y=-4: ${fmt(s.blender)}`);
  // into the rotunda: the centrepiece pedestal blocks the centre line, the drum stops a walk beside it
  await c.at(-2, 0, 0, 180);
  s = await c.walk('forward', 3);
  assert(s.blender[0] > -6.6, `the Greek Slave's pedestal at (-7, 0) should block: ${fmt(s.blender)}`);
  await c.at(-2, 2.5, 0, 180);
  s = await c.walk('forward', 4);
  assert(s.blender[0] > -13.9 && s.blender[0] < -9, `the rotunda drum should stop the walk: ${fmt(s.blender)}`);
  assert(s.geoRoom === 'hub', `still in the hub geo room: ${s.geoRoom}`);
  return s.blender;
});

// ---- 2. every door -----------------------------------------------------------------------------
for (const room of ROOM_IDS) {
  test(`door_${room}`, async (c) => {
    await c.load('test');
    const manifest = await c.ev(() => window.museumDebug.manifest);
    if (await c.ev(() => window.museumDebug.scenes.currentId()) !== 'hub') {
      await c.ev(async () => { await window.museumDebug.enterRoom('hub', { fade: false }); });
      await c.ev(B.settle);
    }
    const f = await c.ev(B.faceDoor, `DOOR-${room}`);
    assert(f.probe === `DOOR-${room}`, `looking at the door should probe it, got ${f.probe}`);
    assert(/^Enter /.test(f.prompt), `door prompt: ${f.prompt}`);
    await c.page.mouse.click(640, 360);
    const s = await c.ev(B.settle);
    const n = await c.ev(B.counts);
    assert(n.scene === room && n.room === room, `after the click expected ${room}, got ${JSON.stringify(n)}`);
    const expected = worksInRoom(manifest, room);
    assert(n.art === expected, `${room}: ${n.art} works hung, manifest has ${expected}`);
    const check = await c.ev((rid) => {
      const D = window.museumDebug;
      const unknown = D.lists.art.filter((m) => !D.manifestIndex.byMeshName.has(m.name)).length;
      const wrongRoom = D.lists.art.filter((m) => m.userData.room !== rid).length;
      const title = document.getElementById('title-card');
      return { unknown, wrongRoom, titleShown: title && title.classList.contains('visible'), titleText: title ? title.textContent.trim().slice(0, 40) : '' };
    }, room);
    assert(check.unknown === 0 && check.wrongRoom === 0, `art meshes: ${JSON.stringify(check)}`);
    assert(check.titleShown, `title card should show on entry: ${JSON.stringify(check)}`);
    assert(near(s.blender[0], 0, 0.3) && between(s.blender[1], 1.5, 4.0), `arrived just inside the hall door: ${fmt(s.blender)}`);
    // walk in: the floor carries us, the north wall stops us
    const w = await c.walk('forward', 12);
    assert(w.geoRoom === room && w.blender[1] > 8, `walking into the room: ${fmt(w.blender)} in ${w.geoRoom}`);
    if (SHOT_ROOMS.has(room)) {
      await c.ev(async (rid) => { await window.museumDebug.setView(`${rid}_door`); }, room);
      await c.shot(`view_${room}`);
    }
    // back through the hall door
    const g = await c.ev(B.faceDoor, 'DOOR-hub');
    assert(g.probe === 'DOOR-hub' && /Grand Hall/.test(g.prompt), `hub door: ${JSON.stringify(g)}`);
    await c.page.keyboard.press('KeyE');
    await c.ev(B.settle);
    const back = await c.ev(B.counts);
    assert(back.scene === 'hub' && back.art === 0 && back.doors === 16, `back in the hub: ${JSON.stringify(back)}`);
    const pos = await c.snap();
    const hubDoor = manifest.rooms.find((r) => r.id === 'hub').doors[room];
    assert(near(pos.blender[0], hubDoor[0], 0.5) && Math.abs(pos.blender[1]) < 3.9, `spawned inside the hall by the ${room} door: ${fmt(pos.blender)} vs ${fmt(hubDoor)}`);
    assert(c.errors.length === 0, `console errors: ${c.errors.join(' | ')}`);
    return { works: n.art, spawn: s.blender.map((v) => +v.toFixed(2)) };
  });
}

// ---- 3. works, placards, sizes -------------------------------------------------------------
test('placard_click_and_size', async (c) => {
  await c.load('test');
  const r = await c.ev(async () => {
    const D = window.museumDebug;
    const ok = await D.navigate.goToWork('night-watch');
    await D.scenes.world().whenLoaded();
    D.step(1 / 60, 3);
    const meta = document.getElementById('placard-meta').textContent;
    const title = document.getElementById('placard-title').textContent;
    D.interactions.closePlacard();
    D.step(1 / 60, 2);
    const probe = D.probeArt();
    const prompt = document.getElementById('look-prompt').textContent;
    D.interactions.openAtCrosshair();
    return { ok, meta, title, probe, prompt, open: D.interactions.isOpen(), scene: D.scenes.currentId() };
  });
  assert(r.ok && r.scene === 'gallery-c', `goToWork: ${JSON.stringify(r)}`);
  assert(/Night Watch/.test(r.title), `title: ${r.title}`);
  assert(/3\.79 m × 4\.5[34] m · shown at actual size/.test(r.meta), `real size on the placard: ${r.meta}`);
  assert(r.probe === 'ART-rembrandt__night-watch' && /Night Watch/.test(r.prompt), `look prompt: ${JSON.stringify(r)}`);
  assert(r.open, 'clicking the work under the crosshair opens the placard');
  await c.shot('feature_placard');
  return r;
});

test('placard_scale_note', async (c) => {
  await c.load('test');
  const r = await c.ev(async () => {
    const D = window.museumDebug;
    await D.navigate.goToWork('last-supper');
    return { meta: document.getElementById('placard-meta').textContent, scene: D.scenes.currentId() };
  });
  assert(r.scene === 'gallery-b' && /shown at 1:2/.test(r.meta), `Last Supper (4.6 × 8.8 m) is shown at 1:2: ${r.meta}`);
  return r;
});

test('hang_sizes_match_dimensions', async (c) => {
  await c.load('test');
  const bad = [];
  for (const room of ['gallery-c', 'gallery-d', 'people-iron-age']) {
    const r = await c.ev(async (rid) => {
      const D = window.museumDebug;
      await D.enterRoom(rid, { fade: false });
      await D.scenes.world().whenLoaded();
      const hangs = D.layout.scenes[rid].hangs;
      const out = [];
      const box = new D.THREE.Box3(), size = new D.THREE.Vector3();
      for (const m of D.lists.art) {
        const e = D.manifestIndex.byMeshName.get(m.name);
        const h = hangs[e.work.id];
        box.setFromObject(m); box.getSize(size);
        const w = Math.max(size.x, size.z), hh = size.y;
        const expW = e.work.dims.disp_w * (h.scale / (e.work.dims.scale || 1)), expH = e.work.dims.disp_h * (h.scale / (e.work.dims.scale || 1));
        if (Math.abs(w - expW) > 0.02 || Math.abs(hh - expH) > 0.02) out.push(`${e.work.id}: ${w.toFixed(2)}×${hh.toFixed(2)} vs ${expW.toFixed(2)}×${expH.toFixed(2)}`);
      }
      return out;
    }, room);
    bad.push(...r);
  }
  assert(bad.length === 0, `hung sizes differ from work-dimensions: ${bad.slice(0, 5).join('; ')}`);
  return 'ok';
});

test('no_art_overlap', async (c) => {
  await c.load('test');
  const r = await c.ev(() => {
    const D = window.museumDebug;
    const bad = [];
    for (const [rid, sc] of Object.entries(D.layout.scenes)) {
      const byWall = {};
      for (const h of Object.values(sc.hangs || {})) (byWall[h.wall] = byWall[h.wall] || []).push(h);
      for (const lst of Object.values(byWall)) {
        for (let i = 0; i < lst.length; i++) for (let j = i + 1; j < lst.length; j++) {
          const a = lst[i], b = lst[j];
          const fa = a.frame.width + 0.01, fb = b.frame.width + 0.01;
          const ox = Math.abs(a.along - b.along) < (a.w + b.w) / 2 + fa + fb + 0.24;
          const oz = Math.abs(a.pos[2] - b.pos[2]) < (a.h + b.h) / 2 + fa + fb + 0.2;
          if (ox && oz) bad.push(`${rid}: ${a.id} / ${b.id}`);
        }
      }
    }
    return bad;
  });
  assert(r.length === 0, `overlapping hangs: ${r.slice(0, 5).join('; ')}`);
  return 'ok';
});

test('look_prompt_keys_map_help', async (c) => {
  await c.load('test');
  await c.ev(async () => { const D = window.museumDebug; D.enter({ pointerLock: false }); await D.navigate.goToWork('girl-with-a-pearl-earring'); D.interactions.closePlacard(); D.step(1 / 60, 3); });
  const hot = await c.ev(() => ({ hot: document.getElementById('crosshair').classList.contains('hot'), prompt: document.getElementById('look-prompt').textContent }));
  assert(hot.hot && /Pearl Earring/.test(hot.prompt), `prompt: ${JSON.stringify(hot)}`);
  await c.page.keyboard.press('KeyE');
  assert(await c.ev(() => window.museumDebug.interactions.isOpen()), 'E opens the placard');
  await c.page.keyboard.press('Escape');
  assert(!(await c.ev(() => window.museumDebug.interactions.isOpen())), 'Esc closes the placard');
  await c.page.keyboard.press('KeyM');
  assert(await c.ev(() => window.museumDebug.hud.isMapOpen()), 'M opens the map');
  await c.shot('feature_map_room');
  await c.page.keyboard.press('KeyM');
  assert(!(await c.ev(() => window.museumDebug.hud.isMapOpen())), 'M closes the map');
  await c.page.keyboard.press('KeyH');
  assert(await c.ev(() => window.museumDebug.ui.isHelpOpen()), 'H opens help');
  await c.page.keyboard.press('Escape');
  return hot;
});

test('minimap_door_click', async (c) => {
  await c.load('test');
  await c.ev(async () => { await window.museumDebug.enterRoom('hub', { fade: false }); });
  await c.ev(B.settle);
  await c.ev(() => { window.museumDebug.step(1 / 60, 40); window.museumDebug.hud.openMap(); });
  await c.shot('feature_map_hub');
  const under = await c.ev(() => { const el = document.elementFromPoint(640, 360); return el ? `${el.tagName}#${el.id || (el.parentElement && el.parentElement.id)}` : null; });
  assert(/map-large/.test(under), `the large map should be on top at the screen centre, got ${under}`);
  const pt = await c.ev(() => {
    const D = window.museumDebug;
    const canvas = document.querySelector('#map-large canvas');
    const rect = canvas.getBoundingClientRect();
    for (let y = 0; y < rect.height; y += 3) for (let x = 0; x < rect.width; x += 3) {
      const h = D.hud.hitAtScreen(rect.left + x, rect.top + y);
      if (h && h.kind === 'door' && h.id === 'gallery-b') return { x: rect.left + x, y: rect.top + y };
    }
    return null;
  });
  assert(pt, 'the large map should have a clickable Gallery B door');
  const before = await c.ev((p) => { const D = window.museumDebug; const h = D.hud.hitAtScreen(p.x, p.y); const el = document.elementFromPoint(p.x, p.y); return { hit: h ? `${h.kind}:${h.id}` : null, el: el ? `${el.tagName}#${el.id || (el.parentElement && el.parentElement.id)}` : null }; }, pt);
  assert(before.hit === 'door:gallery-b' && /map-large/.test(before.el), `the map point should be the Gallery B door under the map canvas: ${JSON.stringify(before)}`);
  await c.page.mouse.click(pt.x, pt.y);
  const s = await c.ev(async () => {
    const D = window.museumDebug;
    for (let i = 0; i < 100 && D.scenes.currentId() === 'hub'; i++) await new Promise((r) => setTimeout(r, 30));
    return B_settle();
    function B_settle() { return (async () => { while (D.scenes.isSwitching()) await new Promise((r) => setTimeout(r, 30)); await D.scenes.world().whenLoaded(); D.step(1 / 60, 5); return { ...D.snapshot(), mapOpen: D.hud.isMapOpen() }; })(); }
  });
  assert(s.scene === 'gallery-b', `clicking the door on the map enters the room: ${s.scene} (map still open: ${s.mapOpen}, point ${JSON.stringify(pt)}, before ${JSON.stringify(before)})`);
  assert(!(await c.ev(() => window.museumDebug.hud.isMapOpen())), 'the map closes after the click');
  return s.scene;
});

test('navigate_filter_goto', async (c) => {
  await c.load('test');
  const r = await c.ev(async () => {
    const D = window.museumDebug;
    D.navigate.open();
    const n = D.navigate.filter('vermeer');
    const shown = [...document.querySelectorAll('#nav-panel .nav-artist')].filter((e) => !e.hidden).map((e) => e.textContent.trim().slice(0, 20));
    D.navigate.close();
    const ok = await D.navigate.goToWork('the-little-street');
    return { n, shown, ok, scene: D.scenes.currentId(), open: D.interactions.isOpen(), title: document.getElementById('placard-title').textContent };
  });
  assert(r.n >= 1 && r.shown.some((t) => /Vermeer/.test(t)), `filter: ${JSON.stringify(r)}`);
  assert(r.ok && r.scene === 'gallery-c' && r.open && /Little Street/.test(r.title), `go to: ${JSON.stringify(r)}`);
  return r;
});

test('placard_prev_next_crosses_rooms', async (c) => {
  await c.load('test');
  const r = await c.ev(async () => {
    const D = window.museumDebug;
    const galleryA = D.manifestIndex.flatWorks.filter((e) => e.room === 'gallery-a');
    const last = galleryA[galleryA.length - 1];
    await D.navigate.goToWork(last.work.id);
    document.getElementById('placard-next').click();
    await new Promise((res) => setTimeout(res, 50));
    while (D.scenes.isSwitching()) await new Promise((res) => setTimeout(res, 30));
    await D.scenes.world().whenLoaded();
    const after = D.interactions.current();
    return { from: last.work.id, to: after ? after.work.id : null, scene: D.scenes.currentId(), room: after ? after.room : null };
  });
  assert(r.scene === 'gallery-b' && r.room === 'gallery-b' && r.to, `next work from the last of Gallery A enters Gallery B: ${JSON.stringify(r)}`);
  return r;
});

test('people_placard', async (c) => {
  await c.load('test');
  const r = await c.ev(async () => {
    const D = window.museumDebug;
    const e = D.manifestIndex.flatWorks.find((x) => x.work.id === 'people--ada-lovelace--1') || D.manifestIndex.flatWorks.find((x) => x.wing === 'people');
    await D.navigate.goToWork(e.work.id);
    return { id: e.work.id, scene: D.scenes.currentId(), title: document.getElementById('placard-title').textContent,
      artist: document.getElementById('placard-artist').textContent, credit: document.getElementById('placard-credit').textContent, meta: document.getElementById('placard-meta').textContent };
  });
  assert(/^people-/.test(r.scene) && r.title.length > 2 && /Image/.test(r.credit), `people placard: ${JSON.stringify(r)}`);
  assert(/typical size/.test(r.meta) || /shown at/.test(r.meta), `size line: ${r.meta}`);
  await c.shot('feature_people_placard');
  return r;
});

// ---- 4. trails, tour, deep links, persistence ---------------------------------------------------
test('guide_trail_to_another_room', async (c) => {
  await c.load('test');
  const r = await c.ev(async () => {
    const D = window.museumDebug;
    await D.enterRoom('gallery-a', { fade: false });
    await D.scenes.world().whenLoaded();
    D.waypointTrail.showPathTo('gallery-a', 'gallery-c', D.camera.position);
    const mesh = D.scene.getObjectByName('trail');
    const pos = mesh.geometry.attributes.position;
    let ex = 0, ez = 0;
    for (let i = pos.count - 8; i < pos.count; i++) { ex += pos.getX(i) / 8; ez += pos.getZ(i) / 8; }
    const door = D.lists.doors.find((m) => m.name === 'DOOR-hub').userData.center;
    const segs = D.waypointTrail.segmentsTo('gallery-a', 'gallery-c', D.camera.position);
    const before = { has: D.waypointTrail.hasTrail(), endDist: Math.hypot(ex - door.x, ez - door.z), segs: segs.map((s) => [s.scene, s.exitDoor]) };
    await D.enterRoom('hub', { via: 'gallery-a' });
    await D.scenes.world().whenLoaded();
    const hubHas = D.waypointTrail.hasTrail();
    await D.enterRoom('gallery-c', { via: 'hub' });
    return { before, hubHas, arrivedHas: D.waypointTrail.hasTrail(), target: D.waypointTrail.target() };
  });
  assert(r.before.has && r.before.endDist < 2.6, `trail ends at the hall door: ${JSON.stringify(r.before)}`);
  assert(r.before.segs.length === 3 && r.before.segs[1][0] === 'hub', `route segments: ${JSON.stringify(r.before.segs)}`);
  assert(r.hubHas, 'the trail continues in the hub after the switch');
  assert(!r.arrivedHas && !r.target, `the trail clears on arrival: ${JSON.stringify(r)}`);
  return r;
});

test('tour_crosses_door', async (c) => {
  await c.load('test');
  const r = await c.ev(async () => {
    const D = window.museumDebug;
    await D.enterRoom('gallery-d', { fade: false });
    await D.scenes.world().whenLoaded();
    const works = D.manifestIndex.flatWorks.filter((w) => w.room === 'gallery-d').slice(-2).concat(D.manifestIndex.flatWorks.filter((w) => w.room === 'gallery-e').slice(0, 1));
    D.tour.start({ works, dwell: 0.3 });
    let guard = 0, crossed = false, outside = 0, placards = 0, samples = 0;
    while (D.tour.active() && guard++ < 4000) {
      D.step(1 / 60, 10);
      samples++;
      if (D.scenes.isSwitching() || D.tour.state().phase === 'switching') { await new Promise((res) => setTimeout(res, 30)); continue; }
      if (!D.roomAt(D.camera.position)) outside++;
      if (D.scenes.currentId() === 'gallery-e') crossed = true;
      if (D.tour.state().phase === 'dwell' && D.interactions.isOpen()) placards++;
    }
    return { crossed, outside, placards, samples, final: D.scenes.currentId(), collision: D.controls.getCollision(), state: D.tour.state() };
  });
  assert(r.crossed && r.final === 'gallery-e', `the tour walked through the door: ${JSON.stringify(r)}`);
  assert(r.outside === 0, `${r.outside} tour samples were outside a room`);
  assert(r.placards > 0 && r.collision, `placards opened and collision restored: ${JSON.stringify(r)}`);
  return r;
});

test('deep_link_room', async (c) => {
  await c.load('test&room=gallery-d', { fresh: true });
  const n = await c.ev(B.counts);
  const blocker = await c.ev(() => document.getElementById('blocker').classList.contains('hidden'));
  assert(n.scene === 'gallery-d' && n.art === worksInRoom(await c.ev(() => window.museumDebug.manifest), 'gallery-d') && blocker, `?room=: ${JSON.stringify(n)}`);
  return n;
});

test('deep_link_work', async (c) => {
  await c.load('test&work=great-wave', { fresh: true });
  const r = await c.ev(() => ({ scene: window.museumDebug.scenes.currentId(), open: window.museumDebug.interactions.isOpen(), title: document.getElementById('placard-title').textContent, probe: window.museumDebug.probeArt() }));
  assert(r.scene === 'gallery-d' && r.open && /Wave/.test(r.title), `?work=: ${JSON.stringify(r)}`);
  assert(r.probe === 'ART-hokusai__great-wave', `standing in front of the work: ${r.probe}`);
  await c.shot('feature_deep_link_work');
  return r;
});

test('persist_resume', async (c) => {
  await c.load('test', { fresh: true });
  const saved = await c.ev(async () => {
    const D = window.museumDebug;
    await D.enterRoom('gallery-e', { fade: false });
    D.controls.teleport(new D.THREE.Vector3(3, 1.7, -6), { yaw: 0.7, pitch: 0 });
    D.step(1 / 60, 2);
    return { ok: D.persist.save(), read: D.persist.read() };
  });
  assert(saved.ok && saved.read.scene === 'gallery-e', `saved: ${JSON.stringify(saved)}`);
  await c.load('test&resume=1', { fresh: true });
  const s = await c.snap();
  assert(s.scene === 'gallery-e' && near(s.pos[0], 3, 0.05) && near(s.pos[2], -6, 0.05) && near(s.yaw, 0.7, 0.01), `resumed where we stood: ${JSON.stringify(s)}`);
  return s;
});

test('touch_tap_reads', async (c) => {
  await c.load('test');
  const r = await c.ev(async () => {
    const D = window.museumDebug;
    await D.navigate.goToWork('the-scream');
    D.interactions.closePlacard();
    D.step(1 / 60, 2);
    const res = D.interactions.openAtScreen(0, 0);
    return { res: res ? res.work ? res.work.id : res : null, open: D.interactions.isOpen() };
  });
  assert(r.open && r.res === 'the-scream', `tap at the screen centre reads the work: ${JSON.stringify(r)}`);
  return r;
});

test('gamepad_walk_look_buttons', async (c) => {
  await c.load('test');
  const r = await c.ev(async () => {
    const D = window.museumDebug;
    D.enter({ pointerLock: false });
    await D.navigate.goToWork('the-scream');
    D.interactions.closePlacard();
    D.step(1 / 60, 2);
    const pad = { mapping: 'standard', connected: true, axes: [0, 0, 0, 0], buttons: Array.from({ length: 16 }, () => ({ pressed: false, value: 0 })) };
    D.gamepad.setSource(() => pad);
    const press = (i) => { pad.buttons[i].pressed = true; D.step(1 / 60, 1); pad.buttons[i].pressed = false; D.step(1 / 60, 1); };
    const out = {};
    const s0 = D.snapshot();
    pad.axes = [0, -1, 0, 0]; // left stick forward
    const s1 = D.step(1 / 60, 30);
    out.walked = Math.hypot(s1.pos[0] - s0.pos[0], s1.pos[2] - s0.pos[2]);
    pad.axes = [0, 0, 0, 0];
    const s2 = D.step(1 / 60, 10);
    out.rest = Math.hypot(s2.pos[0] - s1.pos[0], s2.pos[2] - s1.pos[2]);
    pad.axes = [0, 0, 1, 0]; // right stick right
    const s3 = D.step(1 / 60, 30);
    out.turned = s2.yaw - s3.yaw;
    pad.axes = [0, 0, 0, 0];
    out.connected = D.gamepad.connected();
    out.toast = document.getElementById('gamepad-toast').classList.contains('visible');
    // back to the work, then buttons
    await D.navigate.goToWork('the-scream');
    D.interactions.closePlacard();
    D.step(1 / 60, 3);
    press(0); out.aOpens = D.interactions.isOpen();
    press(1); out.bCloses = !D.interactions.isOpen();
    press(2); out.xMap = D.hud.isMapOpen();
    press(1); out.bClosesMap = !D.hud.isMapOpen();
    press(3); out.yGoto = D.navigate.isOpen();
    press(1); out.bClosesGoto = !D.navigate.isOpen();
    press(9); out.menuHelp = D.ui.isHelpOpen();
    press(1); out.bClosesHelp = !D.ui.isHelpOpen();
    D.gamepad.setSource(null);
    return out;
  });
  assert(Math.abs(r.walked - 4.2 * 0.5) < 0.3, `left stick walks ~2.1 m in half a second: ${r.walked.toFixed(2)}`);
  assert(r.rest < 1e-6, `released stick stops: ${r.rest}`);
  const expectTurn = 2.4 * 0.5;
  assert(r.turned > 0 && Math.abs(r.turned - expectTurn) < 0.15, `right stick turns right by ~${expectTurn} rad: ${r.turned.toFixed(3)}`);
  assert(r.connected && r.toast, `connection state and toast: ${JSON.stringify(r)}`);
  for (const k of ['aOpens', 'bCloses', 'xMap', 'bClosesMap', 'yGoto', 'bClosesGoto', 'menuHelp', 'bClosesHelp']) assert(r[k], `${k}: ${JSON.stringify(r)}`);
  return r;
});

// ---- 5. look, fixtures, models, budgets ------------------------------------------------------
test('textures_pbr_world_uv', async (c) => {
  await c.load('test');
  const r = await c.ev(async () => {
    const D = window.museumDebug;
    await D.enterRoom('hub', { fade: false });
    const floor = D.scene.getObjectByName('GEO-hub_floor');
    const m = floor.material;
    const uv = floor.geometry.attributes.uv;
    let lo = Infinity, hi = -Infinity;
    for (let i = 0; i < uv.count; i++) { lo = Math.min(lo, uv.getX(i)); hi = Math.max(hi, uv.getX(i)); }
    return { map: !!m.map, normal: !!m.normalMap, rough: !!m.roughnessMap, pbr: !!m.userData.pbr, span: hi - lo, slot: m.userData.slot };
  });
  assert(r.map && r.normal && r.rough && r.pbr, `hub floor material: ${JSON.stringify(r)}`);
  assert(r.span > 5, `world-space tiling across the 80 m hall: uv span ${r.span}`);
  return r;
});

test('fixtures_drive_the_light_pool', async (c) => {
  await c.load('test');
  const r = await c.ev(async () => {
    const D = window.museumDebug;
    await D.enterRoom('gallery-c', { fade: false });
    await D.scenes.world().whenLoaded();
    D.step(1 / 60, 20);
    D.lights.update(D.camera, 0, true);
    return D.lights.state();
  });
  assert(r.mode === 'fx' && r.sun.mode === 'laylight' && r.chandelier && /chandelier/.test(r.chandelier), `light pool: ${JSON.stringify(r)}`);
  assert(r.pool.filter(Boolean).length >= 3, `pool lights parked on fixtures: ${JSON.stringify(r.pool)}`);
  return r;
});

test('doors_themed_with_plaques', async (c) => {
  await c.load('test');
  const r = await c.ev(async () => {
    const D = window.museumDebug;
    await D.enterRoom('hub', { fade: false });
    const out = [];
    for (const d of D.lists.doors) {
      const plaque = D.scene.getObjectByName(`GEO-hub_plaque_${d.userData.target}`);
      out.push({ door: d.name, theme: d.userData.theme, plaque: !!(plaque && plaque.material.map && plaque.material.map.isCanvasTexture), leaf: d.material.name });
    }
    return out;
  });
  const missing = r.filter((x) => !x.plaque || !x.theme);
  assert(missing.length === 0, `doors without a theme/plaque: ${JSON.stringify(missing)}`);
  const themes = new Set(r.map((x) => x.theme));
  assert(themes.size >= 7, `themes in use: ${[...themes].join(', ')}`);
  return [...themes];
});

test('models_load_and_sculpture_placard', async (c) => {
  await c.load('test');
  const r = await c.ev(async () => {
    const D = window.museumDebug, T = D.THREE;
    await D.enterRoom('hub', { fade: false });
    await D.scenes.world().whenLoaded();
    const sculpts = D.lists.pickables.filter((m) => m.name.startsWith('SCULPT-')).map((m) => m.name);
    const sc = D.lists.pickables.find((m) => m.name === 'SCULPT-si-greek-slave');
    const c = new T.Vector3();
    new T.Box3().setFromObject(sc).getCenter(c);
    D.controls.teleport(new T.Vector3(c.x + 2.4, 1.7, c.z + 0.6), { lookAt: c });
    D.enter({ pointerLock: false });
    D.step(1 / 60, 3);
    const probe = D.probeArt();
    const prompt = document.getElementById('look-prompt').textContent;
    D.interactions.openAtCrosshair();
    const title = document.getElementById('placard-title').textContent;
    const credit = document.getElementById('placard-credit').textContent;
    const models = D.models.state();
    return { count: sculpts.length, probe, prompt, title, credit, loads: models.loads, failures: models.failures };
  });
  assert(r.count >= 15, `sculptures in the hub: ${r.count}`);
  assert(r.probe === 'SCULPT-si-greek-slave' && /Greek Slave/.test(r.prompt), `sculpture under the crosshair: ${JSON.stringify(r)}`);
  assert(/Greek Slave/.test(r.title) && /CC0/.test(r.credit), `sculpture placard: ${JSON.stringify(r)}`);
  assert(r.failures === 0, `model failures: ${r.failures}`);
  await c.shot('feature_sculpture_placard');
  return r;
});

test('room_budget', async (c) => {
  await c.load('test');
  const r = await c.ev(async () => {
    const D = window.museumDebug;
    const out = {};
    for (const id of ['hub', 'gallery-c', 'people-industrial-age-2']) {
      await D.enterRoom(id, { fade: false });
      await D.scenes.world().whenLoaded();
      await D.setView(id === 'hub' ? 'hub_west' : `${id}_door`);
      D.renderOnce();
      out[id] = { calls: D.renderer.info.render.calls, tris: D.renderer.info.render.triangles, geometries: D.renderer.info.memory.geometries, textures: D.renderer.info.memory.textures };
    }
    return out;
  });
  for (const [id, v] of Object.entries(r)) {
    assert(v.calls <= 450 && v.tris <= 2_000_000, `${id} over budget: ${JSON.stringify(v)}`);
  }
  return r;
});

test('models_memory_returns_after_switches', async (c) => {
  await c.load('test');
  const r = await c.ev(async () => {
    const D = window.museumDebug;
    const go = async (id) => { await D.enterRoom(id, { fade: false }); await D.scenes.world().whenLoaded(); D.renderOnce(); return { ...D.renderer.info.memory }; };
    const base = await go('hub');
    const seq = [];
    for (let i = 0; i < 3; i++) { await go('gallery-c'); seq.push(await go('hub')); }
    return { base, seq };
  });
  const last = r.seq[r.seq.length - 1];
  assert(last.textures <= r.base.textures + 8 && last.geometries <= r.base.geometries + 8, `GPU memory should return to the hub baseline: ${JSON.stringify(r)}`);
  return r;
});

test('framing_views', async (c) => {
  await c.load('test');
  for (const v of ['hub_west', 'hub_rotunda', 'hub_bays', 'hub_east', 'gallery-c_corner', 'gallery-f_door', 'people-medieval-period-1_corner']) {
    const ok = await c.ev(async (name) => { const D = window.museumDebug; const r = await D.setView(name); await D.scenes.world().whenLoaded(); D.renderOnce(); return r; }, v);
    assert(ok, `unknown view ${v}`);
    await c.shot(`view_${v}`);
  }
  return 'ok';
});

test('wing_off_flag', async (c) => {
  await c.load('test&wing=0', { fresh: true });
  const n = await c.ev(B.counts);
  const m = await c.ev(() => ({ artists: window.museumDebug.manifest.artists.length, rooms: window.museumDebug.manifest.rooms.length, wings: window.museumDebug.manifest.wings.length }));
  assert(n.doors === 6 && m.artists === 53 && m.rooms === 7 && m.wings === 1, `?wing=0: ${JSON.stringify({ n, m })}`);
  return { n, m };
});

test('classic_mode_loads', async (c) => {
  await c.load('test&classic', { fresh: true });
  const n = await c.ev(B.counts);
  assert(n.pipeline === 'classic' && n.scene === 'hub' && n.doors === 16, `classic mode: ${JSON.stringify(n)}`);
  await c.ev(async () => { await window.museumDebug.enterRoom('gallery-b', { fade: false }); await window.museumDebug.scenes.world().whenLoaded(); window.museumDebug.renderOnce(); });
  await c.shot('view_classic_gallery_b');
  return n;
});

test('no_console_errors', async (c) => {
  await c.load('test');
  assert(c.errors.length === 0, `console errors on the last page: ${c.errors.join(' | ')}`);
  return 'ok';
});

// ---- runner --------------------------------------------------------------------------------
async function main() {
  if (opt.list) { for (const t of tests) console.log(t.name); return 0; }
  fs.mkdirSync(opt.out, { recursive: true });
  const { server, port } = await startServer();
  const base = `http://127.0.0.1:${port}`;
  const browser = await chromium.launch({
    executablePath: opt.chromium,
    headless: !opt.headed,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--no-sandbox'],
  });
  const ctx = new Ctx(browser, base);
  const report = { started: new Date().toISOString(), base, results: [] };
  const greps = opt.grep ? opt.grep.split(',').map((g) => g.trim()).filter(Boolean) : [];
  const selected = tests.filter((t) => !greps.length || greps.some((g) => t.name.includes(g)));
  let failed = 0;
  for (const t of selected) {
    const t0 = Date.now();
    try {
      const value = await t.fn(ctx);
      report.results.push({ name: t.name, ok: true, ms: Date.now() - t0, value });
      console.log(`  ok    ${t.name}  (${((Date.now() - t0) / 1000).toFixed(1)} s)`);
    } catch (e) {
      failed++;
      report.results.push({ name: t.name, ok: false, ms: Date.now() - t0, error: String(e && e.message || e) });
      console.log(`  FAIL  ${t.name}  (${((Date.now() - t0) / 1000).toFixed(1)} s)\n        ${String(e && e.message || e).replace(/\n/g, '\n        ')}`);
      if (opt.shots && ctx.page) { try { await ctx.shot(`fail_${t.name}`); } catch (e2) { /* ignore */ } }
    }
  }
  if (opt.shots && shots.length) {
    const rel = (f) => path.basename(f);
    const html = `<!doctype html><meta charset="utf-8"><body style="margin:0;background:#111;font:12px sans-serif;color:#ddd">
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px;padding:6px;width:1280px">
${shots.map((f) => `<figure style="margin:0"><img src="${rel(f)}" style="width:100%;display:block"><figcaption style="padding:2px 4px">${rel(f)}</figcaption></figure>`).join('\n')}
</div></body>`;
    fs.writeFileSync(path.join(opt.out, 'sheet.html'), html);
    const page = await browser.newPage({ viewport: { width: 1292, height: 800 } });
    await page.goto(`file://${path.join(opt.out, 'sheet.html')}`);
    await page.screenshot({ path: path.join(opt.out, 'contact_sheet.png'), fullPage: true });
    await page.close();
  }
  report.finished = new Date().toISOString();
  report.failed = failed;
  report.consoleErrors = ctx.errors;
  fs.writeFileSync(path.join(opt.out, 'report.json'), JSON.stringify(report, null, 2));
  await browser.close();
  server.close();
  console.log(`\n${selected.length - failed}/${selected.length} passed${failed ? `, ${failed} FAILED` : ''}. Report: ${path.join(opt.out, 'report.json')}`);
  return failed ? 1 : 0;
}

main().then((code) => process.exit(code)).catch((e) => { console.error(e); process.exit(2); });
