# The Chronicle Museum

A walkable 3D museum, generated in the browser from data. A **Grand Hall** with an era-themed
door to every gallery leads to sixteen rooms: six **Art-Talk** galleries (53 artists, 299 works,
973–1968) and ten **Earth Chronicle People** rooms (203 people, 387 portraits, Bronze Age to
Information Age). Paintings hang at their real-world size in a salon grid, in bevelled frames under
picture lights; public-domain museum sculptures stand on column pedestals between the doors. Only one
scene is ever loaded: click a door and the room is built, the previous one disposed.

## How to view it

1. Start a static file server rooted at the **project root** (the viewer reads `../../Art-Talk-main/`
   and `../../_Site/` for the works' images):
   ```
   python -m http.server 8767
   ```
2. Open `http://localhost:8767/_Museum/web/index.html`.
3. **Explore** (walk yourself), **Start guided tour** (be walked from work to work, through the
   doors), or **Resume last visit** (the scene and spot you last stood in, remembered by the browser).

Three.js r160 is vendored in `web/vendor/three/` (MIT), with the Draco decoder the Smithsonian scans
need, so the viewer needs no network access beyond its own files. The GitHub Pages deploy
(`.github/workflows/deploy-pages.yml`, on every push to `main`) publishes the project root; the
museum is live at `<pages-url>/_Museum/web/`.

### Controls

| Input | Action |
|---|---|
| `W A S D` / arrows | walk |
| mouse | look (click the view to capture the mouse; click-drag if the browser blocks Pointer Lock) |
| click / `E` | go through the door under the crosshair · read the work or sculpture under it |
| `M` | floor plan of the scene: click a door to go through it, a room to go there; the corner minimap is always on |
| `Tab` | "Go to": wing → room → artist → works, with a filter; teleports into the right room |
| `Space` `N` `P` | guided tour: pause / resume, next work, previous work |
| `Esc` | close panels, end the tour, release the mouse |
| `?` / `H` | help |
| touch | left half of the screen: joystick to walk · right half: drag to look · tap a work or door |
| controller | Xbox or any "standard"-mapped gamepad (Bluetooth / USB): left stick or D-pad walk · right stick look · `A` read / go through the door (Explore on the start screen) · `B` back · `X` map · `Y` go to · `LB` `RB` previous / next · Menu help · View tour |

The placard shows the work's real size ("379 cm × 454 cm · shown at actual size", or "shown at 1:2"
for the few works too big for a wall), previous / next work buttons and, under "Suggested next",
**Guide me** (a glowing trail to the door, continued in the next scene) and **Teleport**.

### URL flags

`?room=<room-id>` and `?work=<work-id>` open the museum in that room (skipping the entrance screen);
`?resume=1` restores the last saved scene and position; `?wing=0` leaves the People wing out (its doors
and rooms). Look-dev flags: `?classic` (no tone mapping / bloom / shadows), `?exposure=`, `?bloom=`,
`?env=`, `?lights=`, `?shadows=0`, `?debug` (overlay), `?view=<name>` (a camera from the layout's
`views`, e.g. `hub_west`, `gallery-c_door`), `?tourDwell=<s>`, `?test` (no animation loop; the harness
drives the page).

## Pipeline

```
Art-Talk-main/artists/*.md + data/image-credits.json      _Site/data/notes-person.json (+ era, region)
        │                                                          │  people_entries.py
        └───────────────┬──────────────────────────────────────────┘
                        │  build_manifest.py
                        │    ├─ build_dimensions.py → data/work-dimensions.json   real-world sizes (cached)
                        │    └─ build_layout.py     → data/museum-layout.json     hub + 16 room scenes, lint
                        ▼
data/museum-manifest.json   rooms (hub + galleries), wings, artists, works with `dims`
data/museum-layout.json     per scene: boxes, lathes, mouldings, doors, hangs, frames, fixtures, props, views
assets/models.json  ── fetch_models.py ──▶ assets/models/<id>/   CC0 sculptures and props (26 MB)
        ▼
web/js/scenes.js  builds one scene at a time with procroom.js (geometry, materials, hangs, frames,
                  fixtures, pedestals, texture streaming), doors.js (themed doors), models.js (GLB cache)
```

