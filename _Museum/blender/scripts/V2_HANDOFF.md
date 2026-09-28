# Hyper-Realism Pass v2: handoff (updated 2026-09-28 09:05)

The plan: the pasted "Hyper-Realism Pass — Chronicle Museum (v2)" (Phases 0–5, with a user review gate after Phase 2).
**The agent contract, `V2_CONTRACT.md` (same folder), is the spec.** Read it first. This file records state and next steps.

## Why we stopped
The build workflow (`museum-v2-build`, run `wf_1d65d52f-1df`) ran 02:08–08:57 on 2026-09-28 and was stopped at the user's
request. Only the baseline agent finished. The core-lib, layout, texture-pack and web-renderer agents died repeatedly
("API Error: Connection lost mid-response"; the machine also slept from 02:29 to 08:31). The workflow restarted each of them
**from scratch** (13 agent starts), so long-thinking agents never finished. Nothing was integrated, `museum.blend` was **not
modified**, and there is no `museum_v2.gltf` yet.
**Lesson for the retry:** use smaller agents that write their file early and incrementally (a skeleton first, then fill it in),
run fewer at once, and make each prompt say "if the file already exists, continue it; don't restart".
The script is kept at
`C:\Users\utopi\.claude\projects\C--Users-utopi-OneDrive-Desktop-Earth--WorldBuilding--Museum\93f317bc-0195-44c0-8de7-8472e0cdc052\workflows\scripts\museum-v2-build-wf_1d65d52f-1df.js`.
Resuming with `resumeFromRunId` only replays the cached baseline result, so edit the prompts per "Next steps" first.

## Done
**Phase 0 infrastructure (orchestrator)**
- `museum_lib.py`: the v1 library dumped out of the .blend's text block.
- `tools/dump_inventory.py` produces `scene_inventory_v1.json` (484 objects, world AABBs, materials, lights, ART positions).
- `rooms_v2.json`: room table (bounds, wall centre-lines, doors, exterior spans, hero/refined style, slice).
- `framings.json`: 9 check cameras. **fov_deg corrected 2026-09-28** to the 16:9 value, 2·atan(10.125/lens).
- `V2_CONTRACT.md`: naming traps, APIs, material slots and texture sets, FX metadata, web contract, styles, budgets, stage order.
- Backups: `snapshots/museum_stage0_v1.blend` (identical to the current `museum.blend`), `export/_v1_backup/museum.gltf|bin`,
  `web/js/_v1_backup/main.js` (the v1 main.js, reconstructed from the session transcript).

**Textures (user approved the downloads 2026-09-28)**
- CC0 scans are in `assets/textures_src/`: Poly Haven herringbone_parquet (2K diff/nor_gl/arm, 3.4 m tile); ambientCG Marble012 (2K),
  PaintedPlaster017 (1K, 1024×512, so `square_mode: stack`) and Metal048A (1K gold, `albedo_mode: neutralize`). Logged in `assets/CREDITS.md`.
- `assets/texture_downloads.json` (orchestrator-owned) maps each set to its source files.
- `tools/pack_textures.py` (67 KB, written by the texture-pack agent) produced `assets/textures/v2_{parquet,marble,plaster,metal}_{albedo,normal,orm}.jpg`
  and `assets/texture_map.json` (last run 08:32). Previews are in `renders/dev/textures/`. **Unverified:** the agent died before
  reporting. Check that its last run used the downloads for all four sets, honoured stack/neutralize, has no seams, and totals ≤ 12 MB.

**Phase 0 baseline renders (done, verified by the agent)**
- `tools/render_framings.py`: in Blender it renders framings (never saves); on desktop Python it builds contact sheets. Usage is in `renders/baseline/_report.json`.
- `renders/baseline/baseline_<name>.png` for all 9 framings (1280×720, EEVEE 64 samples, AgX), plus `_contact_sheet.jpg`.
- `renders/baseline/_suggested/`: better camera positions for rotunda_wide, spine1_west and gallery_a_art (not applied yet; see Next steps).

**Phase 1 web renderer: work in progress, unreviewed but loads**
- New `web/js/render.js` (AgX, PMREM RoomEnvironment, sky_v2.jpg background probe, composer with MSAA HalfFloat target +
  UnrealBloom + OutputPass, `?classic`, `?v2` with fallback), `lights.js` (constant 8-light pool from FX-* empties, with a v1 fallback rig),
  `materials.js` (name-based patches, anisotropy, shadows) and `debug.js` (`?debug` overlay, `?view=<framing>`, museumDebug.setView/renderOnce/measure/probe/tune).
