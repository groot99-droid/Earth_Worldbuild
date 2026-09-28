#!/usr/bin/env node
// Browser walk-through tests for the Chronicle Museum viewer.
//
//   node _Museum/tools/walk_test.mjs [--out DIR] [--grep NAME] [--no-shots] [--headed] [--list]
//
// Starts a static server on the project root, opens the viewer in headless Chromium
// (software WebGL is fine) with ?test (no animation loop) and drives it through
// window.museumDebug: deterministic steps, walks, teleports, clicks. Assertions are in
// Blender metres (x east, y north, z up), like the manifest. Screenshots and report.json
// go to --out (default _Museum/tools/out, git-ignored).
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

const ignoreConsole = (t) => /museum_v2\.gltf|sky_v2\.jpg|favicon\.ico/.test(t);

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
    await this.page.screenshot({ path: file });
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

// ---- tests -------------------------------------------------------------------------------
test('load', async (c) => {
  await c.load('test');
  const n = await c.ev(() => {
    const D = window.museumDebug;
    return { art: D.artMeshes.length, walls: D.wallMeshes.length, floors: D.floorMeshes.length, rooms: D.rooms.size, model: D.modelUrl, subtitle: document.getElementById('blocker-subtitle').textContent };
  });
  assert(c.errors.length === 0, `console errors: ${c.errors.join(' | ')}`);
  assert(/Art-Talk Wing — 53 artists, 299 works, 973–1968/.test(n.subtitle), `subtitle: ${n.subtitle}`);
  assert(n.art >= 299, `expected >= 299 ART meshes, got ${n.art}`);
  assert(n.walls >= 50, `expected >= 50 wall meshes, got ${n.walls}`);
  assert(n.floors >= 14, `expected >= 14 floor meshes, got ${n.floors}`);
  assert(n.rooms >= 11, `expected >= 11 geometry rooms, got ${n.rooms}`);
  return n;
});

test('rotunda_to_spine', async (c) => {
  await c.load('test');
  await c.at(0, 0, 0, 0);
  const s = await c.walk('forward', 3.5);
  const [x, y] = s.blender;
  assert(between(x, 13.5, 16) && Math.abs(y) < 0.3, `expected x 13.5-16, |y|<0.3; got ${fmt(s.blender)}`);
  assert(s.geoRoom === 'spine1', `expected geometry room spine1, got ${s.geoRoom}`);
  return s.blender;
});

test('spine_to_gallery_a', async (c) => {
  await c.load('test');
  await c.at(20, 0, 0, 90);
  const s = await c.walk('forward', 2.5);
  assert(between(s.blender[1], 9, 12), `expected y 9-12, got ${fmt(s.blender)}`);
  assert(s.room === 'gallery-a', `expected room gallery-a, got ${s.room}`);
  return s.blender;
});

test('wall_blocks', async (c) => {
  await c.load('test');
  await c.at(20, 14, 0, 90);
  const s = await c.walk('forward', 3);
  assert(between(s.blender[1], 16.0, 16.8), `Gallery A north wall should stop at y 16.0-16.8, got ${fmt(s.blender)}`);
  return s.blender;
});

test('doors_passable', async (c) => {
  await c.load('test');
  // For every manifest door (both directions): stand 1.5 m before it on the owner's side, walk
  // 4.2 m through. The travel axis is the one perpendicular to the wall the door sits in, found
  // from the geometry room boxes (owner's box first, then the neighbour's).
  const plan = await c.ev(() => {
    const D = window.museumDebug;
    const rooms = D.manifest.rooms;
    const byId = new Map(rooms.map((r) => [r.id, r]));
    const b2t = (p) => new D.THREE.Vector3(p[0], p[2], -p[1]);
    const geoFor = (room) => D.roomAt(b2t(room.position).add(new D.THREE.Vector3(0, 1.7, 0)));
    const onEdge = (door, g) => {
      if (!g) return null;
      const bx = g.box, x = door[0], z = -door[1];
      const inX = x > bx.min.x - 0.7 && x < bx.max.x + 0.7, inZ = z > bx.min.z - 0.7 && z < bx.max.z + 0.7;
      if (inZ && Math.abs(x - bx.min.x) < 0.7) return { axis: 'x', edge: -1 };
      if (inZ && Math.abs(x - bx.max.x) < 0.7) return { axis: 'x', edge: 1 };
      if (inX && Math.abs(z - bx.min.z) < 0.7) return { axis: 'y', edge: 1 };  // three -z = Blender +y
      if (inX && Math.abs(z - bx.max.z) < 0.7) return { axis: 'y', edge: -1 };
      return null;
    };
    const out = [];
    for (const room of rooms) {
      for (const [otherId, door] of Object.entries(room.doors || {})) {
        const other = byId.get(otherId);
        if (!other) continue;
        let axis, sign;
        const own = onEdge(door, geoFor(room));
        if (own) { axis = own.axis; sign = own.edge; }
        else {
          const theirs = onEdge(door, geoFor(other));
          if (theirs) { axis = theirs.axis; sign = -theirs.edge; }
          else {
            const dx = door[0] - room.position[0], dy = door[1] - room.position[1];
            axis = Math.abs(dx) >= Math.abs(dy) ? 'x' : 'y';
            sign = Math.sign(axis === 'x' ? dx : dy) || 1;
          }
        }
        out.push({ from: room.id, to: otherId, door, axis, sign });
      }
    }
    return out;
  });
  const failures = [];
  for (const d of plan) {
    const heading = d.axis === 'x' ? (d.sign > 0 ? 0 : 180) : (d.sign > 0 ? 90 : 270);
    const start = [d.door[0], d.door[1], d.door[2] - 0.05];
    if (d.axis === 'x') start[0] -= d.sign * 1.5; else start[1] -= d.sign * 1.5;
    await c.at(start[0], start[1], start[2], heading);
    const s = await c.walk('forward', 1.0); // 4.2 m
    const travelled = d.axis === 'x' ? (s.blender[0] - start[0]) * d.sign : (s.blender[1] - start[1]) * d.sign;
    if (travelled < 2.7) failures.push(`${d.from}>${d.to} at ${fmt(d.door)} heading ${heading}: moved ${travelled.toFixed(2)} m (${fmt(s.blender)})`);
  }
  assert(failures.length === 0, `${failures.length}/${plan.length} doors blocked:\n    ${failures.join('\n    ')}`);
  return { checked: plan.length };
});