The **manifest is the contract** for everything textual (rooms, wings, works, placards, the rewrite
layer); the **layout is the contract** for everything spatial. Both are written by
`python3 _Museum/build_manifest.py` (add `--lint` to check without writing). The viewer knows nothing
about Blender any more: `blender/scripts/` is kept as the spec of the naming contract it still follows.

### Real-world sizes (`build_dimensions.py`)

Every work gets a height and width in metres, in this order of preference (kept per work in
`work-dimensions.json` as `source`): the "H × W cm" in the Art-Talk `medium` string (146 works,
checked against the image aspect); the Wikidata item the Commons image belongs to (`P18`) or a title
search whose hit has the artist as creator (`P2048`/`P2049`); else a typical size for the type of thing
(film still, woodblock print, manuscript folio, hanging scroll, architecture photograph, portrait
photograph...). Works larger than 3.8 × 4.8 m are hung at 1:N and the placard says so. The cache is
committed; `python3 _Museum/build_dimensions.py` refreshes only what is missing (`--offline` never
fetches; `--refresh [ids]` re-resolves; an entry with `"lock": true` is a hand correction).

### Layout (`build_layout.py`)

Every scene has its own origin. A room spans `x ∈ [-W/2, W/2]`, `y ∈ [0, D]` (Blender metres,
z up; `web/js/coords.js` converts) with the hall door centred on the south wall; `DOOR-<prev>` and
`DOOR-<next>` on the west and east walls lead to the neighbouring rooms in time, so the tour never has
to return to the hall. Works are packed on the W, N and E walls by a salon-grid packer: chronological
order across the walls, first-fit-decreasing rows within a wall (the largest works at eye level, rows
above bottom-aligned on a shared line), gaps equalised, a room grows by 2 m steps when its works need
more wall and only then are they scaled down (never below 0.7). Frames are chosen by room era and work
type (gilt ornate / simple, dark wood, black lacquer, thin metal, rods for scrolls). Fixtures are
`FX-` records the light pool reads (a chandelier, sconces by the doors, picture lights over large works,
a laylight). The hub is an 80 m hall with the entrance rotunda at the west end and an apse at the east;
Art-Talk doors along the south wall, People-wing doors along the north, both in order of time, with
pedestal bays between them. `lint()` refuses a layout with overlapping works, works outside
0.45–5.6 m, blocked doors, colliders named like decoration, or props without a model.

### Models (`fetch_models.py`, `assets/models.json`)

Museums' open-access 3D scans are the sculptures. Two sources are fetched automatically, both CC0:
the **Smithsonian 3D API** (Voyager packages on `3d-api.si.edu`; the package ids come from the
Smithsonian Open Access metadata dumps, records whose media type is `3d_voyager`) and **Poly Haven**
(`api.polyhaven.com`, photoscanned busts, animal heads, chandeliers, vases, a bench). A third kind,
`"source": "local"`, is a file dropped in by hand (for example a Scan the World scan converted to GLB;
those are CC BY-NC and are not fetched). `python3 _Museum/fetch_models.py` downloads what is listed,
records each model's bounding box and writes the Models section of `assets/CREDITS.md`; `--check`
verifies the files exist. `target_h` is the height a model is shown at (its real size unless noted).
`build_layout.PLACEMENTS` says where each one stands (hub bays are era-matched: Shang bronzes by the
Bronze Age door, Northern Qi Buddhas by Medieval, Kangxi vases by Baroque, Houdon's Washington by
Romanticism, Edmonia Lewis and the presidential busts along the Industrial bays).

### Web viewer modules (`web/js/`)

