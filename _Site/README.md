# Earth Chronicle site

Static explorer for the vault (963 notes; everything except `00_Meta` and `_Templates`). Design decisions: [DESIGN.md](DESIGN.md).

```
python scripts/plan_images.py            # data/image-plan.json (1..ceiling images per note by richness)
python scripts/fetch_images.py           # resumable; images/<type>/<slug>/<n>.jpg, data/image-credits.json, data/image-gaps.json
python scripts/borrow_gaps.py            # related-note image for non-source notes that ended with none (flagged as borrowed)
python scripts/make_thumbs.py            # 480px thumbnails in images/_t/
python scripts/build_site.py --check     # data/*.json, recommendations (recs.json, featured.json); verifies counts, paths, links
python scripts/check_images.py           # every image opens, is big enough, has a credit
python scripts/check_contrast.py         # WCAG contrast for every text pair in light and dark
python scripts/eval_recs.py              # suggestion quality gate (hidden-link prediction); --tune, --update
python scripts/ai_assets.py register-images <dir>   # import Higgsfield art; validate-text <file> for Gemini output
python scripts/audit_images.py            # flags duplicates, off-topic/misleading, low-quality, sensitive images -> data/audit/image-audit.json
python scripts/audit_sheets.py            # labelled contact sheets for a visual review -> data/audit/sheets/
python scripts/verdict.py <sheet> "<tile>=<code>:<reason>" ...   # record a review verdict -> data/audit/verdicts.json
python scripts/apply_audit.py [--dry|--restore]   # remove/demote per the verdicts, quarantines removed files (reversible)
```

## Image audit (2026-09-27)
Every one of the 1,722 images was checked automatically (exact/near duplicates, off-topic captions, flat diagrams/maps/flags,
too small, blank/dark) and then reviewed visually across 43 labelled contact sheets. 352 images got a verdict; 134 were removed
(24 wrong-subject/name-coincidence mix-ups, 72 off-topic or misleading, 14 unusable quality, 14 duplicates, 8 distressing
photographs unsuited to a card) and moved to `_quarantine/` (restorable with `apply_audit.py --restore`); 221 weak or
not-lead images (maps, diagrams, flags, tangential photos) were kept but demoted behind better images. That left 58 notes
with no image or only weak ones; each got a new Higgsfield lead image (`register_batch2.py`), after which every non-source
note has at least one image (one, `person/laozi`, needed a manual re-fetch to replace a too-small combined portrait).
Total AI images: 84 (26 concept art + 1 hero from the first pass, 58 replacements). See `data/audit/` for the full record.
Serve `_Site/` with any static server (`preview_start earth-chronicle` uses port 8766). Open `/?selftest=images` to decode every image in the browser.

`fetch_images.py` options: `--sample 20`, `--only <slug|title>`, `--types person event`, `--limit N`, `--force`, `--retry-gaps`, `--phase discover`.
Caches live in `data/cache/`. Set `SI_API_KEY` to enable Smithsonian Open Access. Only CC0 / public domain / CC BY / CC BY-SA files are kept.
On Windows set `PYTHONUTF8=1` for long runs. Rebuild the site after each fetch run. Keep `images/` on this device if the vault syncs through OneDrive.

## Suggestions
`scripts/recommend.py` ranks related notes from text similarity (TF-IDF), link structure (Adamic-Adar), era/region/theme overlap and closeness in time,
fuses them with weighted reciprocal-rank fusion, and diversifies with MMR. Each suggestion carries a reason. `eval_recs.py` hides 20% of links and checks
that they are recovered. In the browser, `js/recs.js` adds a recency-weighted "Continue exploring" rail from what the reader has viewed (stored only in
this browser), guided journeys, and "connect two notes" (shortest chain of links).

## AI-made material
Higgsfield concept art (badged "AI illustration") and the header banner; credits carry model, prompt and job id. Gemini text extras (In brief,
journey narration, quiz) read `data/ai-text.json`; `ai_assets.py validate-text` rejects any line that adds a number or name not in the note itself.

## Rewrite layer
Every note's text is overlaid with an AI rewrite in one of the creative-writing tool's four voices (`data/rewrite-<type>.json`,
`data/rewrite-index.json` for card blurbs), labelled in the note panel. It lives in `_Rewrite/` (see its README); `build_site.py`
republishes it after each build, drops rewrites whose note changed, and prints how many notes are waiting. New notes are
rewritten by the `chronicle-rewriter` agent (`.claude/agents/`).