test('stairs_to_mezzanine', async (c) => {
  await c.load('test');
  await c.at(85, 0, 0, 0);
  const s = await c.walk('forward', 4);
  assert(feet(s) >= 6.9, `expected to climb to feet >= 6.9, got ${fmt(s.blender)}`);
  assert(s.blender[0] >= 96, `expected x >= 96 on the landing, got ${fmt(s.blender)}`);
  assert(s.room === 'mezzanine', `expected room mezzanine, got ${s.room}`);
  return s.blender;
});

test('mezzanine_to_spine2', async (c) => {
  await c.load('test');
  await c.at(97, 0, 7, 90);
  let s = await c.walk('forward', 1.0);   // north onto the balcony ring
  assert(near(feet(s), 7.1, 0.3), `expected feet at z 7.1 on the balcony, got ${fmt(s.blender)}`);
  await c.at(s.blender[0], s.blender[1], 7, 180);
  s = await c.walk('forward', 2.6);       // west along the ring to the stair hall's west wall
  assert(near(feet(s), 7.1, 0.3) && between(s.blender[0], 84.2, 86.5), `expected to stop at the west wall on the balcony, got ${fmt(s.blender)}`);
  await c.at(s.blender[0], s.blender[1], 7, 225);
  s = await c.walk('forward', 1.2);       // south-west through the spine opening (|y| < 3) into spine2
  assert(near(feet(s), 7.1, 0.3), `expected feet at z 7.1 in spine2, got ${fmt(s.blender)}`);
  assert(s.blender[0] < 84 && Math.abs(s.blender[1]) < 3, `expected to reach spine2 (x < 84, |y| < 3), got ${fmt(s.blender)}`);
  assert(s.geoRoom === 'spine2', `expected geometry room spine2, got ${s.geoRoom}`);
  return s.blender;
});

test('balcony_edge_blocks', async (c) => {
  await c.load('test');
  await c.at(91, 4, 7, 270); // on the north ring, heading south toward the stairwell
  const s = await c.walk('forward', 1.5);
  assert(s.blender[1] > 1.6, `balustrade should stop at y > 1.6, got ${fmt(s.blender)}`);
  assert(near(feet(s), 7.1, 0.3), `should stay on the balcony, got ${fmt(s.blender)}`);
  return s.blender;
});

test('upper_ignores_ground_walls', async (c) => {
  await c.load('test');
  await c.at(16, 5, 7, 180); // gallery F (upper), heading west across gallery A's west wall line (x=12)
  const s = await c.walk('forward', 1.5);
  assert(s.blender[0] < 11, `ground-floor wall at x=12 must not block the upper floor, got ${fmt(s.blender)}`);
  assert(near(feet(s), 7.1, 0.3), `should stay on the upper floor, got ${fmt(s.blender)}`);
  return s.blender;
});

test('ground_ignores_upper_walls', async (c) => {
  await c.load('test');
  await c.at(25, 0, 0, 0); // spine1, heading east under spine2's west wall (x=28, upper)
  const s = await c.walk('forward', 1.5);
  assert(s.blender[0] > 29, `upper-floor wall at x=28 must not block the ground floor, got ${fmt(s.blender)}`);
  return s.blender;
});

