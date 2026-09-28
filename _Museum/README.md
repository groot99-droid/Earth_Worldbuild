# The Chronicle Museum

A walkable 3D museum built in Blender and exported to a Three.js web viewer.
The first wing (**Art-Talk**: 53 artists, 299 works, 973–1968) is built and
populated. This doc explains how the pipeline works and how to add the next
wing without rebuilding anything that already exists.

## How to view it

1. Start a static file server rooted at the **project root** (not `_Museum/`
   itself — the web app reads `../../Art-Talk-main/` for full-resolution
   placard images). The repo already has a launch config for this:
   ```
   python -m http.server 8767
   ```
   (or use the `museum` entry in `.claude/launch.json` via the `run` skill /
   `preview_start` tool).
2. Open `http://localhost:8767/_Museum/web/index.html`.
3. Click to enter, WASD/arrows to walk, mouse to look (or click-drag to look,
   if your browser/embed context blocks the Pointer Lock API), click a
   painting to read about it, click a "Suggested next" thumbnail to draw the
   glowing waypoint trail to it.

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
_Museum/web/  (Three.js: movement, raycast placards, waypoint trail)
```

The **manifest is the contract** between Blender and the web app. Everything
the web viewer knows about rooms, doors, and artwork placard text comes from
`museum-manifest.json` — the glTF only supplies geometry/materials, matched
up by mesh name (`ART-{artist-slug}__{work-id}`).

## Coordinate system gotcha

`museum-manifest.json` positions (room `position`, room `doors`) are authored
in **Blender's Z-up convention** (`x`, `y` = north/south, `z` = height),
because that's what's natural to write inside `build_manifest.py` alongside
the Blender build script. The glTF export uses `export_yup=True`, which
converts every point to **Three.js's Y-up convention**: `(x, y, z)_blender ->
(x, z, -y)_three`. Both `_Museum/web/js/main.js` and `waypoints.js` have a
`blenderToThree()` helper for this — **any new code that reads a manifest
position must go through it**, or it will silently place things in the wrong
spot (this bit us once already during this build).

## Adding the next wing (e.g. Earth Chronicle "People")

The Earth Chronicle vault's `_Site/data/notes-person.json` is already shaped
almost exactly like what the manifest needs (`title`, `summary`/description,
`images: [{src, caption, author, license}]`), so the pattern is:

1. **Write a new manifest builder** (or extend `_Museum/build_manifest.py`)
   that parses `_Site/data/notes-<type>.json` the same way `build_manifest.py`
   parses `Art-Talk-main/artists/*.md` — output the same per-entry shape
   (`slug`, `name`/`title`, `room`, `order`, `works`/`images` with
   `id, title, description, image, credit`).
2. **Pick/build a room** for it. The shell already has one stubbed doorway
   reserved for this off the Rotunda's west side (`future-wing-1` in the
   manifest's `rooms` list) — either build out that stub into a real room
   (reuse `room_shell()` / `wall_run()` / `rotunda_shell()` from the
   `museum_lib` text block stored in `museum.blend`, following the same
   pattern as Galleries A–F in this session's build), or extend the enfilade
   further with a new spine segment if the new wing is large.
3. **Add the room + its door(s)** to `ROOMS` in `build_manifest.py` (or the
   new wing's own manifest section), with `position` and `doors` in
   Blender-space coordinates matching whatever you actually build.
4. **Place exhibits**: reuse `build_gallery_exhibits()` from `museum_lib`
   (it takes a room's center/size/wall-sides + an artist-shaped list and
   proportionally hangs every work across the available walls — this is
   exactly what placed all 299 Art-Talk works, no manual placement needed).
5. **Re-export**: rerun the glTF export step (Blender skill: `blender-export`,
   `GLTF_SEPARATE` format, images downscaled first the same way — see the
   `MAX_DIM` resize pass in this session's build before exporting).
6. **No web viewer code changes needed** — `main.js` builds its mesh/manifest
   index generically from whatever `museum-manifest.json` + `museum.gltf`
   contain; a new room with new `ART-*` meshes and manifest entries is picked
   up automatically.

## Placard rewrite layer

Placard descriptions are shown as an AI rewrite in one of the creative-writing tool's four voices
(`data/placard-rewrite.json`, labelled on the placard). It is an overlay: `museum-manifest.json` keeps the original text. It lives in
`_Rewrite/` (see its README). `build_manifest.py` republishes it after each build and prints how many placards are waiting;
a new wing's placards are rewritten by the `chronicle-rewriter` agent (`.claude/agents/`) on "pending museum". The web
viewer needs no change for new wings: it looks each work up by id.

## Known limitations / deferred polish

- The stair hall's upper landing is a solid slab covering the whole stairwell
  footprint (no open double-height void) — purely a visual simplification,
  not a functional issue.
- No gold picture-rail moldings or arched doorway trim yet — the "Louvre"
  read currently comes from proportions + warm lighting + cream/gold palette,
  not applied ornament.
- Suggested-next logic is a simple flat chronological order (next work, plus
  a jump to the next room's first work when staying in-room) — no
  movement/region-based recommendations yet, though `artist.movements` and
  `artist.region` are already in the manifest if you want to build that.
- Texture budget: source images are full-resolution in `Art-Talk-main/`, but
  the 3D exhibit textures are downscaled to 900px max before export (67MB →
  31MB). The 2D placard/suggestion-thumbnail images load the *original*
  full-resolution files directly from `Art-Talk-main/`, so a closer look is
  still possible.