| Module | Role |
|---|---|
| `main.js` | loads manifest + layout, wires every module, `simulate()`/`frame()` loop, `window.museumDebug` |
| `scenes.js` | the scene manager: builds/disposes one scene at a time, refills the shared mesh lists, re-anchors lights, HUD and picking |
| `procroom.js` | builds a scene from its layout record: boxes with world-space UVs, lathes (rotunda drum, dome, apse), mitred profile-swept mouldings, art planes, bevelled frames, fixtures, pedestals, models, texture streaming |
| `doors.js` | door leaves (`DOOR-<room>`), era-themed surrounds (post-and-lintel, pointed / round arch, Doric and broken pediments, cast-iron fanlight, Art Deco, steel portal), plaques |
| `matlib.js` | PBR material library from `assets/textures/<set>/`, world-space tiling |
| `models.js` | GLTF + Draco loader, cache and reference-counted clones for `assets/models/` |
| `coords.js` | `blenderToThree` and friends: the only place coordinates are converted |
| `controls.js` | first-person movement, collision (rays at feet + 1.2 m), floor following, `teleport` |
| `interactions.js` | centre-ray picking of works, doors and sculptures; look prompt; the placard (size line, rewrite overlay, credits, prev/next, suggestions) |
| `waypoints.js` | room-graph BFS, per-scene route segments, the glowing trail (continued after a switch) |
| `hud.js` | minimap and large floor plan of the current scene; labelled doors; teleports |
| `navigate.js` | the "Go to" panel |
| `tour.js` | guided tour: walks a scene's segment, goes through the door, continues |
| `titlecard.js` | the room title card shown on entry |
| `ui.js`, `touch.js`, `gamepad.js`, `persist.js` | key router / help / buttons, virtual joystick, gamepad polling, last scene + position in localStorage |
| `render.js`, `lights.js`, `materials.js`, `debug.js` | AgX + composer, the constant 8-light pool re-anchored per scene, material patches, `?debug` overlay |

Mesh-name classification: `ART-<slug>__<id>` = clickable work; `DOOR-<room>` = clickable door (it
also collides); `SCULPT-<model>` = clickable sculpture (an invisible proxy); a name containing `wall`
or `outer` collides; `floor`, `landing` or `step` is walkable; `GEO-<scene>_floor*` defines the geo
room; `FX-*` empties carry `userData.fx_*` for the light pool. Decorative pieces avoid the structural
words (work ids can contain them, so nothing is named after a work id).

## Testing: the browser walk-through harness

`tools/walk_test.mjs` drives the real viewer in headless Chromium (software WebGL is enough). It runs
the Python lint first, then loads the hub, walks the hall, and for **every door** looks at it, clicks
it, checks the room built with exactly the manifest's works, the title card, the floor, and comes back
through the hall door. It reads placards (real size, 1:N note), checks hung sizes against
`work-dimensions.json`, that no works overlap, the look prompt and keys, a map click through a door,
the go-to panel, prev/next across rooms, the People placards, a guide trail into another scene, a tour
that walks through a door, deep links, resume, touch, PBR world tiling, the fixture-driven light pool,
themed doors with plaques, model loading and the sculpture placard, draw-call/triangle budgets, GPU
memory returning after switches, `?wing=0`, `?classic`, and console errors. It screenshots the
standard views (`layout.scenes[*].views`) and builds a contact sheet.

```
node _Museum/tools/walk_test.mjs [--no-shots] [--grep name[,name]] [--out DIR] [--list]
```

Output (git-ignored): `_Museum/tools/out/report.json`, `view_*.png`, `feature_*.png`, `contact_sheet.png`.
Playwright and Chromium are found at their usual places (`CHROMIUM=` overrides the browser).

## Adding things

- **A room**: add it to `ROOM_PLAN` in `build_manifest.py` (Art-Talk) or `people_entries.ROOM_PLAN`
  (People), a style in `build_layout.ROOM_STYLE` (door theme, wall paint, frames), run
  `build_manifest.py`. The hub grows a door for it automatically.
- **A model**: add an entry to `assets/models.json` (Smithsonian package id, Poly Haven asset id, or a
  local file), run `fetch_models.py`, place it in `build_layout.PLACEMENTS` (a hub bay, `hub:rotunda`,
  `hub:apse`, or a room id) or `WALL_RELIEFS`, run `build_manifest.py`.
- **A size correction**: edit the work's entry in `data/work-dimensions.json` and add `"lock": true`.

## Placard rewrite layer

Placard descriptions are shown as an AI rewrite in one of the creative-writing tool's four voices
(`data/placard-rewrite.json`, labelled on the placard). It is an overlay: `museum-manifest.json` keeps
the original text. It lives in `_Rewrite/` (see its README); `build_manifest.py` republishes it after
each build and prints how many placards are waiting for the `chronicle-rewriter` agent.

## Known limitations

- Sizes for works without a stated size and without a Wikidata match are typical sizes for their type
  (the placard says "typical size"); `build_dimensions.py` keeps trying those online on each run.
- The rooms' salon rows are sized by the packer; a room with very large works (Gallery C: the Night
  Watch, Las Meninas) grows to 26 × 26 m and can feel sparse in the middle.
- Suggested-next is still the flat chronological order.