- `main.js` is wired to them. `controls.js` has the collision ray at feet+1.2 (`rayY`); set it back to 1.2 to roll back.
- Smoke test 08:58: `index.html?debug&view=gallery_a_north` loads the v1 model with the new renderer: 299 ART, 47 wall and 13 floor
  meshes, 262 draw calls, 13 programs, and no JS errors apart from the expected 404 probes (museum_v2.gltf, sky_v2.jpg). The look is warm and plausible.
- **Not yet done:** adversarial review, collision walk tests (rotunda→spine, gallery_a door, gallery_f upper floor, stairs),
  a `?classic` A/B check, and exposure/bloom tuning sign-off. debug.js uses `framings.fov_deg`, which is now correct.

## Findings to carry forward
- **Stray default light:** a 1000 W point light named `Light` at (4.08, 1.0, 5.9) in museum.blend makes a hot spot in the rotunda. Retire or delete it in v2.
- **Coplanar slabs z-fight:** `GEO-gallery_f_floor` (z 6.9–7.1) coincides with `gallery_a_ceiling` and `spine1_ceiling`, and `spine2_floor` with `spine1_ceiling`.
  v2 ceilings, laylights and coffers must sit below z 6.9, or the v1 ceilings must be retired.
- The v1 rotunda "ceiling" is `GEO-rotunda_dome_ring1`, a solid disc hiding the oculus. The v2 dome replaces rings 1–3, the oculus rim and the oculus glass.
- **ART images:** the core-lib agent reported that all 299 ART images already meet the ≤900 px limit (Art-Talk sources), which contradicts the older README note. Re-check with a quick count before relying on it; keep `prepare_art_images(900)` as a no-op safety.
- **Light units for Blender companion lights:** point/spot W = 4π·cd; sun strength = lux; area W = π·cd (per the core-lib agent's probes in `_dev/core/`).
- **Collision:** the v1 ray at absolute y=1.2 made upper floors collide with ground-floor walls (e.g. you couldn't enter gallery_e). The feet+1.2 fix is in the WIP controls.js, untested.
- The rotunda's v1 16-gon doors span two facets; rebuild it as a 64-segment shell (the plan is in the contract).
- Blender stdout is block-buffered when redirected; trust output files and the `RENDER_FRAMINGS_DONE` marker. Host sleep breaks timings.

## Next steps (in order)
1. **Retry the build in smaller pieces**, one or two agents at a time, each writing its file early:
   a. `museum_lib_v2.py` (contract §4) + `tools/test_core.py`. Helpful leftovers are in `blender/_dev/core/` (api_probe.py, units_test.py).
   b. `v2_layout.py` (pure Python; API in the workflow script's LAYOUT prompt) + `tools/test_layout.py` + plan/elevation PNGs.
   c. Verify the pack_textures output (see Textures above).
   d. `v2_materials.py`, `v2_windows.py`, `v2_trim.py`, `v2_fixtures.py` (prompts MATERIALS / WINDOWS / TRIM / FIXTURES in the script),
      each tested on a scratch copy of `snapshots/museum_stage0_v1.blend`.
   e. Integration: `build_v2.py` + `export_v2.py` on the slice (rotunda, gallery_a, spine1 x 7–30), lint, v2 renders at the framings,
      before/after comparison sheets `renders/v2/compare_<name>.jpg`, export `export/museum_v2.gltf`, `V2_STATUS.md`.
2. **Web:** have an adversarial review of the WIP renderer (prompt WEB_REVIEW), fix it, then run the collision tests in the browser (preview config `museum`, port 8767).
3. Optionally adopt the suggested framings (rotunda_wide pos [-4.7,-2.9,1.7] → target [6.6,0,2.9]; spine1_west pos [8.6,-1.6,1.7] → target [28,2.4,2.5];
   gallery_a_art pos [20,13.2,1.7] → target [20,17,1.95]) and re-render those three baselines with render_framings.py `--prefix baseline_`.
4. Final `?v2` browser check, then **show the user the before/after renders** (they asked for this) and pause for the Phase 2 review gate.
5. After approval: Phase 3 rollout to the other rooms, Phase 4 (join per room+material, AO bake), Phase 5 (rope barrier etc.).