test('placard_click', async (c) => {
  await c.load('test');
  const info = await c.ev(() => {
    const D = window.museumDebug;
    const entry = D.manifestIndex.byMeshName.get('ART-giotto__lamentation');
    const spot = D.interactions.spotFor(entry);
    D.controls.teleport(spot.position, { lookAt: spot.lookAt });
    D.enter({ pointerLock: false });
    D.step(1 / 60, 2);
    return { probe: D.probeArt(), pos: D.snapshot().blender };
  });
  assert(info.probe === 'ART-giotto__lamentation', `crosshair should be on the work, probe = ${info.probe} at ${fmt(info.pos)}`);
  await c.page.mouse.click(640, 360);
  await c.page.waitForFunction(() => document.getElementById('placard').classList.contains('visible'), null, { timeout: 5000 });
  const p = await c.ev(() => ({
    title: document.getElementById('placard-title').textContent,
    artist: document.getElementById('placard-artist').textContent,
    voice: document.getElementById('placard-voice').textContent,
    voiceHidden: document.getElementById('placard-voice').hidden,
    img: document.getElementById('placard-image').getAttribute('src'),
    desc: document.getElementById('placard-description').textContent.length,
    suggestions: document.querySelectorAll('#suggested-list .suggested-item').length,
  }));
  const rewrites = JSON.parse(fs.readFileSync(path.join(ROOT, '_Museum/data/placard-rewrite.json'), 'utf8'));
  assert(/^Lamentation/.test(p.title), `title: ${p.title}`);
  assert(/Giotto/.test(p.artist), `artist line: ${p.artist}`);
  assert(p.desc > 50, `description too short (${p.desc} chars)`);
  assert(p.img.endsWith('Art-Talk-main/images/giotto/lamentation.jpg'), `image src: ${p.img}`);
  assert(p.suggestions >= 1, 'no suggestions rendered');
  if (rewrites.lamentation) assert(!p.voiceHidden && /AI rewrite/.test(p.voice), `voice label missing: "${p.voice}"`);
  else assert(p.voiceHidden, 'voice label shown without a rewrite');
  await c.shot('feature_placard');
  await c.ev(() => window.museumDebug.interactions.closePlacard());
  return p;
});

test('look_prompt', async (c) => {
  await c.load('test');
  const r = await c.ev(() => {
    const D = window.museumDebug;
    const entry = D.manifestIndex.byMeshName.get('ART-vermeer__girl-with-a-pearl-earring');
    const spot = D.interactions.spotFor(entry);
    D.controls.teleport(spot.position, { lookAt: spot.lookAt });
    D.enter({ pointerLock: false });
    D.step(1 / 60, 6);
    const el = document.getElementById('look-prompt');
    const on = { hidden: el.hidden, text: el.textContent, hot: document.getElementById('crosshair').classList.contains('hot') };
    D.controls.setLook(D.controls.getLook().yaw + Math.PI, 0); // turn around
    D.step(1 / 60, 6);
    const off = { hidden: el.hidden };
    return { on, off };
  });
  assert(!r.on.hidden && /Girl with a Pearl Earring/.test(r.on.text) && r.on.hot, `prompt not shown: ${JSON.stringify(r.on)}`);
  assert(r.off.hidden, 'prompt should hide when looking away');
  return r;
});

test('framing_views', async (c) => {
  await c.load('test');
  const framings = JSON.parse(fs.readFileSync(path.join(ROOT, '_Museum/blender/scripts/framings.json'), 'utf8')).framings;
  const extra = {
    mezzanine_balcony: { pos: [97, 4, 8.7], target: [84, 0, 8.5], fov_deg: 58.7, desc: 'Balcony ring around the stairwell (procedural)' },
  };
  const results = {};
  await c.ev(() => { const D = window.museumDebug; D.interactions.closePlacard(); if (D.tour.active()) D.tour.stop(); D.enter({ pointerLock: false }); });
  for (const [name, f] of Object.entries({ ...framings, ...extra })) {
    await c.ev((fr) => window.museumDebug.applyFraming(fr), f);
    const s = await c.snap();
    results[name] = s.blender.map((v) => +v.toFixed(2));
    await c.shot(`view_${name}`);
  }
  return results;
});

test('minimap_teleport', async (c) => {
  await c.load('test');
  await c.ev(() => { const D = window.museumDebug; D.interactions.closePlacard(); if (D.tour.active()) D.tour.stop(); D.enter({ pointerLock: false }); });
  const r = await c.ev(() => {
    const D = window.museumDebug;
    const ok = D.hud.teleportToRoom('gallery-c');
    const s = D.step(1 / 60, 2);
    D.hud.openMap();
    const large = document.querySelector('#map-large');
    const canvas = large.querySelector('canvas');
    const rect = canvas.getBoundingClientRect();
    const hit = D.hud.roomAtScreen(rect.left + rect.width / 2, rect.top + rect.height / 2);
    return { ok, s, mini: !!document.getElementById('minimap'), open: large.classList.contains('open'), canvasW: rect.width, hit: hit ? hit.id : null };
  });
  assert(r.ok, 'teleportToRoom returned false');
  assert(r.s.room === 'gallery-c', `expected room gallery-c, got ${r.s.room}`);
  assert(near(r.s.blender[0], 54, 1) && near(r.s.blender[1], 12, 1), `expected ~(54, 12), got ${fmt(r.s.blender)}`);
  assert(r.mini && r.open && r.canvasW > 200, `minimap/large map missing: ${JSON.stringify(r)}`);
  await c.shot('feature_map');
  await c.ev(() => window.museumDebug.hud.closeMap());
  return r;
});

