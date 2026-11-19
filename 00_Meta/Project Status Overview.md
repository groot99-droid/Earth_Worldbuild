---
title: "Project Status Overview"
type: meta
status: seed
tags: [meta, status]
---

## Summary
Earth Chronicle is an Obsidian vault and retrieval (RAG) corpus covering the history of Earth from the formation of the Solar System (about 4.567 billion years ago) to the present. It is written from the point of view of the Observer, an imagined outside anthropologist (see [[Observer's Charter]]). This note is a snapshot of what exists and where the work stands. Its figures are generated: run `python _RAG/tools/status_overview.py --write` to recompute them, and never edit the two generated blocks by hand.

## What Exists
<!-- AUTO:status-exists -->
Counted on 2026-11-19 by `_RAG/tools/status_overview.py` (regenerate it; do not edit by hand). Earth Chronicle holds 1,738 notes, not counting this one, with about 365,000 words of body text and 6,682 wikilinks in note bodies (generated hub lists and timelines left out of both counts).

| Layer | Folder | Notes |
|---|---|---|
| Eras | `01_Eras/` | 41 |
| Regions | `02_Regions/` | 21 |
| Events | `03_Entities/Events/` | 166 |
| People | `03_Entities/People/` | 203 |
| Peoples and Cultures | `03_Entities/Peoples-Cultures/` | 183 |
| Places | `03_Entities/Places/` | 111 |
| Species | `03_Entities/Species/` | 58 |
| Technologies | `03_Entities/Artifacts-Technologies/` | 88 |
| Themes | `04_Themes/` | 9 |
| Observer essays | `05_Observer_Notes/` | 29 |
| Timelines | `06_Timelines/` | 3 |
| Sources | `07_Sources/` | 822 |
| Meta | `00_Meta/` | 4 |

Entity notes by primary era (809 in all), oldest era first: [[Hadean Eon]] 7, [[Archean Eon]] 7, [[Proterozoic Eon]] 9, [[Paleozoic Era]] 18, [[Mesozoic Era]] 9, [[Cenozoic Era]] 14, [[Paleolithic]] 19, [[Pleistocene Epoch]] 19, [[Holocene Epoch]] 1, [[Neolithic]] 43, [[Bronze Age]] 71, [[Iron Age]] 61, [[Classical Antiquity]] 80, [[Medieval Period]] 185, [[Early Modern Period]] 89, [[Industrial Age]] 138, [[Information Age]] 37, [[Anthropocene]] 2.
Eras with no entity note of their own: [[Paleoproterozoic Era]], [[Mesoproterozoic Era]], [[Neoproterozoic Era]], [[Tonian Period]], [[Cryogenian Period]], [[Ediacaran Period]], [[Cambrian Period]], [[Ordovician Period]], [[Silurian Period]], [[Devonian Period]], [[Carboniferous Period]], [[Permian Period]], [[Triassic Period]], [[Jurassic Period]], [[Cretaceous Period]], [[Paleogene Period]], [[Neogene Period]], [[Lower Paleolithic]], [[Quaternary Period]], [[Middle Paleolithic]], [[Upper Paleolithic]], [[Epipaleolithic]], [[Mesolithic]].
The named-artist section (person notes tagged `artist`) has 53 notes, 53 of them with an Art-Talk profile.
<!-- /AUTO:status-exists -->

The same folder also holds four standalone projects built from the vault, which the validator and the indexer skip: the static explorer in `_Site/`, the walkable Chronicle Museum in `_Museum/`, the AI rewrite layer in `_Rewrite/`, and the Art-Talk artist timeline in `Art-Talk-main/`. Each has its own README.

## Design
Earth Chronicle separates each entity note into a neutral `## Facts` layer and a short `## Observer's Reading` layer, so a search for what happened returns facts and a search for what it means returns interpretation. The Observer uses a small translation vocabulary in which each term maps to an ordinary concept: a border is a claim-line, a religion or ideology is a meaning-engine, shared myths and nations are story-glue, writing and archives are memory-outsourcing, and the control of fire is heat-domestication. The voice rules ask for curiosity without contempt and the same standard for every culture, era and belief system, including secular and modern ones.

See [[Observer's Charter]] for the voice rules, [[Glossary of Observer Terms]] for the vocabulary, [[Conventions]] for the schema and [[README]] for the folder layout. Two essays show the method in practice: [[The Fiction of Claim-Lines]] and [[Why the Species Buries Its Dead]].

## Retrieval System
The retrieval system in `_RAG/` runs locally with no API keys. It splits notes by `##` heading, embeds the chunks with `bge-small-en-v1.5`, stores them in SQLite with a keyword index, and combines vector and keyword ranking. The `earth-chronicle` MCP server exposes it to Claude through `search_vault`, `get_note`, `get_neighbors`, `list_timeline` and `reindex`. The index (`_RAG/index/`) is generated and git-ignored, so a fresh clone has none until `python _RAG/build_index.py` runs.

## Where Things Stand
<!-- AUTO:status-standing -->
- **Validator:** 0 error(s), 1 warning(s).
- **Fact-checking:** 599 of 871 era, region and entity notes carry dated `fact_checks`, 1,663 in all (2026-09-20 361, 2026-09-25 62, 2026-09-26 75, 2026-09-27 1044, 2026-11-19 121). Notes without any: culture 98, technology 64, event 38, species 30, era 24, place 18. 53 checks cite the generic [[Encyclopaedia Britannica]] note and 99 the generic [[English Wikipedia]] note, both `not-consulted`.
- **Status:** 912 `seed` (all notes except sources and meta notes). Under [[Conventions]] a note stays `seed` until every claim is checked.
- **Sources:** 822 source notes, 787 marked `verified: true`. By access level: full-text 129, archived-copy 58, reference-text 485, abstract 25, summary-only 89, not-consulted 6, (not set) 30. 42 are "(Search Summaries)" notes. Not verified (35): [[Ancient Civilizations (Scarre and Fagan)]], [[Anderson and Westneat 2007 Dunkleosteus Bite Force]], [[Art-Talk (Expansion Profiles)]], [[Bergström et al. 2020 Origins of Prehistoric Dogs]], [[Braddy et al. 2008 Giant Eurypterid Claw]], [[Cambridge World History]], [[Conway Morris and Caron 2012 Pikaia]], [[Encyclopaedia Britannica]], [[Engelman 2023 Dunkleosteus Body Length]], [[English Wikipedia]], [[Freidline et al. 2023 Tam Pà Ling]], [[Giaccio et al. 2017 Dating the Campanian Ignimbrite]], [[Hays et al. 1976 Pacemaker of the Ice Ages]], [[Higham et al. 2014 Neanderthal Disappearance]], [[Hublin et al. 2020 Bacho Kiro Cave]], [[Iasi et al. 2024 Neanderthal Ancestry Through Time]], [[Lordkipanidze et al. 2013 Dmanisi Skull 5]], [[Love et al. 2009 Cryogenian Sponge Steroids]], [[Maps of Time (Christian)]], [[Mylopotamitaki et al. 2024 Ranis]], [[NobelPrize.org]], [[Paterson et al. 2011 Anomalocaris Eyes]], [[Slimak et al. 2022 Mandrin Cave]], [[Slon et al. 2018 Neanderthal-Denisovan Offspring]], [[Smith and Caron 2015 Hallucigenia Head]], [[The Dawn of Everything (Graeber and Wengrow)]], [[The Human Career (Klein)]], [[The Transformation of the World (Osterhammel)]], [[UNESCO World Heritage Centre]], [[Villmoare et al. 2015 Early Homo at Ledi-Geraru]], [[Willeit et al. 2019 Mid-Pleistocene Transition]], [[Woese and Fox 1977 Prokaryotic Domain]], [[World History Encyclopedia]], [[Zhu et al. 2018 Shangchen Stone Tools]], [[deMenocal et al. 2000 African Humid Period]].
- **Canvas maps:** `08_Canvas_Maps/Themes and Essays Map.canvas` shows 8 of the 29 Observer essays; missing: [[Cargo That Was Not Goods - What Exchange-Webs Carry]], [[Frontiers of Extraction]], [[Institutionalized Doubt - How Strangers Learned to Check Each Other]], [[Plague Years - Disease as a Historical Actor]], [[Sacred Ground - Why Some Places Are Special]], [[Scripts as Borders - Writing and Identity]], [[Second Chances - How the Species Ran the Experiment Again]], [[The Aftermath Problem - How Societies Remember Their Wars]], [[The Kin-Lattice at Scale - From Households to States]], [[The Long Partnership - Domesticates and the Species]], [[The Ratchet and Its Gaps - Why Some Tool-Lineages Stall]], [[Who Counts as a Person - The Long Argument over Status]], [[Who Gets Credit for the Machine]], [[Who Writes the Record]], [[Why Empires Keep Forming]], [[Why Every Meaning-Engine Splits]], [[Why Languages Die and Why Some Spread]], [[Why Prophets Appear in Clusters]], [[Why Strangers Trust Strangers - Money as Story-Glue]], [[Why the Same Discovery Happens Twice]], [[Why the Species Makes Things That Do Nothing]].
- **Site (`_Site/`):** the last build holds 1,734 notes, 1,861 images (944 notes with an image) and 10,345 edges; 1 unresolved link(s).
- **Museum (`_Museum/`):** 17 scenes (the hub and 16 rooms), 256 artists and people, 686 works.
- **Rewrite layer (`_Rewrite/`):** site 1,564 of 1,734 rewritten, 119 stale, 51 not yet rewritten; museum 686 of 686 rewritten, 0 stale, 0 not yet rewritten.
<!-- /AUTO:status-standing -->

## Next Steps
The open work is tracked in handoff files under `_RAG/`, `_RAG/handoff/`, `_Rewrite/` and `_Museum/`; `_RAG/README.md` lists them.
1. Finish the source re-read: apply the Tier 5 patch that is written but not run (`_RAG/HANDOFF_Tier5.md`), then Tier 6 (`_RAG/HANDOFF.md`).
2. Continue the fact-check sweep over the notes that have no `fact_checks` yet (`_RAG/handoff/factcheck_sweep_status.md`).
3. Write the last Brief 2 species (Batches 14 and 15, `_RAG/handoff/HANDOFF_Brief2_Places_and_Species.md`) and the link passes Briefs 1 and 3 left owing.
4. Rewrite the museum placards still waiting for the rewrite layer, with the `chronicle-rewriter` agent (`_Rewrite/HANDOFF.md`).
5. Start the art section expansion, which is planned but not begun (`_RAG/handoff/HANDOFF_Art_Section_Expansion.md`).
6. Promote the best-checked notes from `seed` to `draft` or `reviewed`, and add the missing Observer essays to the Themes and Essays canvas map.
