# Rewrite layer handoff (stopped 2026-09-28; state updated 2026-11-19)

## Where it stands (2026-11-19)

| Target | Rewritten | Left |
|---|---|---|
| Site notes | **1,660 of 1,660, done** | none; 0 stale |
| Museum placards | **299 of 686** | **387 not yet rewritten**, 0 stale |

The site was finished on 2026-09-28 (batches site-039 to site-090, last commits `51c3440` and `35342dc`); every batch in
`_Rewrite/batches/` is merged and `_Rewrite/incoming/` holds nothing unmerged. The 387 museum placards waiting are the
portraits of the Earth Chronicle **People** wing (203 people, ten rooms), which was added to the museum on 2026-09-28
(commit `1b47afc`) after the 299 Art-Talk placards had been rewritten. No museum batch has been exported for them yet.

Run `PYTHONUTF8=1 python _Rewrite/rewrite_layer.py status` for live numbers. A note or placard whose source text changes
becomes stale and shows its original text until it is rewritten again, so any later edit to a note body adds to "left".

Everything rewritten is already published and showing: `_Site/data/rewrite-*.json` and `_Museum/data/placard-rewrite.json`.
Items not yet rewritten show their original text, which is the intended fallback.

## How to resume

1. Open a session in the project root, so the project agent `chronicle-rewriter` (`.claude/agents/`) loads.
2. Ask it for **"pending museum"**. It runs `rewrite_layer.py status`, then `export --target museum`, which writes the new
   batches (`_Rewrite/batches/museum-006.md` onwards), and works through them; past about three batches it hands the rest
   back by path for parallel copies. Launch at most **four agents at a time**: ten at once all stalled on 2026-09-28,
   three or four ran cleanly at 10 to 25 minutes per batch.
3. Once `status` shows 0 left, run `python _Museum/build_manifest.py` (it republishes the layer and prints the pending
   count) and walk a few People-wing placards in the museum (`?room=people-industrial-age-1`, for example). Each rewritten
   placard shows an "AI rewrite" label with its voice.

`_Rewrite/batches/superseded/` holds old batch files (site-010 to site-034) replaced by the 2026-09-28 re-export. Don't run
them; they're kept only so batch numbers never repeat.

## Voice mix (2026-11-19)

- **Site:** essay 1,192, epic-fantasy 440, horror 28.
- **Museum:** epic-fantasy 145, essay 81, confessional 50, horror 23.

## Things to know

- **Rules and tools.** The rules are `_Rewrite/VOICES.md`, the tool is `_Rewrite/rewrite_layer.py`, and the overview is
  `_Rewrite/README.md`. The checker enforces links, numbers (digits and number words), names, hedges by kind, one-to-one
  facts and questions, and length.
- **Build hooks.** `build_site.py` and `_Museum/build_manifest.py` republish the layer after every build and print the
  pending count. A note whose source changes becomes stale and shows its original text until it is rewritten.
- **Source errors.** Agents flag possible errors in vault notes as they go. They are collected in
  `_Rewrite/vault-issues.md` (18 items, all from batches site-002 to site-038; later batches added none to the file). One
  has since been fixed in the vault; the rest stand. Agents keep a flagged error out of the rewrite where they can. Where
  the checker forces a number to stay, they add a hedge ("by one reported count").
- **Unfinished museum check.** On 2026-09-28 a placard could not be clicked through in the in-app browser (the hidden pane
  gave the 3D canvas zero size). The museum's browser harness (`node _Museum/tools/walk_test.mjs`) now reads placards,
  including the People ones, and passed 45 of 45 checks on 2026-11-19, but a rewritten placard has still not been looked at
  by eye. Walk the museum once by hand.
- **Version control.** The project is the git repository `groot99-droid/Earth_Worldbuild`; the store, the batches and the
  published files are committed with the rest.
