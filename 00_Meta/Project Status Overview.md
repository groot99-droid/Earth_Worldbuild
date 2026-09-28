---
title: "Project Status Overview"
type: meta
status: seed
tags: [meta, status]
---

## Summary
Earth Chronicle is an Obsidian vault and retrieval (RAG) corpus covering the history of Earth from the formation of the Solar System (about 4.567 billion years ago) to the COVID-19 pandemic (2019). It is written from the point of view of the Observer, an imagined outside anthropologist (see [[Observer's Charter]]). This note is a snapshot of what had been built as of 2026-09-25. Counts will drift as the vault grows, so regenerate them rather than editing them by hand.

## What Exists
Earth Chronicle held 706 notes at the time of this snapshot (not counting this note), with about 113,000 words of body text and 4,236 wikilinks.

| Layer | Folder | Notes |
|---|---|---|
| Eras | `01_Eras/` | 18 |
| Regions | `02_Regions/` | 21 |
| Events | `03_Entities/Events/` | 128 |
| People | `03_Entities/People/` | 49 |
| Peoples and Cultures | `03_Entities/Peoples-Cultures/` | 81 |
| Places | `03_Entities/Places/` | 38 |
| Species | `03_Entities/Species/` | 18 |
| Technologies | `03_Entities/Artifacts-Technologies/` | 24 |
| Themes | `04_Themes/` | 9 |
| Observer essays | `05_Observer_Notes/` | 11 |
| Timelines | `06_Timelines/` | 3 |
| Sources | `07_Sources/` | 302 |

Entity coverage is uneven across time. The [[Medieval Period]] has 80 entity notes, the [[Industrial Age]] has 61 and [[Classical Antiquity]] has 34. The five deep-time eras from the Hadean Eon through the Mesozoic Era have 24 entity notes between them, and the [[Anthropocene]] has only 2.

## Design
Earth Chronicle separates each entity note into a neutral `## Facts` layer and a short `## Observer's Reading` layer, so a search for what happened returns facts and a search for what it means returns interpretation. The Observer uses a small translation vocabulary in which each term maps to an ordinary concept: a border is a claim-line, a religion or ideology is a meaning-engine, shared myths and nations are story-glue, writing and archives are memory-outsourcing, and the control of fire is heat-domestication. The voice rules ask for curiosity without contempt and the same standard for every culture, era and belief system, including secular and modern ones.

See [[Observer's Charter]] for the voice rules, [[Glossary of Observer Terms]] for the vocabulary, [[Conventions]] for the schema and [[README]] for the folder layout. Two essays show the method in practice: [[The Fiction of Claim-Lines]] and [[Why the Species Buries Its Dead]].

## Retrieval System
The retrieval system in `_RAG/` runs locally with no API keys. It splits notes by `##` heading, embeds the chunks with `bge-small-en-v1.5`, stores them in SQLite with a keyword index, and combines vector and keyword ranking. The `earth-chronicle` MCP server exposes it to Claude through `search_vault`, `get_note`, `get_neighbors`, `list_timeline` and `reindex`. On 2026-09-25 the validator reported 0 errors and 0 warnings and the index was current.

## Where Things Stand
- **Fact-checking is well underway.** All 377 era, region and entity notes carry dated `fact_checks`, 604 in total: 546 logged on 2026-09-20 and 58 on 2026-09-25. The 2026-09-25 pass removed an unsupported lower bound on the death toll in [[Partition of India]].
- **No note has been promoted yet.** All 400 content notes other than sources and meta notes are still `status: seed`. Under [[Conventions]], a note stays seed until every one of its claims is checked.
- **Source verification is weaker than the counts suggest.** 295 of the 302 source notes are marked `verified: true`, but 42 are "Search Summaries" notes and 58 record that only search-result summaries were read and the pages were not opened. Seven foundational references are still `verified: false`: [[Encyclopaedia Britannica]], [[Cambridge World History]], [[The Dawn of Everything (Graeber and Wengrow)]], [[The Human Career (Klein)]], [[Maps of Time (Christian)]], [[Ancient Civilizations (Scarre and Fagan)]] and [[The Transformation of the World (Osterhammel)]].
- **One canvas map is out of date.** `08_Canvas_Maps/Themes and Essays Map.canvas` lists 8 of the 11 Observer essays. It is missing [[Frontiers of Extraction]], [[Second Chances - How the Species Ran the Experiment Again]] and [[Who Writes the Record]].

## Next Steps
1. Promote the best-checked notes from `seed` to `draft` or `reviewed`.
2. Verify the seven foundational sources that are still cited from memory.
3. Add the three missing essays to the Themes and Essays canvas map.
4. Deepen coverage of the deep-time eras and the Anthropocene.
