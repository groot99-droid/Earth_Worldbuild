# Chronicle Museum v2 — build contract (every agent reads this first)

Goal: Phase 0–2 of the Hyper-Realism Pass. Make the museum read as "Louvre": refined neoclassical galleries and
lavish gilded hero spaces (Rotunda, Grand Staircase). Every artwork keeps its hang position.
The deliverable is the **web viewer** (Three.js r160). Blender produces geometry, materials and FX metadata; lights do not
travel through glTF.

Companion files (same folder): `rooms_v2.json` (room table: bounds, wall centre-lines, doors, exterior spans, style, slice),
`framings.json` (standard cameras), `scene_inventory_v1.json` (every v1 object: world AABB, materials; ART-* positions),
`museum_lib.py` (v1 library, for reference only), `V2_HANDOFF.md` (history).

## 0. Paths, tools, run model

- Project: `C:\Users\utopi\OneDrive\Desktop\Earth _WorldBuilding\_Museum` (below: `M/`). Scripts: `M/blender/scripts/`.
- Blender 5.2.1: `"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"`. **Run it headless only**:
  `blender -b <file.blend> --python <script.py> -- <args>` (or `--python-expr`). Never use the Blender GUI/MCP socket.
  EEVEE renders headless (~40 s per frame incl. shader compile). Blender's Python has numpy but **not** PIL.
- Desktop Python with PIL + numpy: `M/../_RAG/.venv/Scripts/python.exe`. There is no `node` on PATH.
- Import v2 modules in Blender with `sys.path.insert(0, SCRIPTS_DIR)` then `import museum_lib_v2 as L` (use `importlib.reload`
  when iterating). Modules are plain `.py` files; no bpy text blocks.
- **Only the integration stage writes `M/blender/museum.blend`.** Module agents copy the pristine snapshot
  `M/blender/snapshots/museum_stage0_v1.blend` to their own scratch folder and work there. Dev renders go to
  `M/blender/renders/dev/<module>/`; baseline renders go to `M/blender/renders/baseline/`; integration renders go to
  `M/blender/renders/v2/`.
- Never edit v1 files: `museum_lib.py`, `scene_inventory_v1.json`, `rooms_v2.json`, `framings.json`, `snapshots/*`,
  `export/museum.gltf`/`museum.bin`, `export/_v1_backup/*`. If a companion file is wrong, say so in your report instead.
- Web files other sessions also edit: `web/index.html`, `web/css/museum.css`, `web/js/interactions.js`, `README.md`.
  **Do not modify them.** `web/js/main.js`, `controls.js` and `waypoints.js`: targeted Edit calls only, no full rewrites.

## 1. Coordinates and units

Blender Z-up metres: x east, y north, z up. three.js = `(x, z, -y)`. Manifest positions are Blender coords (convert with
`blenderToThree`). All rooms are 7 m tall except `stairhall` (14 m). Wall thickness 0.4; `rooms_v2.json` gives wall
**centre-lines** (the interior face is 0.2 m toward the room centre). Rotunda: centre (0,0), outer radius 7.0,
v1 inner vertex radius 6.6 (16-gon). Art planes (`ART-*`) sit 0.25 m from the wall **centre-line**, i.e. only
0.05 m proud of the interior face (e.g. Gallery A north wall centre y=17, face y=16.8, art plane y=16.75). So wall-mounted
trim thicker than 0.05 m that passes behind a painting would poke through it: skirting (below the art) is fine; a picture
rail at 4.0 m is fine; anything at 0.74–2.66 m on an art wall is not. Take real art positions from `scene_inventory_v1.json`.
Picture frames must wrap the canvas edge (they may extend 0.05 m back to the wall face and ~0.04 m forward).

## 2. Naming rules (the viewer classifies meshes by substring — case-sensitive, lowercase)

