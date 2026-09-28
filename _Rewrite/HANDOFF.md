# Rewrite layer handoff (stopped 2026-09-28)

## Where it stands

| Target | Rewritten | Left |
|---|---|---|
| Museum placards | **299 of 299, done** | none |
| Site notes | **351 of 1,284** | 932 not yet rewritten, 1 stale (`source/english-wikipedia`, its source changed) |

Run `PYTHONUTF8=1 python _Rewrite/rewrite_layer.py status` for live numbers. The site keeps growing, because other sessions
add notes (Brief 2 species), so the total will be higher next time.

Everything rewritten is already published and showing: `_Site/data/rewrite-*.json` and `_Museum/data/placard-rewrite.json`.
Notes not yet rewritten show their original text, which is the intended fallback.

## How to resume

1. Open a session in `Earth _WorldBuilding`, so the project agent `chronicle-rewriter` (`.claude/agents/`) loads.
2. Remaining work is already exported as batches `_Rewrite/batches/site-039.md` to `site-068.md`. The first four are part
   done:

   | Batch | Left | Notes |
   |---|---|---|
   | site-039 | 14 of 33 | |
   | site-040 | 20 of 32 | |
   | site-041 | 23 of 30 | |
   | site-042 | 24 of 30 | |
   | site-043 to site-059 | all | mixed notes; 057 to 059 are the 8 very long theme notes |
   | site-060 to site-068 | all | 510 short source notes |

   Each agent runs `rewrite_layer.py todo <batch>` first and skips anything already merged, so just hand it the batch path.
3. Launch agents **four at a time at most**, one batch each, e.g. *"Rewrite the batch `_Rewrite/batches/site-043.md`"*. Ten
   at once all stalled; three or four at a time ran cleanly, at 10 to 25 minutes per batch.
4. When the batches are done, pick up anything new or stale with one agent on **"all pending site"**, or run
   `rewrite_layer.py export --target site` and repeat step 3 for the new batches. That catches notes added since
   2026-09-28 and `source/english-wikipedia`.
5. Once `status` shows 0 left, run `python _Site/scripts/build_site.py --check` and spot-check a few notes in the site
   (`preview_start earth-chronicle`, port 8766). Each rewritten note shows an "AI rewrite · <voice> voice" badge.

`_Rewrite/batches/superseded/` holds old batch files (site-010 to site-034) replaced by the 2026-09-28 re-export. Don't run
them; they're kept only so batch numbers never repeat.

## Voice mix so far

- **Museum:** epic-fantasy 145, essay 81, confessional 50, horror 23.
- **Site:** epic 293, essay 53, horror 5. It is epic-heavy because the finished batches were eras, regions, places, species
  and cultures. Events, people, technologies and sources come next, and will shift the mix toward essay (and horror for the
  pre-modern catastrophes).

## Things to know

- **Rules and tools.** The rules are `_Rewrite/VOICES.md`, the tool is `_Rewrite/rewrite_layer.py`, and the overview is
  `_Rewrite/README.md`. The checker enforces links, numbers (digits and number words), names, hedges by kind, one-to-one
  facts and questions, and length.
- **Build hooks.** `build_site.py` and `_Museum/build_manifest.py` republish the layer after every build and print the
  pending count. A note whose source changes becomes stale and shows its original text until it is rewritten.
- **Source errors.** Agents flag possible errors in vault notes as they go. They are collected in
  `_Rewrite/vault-issues.md`, 18 so far, none of them fixed in the vault. Agents keep a flagged error out of the rewrite
  where they can. Where the checker forces a number to stay, they add a hedge ("by one reported count").
- **Unfinished museum check.** Opening a museum placard could not be clicked through in the in-app browser: the pane is
  hidden, so the 3D canvas has zero size and camera raycasts return nothing. The page loads, the placard layer loads
  (HTTP 200), and the code picks the rewrite by work id, but a placard hasn't been looked at on screen. Walk the museum
  once by hand.
- **No commit.** The project folder is not a git repository, so none of this is committed.
