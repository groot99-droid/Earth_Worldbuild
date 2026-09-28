---
title: "README"
type: meta
status: reviewed
tags: [meta, start-here]
---

## What This Vault Is
**Earth Chronicle** is a knowledge base on the history of Earth, from the formation of the planet about 4.54 billion years ago to the present. It is written from the point of view of the **Observer**, an imagined outside anthropologist studying humanity as an unfamiliar species. See [[Observer's Charter]].

It is also a **retrieval (RAG) corpus**: every note is short, structured, and self-contained so that a search system can return precise, well-sourced passages to a language model.

## How the Vault Is Organized
The vault has four main axes, and every entity note connects to each of them.

| Axis | Where | Examples |
|---|---|---|
| Time | `01_Eras/` | [[Hadean Eon]], [[Paleolithic]], [[Industrial Age]] |
| Place | `02_Regions/` | [[Mesopotamia]], [[Sub-Saharan Africa]], [[Andes]] |
| Entities | `03_Entities/` | events, people, places, cultures, species, technologies |
| Themes | `04_Themes/` | [[Science]], [[Religion and Belief]], [[Trade and Economy]] |

Two further layers sit on top:
- `05_Observer_Notes/`: essays that ask cross-cutting questions about the species, such as [[Why the Species Buries Its Dead]] and [[The Settling and Its Bargain]].
- `06_Timelines/`: [[Master Timeline]], [[Deep-Time Timeline]], and [[Human Timeline]], generated from note frontmatter.

Supporting material: `07_Sources/` (bibliography), `08_Canvas_Maps/` (Obsidian canvases), `_Templates/` (note templates).

## Where to Start
1. Read the [[Observer's Charter]], then the [[Glossary of Observer Terms]].
2. Read [[Conventions]] before adding notes.
3. Browse by era, starting at [[Hadean Eon]], or by theme, starting at [[Science]].
4. For a guided tour, read the essays in `05_Observer_Notes/`.

## The Two-Layer Rule
Each entity note separates **facts** (`## Facts`, neutral and sourced) from **interpretation** (`## Observer's Reading`). This keeps retrieval honest: a question about what happened returns facts, and a question about what it means returns readings.

## Status of the Content
All seed content is `status: seed`: a first pass written from general knowledge, with claims checked against sources one at a time (see `fact_checks` in [[Conventions]]). Treat dates and figures as approximate until a note is marked `reviewed`. Each note in `07_Sources/` records how much of its source was read in an `access` field, from `full-text` down to `summary-only` (search-result summaries only) or `not-consulted` (cited from memory); see Source Access Levels in [[Conventions]]. Sources are being re-read in full with `_RAG/tools/fetch_source.py`, so the counts by access level change as that work proceeds.

## Adding a Note
1. Copy the matching template from `_Templates/` (Obsidian: Templates plugin, "Insert template").
2. Fill in frontmatter. Link `era`, `region`, and at least one theme.
3. Write the five sections. Make each stand alone.
4. Run the validator, then regenerate the hubs and timelines, then update the index:

```bash
python _RAG/tools/validate_vault.py
python _RAG/tools/update_hubs.py
python _RAG/build_index.py
```

## Searching the Vault (RAG)
The search stack lives in `_RAG/`. See `_RAG/README.md` for setup, the command-line search, and how to connect the MCP server so Claude can query the vault directly. Obsidian-side plugin setup is in `_RAG/OBSIDIAN_PLUGINS.md`.