| substring in object name | viewer behaviour |
|---|---|
| `ART-` prefix | clickable painting. **Never** rename, move, merge, re-material or delete. Must stay exactly 299. |
| `wall` or `outer` | collision (horizontal rays, currently at absolute y=1.2; being changed to feet+1.2) |
| `floor`, `landing` or `step` | floor-follow (downward ray) |

- Every new object must be named `GEO-<room>_<part>[_<n>]`, or `FX-<room>_<type>_<n>` for fixture empties.
  `<room>` is the rooms_v2 id (`rotunda`, `gallery_a`, `spine1`, …).
- New decorative geometry must **not** contain `wall`, `outer`, `floor`, `landing` or `step` (watch out for words like
  "footstep" and "flooring"). Use `crown_`, `cornice_`, `base_`, `dado_`, `wainscot_`, `pilaster_`, `coffer_`, `rosette_`,
  `inlay_`, `arch_`, `architrave_`, `glaze_`, `sash_`, `sill_`, `sconce_`, `pendant_`, `chandelier_`, `piclight_`,
  `frame_`, `godray_`, `sunpatch_`, `laylight_`, `dome_`.
- Regenerated structural pieces **must keep** their class word: walls `GEO-<room>_wall<S>_v2_<n>` (S = N/S/E/W),
  rotunda shell `GEO-rotunda_outer_v2`, floors `GEO-<room>_floor_v2`.
- Full-height glass that a player could otherwise walk through (sill < 1.3 m above the room floor) must contain `wall`,
  e.g. `GEO-spine1_wallS_glaze_3`. Clerestory glass (sill ≥ 1.3 m) must not, e.g. `GEO-gallery_a_glaze_n2`.
- Door gaps must stay passable: a horizontal ray at room z0+1.2 through every door centre must not hit any
  `wall`/`outer` mesh. Every window opening must be blocked at z0+1.2 if its sill is below 1.3 m.
- Pre-existing v1 names are not renamed. v1 objects replaced by v2 are *retired* (see §3), never deleted.

## 3. Idempotency, tagging, retirement (museum_lib_v2)

- Every generated object gets `obj["gen_tag"] = "<stage>:<room>"` (e.g. `"trim:gallery_a"`), plus `obj["v2"] = 1`.
- `clear_generated(prefix)` deletes all objects whose `gen_tag` starts with `prefix` (plus orphaned meshes); each builder
  calls it first, so re-running is safe.
- `retire_v1(names)` moves v1 objects into the collection `_retired_v1` (excluded from the view layer, hidden for render,
  skipped by export) and records `obj["retired_by"] = "<stage>:<room>"`. `restore_v1(prefix)` undoes it. Never
  `bpy.data.objects.remove` a v1 object.
- New objects go into the room's v1 collection (from rooms_v2 `collection`) inside a child collection `<Collection>_v2`.

## 4. Core API (museum_lib_v2.py) — use these, don't re-invent them

Prefer bmesh / `bpy.data` construction (no operators, no selection state) for speed and determinism.
- `SCRIPTS_DIR, M_DIR, ROOMS, room(room_id), FRAMINGS`
- `tag(obj, stage, room_id)`, `clear_generated(prefix)`, `retire_v1(names_or_objs, by)`, `restore_v1(prefix)`
- `room_coll(room_id)` → the `<Collection>_v2` collection
- `mesh_object(name, verts, faces, coll, material=None, uvs=None, smooth=False)` → obj
- `box_object(name, center, size, coll, material=None)`; `join_objects(objs, name)` (for generated pieces only)
- `sweep_profile(name, profile2d, path, coll, material, closed=False, miter=True, up=(0,0,1))`:
  `profile2d` = list of (u, v): u = offset **outward from the wall face into the room** (m), v = height offset (m).
  `path` = list of 3-D points along the wall face at the profile base, ordered so the room lies to the **left** of
  travel when seen from above (counter-clockwise around the room interior). Corners are mitered. Returns obj.
- `lathe(name, profile_rz, segments, coll, material, center=(0,0,0), angle0=0, angle1=2π)` for chandeliers, balusters,
  rosettes, stanchions and domes.
