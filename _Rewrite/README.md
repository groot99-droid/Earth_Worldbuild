# Rewrite layer

The text of the Earth Chronicle site (`_Site/`) and the Chronicle Museum (`_Museum/`), retold by AI in the four voices of the
creative-writing tool (`Pipelines/creative-writing`): epic-fantasy, horror-prose, essay/self-help and confessional poetry,
each where it fits. The rewrite is a **layer**: the vault notes and the museum manifest are never edited, and both sites label
the rewritten text ("AI rewrite", plus its voice).

- Site: summary, facts, context, Observer's Reading, open questions and extra sections of every note, plus the card blurbs.
- Museum: every placard description.
- `VOICES.md` is the brief (which voice fits where, the fidelity rules, the batch format).
- `.claude/agents/chronicle-rewriter.md` is the agent that does the writing.

## Layout

```
rewrite_layer.py   export / validate / merge / publish / status
VOICES.md          the brief every rewrite follows
batches/           exported source text, one file per batch (site-NNN.md, museum-NNN.md)
incoming/          rewrites waiting to be merged; merged ones move to incoming/merged/
store/site.json    every accepted site rewrite, with the source hash it was written from
store/museum.json  the same for the museum
```

Published files: `_Site/data/rewrite-<type>.json` and `_Site/data/rewrite-index.json` (card blurbs), and
`_Museum/data/placard-rewrite.json`. The sites overlay these on the original text at load time, so deleting them brings back
the original wording.

## New additions

`_Site/scripts/build_site.py` and `_Museum/build_manifest.py` republish the layer at the end of every build and print how many
items are waiting for a rewrite. A note or placard whose source text changed is "stale": the build drops its old rewrite, so
it shows the original until it is rewritten again. To catch up, ask Claude to run the **chronicle-rewriter** agent on
"all pending". It exports the pending items, writes, validates and merges them. By hand:

```
python _Rewrite/rewrite_layer.py status
python _Rewrite/rewrite_layer.py export --target site      # or --target museum
# write _Rewrite/incoming/<batch>.md, then:
python _Rewrite/rewrite_layer.py validate _Rewrite/incoming/<batch>.md
python _Rewrite/rewrite_layer.py merge _Rewrite/incoming/<batch>.md
```

## What the checker enforces

Per field, against the source: every `[[id|Label]]` link token kept, every number kept (with its scale word and BCE/CE marker)
and no new ones, no capitalised word that isn't in the source item, a hedge kept wherever the source hedges, questions still
questions, facts and questions one-to-one, extra-section titles unchanged, and length within 0.6 to 1.8 times the source.
What it cannot check (no new claims, facts staying declarative, restraint around atrocity) is in `VOICES.md`, and is the
writer's job.

On Windows set `PYTHONUTF8=1`.
