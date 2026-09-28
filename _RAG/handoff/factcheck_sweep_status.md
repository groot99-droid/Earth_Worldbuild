# Handoff: fact-check + image sweep (stopped 2026-09-28 by the user's request)

Paths are relative to the vault root `C:\Users\utopi\OneDrive\Desktop\Earth _WorldBuilding`. Use `_RAG/.venv/Scripts/python.exe` for every script and set `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` (accented titles crash cp1252). Memory note: `factcheck-image-sweep`.

## Goal and decisions already made by the user
Give every entity/era/region note a cited `fact_checks` list (fixing any wrong or unsupported text found), give every content note at least one credited image, then push to the site (`_Site/scripts/build_site.py --check`; the site is static JS reading `_Site/data/*.json`, no HTML templating).
- Scope: the FULL backlog, not only the newest notes.
- Images: content notes only (person, place, technology, species), zero-image gaps only. Not `07_Sources`, not the under-quota tail (notes with 1 image below their richness ceiling).
- AI fallback allowed when Commons/Smithsonian has nothing: Higgsfield model id `recraft_v4_1`, labelled "AI illustration".

## State at stop
- Fact-check coverage (validator line): see "Final numbers" at the bottom. All 8 `person` gaps are closed (worklist says person 0). Remaining gaps by type when I stopped (recompute, it grows as other sessions add notes): place 20, technology 48, event 38, era 23, species 32, culture 24, region 0 (185 total).
- Batches done (fact_checks applied, plus corrections applied unless noted): 1 (8 People), 2 (40), 3 (40), 4 (39), 5 (40, incl. 13 Places), 6 (40 Places).
- **Batch 6 corrections are NOT applied yet.** Fact-checks for batch 6 are in the vault. The raw workflow result is saved at `_RAG/handoff/sweep_pending/wf_b6_factcheck_result.json`, the discrepancy list at `_RAG/handoff/sweep_pending/corr_b6.json`, and the ready Workflow args at `_RAG/handoff/sweep_pending/corr_b6_args.json`. Next step: run the corrections stage (below) with `file` pointing at `corr_b6.json`.
- Images: every zero-image person/place/technology/species note got a Commons/Wikipedia image, plus one AI illustration (`person/sunni-ali`, job bbcb1373-095f-4e0b-939e-c99cbb056b4c). `check_images.py` and `build_site.py --check` passed at the last run. Notes added by other sessions since then may need images: run `worklist.py images` after `plan_images.py`.
- Not run: the quiet-window checkpoint `update_hubs.py` -> MCP `earth-chronicle` `reindex`. My edits did not add, rename or re-era any notes, so hubs are unaffected, but the search index still holds the old text. Do it when `find . \( -path ./_RAG -o -path ./.obsidian \) -prune -o -type f -mmin -4 -print` returns nothing.

## Tools (`_RAG/tools/`)
- `worklist.py factcheck [--type T]` and `worklist.py images [--type T]`: live gap lists (`plan_images.py` in `_Site/scripts` must be rerun first for images).
- `apply_patch.py` (fixed this session): a `checks` patch now inserts a missing `fact_checks` line. Always `--dry` first. On OneDrive a real apply can take several minutes: run it with `run_in_background`.
- `sweep/batch_args.py N`: prints the next N notes as JSON (order person, place, technology, event, era, species, culture, region; skips notes modified in the last 30 minutes).
- `sweep/factcheck_wf.js`: Workflow script, args = the batch JSON. One agent per note reads it, verifies claims against pages it actually read, returns checks, new source records and discrepancies. About 100k subagent tokens per note; a batch of 40 takes 5 to 15 minutes.
- `sweep/build_spec2.py <workflow .output> <spec.json>`: turns the result into an apply_patch spec (HEAD-checks each source URL and drops 404s, removes double quotes, downgrades snippet-only reads to `summary-only`, drops notes whose agent returned "UNVERIFIED" placeholders).
- `sweep/make_corr_args.py <workflow .output> <corr.json>`: writes the discrepancy file and prints the Workflow args for `sweep/corrections_wf.js`.
- `sweep/corrections_wf.js`: one agent per note with discrepancies proposes minimal exact-once replacements (hedge or correct, body text only, no frontmatter).
- `sweep/build_corr_spec.py <corr workflow .output> <spec> <review.txt>`: validates each `old` occurs exactly once, writes the spec and a human review file.