test('navigate_filter_goto', async (c) => {
  await c.load('test');
  const r = await c.ev(() => {
    const D = window.museumDebug;
    D.navigate.open();
    const n = D.navigate.filter('vermeer');
    const visible = [...document.querySelectorAll('#nav-panel .nav-artist')].filter((el) => !el.hidden).map((el) => el.textContent.trim());
    return { n, visible: visible.slice(0, 5), open: D.navigate.isOpen() };
  });
  assert(r.open && r.n >= 1 && r.visible.some((t) => /Vermeer/.test(t)), `filter failed: ${JSON.stringify(r)}`);
  await c.shot('feature_navigate');
  const g = await c.ev(() => {
    const D = window.museumDebug;
    const ok = D.navigate.goToWork('girl-with-a-pearl-earring');
    const s = D.step(1 / 60, 2);
    return { ok, s, probe: D.probeArt(), title: document.getElementById('placard-title').textContent, visible: document.getElementById('placard').classList.contains('visible'), navOpen: D.navigate.isOpen() };
  });
  assert(g.ok && g.visible && /Girl with a Pearl Earring/.test(g.title), `goToWork failed: ${JSON.stringify(g)}`);
  assert(g.probe === 'ART-vermeer__girl-with-a-pearl-earring', `crosshair not on the work: ${g.probe} at ${fmt(g.s.blender)}`);
  assert(g.s.room === 'gallery-c', `expected gallery-c, got ${g.s.room}`);
  assert(!g.navOpen, 'nav panel should close after going somewhere');
  return g;
});

test('placard_prev_next', async (c) => {
  await c.load('test');
  const r = await c.ev(() => {
    const D = window.museumDebug;
    D.navigate.goToWork('girl-with-a-pearl-earring');
    const list = D.manifestIndex.flatWorks;
    const idx = list.findIndex((e) => e.work.id === 'girl-with-a-pearl-earring');
    document.getElementById('placard-next').click();
    D.step(1 / 60, 2);
    const next = { title: document.getElementById('placard-title').textContent, probe: D.probeArt(), expect: list[idx + 1].meshName, expectTitle: list[idx + 1].work.title };
    document.getElementById('placard-prev').click();
    D.step(1 / 60, 2);
    const back = { title: document.getElementById('placard-title').textContent, probe: D.probeArt() };
    return { next, back };
  });
  assert(r.next.probe === r.next.expect && r.next.title === r.next.expectTitle, `next failed: ${JSON.stringify(r.next)}`);
  assert(r.back.probe === 'ART-vermeer__girl-with-a-pearl-earring', `prev failed: ${JSON.stringify(r.back)}`);
  await c.ev(() => window.museumDebug.interactions.closePlacard());
  return r;
});

test('guide_trail', async (c) => {
  await c.load('test');
  const r = await c.ev(() => {
    const D = window.museumDebug;
    D.navigate.goToWork('lamentation'); // gallery-a; its suggestions include the next room's first work
    const items = [...document.querySelectorAll('#suggested-list .suggested-item')];
    const guide = items.map((el) => [...el.querySelectorAll('button')].find((b) => /Guide/.test(b.textContent))).filter(Boolean);
    const before = D.waypointTrail.hasTrail();
    if (guide[guide.length - 1]) guide[guide.length - 1].click();
    const after = D.waypointTrail.hasTrail();
    // the trail must not cut through the spine walls: sample the tube's centre curve via a fresh route
    const rooms = D.roomsById;
    const path = D.waypointTrail.findPath('gallery-a', 'gallery-b');
    D.interactions.closePlacard();
    return { items: items.length, guides: guide.length, before, after, path, cleared: D.waypointTrail.hasTrail() };
  });
  assert(r.items >= 1 && r.guides >= 1, `no suggestions with a guide button: ${JSON.stringify(r)}`);
  assert(!r.before && r.after, `guide button should draw the trail: ${JSON.stringify(r)}`);
  assert(!r.cleared, 'closing the placard should clear the trail');
  assert(r.path.join('>') === 'gallery-a>gallery-b', `path: ${r.path}`);
  return r;
});

