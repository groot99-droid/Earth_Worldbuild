# The Chronicle Museum

A walkable 3D museum built in Blender and exported to a Three.js web viewer.
Two wings are open: **Art-Talk** (53 artists, 299 works, 973–1968, built in
Blender) and **Earth Chronicle People** (203 people, 387 portraits, generated
procedurally in the viewer). This doc explains how the pipeline works, what the
walkthrough offers, how it is tested, and how to add another wing without
rebuilding anything that already exists.

## How to view it

1. Start a static file server rooted at the **project root** (not `_Museum/`
   itself — the web app reads `../../Art-Talk-main/` and `../../_Site/` for
   placard images and portrait textures). The repo already has a launch config for this:
   ```
   python -m http.server 8767
   ```
   (or use the `museum` entry in `.claude/launch.json` via the `run` skill /
   `preview_start` tool).
2. Open `http://localhost:8767/_Museum/web/index.html`.
3. **Explore** (walk yourself), **Start guided tour** (be walked from work to
   work), or **Resume last visit** (where you last stood, remembered by the browser).

Three.js r160 is vendored in `web/vendor/three/` (MIT, `LICENSE` alongside), so the
viewer needs no network access.

The repo's GitHub Pages deploy (`.github/workflows/deploy-pages.yml`, on every
push to `main`) publishes the project root, so the museum is live at
`<pages-url>/_Museum/web/` and the root landing page links to it. The deploy
keeps only `blender/scripts/framings.json` out of the Blender folder, which is
all the viewer reads from it at runtime; everything else the page loads
(`data/`, `export/`, `web/`, `Art-Talk-main/images/`, `_Site/images/`) ships.

### Controls

| Input | Action |
|---|---|
| `W A S D` / arrows | walk |
| mouse | look (click the view to capture the mouse; click-drag if the browser blocks Pointer Lock) |
| click / `E` | read the placard of the work under the crosshair (a prompt names it when one is in reach) |
| `M` | floor plan of the current level: click a room to teleport there; the corner minimap is always on |
| `Tab` | "Go to": wing → room → artist → works, with a filter; teleport in front of a work or draw a guide trail |
| `Space` `N` `P` | guided tour: pause / resume, next work, previous work |
| `Esc` | close panels, end the tour, release the mouse |
| `?` / `H` | help |
| touch | left half of the screen: joystick to walk · right half: drag to look · tap a work to read |

The placard has previous / next work buttons (chronological order) and, under
"Suggested next", **Guide me** (a glowing trail through the doors to that work's
room) and **Teleport**.

### URL flags

`?room=<room-id>` and `?work=<work-id>` open the museum at that place (skipping
the entrance screen); `?resume=1` restores the last saved position; `?wing=0`
leaves the People wing out. Look-dev
flags: `?classic` (v1 look: no tone mapping / bloom / shadows), `?exposure=`,
`?bloom=`, `?env=`, `?lights=`, `?shadows=0`, `?debug` (overlay), `?view=<framing>`
(a camera from `blender/scripts/framings.json`), `?tourDwell=<s>`, `?nopatch`
(skip the procedural mezzanine balcony), `?test` (no animation loop; the harness
drives the page).

## Pipeline architecture

```
source markdown (Art-Talk-main/artists/*.md)
        │  build_manifest.py  (pure Python, no Blender needed)
        ▼
_Museum/data/museum-manifest.json   ← single source of truth: rooms, doors,
        │                             waypoint positions, every artist/work
        │  build_museum.py-style bpy scripts (run via Blender MCP,
        │  see _Museum/blender/museum.blend's "museum_lib" text block)
        ▼
_Museum/blender/museum.blend         ← architecture + materials/lighting +
        │                              299 image-textured exhibit frames
        │  glTF export (GLTF_SEPARATE, images downscaled to 900px first)
        ▼
_Museum/export/museum.gltf + *.jpg
        │  loaded by the web viewer
        ▼
_Museum/web/  (Three.js: movement, raycast placards, waypoint trail, minimap,
               go-to menu, guided tour, procedural geometry)
```

The **manifest is the contract** between Blender and the web app. Everything
the web viewer knows about rooms, doors, and artwork placard text comes from
`museum-manifest.json` — the glTF only supplies geometry/materials, matched
up by mesh name (`ART-{artist-slug}__{work-id}`).