## Recipe for one batch (about 30 minutes wall clock)
1. `sweep/batch_args.py 40 > batch.json`, then run `Workflow` with scriptPath `_RAG/tools/sweep/factcheck_wf.js` and args = that JSON.
2. `sweep/build_spec2.py <output> spec.json`, `apply_patch.py spec.json --dry`, then apply in the background. Also run `sweep/make_corr_args.py`.
3. Run `Workflow` with `sweep/corrections_wf.js` and the printed args. Then `sweep/build_corr_spec.py`, and READ the review file before applying.
4. Apply the corrections (dry, then real). Align a frontmatter date only when the corrected body text now contradicts it (add `["date_end: 1503","date_end: 1504"]`-style pairs to the spec).
5. `validate_vault.py` (0 errors expected), then every few batches the quiet-window hub/reindex checkpoint and `build_site.py --check`.
Rerun `batch_args.py` between batches; finished notes drop out automatically because `fact_checks` now exists.

## Lessons and hazards
- The correction agents sometimes add specifics that no page they cited supports (examples I removed: Pericles "444 to 430", a Chandragupta territory list, an Amanitore relief detail, Sagrada Familia 2026 milestones). Spot-check anything with new names, numbers or dates; Wikipedia text is fetchable with `urllib` (`_RAG/tools/sweep` scripts show the pattern; use a descriptive User-Agent).
- A "safety classifier unavailable" note on an agent result means verify that agent's output extra carefully.
- The account hit its monthly spend limit twice mid-run. Failed agents come back as errors; rerun the same Workflow with `resumeFromRunId` (successes are cached).
- Britannica returns 403 to agents; snippet-only reads must be `access: summary-only`. New source notes created here are `verified: true` but have no `_RAG/source_cache` entry, so the Tier 4/5 source re-read may pick them up later.
- The validator's `apply_patch` check syntax requires each check to end with exactly one `[Source A; Source B]` bracket and contain no double quotes.
- `_Rewrite/` and `.claude` were added to `SKIP_DIRS` in `_RAG/vault.py` because they broke the validator and the site scripts. `_Rewrite` belongs to another session (AI retelling layer; its build message says about 1000 site notes are not rewritten yet; my edits did not make any rewrite stale).
- AI image step (only if a note still has no image): pick a subject with no people or faces, prefix with the house STYLE string in `_Site/scripts/ai_assets.py`, call `generate_image_batch` with model `recraft_v4_1` (aspect 4:3), `jobs_wait`, download the PNG with curl into a scratch dir as `00.png`, write `ids.json` (`["type/slug"]`), `prompts.json` (`{"prompts": {"type/slug": "<subject>"}}`), `jobids.json` (`{"0": "<job id>"}`), run `_Site/scripts/register_batch2.py <dir> ids prompts jobids`, then fix the caption capitalisation (it lowercases proper nouns) and the `generated` date (the script hardcodes 2026-09-26) directly in `_Site/data/image-credits.json`, then `make_thumbs.py`, `check_images.py`.

## Frontmatter dates deliberately left for the user's decision
Enheduanna (-2285/-2250 vs "fl. c. 2300 BCE"), Sitting Bull (1831 vs 1831 to 1837), Tupac Amaru II (1738 vs c. 1742), Queen Amina (1576 to 1610 vs other datings), Jan van Eyck (1390 vs 1380/1390), Amanitore (1 to 25, sources say mid-1st century AD), Kupe (900 to 1100), Montezuma II (1466 vs c. 1471), Karakorum date_end 1388 (sources: damaged 1372, razed 1380), Kyoto date_end 1868 (sources: 1869), Dido, Jadwiga (1373 or 1374), Tamar (1160 or 1166), Basawan (1560 is earliest attribution; flourished 1580 to 1600), Petra and Arkaim (dates shifted by newer dating), Pericles (`sources:` still lists only the placeholder Britannica/Wikipedia homepages). Dates I did change to match corrected body text: Anacaona date_end 1504, Ban Zhao date_end 117, Behzad date_start 1455, Ezana date_start 320 and date_end 360, Sofonisba Anguissola date_end 1629, Artemisia Gentileschi date_end 1654, Ambiorix date_start -54, Ba Trieu date_start 248, Seondeok date_start 632, Eleanor of Aquitaine date_start 1124.

## Not part of this sweep
Source re-read Tiers 4 to 6 (`_RAG/HANDOFF.md`), the Rewrite layer, the Art section expansion and the Museum work belong to other sessions and are tracked in their own handoffs.

## Final numbers
- Validator: 0 errors; `Fact-check coverage: 584/769` entity, era and region notes (was 377/675 when this sweep started).
- `build_site.py --check`: OK, 1540 notes, 1861 images, 944 notes with an image, 9033 edges, 1 unresolved link (`species/homo-sapiens -> Observer's Charter`, pre-existing).
- The image count did not change in the last build although other sessions added many notes since (for example new technology and species notes): run `plan_images.py` then `worklist.py images` first thing next time.
