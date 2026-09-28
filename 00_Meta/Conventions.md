---
title: "Conventions"
type: meta
status: reviewed
tags: [meta, schema]
---

## Note Types and Folders
| type | folder |
|---|---|
| era | `01_Eras/` |
| region | `02_Regions/` |
| event | `03_Entities/Events/` |
| person | `03_Entities/People/` |
| place | `03_Entities/Places/` |
| culture | `03_Entities/Peoples-Cultures/` |
| species | `03_Entities/Species/` |
| technology | `03_Entities/Artifacts-Technologies/` |
| theme | `04_Themes/` |
| observer-note | `05_Observer_Notes/` |
| timeline | `06_Timelines/` |
| source | `07_Sources/` |
| meta | `00_Meta/` |

Templates are in `_Templates/`. Filenames are the note titles. **Titles must be unique across the whole vault**, since links use bare names.

## Frontmatter Schema
```yaml
title:
type:            # see table above
era: "[[...]]"   # primary chronological frame; must be an 01_Eras note
region: "[[...]]"# primary location; must be an 02_Regions note ("Planet-wide" if global)
themes: []       # slugs from the theme list below
date_start:      # integer years relative to 1 CE; negative = BCE; deep time uses full years (e.g. -4540000000)
date_end:
date_precision:  # exact | year | decade | century | approx | deep-time
related: []      # list of "[[...]]"
sources: []      # list of "[[...]]" pointing to 07_Sources
confidence:      # high | medium | low
status:          # seed | draft | reviewed
tags: []
```

## Theme Slugs
`science`, `technology`, `religion`, `war`, `trade`, `kinship`, `language`, `art`, `earth-systems`. Each has a hub note in `04_Themes/`.

## Dates
- Integers, years relative to 1 CE. There is no year 0, but this vault treats 1 CE as year 1 and 1 BCE as -1 for simplicity.
- Deep-time dates are given in full years (`-66000000` for 66 Ma) with `date_precision: deep-time` or `approx`.
- `date_end` may be empty for ongoing or instantaneous things.
- All dates before about 1000 CE are approximate unless marked `exact`.

## Body Sections
Entity notes use: `## Summary`, `## Facts`, `## Context & Connections`, `## Observer's Reading`, `## Open Questions`. Observer essays use: `## Question`, `## What the Record Shows`, `## Observer's Reading`, `## Limits of This Reading`. Each section should stand alone as a retrieval chunk, so name the subject explicitly instead of writing "it" or "this event" at the start of a section.

## Confidence and Status
- `confidence: high`: well-established consensus. `medium`: broadly accepted but details debated. `low`: contested, sparse evidence, or legendary.
- `status: seed`: model-written first pass, unreviewed. `draft`: human-edited. `reviewed`: checked against sources.
- `fact_checks` (optional list): specific claims that were verified against a named source, each written `YYYY-MM-DD: claim [Source Title]`. A note stays `seed` until **all** of its claims are checked, so `fact_checks` records partial verification honestly. The named sources are linked in `sources:` and live in `07_Sources/` with `verified: true` and `checked_on`.
- Source notes: `verified: true` means the source was actually consulted (see its `## Caveats` and `access` for how); `verified: false` means the citation is from memory. See Source Access Levels below.

## Source Access Levels
Source notes (`type: source`) record how much of the source was actually read, in three optional fields:
- `access`: one of `full-text` (the article body, read from the publisher, an open-access copy or a repository), `archived-copy` (a full page read from a web-archive snapshot, which may differ from the live page), `reference-text` (raw text of a reference work such as Wikipedia wikitext, with the revision recorded), `abstract` (only the abstract and metadata), `summary-only` (only search-result summaries, page not opened) or `not-consulted` (cited from memory, for example a print book that cannot be fetched).
- `access_route`: how the text was obtained, for example "Europe PMC full-text XML" or "Wayback Machine snapshot of 2026-09-20".
- `read_on`: the date the text was read (`YYYY-MM-DD`).

A claim counts as confirmed only if the text actually read contains it, so an `abstract` source confirms only what its abstract says, and an abstract-only source never moves a note toward `status: reviewed`. Use `verified: false` with `not-consulted`. The `## Caveats` section says what was and was not read. `validate_vault.py` checks the values and prints the sources by access level. `_RAG/tools/fetch_source.py` reads sources through routes that work for automated requests and never bypasses a CAPTCHA, cookie wall or paywall (see `_RAG/README.md`).

## Named-Artist Notes
The named-artist section is the `person` notes tagged `artist`. It began as 53 profiles converted from the Art-Talk project (`Art-Talk-main/`) and is being expanded by a ledger-driven plan (`_RAG/handoff/HANDOFF_Art_Section_Expansion.md`).
- `tags: [artist, <discipline>, ...]`, primary discipline first, from `painting`, `sculpture`, `architecture`, `design`, `craft`, `calligraphy`, `photography`, `film`, `literature`, `music`, `dance`, `theatre`. Artists with no Art-Talk profile add `text-only`; the note's Context says why (no freely licensed images, because the artist died recently or is living).
- `art_talk: <slug>` names the profile in `Art-Talk-main/artists/`; only illustrated notes have one. Their `sources` are `["[[English Wikipedia]]", "[[Art-Talk (Expansion Profiles)]]"]`; the original 53 cite `[[Art-Talk (Artist Profiles)]]`.
- `themes` come from the closed set: `art`, plus `language` for writers, `technology` for architects and `religion` for sacred music.
- Era is the period of main activity. For 20th-century figures use the era containing the career midpoint (a tie goes to the earlier era), and anyone working mainly after 1945 is Information Age. Living artists get no `date_end` and "as of 2026" phrasing.
- Gender is tracked only in the expansion ledger, never in frontmatter.
- Movements and schools are `type: event` notes tagged `[movement, <discipline>]`. Omit `date_end` for ongoing traditions.

## Linking
Use `[[Note Title]]` wikilinks in body text. Link the subject to its era, its region, and at least one theme hub (via `themes:` and in Context). See [[Observer's Charter]] for the two-layer rule.

## Validation and Indexing
- `_RAG/tools/validate_vault.py` checks schema and links.
- `_RAG/build_index.py` builds the search index. See [[README]].