Room records carry `position` (centre) and `doors` (neighbour id → doorway
position); two optional fields refine routing: `spawn` (where a teleport lands
when the centre is not walkable, e.g. the stairwell void) and `through`
(`"<prev>><next>": [points]`, the walkable route across the room between two
neighbours when a straight line through the centre is not one — the mezzanine
uses it for stairs → balcony → upper spine). Rooms with `kind: "spine"` are
corridors: routes pass door to door without visiting their centre.

### Web viewer modules (`web/js/`)

| Module | Role |
|---|---|
| `main.js` | loads manifest + glTF, adds procedural geometry, classifies meshes, wires every module, `simulate()`/`frame()` loop, `window.museumDebug` |
| `coords.js` | `blenderToThree` and friends — the only place coordinates are converted |
| `controls.js` | first-person movement, collision (rays at feet+1.2 m), floor following, look state, `teleport`, `groundY`, test hooks |
| `interactions.js` | centre-ray picking, look prompt, placard (rewrite overlay, credits, prev/next, suggestions) |
| `waypoints.js` | room-graph BFS, `routePoints` (door-to-door routing), the glowing trail |
| `artgeom.js` | art plane centre / facing / viewing spot (works for glTF and procedural planes) |
| `procgeo.js` | Blender-extent box factory for procedural geometry; the mezzanine balcony patch |
| `procwing.js` | the People wing: boxes and portrait planes from `data/people-wing.json`, texture streaming |
| `hud.js` | minimap and large floor plan, room teleports |
| `navigate.js` | the "Go to" panel |
| `tour.js` | guided tour path building and motion |
| `ui.js` | key router, help, blocker buttons, HUD buttons, manifest-driven subtitle |
| `touch.js` | virtual joystick / drag look / tap to read |
| `persist.js` | last position in localStorage |
| `render.js`, `lights.js`, `materials.js`, `debug.js` | the v2 look: AgX + composer, 8-light pool, material patches, `?debug` overlay |

Mesh-name classification (unchanged, see `blender/scripts/V2_CONTRACT.md` §2):
`ART-` prefix = clickable work; a name containing `wall` or `outer` collides;
`floor`, `landing` or `step` is walkable; `GEO-<room>_floor` defines a room for
lights, minimap and room labels. Procedural geometry follows the same rules and
is added under the glTF scene before classification, so nothing downstream knows
the difference.

## Coordinate system gotcha

`museum-manifest.json` positions (room `position`, room `doors`, `spawn`,
`through`) are authored in **Blender's Z-up convention** (`x`, `y` = north/south,
`z` = height), because that's what's natural to write inside `build_manifest.py`
alongside the Blender build script. The glTF export uses `export_yup=True`, which
converts every point to **Three.js's Y-up convention**: `(x, y, z)_blender ->
(x, z, -y)_three`. `web/js/coords.js` exports `blenderToThree()` — **any new code
that reads a manifest position must go through it**, or it will silently place
things in the wrong spot (this bit us once already during this build). The test
harness asserts positions in Blender coordinates for the same reason.

## Testing: the browser walk-through harness

`tools/walk_test.mjs` drives the real viewer in headless Chromium (software WebGL
is enough) and checks what a visitor would notice: it walks through every
manifest door in both directions, into the galleries, up the stairs and around
the balcony, checks that walls block and that upper-floor walls don't block the
ground floor (and vice versa), clicks a painting and reads its placard, exercises
the look prompt, keys, minimap teleport, go-to filter, placard prev/next, the
guided tour (every sampled position must be inside a room), deep links,
resume, and `?classic`. It screenshots the standard framings and each feature
and builds a contact sheet.

```
npm i -g playwright            # once (Chromium via `npx playwright install chromium`)
node _Museum/tools/walk_test.mjs [--no-shots] [--grep name[,name]] [--out DIR] [--list]
```

Output (git-ignored): `_Museum/tools/out/report.json`, `view_*.png`,
`feature_*.png`, `contact_sheet.png`. The page is loaded with `?test` so nothing
animates on its own; the harness advances the simulation with
`museumDebug.step(dt, n)` and renders only for screenshots. Set `CHROMIUM=` to
point at a browser binary if Playwright's default is not installed.

## Procedural geometry

The viewer can add geometry at load time (`procgeo.js`), named by the same
contract as the export. Today that is the **mezzanine balcony**: the v1 export
left the stair hall's upper level as a 1.5 m strip at its east end, so the top
of the stairs never met the upper spine hall; the viewer adds the balcony ring
around the stairwell, gilt balustrades, and closes the stair hall's open west
side. `?nopatch` shows the bare export.

## The Earth Chronicle People wing (procedural, no Blender)

The second wing hangs the vault's people: 203 of them, 387 credited portraits
from `_Site/data/notes-person.json`, in ten era rooms off a 100 m hall that
opens west of the rotunda through the former "future wing" stub (now the
vestibule). It exists as data, not as Blender geometry:

```
_Site/data/notes-person.json (+ notes-era.json, notes-region.json)
        │  build_people_wing.py  (called by build_manifest.py; pure Python)
        ▼