test('route_points_avoid_walls', async (c) => {
  await c.load('test');
  // door-to-door routing between chained galleries must stay inside the spine (|y| <= 3) between the doors
  const r = await c.ev(async () => {
    const D = window.museumDebug;
    const mod = await import('./js/waypoints.js');
    const pts = mod.routePoints(D.roomsById, ['gallery-a', 'gallery-b']).map((v) => [v.x, -v.z, v.y]);
    return pts;
  });
  // expected: A centre (20,10) -> A's door (20,3) -> B's door (36,-3) -> B centre (36,-11)
  assert(r.length === 4, `expected 4 route points, got ${JSON.stringify(r)}`);
  assert(near(r[1][0], 20, 0.01) && near(r[1][1], 3, 0.01) && near(r[2][0], 36, 0.01) && near(r[2][1], -3, 0.01), `doors missing from the route: ${JSON.stringify(r)}`);
  return r;
});

test('keys_e_m_help', async (c) => {
  await c.load('test');
  await c.ev(() => {
    const D = window.museumDebug;
    const entry = D.manifestIndex.byMeshName.get('ART-hokusai__' + D.manifest.artists.find((a) => a.slug === 'hokusai').works[0].id);
    const spot = D.interactions.spotFor(entry);
    D.controls.teleport(spot.position, { lookAt: spot.lookAt });
    D.enter({ pointerLock: false });
    D.step(1 / 60, 4);
  });
  const state = () => c.ev(() => ({
    placard: document.getElementById('placard').classList.contains('visible'),
    title: document.getElementById('placard-title').textContent,
    map: document.getElementById('map-large').classList.contains('open'),
    help: document.getElementById('help').classList.contains('open'),
    nav: document.getElementById('nav-panel').classList.contains('open'),
    active: document.activeElement ? document.activeElement.tagName : null,
    tour: window.museumDebug.tour.active(),
  }));
  const trace = [];
  const press = async (key, expect, what) => {
    await c.page.keyboard.press(key);
    const st = await state();
    trace.push({ key, ...st });
    for (const [k, v] of Object.entries(expect)) {
      assert(st[k] === v, `${what}: expected ${k}=${v}, got ${JSON.stringify(st)}; trace ${JSON.stringify(trace)}`);
    }
    return st;
  };
  await press('KeyE', { placard: true }, 'E should open the placard');
  await press('Escape', { placard: false }, 'Escape should close the placard');
  await press('KeyM', { map: true }, 'M should open the map');
  await press('Escape', { map: false }, 'Escape should close the map');
  await press('Shift+Slash', { help: true, map: false }, '? should open help');
  await c.shot('feature_help');
  await press('Escape', { help: false }, 'Escape should close help');
  await press('Tab', { nav: true, help: false }, 'Tab should open the go-to panel');
  await press('Escape', { nav: false }, 'Escape should close the go-to panel');
  await press('KeyH', { help: true }, 'H should open help');
  await press('Escape', { help: false }, 'Escape should close help again');
  return trace;
});

test('tour_runs_inside_rooms', async (c) => {
  await c.load('test');
  const r = await c.ev(() => {
    const D = window.museumDebug;
    D.interactions.closePlacard();
    D.hud.teleportToRoom('rotunda');
    D.tour.start({ from: 0, dwell: 0.5 });
    const outside = [];
    let maxIndex = 0;
    let shotState = null;
    for (let i = 0; i < 1800; i += 10) {
      D.step(1 / 60, 10);
      const st = D.tour.state();
      maxIndex = Math.max(maxIndex, st.index);
      const geo = D.roomAt(D.camera.position);
      if (!geo) outside.push({ i, pos: D.snapshot().blender, state: st });
      if (i === 900) shotState = st;
    }
    const status = document.getElementById('tour-status');
    const out = { maxIndex, outside: outside.slice(0, 5), nOutside: outside.length, active: D.tour.active(), status: status.textContent, statusHidden: status.hidden, shotState };
    return out;
  });
  assert(r.active, 'tour should still be running after 30 s of simulated time');
  assert(r.maxIndex >= 2, `tour should have reached the third work, index ${r.maxIndex}`);
  assert(r.nOutside === 0, `${r.nOutside} samples outside any room, e.g. ${JSON.stringify(r.outside)}`);
  assert(!r.statusHidden && /Guided tour/.test(r.status), `tour status missing: ${r.status}`);
  await c.shot('feature_tour');
  const stopped = await c.ev(() => { const D = window.museumDebug; D.tour.stop(); return { active: D.tour.active(), collision: D.controls.getCollision() }; });
  assert(!stopped.active && stopped.collision, `stop() should end the tour and restore collision: ${JSON.stringify(stopped)}`);
  return r;
});