- `arc_points(center, radius, a0, a1, n, plane='xz'|'yz'|'xy')`
- `apply_world_uv(obj, mode='box'|'cyl', cyl_center=None, tile_m=None)`: writes UV map `UVMap` (index 0) = world metres
  divided by the tile size (the `tile_m` argument, else the face material's custom prop `tile_m`, else 1.0). Box mode projects
  each face on its dominant axis; cyl mode uses u = arc length / tile, v = z / tile. No KHR_texture_transform is needed.
- `add_lightmap_uv(obj)` → UV map `LightmapUV` (index 1) via Smart UV Project (Phase 4; may be a stub now).
- `fx_empty(name, location, fx_type, color_hex, intensity, distance=0, shadow=0, room_id=None, extra=None)` → empty with
  custom props (see §6). Parented to nothing; located in world coords.
- `get_material(slot)` → `bpy.data.materials["MAT-v2_<slot>"]`, created on first use as a flat Principled material with
  the §5 fallback factors (the materials module later upgrades the same datablock in place with textures).
- `lint(report_path=None)` → dict: ART count/unmerged/unchanged transforms vs inventory, naming-trap violations,
  door-passability and window-blocking rays (Blender `scene.ray_cast` against wall/outer meshes only), tri counts per room, objects
  missing `gen_tag` in v2 collections. Returns ok=False on any hard failure.
- `look_at_camera(framing_name)` and `render_framing(name, out_png, res=(1280,720), samples=32, engine='BLENDER_EEVEE')`
  using framings.json. It must not leave a changed active camera or resolution in saved files, and must never save.
- `save_stage(n, label)` → saves `museum.blend` and copies it to `snapshots/museum_stage<n>_<label>.blend` (integration only).

## 5. Materials (`MAT-v2_<slot>`; custom props `tile_m`, `slot`)

Textures are packed **per texture set** (not per slot) so several slots share one image: sets = `parquet`, `marble`,
`plaster`, `metal`. Files: `M/assets/textures/v2_<set>_albedo.jpg` (sRGB), `v2_<set>_normal.jpg` (OpenGL +Y, Non-Color),
`v2_<set>_orm.jpg` (R = AO, G = roughness, B = metal, Non-Color). Blender image datablocks use the same names, so the
exported files keep their `v2_` names. Sources live in `M/assets/textures_src/`. `M/assets/texture_map.json` (owned by
`tools/pack_textures.py`) defines sets, resolutions and placeholder settings. `M/assets/texture_downloads.json` (owned by
the orchestrator) lists real downloaded CC0 sources per set and **takes priority** when present. `tools/pack_textures.py`
builds every set from downloads when available, else from a seamless procedural placeholder, and is safe to re-run.
Tints and variants use `baseColorFactor` (Mix Multiply with the texture) so one image serves several materials.

| slot | used for | texture set / res | tile_m | fallback base colour (linear) | rough | metal |
|---|---|---|---|---|---|---|
| parquet | gallery & spine floors | parquet 2048 | 2.0 | .36 .22 .12 | .35 | 0 |
| marble_white | rotunda floor field, hero wainscot, stair treads | marble 2048 | 2.0 | .88 .86 .82 | .18 | 0 |
| marble_dark | inlays, hero plinths, bases | marble (tint) | 2.0 | .10 .09 .085 | .2 | 0 |
| marble_stair | stairs | marble (tint) | 2.0 | .80 .76 .68 | .25 | 0 |
| plaster_wall | walls | plaster 1024 | 3.0 | .86 .82 .72 | .6 | 0 |
| plaster_ceiling | ceilings, coffers, cornice fields, dome | plaster (tint) | 3.0 | .93 .91 .87 | .65 | 0 |
| painted_trim | refined mouldings, window casings | plaster (tint) | 1.0 | .90 .88 .82 | .45 | 0 |
| gilt | hero trim, capitals, frames, rosettes | metal 1024 | 0.5 | 1.0 .78 .34 | .28 | 1 |
| brass | fixtures, picture lights, stanchions | metal (tint) | 0.5 | .90 .70 .40 | .35 | 1 |
| window_frame | sashes, mullions | metal (tint) | 1.0 | .22 .18 .14 | .5 | .6 |
| glass | glazing (alpha blend, no transmission) | — | — | .9 .95 1.0, alpha .12 | .05 | 0 |
| crystal | chandelier drops | — | — | .95 .97 1.0, alpha .35 | .02 | 0 |
| candle | candle flames / bulbs (emissive strength 6–12) | — | — | emissive 1 .78 .5 | — | — |
| laylight | laylight glazing (emissive strength ~2) | — | — | emissive 1 .97 .9 | — | — |
| godray | additive beams / floor sun patches | — | — | emissive 1 .85 .6, strength ~0.6 | — | — |
| exterior_ground | ground plane outside | — | 4.0 | .20 .22 .16 | .9 | 0 |

The viewer patches materials by name (§7), so keep these names exact. v1 materials (`MAT-trim_gold`, …) stay on
un-upgraded rooms.

## 6. Fixture metadata (FX-* empties, exported via `export_extras=True` → three.js `userData`)

Custom props: `fx_type` ∈ {chandelier, sconce, pendant, picture_light, laylight, sun, oculus}; `fx_color` "#rrggbb";
`fx_intensity` float in **three.js physical units** (candela for point/spot, lux for directional/sun); `fx_distance` (m, 0 means
infinite); `fx_shadow` 0/1; `fx_room` (rooms_v2 id); optional `fx_dir_three` = [x,y,z] (a unit direction **already in
three.js coords**) for sun/spot; optional `fx_size` [w,h] for laylights. Vector props are always pre-converted and use
the `_three` suffix. Position comes from the empty's (exporter-converted) node transform.
Suggested defaults: chandelier 350 cd / 14 m / shadow 1; sconce 25 cd / 6 m; pendant 60 cd / 9 m;
picture_light 8 cd / 2.5 m (a spot pointing at the canvas, `fx_dir_three` set); sun 3.5 lux, warm #ffc987, golden hour
(elevation ~12°, azimuth chosen so light enters the slice windows), shadow 1.

## 7. Web viewer contract (Phase 1)

- Model URL: default stays `../export/museum.gltf` (v1) until the user's review gate; `?v2` loads
  `../export/museum_v2.gltf`, with a console warning and a fallback to v1 if it is missing.
- New modules: `web/js/render.js` (EffectComposer with a multisampled HalfFloat target, RenderPass, UnrealBloomPass that only
  blooms emissive values > 1, OutputPass; resize), `web/js/lights.js` (light pool: a constant set of ≤ 8 lights: 1 hemisphere fill,
  1 shadow-casting DirectionalLight for sun/oculus fitted to the active area, 1 chandelier PointLight, and pooled
  PointLights re-parked on the nearest FX empties (distance-based, same level ±3 m, hysteresis, re-evaluated ≤ 4×/s);
  a manifest-based fallback when the model has no FX-* empties),
  `web/js/materials.js` (patches by name: gilt|trim_gold → metalness 1, roughness ~.28, envMapIntensity ~1.6;
  brass → metal 1, rough .35; glass|glaze|crystal → transparent alpha-blend, depthWrite false, no transmission;
  godray|sunpatch → MeshBasicMaterial additive, depthWrite false; ART → envMapIntensity ~.35; all textures anisotropy
  = max; castShadow/receiveShadow on GEO-*; ART receive only), `web/js/debug.js` (`?debug` overlay: fps, draw calls,
  triangles, textures, geometries, programs, camera position in **Blender** coords, nearest room; `?view=<framing>`
  places the camera at a framings.json view on load; exposes `window.museumDebug.renderer/pipeline/lights`).
- main.js: `renderer.toneMapping = THREE.AgXToneMapping`, exposure 1 (`?exposure=` overrides), shadowMap enabled
  (PCFSoftShadowMap), `scene.environment` = PMREM of `RoomEnvironment` (per-room baked probes later),
  `scene.background` = equirect `../export/sky_v2.jpg` if present else a warm dark colour; render through the
  pipeline. Keep the substring mesh classification and `window.museumDebug` keys backward-compatible.
- framings.json lives in `blender/scripts/`; the viewer may fetch it from `../blender/scripts/framings.json`.

## 8. Styles

- **hero** (rotunda, stairhall): marble floor with a dark-marble inlay (compass rosette in the rotunda); dark-marble plinth
  0.30 m; marble wainscot to a gilt-edged dado at 0.95 m; giant-order pilasters (base, shaft, gilt capital) carrying a
  full entablature (architrave, frieze, gilt-dentilled cornice) at the wall head; arched grand doors with gilt archivolts;
  coffered dome with gilt rosettes and oculus; crystal chandelier; brass-and-crystal sconces.
- **refined** (galleries, spines, future wing): parquet floor; painted skirting 0.28 m with a thin gilt fillet;
  **no dado or wainscot in galleries** (art hangs from ~0.74 m); a picture rail at 4.0 m (gilt edge); a clerestory band
  4.3–6.4 m with arched windows; a deep cornice/crown 6.55–7.0 m; laylight in the gallery ceiling within a coved,
  coffered border; door architraves with an entablature (pediment only on grand doors). Spines: painted wainscot panels to a dado at 0.95 m,
  pilasters between window bays, coffered flat ceiling with flush pendants, full-height arched windows on exterior
  spans (their glass named with `wall`).
- Art rule: no vertical element (pilaster, sconce, window, panel moulding) may overlap any `ART-*` footprint on the
  wall below the picture rail (0.1 m margin). Horizontal runs (skirting) may pass behind art.
- Windows: clerestory sill 4.3, head 6.4 (semicircular head), width ~1.4, bays evenly spaced on exterior spans;
  frame, mullion and transom, stone sill, glass. Full-height (spines/stair hall/rotunda drum): sill ≥ 0.6, head per room;
  rotunda drum windows sill 4.4, head 6.3. Outside: a sky backdrop (three `scene.background` = `export/sky_v2.jpg`,
  rendered from Blender's Sky Texture at golden hour, ~0.3 MB) plus `GEO-exterior_ground`. God-rays: additive gradient
  beam meshes from windows along the sun direction plus a window-shaped floor patch; a real shadow-mapped sun only in the
  rotunda and stair hall.

## 9. Budgets

Scene total ≤ 1.5 M triangles; chandelier ≤ 30 k; per-room trim ≤ 150 k; picture frames ≤ 400 tris each;
export folder (what the browser downloads for `?v2`) ≤ 100 MB, target ~60 MB. Art textures ≤ 900 px (the export must
re-apply the in-memory resize: museum.blend references full-resolution originals). Paintings stay 299 separate meshes.

## 10. Phase 2 vertical slice

Rooms: `rotunda` (all), `gallery_a` (all), `spine1` restricted to x ∈ [7, 30] for trim, windows and fixtures (materials may
cover the whole spine1 slab objects). Other rooms stay v1 until the user's review gate. Stage order in `build_v2.py`:
`materials → windows(+exterior) → trim(+ceilings, dome, inlays, architraves) → fixtures(+frames, FX, sun effects) → lint`,
with snapshot `museum_stage<n>_<label>.blend` after each stage. `export_v2.py` loads the saved blend, never saves, excludes
`_retired_v1`/cameras/lights, re-applies the ≤900 px art resize in memory, and exports GLTF_SEPARATE with `export_extras=True`
to `M/export/museum_v2.gltf` (image files in the same folder; v2 textures keep their `v2_` names). It then prints a size and
`extensionsUsed` report.