museum-manifest.json  ← rooms (people-spine, people-<era>[-n]), a "people" wing,
        │               one artist-shaped entry per person, one work per image
        │               (ids people--<slug>--<n>, image paths relative to _Site/)
data/people-wing.json ← geometry: every wall/floor/ceiling/trim box and every
        │               hang (position, facing, size), Blender coords
        ▼
web/js/procwing.js    ← builds the meshes at load time under the glTF scene,
                        named by the classification contract; streams portrait
                        thumbnails by room distance (?wing=0 skips the wing)
```

Layout rules (`build_people_wing.py`): rooms alternate north/south of the hall
like the Art-Talk enfilade; each era's people are sorted by birth year and split
into contiguous rooms (Medieval, Early Modern and Industrial have two each);
every person gets one **salon column** — their 1–3 images stacked at 1.7 m, or
1.2/2.5 m, or 0.95/2.15/3.35 m — across the room's three art walls in reading
order (turn left at the door), images ≤ 1.1 m tall and ≤ 1.4 m wide, gaps
0.5–1.2 m. `lint()` fails the build if columns overlap or leave the wall span,
stacks overlap, a door opening is blocked, a room overlaps another (including
the exported building), or a decorative box is named like structure. Room sizes
live in `ROOM_PLAN`; if the vault gains people, widen a room or add one there.

Placards show the person's summary and facts (the rewrite layer lists the 387
new placards as pending; the viewer shows the original text until the
`chronicle-rewriter` agent has done "pending museum"), the caption as the
"medium", era and region on the artist line, and the image credit with the AI
flag when the site used an illustration.

## Adding another wing

Two routes. **With Blender** (the original recipe): build the rooms with
`room_shell()` / `wall_run()` from the `museum_lib` text block, hang works with
`build_gallery_exhibits()`, add the rooms and doors to `ROOMS` in
`build_manifest.py`, re-export. **Without Blender**: follow
`build_people_wing.py` — emit rooms, entries, boxes and hangs as data and let
`procwing.js`/`procgeo.js` build them. In both cases the manifest gets the new
rooms (`position`, `doors`, `connects_to`, a `wing`) and artist-shaped entries
whose works have globally unique ids, plus an entry in `manifest.wings`
(`image_base`, `nouns`, `years`); the viewer needs no code changes for placards,
minimap, go-to or the tour: they iterate the manifest.

## Placard rewrite layer

Placard descriptions are shown as an AI rewrite in one of the creative-writing tool's four voices
(`data/placard-rewrite.json`, labelled on the placard). It is an overlay: `museum-manifest.json` keeps the original text. It lives in
`_Rewrite/` (see its README). `build_manifest.py` republishes it after each build and prints how many placards are waiting;
a new wing's placards are rewritten by the `chronicle-rewriter` agent (`.claude/agents/`) on "pending museum". The web
viewer needs no change for new wings: it looks each work up by id.

## Known limitations / deferred polish

- No gold picture-rail moldings or arched doorway trim yet — the "Louvre"
  read currently comes from proportions + warm lighting + cream/gold palette,
  not applied ornament. The v2 hyper-realism pass (`blender/scripts/V2_*.md`)
  is unfinished: `museum_v2.gltf` and `sky_v2.jpg` do not exist yet, so `?v2`
  falls back to v1.
- Suggested-next logic is a simple flat chronological order (next work, plus
  a jump to the next room's first work when staying in-room) — no
  movement/region-based recommendations yet, though `artist.movements` and
  `artist.region` are already in the manifest if you want to build that.
- The guided tour routes through the manifest's room graph (galleries are
  chained A→B→C→…), so a long jump visits each intermediate gallery's centre;
  consecutive works are neighbours, so the normal tour never notices.
- Texture budget: the 3D exhibit textures are ≤900 px (the Art-Talk sources
  already are); the placard shows the full image from `Art-Talk-main/`.