test('tour_long_route', async (c) => {
  await c.load('test');
  // a leg that crosses the whole building: from the rotunda to the Art-Talk wing's last work (upper floor, gallery F)
  const r = await c.ev(() => {
    const D = window.museumDebug;
    D.hud.teleportToRoom('rotunda');
    const list = D.manifestIndex.flatWorks.filter((e) => e.wing === 'art-talk');
    D.tour.start({ works: [list[list.length - 1]], from: 0, dwell: 0.5 });
    const outside = [];
    let arrived = null;
    const trail = [];
    for (let i = 0; i < 60 * 200; i += 10) {
      D.step(1 / 60, 10);
      const geo = D.roomAt(D.camera.position);
      if (!geo) outside.push({ i, pos: D.snapshot().blender });
      const st = D.tour.state();
      if (i % 600 === 0) trail.push({ t: i / 60, pos: D.snapshot().blender.map((v) => +v.toFixed(1)), progress: st.progress, phase: st.phase });
      if (st.phase === 'dwell' && !arrived) { D.step(1 / 60, 15); arrived = { i, seconds: i / 60, pos: D.snapshot().blender, probe: D.probeArt(), placard: document.getElementById('placard').classList.contains('visible') }; }
      if (!D.tour.active()) break;
    }
    const final = { state: D.tour.state(), pos: D.snapshot().blender };
    D.tour.stop();
    return { outside: outside.slice(0, 5), nOutside: outside.length, arrived, last: list[list.length - 1].meshName, trail, final };
  });
  assert(r.arrived, `tour never arrived at the last work; final ${JSON.stringify(r.final)}; trail ${JSON.stringify(r.trail)}`);
  assert(r.nOutside === 0, `${r.nOutside} samples outside any room, e.g. ${JSON.stringify(r.outside)}`);
  assert(r.arrived.probe === r.last && r.arrived.placard, `arrival should face the work with its placard open: ${JSON.stringify(r.arrived)}`);
  assert(feet({ blender: r.arrived.pos }) > 6.5, `the last work is on the upper floor, arrived at ${fmt(r.arrived.pos)}`);
  return r;
});

test('deep_link_room', async (c) => {
  await c.load('test&room=gallery-d');
  const s = await c.ev(() => ({ ...window.museumDebug.snapshot(), blocker: document.getElementById('blocker').classList.contains('hidden') }));
  assert(s.room === 'gallery-d' && s.blocker, `?room= failed: ${JSON.stringify(s)}`);
  assert(c.errors.length === 0, `console errors: ${c.errors.join(' | ')}`);
  return s.blender;
});

test('deep_link_work', async (c) => {
  await c.load('test&work=great-wave');
  const s = await c.ev(() => ({
    ...window.museumDebug.snapshot(), probe: window.museumDebug.probeArt(),
    placard: document.getElementById('placard').classList.contains('visible'), title: document.getElementById('placard-title').textContent,
    blocker: document.getElementById('blocker').classList.contains('hidden'),
  }));
  assert(s.placard && s.title.length > 0 && s.blocker, `?work= failed: ${JSON.stringify(s)}`);
  assert(/^ART-hokusai__/.test(s.probe || ''), `crosshair not on the work: ${s.probe}`);
  return s.blender;
});

test('persist_resume', async (c) => {
  await c.load('test', { fresh: true });
  await c.at(30, -8, 0, 45);
  const saved = await c.ev(() => { const D = window.museumDebug; return { ok: D.persist.save(), has: D.persist.hasSave(), s: D.snapshot() }; });
  assert(saved.ok && saved.has, `save failed: ${JSON.stringify(saved)}`);
  await c.load('test&resume=1', { fresh: true });
  const s = await c.ev(() => ({ ...window.museumDebug.snapshot(), blocker: document.getElementById('blocker').classList.contains('hidden') }));
  assert(near(s.blender[0], 30, 0.05) && near(s.blender[1], -8, 0.05), `resume position ${fmt(s.blender)} != (30, -8)`);
  assert(near(s.yaw, saved.s.yaw, 0.01), `resume yaw ${s.yaw} != ${saved.s.yaw}`);
  assert(s.blocker, 'blocker should be hidden after ?resume=1');
  await c.ev(() => window.museumDebug.persist.clear());
  return s.blender;
});

