# The Chronicle Museum

A walkable 3D museum built in Blender and exported to a Three.js web viewer.
The first wing (**Art-Talk**: 53 artists, 299 works, 973–1968) is built and
populated. This doc explains how the pipeline works, what the walkthrough offers,
how it is tested, and how to add the next wing without rebuilding anything that
already exists.

## How to view it

1. Start a static file server rooted at the **project root** (not `_Museum/`
   itself — the web app reads `../../Art-Talk-main/` and `../../_Site/` for
   full-resolution placard images). The repo already has a launch config for this:
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
the entrance screen); `?resume=1` restores the last saved position. Look-dev
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

## Adding the next wing

Two routes. **With Blender** (the original recipe): build the rooms with
`room_shell()` / `wall_run()` from the `museum_lib` text block, hang works with
`build_gallery_exhibits()`, add the rooms and doors to `ROOMS` in
`build_manifest.py`, re-export. **Without Blender** (what the viewer supports
now): generate the rooms and hangs as data and let `procgeo.js` build them — the
Earth Chronicle People wing is the worked example; see the "People wing" section
below once it lands. In both cases the manifest gets the new rooms (`position`,
`doors`, `connects_to`) and artist-shaped entries whose works have globally
unique ids, and the viewer needs no code changes for placards, minimap, go-to or
the tour: they iterate the manifest.

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
