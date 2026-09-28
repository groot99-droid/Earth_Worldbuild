# Brief 3 (Technologies and Themes) - handoff, written 2026-09-27

The earlier Desktop bundle (`EarthChronicle_Brief3_Handoff\`) no longer exists (not deleted by Claude; the Desktop copy of Brief 4's briefs is gone too). This file replaces it. House rules: `EarthChronicle_Brief3_Technologies_and_Themes.md` (copied beside this file if the temp copy survived; otherwise ask the user to re-attach it). Scripts: `brief3_tools\`.

## State
- Part A (9 theme hubs): DONE 2026-09-26, spliced into `04_Themes/` above `## Notes Tagged With This Theme`.
- Part B (64 technologies): Batches 1-6 DONE (technologies folder = 72 notes, was 24). Batches 7 and 8 remain (tables below).
- Part C (18 essays): not started (table below).
- Owed at the end: (1) link pass for plain-text mentions of titles that now exist (scan tech notes for plain "Qanat", "Codex", "Water Clock", "Microscope", "Water Chlorination", "Radiocarbon Dating", etc. with a script; exclude names already inside [[ ]]; do not link generic words like radio/battery mid-sentence unless they clearly mean the note); (2) rewrite the "what the vault does not cover yet" bullets in the Technology, Religion, Trade, War, Language, Art and Earth Systems hubs; (3) final validate, `update_hubs.py`, index. New notes carry no `fact_checks`.
- Search index: as of 2026-09-27 the MCP `reindex` hung and `_RAG/build_index.py` failed with `database is locked` (other sessions' processes hold the DB). Batches 5-6 were on disk and validated but not searchable. Try `brief3_tools\index_retry.py` (run from the vault root; retries every 25 s), and never run an indexer while `update_hubs.py` runs.

## Per-batch procedure that worked (Batches 3-6)
1. `python clash.py "Title" ...` (writes titles.txt and reports clashes) and `python has.py "Title" "~substring" ...` to confirm link targets exist. Python is `_RAG/.venv/Scripts/python.exe`. Do NOT use `grep -P` in this shell; run Python with `PYTHONUTF8=1`.
2. Launch ONE Workflow with 8 parallel research agents (one per title). Give each: the house rules, the plan row, a list of confirmed-existing link titles (sibling titles in the same batch are allowed), and a JSON schema (title, date_start, date_precision, era, region, themes, confidence, sources, related, summary, facts 5-6, context, observer_reading, open_questions, reviewer_notes). Use backtick strings in the script (an apostrophe in a single-quoted string broke the parser once). Body target 150-280 words. Agents only research and return JSON; they do not write files.
3. Read the full output file (the notification truncates it). CHECK EVERY OUTPUT BY HAND, especially arithmetic and dates (an agent once converted 852 ft to 256 m; correct is about 260 m) and claims phrased as questions. Verify subagents wrote no vault files.
4. Write each note with the Write tool in the format of `Rosetta Stone.md`: frontmatter (title, type: technology, era, region, themes, date_start, date_precision, related, sources, confidence, status: seed, tags: []; no `fact_checks`), then `## Summary`, `## Facts`, `## Context & Connections`, `## Observer's Reading`, `## Open Questions`.
5. `python check_notes.py "Title" ...` (frontmatter, sections, links, allowed sources, Observer terms only in the Reading, word count 150-315 by `wc -w`-style count including headings). Trim until it passes.
6. validate (`_RAG/tools/validate_vault.py`), `update_hubs.py`, validate again, then index. Report only errors that are yours.

## Conventions settled
- `era` and `region` are wikilinks to existing notes. `related` holds specific notes only (people, events, cultures, sibling technologies), never eras, regions or theme hubs, and at least one entry. Theme hubs appear in Context & Connections as "Threads: [[Hub]] and [[Hub]]."
- Link only to titles that exist on disk; plain text otherwise, then the link pass.
- `date_start` = earliest firm evidence, not legend (Papyrus -2900, Variolation 1549, Chinampas 1150 were moved from the plan for this reason). Contested priority is stated inside the bullet; confidence medium or low.
- `sources`: only the 12 allowed titles, and only ones the research actually consulted.
- Observer vocabulary only in `## Observer's Reading` (2-5 sentences, must say what would weaken it): the species, meaning-engine, story-glue, claim-line, exchange-web, kin-lattice, sound-code / mark-code, memory-outsourcing, grief-rite, tool-lineage, sanctioned harm, the Settling, heat-domestication, status-signal, pattern-taming, ancestor-weight.
- No em or en dashes. Other sessions edit the vault live: fix only your own files' errors.

## Part B remaining (columns: title | date_start | era | region | themes | confidence | key facts and cautions)
### Batch 7
- Water Chlorination | 1897 approx | Industrial Age | Europe | science, technology | med | Maidstone 1897; Jersey City 1908
- Liquid-Fueled Rocket | 1926 year | Industrial Age | North America | technology, science | high | Goddard 16 Mar 1926; V-2 1942-44
- Nuclear Weapons | 1945 year | Information Age | North America | war, science | high | Trinity 16 Jul 1945; link Nuclear Age and Nuclear Fission
- Radiocarbon Dating | 1949 approx | Information Age | North America | science | high | Libby; Nobel Chemistry 1960
- Transistor | 1947 year | Information Age | North America | technology, science | high | Bell Labs Dec 1947; Nobel 1956
- Photovoltaic Cell | 1954 year | Information Age | North America | technology, earth-systems | high | Bell Labs silicon cell
- Container Shipping | 1956 year | Information Age | North America | trade | high | Ideal X, April 1956, McLean
- Hormonal Contraception | 1960 year | Information Age | North America | kinship, science | med | Enovid approval 1960; earlier progestin synthesis (verify)
### Batch 8
- Oral Rehydration Therapy | 1968 approx | Information Age | South Asia | science | med | Dhaka Cholera Research Laboratory 1960s; wide use 1971 (verify)
- Integrated Circuit | 1958 year | Information Age | North America | technology | high | Kilby 1958; Noyce 1959; Nobel 2000
- Internet | 1969 year | Information Age | North America | language, technology | high | ARPANET 1969 (link Digital Revolution); TCP/IP 1983 (verify)
- GPS | 1978 year | Information Age | North America | technology, science | high | first satellite 1978; full operation mid-1990s
- World Wide Web | 1989 year | Information Age | Europe | language, technology | high | Berners-Lee proposal 1989; public 1991 (link Digital Revolution)
- Smartphone | 1994 approx | Information Age | North America | technology | med | IBM Simon 1994; smartphones from about 2007 (link Digital Revolution)
- CRISPR Gene Editing | 2012 year | Information Age | North America | science | high | 2012 paper; Nobel Chemistry 2020; link Genomic Revolution
- mRNA Vaccines | 2020 year | Information Age | Planet-wide | science | high | authorized Dec 2020; link COVID-19 Pandemic; Nobel Medicine 2023
Quota check after Batch 8 (over all 64): at least 20 outside Europe and North America (plan had 28), at least 8 within the last 200 years, at least 8 before 500 BCE, artifacts present. Run a script to confirm.

## Part C: 18 essays in `05_Observer_Notes/`, batches 4, 4, 4, 4, 2
Frontmatter: title, type: observer-note, era (exactly one), themes, related, sources, confidence, status: seed, tags: [] (no region, no dates). Sections in order: `## Question`, `## What the Record Shows` (5-8 checkable bullets with wikilinks, at least 4 regions and 3 eras), `## Observer's Reading` (3-6 sentences, glossary terms, at least one alternative reading), `## Limits of This Reading` (2-4 sentences). 350-500 words. Title style "Short Title - Subtitle". Same standard for every culture; name an alternative reading; say what would weaken it. Run `check_notes.py --essay "Title"`.
| Batch | Title | Theme | Era |
|---|---|---|---|
| C1 | Institutionalized Doubt - How Strangers Learned to Check Each Other | science | Early Modern Period |
| C1 | Why the Same Discovery Happens Twice | science | Industrial Age |
| C1 | Why the Species Makes Things That Do Nothing | art | Paleolithic |
| C1 | Sacred Ground - Why Some Places Are Special | art | Neolithic |
| C2 | Why Languages Die and Why Some Spread | language | Early Modern Period |
| C2 | Scripts as Borders - Writing and Identity | language | Medieval Period |
| C2 | Why Prophets Appear in Clusters | religion | Iron Age |
| C2 | Why Every Meaning-Engine Splits | religion | Medieval Period |
| C3 | The Ratchet and Its Gaps - Why Some Tool-Lineages Stall | technology | Classical Antiquity |
| C3 | Who Gets Credit for the Machine | technology | Industrial Age |
| C3 | Why Strangers Trust Strangers - Money as Story-Glue | trade | Iron Age |
| C3 | Cargo That Was Not Goods - What Exchange-Webs Carry | trade | Classical Antiquity |
| C4 | Why Empires Keep Forming | war | Iron Age |
| C4 | The Aftermath Problem - How Societies Remember Their Wars | war | Industrial Age |
| C4 | The Kin-Lattice at Scale - From Households to States | kinship | Bronze Age |
| C4 | Who Counts as a Person - The Long Argument over Status | kinship | Industrial Age |
| C5 | The Long Partnership - Domesticates and the Species | earth-systems | Neolithic |
| C5 | Plague Years - Disease as a Historical Actor | earth-systems | Medieval Period |
Existing essays to link and stay consistent with: Fire, Then Everything; Frontiers of Extraction; Sanctioned Harm; Second Chances - How the Species Ran the Experiment Again; Story-Glue - How Strangers Cooperate at Scale; The Fiction of Claim-Lines; The Great Outsourcing of Memory; The Settling and Its Bargain; The Species as a Geological Force; Who Writes the Record; Why the Species Buries Its Dead. The many technology notes now on disk (72) are a good fact base; the Batch 3-6 examples of contested priority suit the two technology essays.