test('touch_tap_reads', async (c) => {
  // a separate touch-capable context: body.touch, joystick present, tap on the right half reads the work
  const context = await c.browser.newContext({ viewport: { width: 1280, height: 720 }, hasTouch: true });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  try {
    await page.goto(`${c.base}/_Museum/web/index.html?test`, { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => window.museumDebug && window.museumDebug.ready, null, { timeout: opt.timeout });
    const pre = await page.evaluate(() => {
      const D = window.museumDebug;
      const entry = D.manifestIndex.byMeshName.get('ART-giotto__lamentation');
      const spot = D.interactions.spotFor(entry);
      D.controls.teleport(spot.position, { lookAt: spot.lookAt });
      D.enter({ pointerLock: false });
      D.step(1 / 60, 4);
      return { touch: document.body.classList.contains('touch'), joystick: !!document.getElementById('joystick'), enabled: D.touch.enabled };
    });
    assert(pre.touch && pre.joystick && pre.enabled, `touch mode not enabled: ${JSON.stringify(pre)}`);
    await page.touchscreen.tap(640, 360);
    await page.waitForFunction(() => document.getElementById('placard').classList.contains('visible'), null, { timeout: 5000 });
    const title = await page.evaluate(() => document.getElementById('placard-title').textContent);
    assert(/^Lamentation/.test(title), `tap should open the Giotto placard, got ${title}`);
    assert(errors.length === 0, `page errors: ${errors.join(' | ')}`);
    return { title };
  } finally {
    await context.close();
  }
});

// ---- Phase 2: the procedural People wing --------------------------------------------------
test('wing_counts', async (c) => {
  await c.load('test');
  const n = await c.ev(() => {
    const D = window.museumDebug;
    const hiddenOk = (D.procwing ? D.procwing.hidden : []).every((name) => {
      const o = D.scene.getObjectByName(name);
      return o && !o.visible && !D.wallMeshes.includes(o);
    });
    return {
      art: D.artMeshes.length, rooms: D.rooms.size, wing: !!D.procwing, wingRooms: D.procwing ? D.procwing.rooms.length : 0,
      boxes: D.procwing ? D.procwing.boxes.length : 0, hiddenOk, subtitle: document.getElementById('blocker-subtitle').textContent,
      manifestRooms: D.manifest.rooms.length, wings: D.manifestIndex.wings.map((w) => w.id),
    };
  });
  assert(n.wing && n.wingRooms === 10, `procedural wing missing: ${JSON.stringify(n)}`);
  assert(n.art === 686, `expected 686 ART meshes (299 + 387), got ${n.art}`);
  assert(n.rooms >= 22, `expected >= 22 geometry rooms, got ${n.rooms}`);
  assert(n.hiddenOk, 'the vestibule west wall pieces should be hidden and non-colliding');
  assert(/Earth Chronicle People — 203 people, 387 portraits/.test(n.subtitle), `subtitle: ${n.subtitle}`);
  assert(c.errors.length === 0, `console errors: ${c.errors.join(' | ')}`);
  return n;
});

test('walk_into_wing', async (c) => {
  await c.load('test');
  await c.at(-3, 0, 0, 180); // rotunda, heading west through the vestibule
  let s = await c.walk('forward', 4.5);
  assert(s.blender[0] < -16.5, `expected to pass the vestibule into the hall (x < -16.5), got ${fmt(s.blender)}`);
  assert(s.room === 'people-spine', `expected room people-spine, got ${s.room} (geo ${s.geoRoom})`);
  await c.at(-23, 0, 0, 90); // under the Bronze Age door, heading north
  s = await c.walk('forward', 1.5);
  assert(s.blender[1] > 4 && s.room === 'people-bronze-age', `expected to enter people-bronze-age, got ${s.room} at ${fmt(s.blender)}`);
  await c.at(-23, 9, 0, 90); // its north wall (y = 11) must stop us
  s = await c.walk('forward', 1.5);
  assert(between(s.blender[1], 10.0, 10.8), `wing wall should block at y 10.0-10.8, got ${fmt(s.blender)}`);
  return s.blender;
});

test('people_placard', async (c) => {
  await c.load('test');
  const r = await c.ev(() => {
    const D = window.museumDebug;
    D.enter({ pointerLock: false });
    const ok = D.navigate.goToWork('people--ada-lovelace--1');
    const s = D.step(1 / 60, 2);
    return {
      ok, s, probe: D.probeArt(),
      title: document.getElementById('placard-title').textContent,
      artist: document.getElementById('placard-artist').textContent,
      meta: document.getElementById('placard-meta').textContent,
      credit: document.getElementById('placard-credit').textContent,
      desc: document.getElementById('placard-description').textContent,
      img: document.getElementById('placard-image').getAttribute('src'),
      suggestions: [...document.querySelectorAll('#suggested-list img')].map((i) => i.getAttribute('src')),
    };
  });
  assert(r.ok && r.title === 'Ada Lovelace', `placard: ${JSON.stringify(r)}`);
  assert(/Ada Lovelace \(1815–1852\)/.test(r.artist) && /Industrial Age/.test(r.artist), `artist line: ${r.artist}`);
  assert(/Antoine Claudet/.test(r.credit), `credit: ${r.credit}`);
  assert(/Analytical Engine/.test(r.desc), 'description should carry the person summary');
  assert(r.img.endsWith('_Site/images/person/ada-lovelace/1.jpg'), `image: ${r.img}`);
  assert(r.probe === 'ART-ada-lovelace__people--ada-lovelace--1', `crosshair: ${r.probe} at ${fmt(r.s.blender)}`);
  assert(/^people-industrial-age/.test(r.s.room), `room: ${r.s.room}`);
  assert(r.suggestions.every((u) => /_Site\/images\//.test(u)), `suggestion thumbs: ${r.suggestions}`);
  await c.ev(async () => { const D = window.museumDebug; await D.procwing.whenLoaded(D.getCurrentRoomId()); });
  await c.shot('feature_people_placard');
  await c.ev(() => window.museumDebug.interactions.closePlacard());
  return r;
});

test('people_textures', async (c) => {
  await c.load('test');
  const r = await c.ev(async () => {
    const D = window.museumDebug;
    const room = D.manifestIndex.byWorkId.get('people--ada-lovelace--1').room;
    await D.procwing.whenLoaded(room);
    const meshes = D.artMeshes.filter((m) => m.userData.room === room);
    return { room, n: meshes.length, mapped: meshes.filter((m) => m.material.map && m.material.map.image).length, state: D.procwing.state() };
  });
  assert(r.n > 0 && r.mapped === r.n, `textures: ${JSON.stringify({ ...r, state: undefined })}`);
  assert(r.state.failures === 0, `texture failures: ${r.state.failures}`);
  return r;
});

test('people_tour', async (c) => {
  await c.load('test');
  const r = await c.ev(() => {
    const D = window.museumDebug;
    D.interactions.closePlacard();
    D.hud.teleportToRoom('future-wing-1');
    const works = D.manifestIndex.flatWorks.filter((e) => e.wing === 'people');
    D.tour.start({ works, from: 0, dwell: 0.3 });
    const outside = [];
    let maxIndex = 0;
    for (let i = 0; i < 2400; i += 10) {
      D.step(1 / 60, 10);
      maxIndex = Math.max(maxIndex, D.tour.state().index);
      if (!D.roomAt(D.camera.position)) outside.push({ i, pos: D.snapshot().blender });
    }
    const st = D.tour.state();
    D.tour.stop();
    return { works: works.length, maxIndex, nOutside: outside.length, outside: outside.slice(0, 4), room: st.room };
  });
  assert(r.works === 387, `expected 387 people works, got ${r.works}`);
  assert(r.maxIndex >= 2, `tour should reach the third portrait, index ${r.maxIndex}`);
  assert(r.nOutside === 0, `${r.nOutside} samples outside any room: ${JSON.stringify(r.outside)}`);
  assert(/^people-/.test(r.room || ''), `tour should be in the wing, room ${r.room}`);
  return r;
});

test('wing_framings', async (c) => {
  await c.load('test');
  const extra = {
    vestibule_door: { pos: [-3, 0, 1.7], target: [-20, 0, 2.0], fov_deg: 58.7 },
    people_hall: { pos: [-18, 0, 1.7], target: [-60, 0, 2.2], fov_deg: 58.7 },
    people_industrial: { pos: [-91, -5, 1.7], target: [-91, -22, 2.2], fov_deg: 58.7 },
    people_bronze: { pos: [-23, 4, 1.7], target: [-23, 11, 2.0], fov_deg: 58.7 },
  };
  const out = {};
  await c.ev(() => { const D = window.museumDebug; D.interactions.closePlacard(); if (D.tour.active()) D.tour.stop(); D.enter({ pointerLock: false }); });
  for (const [name, f] of Object.entries(extra)) {
    await c.ev(async (fr) => { const D = window.museumDebug; D.applyFraming(fr); await D.procwing.whenLoaded(D.getCurrentRoomId()); }, f);
    await c.ev(async () => { const D = window.museumDebug; for (const r of D.procwing.rooms) { const s = D.procwing.state().rooms[r]; if (s === 'loading') await D.procwing.whenLoaded(r); } });
    out[name] = (await c.snap()).blender.map((v) => +v.toFixed(2));
    await c.shot(`view_${name}`);
  }
  return out;
});

test('wing_off_flag', async (c) => {
  await c.load('test&wing=0', { fresh: true });
  const n = await c.ev(() => ({ art: window.museumDebug.artMeshes.length, wing: !!window.museumDebug.procwing }));
  assert(!n.wing && n.art === 299, `?wing=0 should skip the wing: ${JSON.stringify(n)}`);
  assert(c.errors.length === 0, `console errors: ${c.errors.join(' | ')}`);
  return n;
});

test('classic_mode_loads', async (c) => {
  await c.load('test&classic', { fresh: true });
  const n = await c.ev(() => { const D = window.museumDebug; return { art: D.artMeshes.length, pipeline: D.pipeline.mode, rooms: D.rooms.size, room: D.getCurrentRoomId() }; });
  assert(c.errors.length === 0, `console errors: ${c.errors.join(' | ')}`);
  assert(n.art >= 299 && n.pipeline === 'classic' && n.rooms >= 11 && n.room === 'rotunda', `classic mode: ${JSON.stringify(n)}`);
  await c.ev(() => window.museumDebug.hud.teleportToRoom('gallery-b'));
  await c.shot('view_classic_gallery_b');
  return n;
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
