# Earth Chronicle RAG

Local, CPU-only retrieval over the vault. No API keys, no cloud calls (after the one-time model download).

## How it works
1. **Chunk**: every note is split by `##` heading (long sections are split further, with overlap). Generated hub lists are skipped. Each chunk is prefixed with `Title (type; era; region) > Heading` so it keeps its context.
2. **Embed**: chunks are embedded with `BAAI/bge-small-en-v1.5` (via `fastembed`, ONNX, CPU).
3. **Store**: SQLite (`index/vault.db`) holds chunks, vectors, note metadata (type, era, region, themes, dates, links), and an FTS5 keyword index.
4. **Search**: cosine similarity and BM25 are combined with reciprocal-rank fusion, then weighted by section (answers outrank "Open Questions"). Optional metadata filters and one-hop wikilink expansion.

Because `## Facts` and `## Observer's Reading` are separate chunks, a query can return facts or interpretation independently.

## Setup (already done on this machine)
```bash
python -m venv _RAG/.venv
_RAG/.venv/Scripts/python.exe -m pip install -r _RAG/requirements.txt
_RAG/.venv/Scripts/python.exe _RAG/build_index.py
```
First build downloads the model (~130 MB) into `_RAG/index/model_cache`. Windows may log a symlink warning; it is harmless.

## Daily workflow
```bash
python _RAG/tools/validate_vault.py    # schema, folders, sections, broken links, orphans
python _RAG/tools/update_hubs.py       # regenerate era/region/theme member lists and timelines
python _RAG/build_index.py             # incremental: only changed notes are re-embedded
```
(Use `_RAG/.venv/Scripts/python.exe` in place of `python`.) `build_index.py --force` rebuilds everything.

## Command-line search
```bash
python _RAG/search.py "when did humans first control fire"
python _RAG/search.py "trade networks" --type event --era "Classical Antiquity" -k 5
python _RAG/search.py "plague" --from -1000 --to 1500 --expand
python _RAG/search.py "borders" --theme war --json
```
Filters: `--type`, `--era`, `--region` (exact note titles), `--theme` (slug), `--from/--to` (years relative to 1 CE, negative = BCE).

## MCP server (lets Claude query the vault)
`.mcp.json` at the vault root registers the server `earth-chronicle` using absolute paths. Open this folder in Claude Code and approve the project server. If the vault moves, update the two paths in `.mcp.json`.

| Tool | Purpose |
|---|---|
| `search_vault(query, k, type, era, region, theme, date_from, date_to, expand)` | hybrid search; returns note sections with metadata |
| `get_note(name)` | full markdown of a note by title or path |
| `get_neighbors(name)` | outgoing and incoming wikilinks with summaries |
| `list_timeline(start, end, theme, types)` | chronological listing |
| `reindex(force)` | re-scan the vault after edits |

The server auto-detects `mcp` 2.x (`MCPServer`) or 1.x (`FastMCP`).

## Files
| File | Role |
|---|---|
| `vault.py` | vault walking, frontmatter parsing, wikilink extraction |
| `build_index.py` | chunk, embed, and store |
| `search.py` | hybrid retrieval, graph lookups, CLI |
| `mcp_server.py` | MCP tools |
| `tools/validate_vault.py` | schema and link validator |
| `tools/update_hubs.py` | generates hub member lists and timelines |
| `tools/fetch_source.py` | reads a source's raw text through routes that work, caches it in `source_cache/`, checks `fact_checks` against it |
| `tools/apply_patch.py` | guarded bulk edits to notes and source notes (exact-once text matches, backups, `fact_checks` bookkeeping) |
| `tools/audit_claims.py` | counts Facts bullets not covered by a `fact_checks` line (compare per patched note, not globally) |
| `tools/helpers/` | scripts for the re-read project, all resolving paths through `_paths.py` (see below) |
| `config.yaml` | model, chunking, search weights |
| `index/` | generated (git-ignored): database and model cache |

## Re-reading sources (fact-checking)
WebFetch returns a model-written summary, and Britannica, science.org, pnas.org, PMC and PubMed web pages refuse automated requests. `tools/fetch_source.py` reads the raw text instead, and never bypasses a CAPTCHA, cookie wall or paywall:

| Kind of source | Route |
|---|---|
| Paper (DOI, PMC or PubMed id) | Europe PMC full text, open-access PDF from OpenAlex, publisher page, PubMed abstract, OpenAlex abstract, Crossref, Wayback Machine |
| Wikipedia | MediaWiki API: raw wikitext plus the revision id |
| Britannica and other blocking hosts | Wayback Machine snapshot (the snapshot date is recorded) |
| Anything else | direct request, then Wayback Machine |

```bash
python _RAG/tools/fetch_source.py fetch "Britannica on Timur"        # cache the text and metadata in _RAG/source_cache/
python _RAG/tools/fetch_source.py claims "Britannica on Timur"       # each fact_check citing it, matched against the real text
python _RAG/tools/fetch_source.py grep "Britannica on Timur" "born 1336"
python _RAG/tools/fetch_source.py queue build                        # one entry per source note, in six tiers
python _RAG/tools/fetch_source.py batch --tier 3 -n 10               # fetch the next ten pending sources of a tier
python _RAG/tools/apply_patch.py spec.json --dry                     # then without --dry: the guarded way to edit notes
```
Helper scripts in `tools/helpers/` (run with the venv Python from anywhere):

| Script | Use |
|---|---|
| `status_table.py TIER` | fetch result per source of a tier: level, route, size, hosts that refused |
| `probe.py` | stdin lines `Source title\|\|term1\|term2` print the matching passages of that source's cached text |
| `showchecks.py "Note"` | a note's sources, `fact_checks`, Facts and Open Questions |
| `t2_report.py TIER LO HI` | each source's abstract beside every check that cites it |
| `t3_claims.py TIER LO HI` / `t3_usedfor.py TIER` | best snippet per check / each source note's used-for claims matched against its text |
| `t2_build.py TIER` | builds `source_updates` (access, route, Caveats) from fetch metadata plus `specs/tierN_manual.json`; cuts a citation that bundles unread "Also ..." pages and records the cut in Caveats |
| `tier3_manual.py` (template: `t2_manual.py`) | hand-written per-source extras, new sources, note patches, discrepancies and the unresolved list for a tier |
| `merge_spec.py TIER` | merges the builder output and the extras into `specs/tierN.json` for `apply_patch.py` |

Generated specs live in `source_cache/specs/`. `source_cache/discrepancies.md` logs each correction; `source_cache/unresolved.md` logs claims that stay in a note although the page cited for them does not contain them (probably correct, unconfirmed), for a later tier to re-attribute. A source note titled `Encyclopaedia Britannica` or `English Wikipedia` stands for the whole work and is `access: not-consulted`: a check should cite the specific article.

A contact email for the polite-pool APIs (Crossref, OpenAlex, NCBI, Wikimedia) comes from the `EARTH_FETCH_EMAIL` environment variable or `_RAG/fetch_config.local.json` (git-ignored, never written into a note). Cached text, `queue.json`, `discrepancies.md` and patch backups live in `_RAG/source_cache/` (git-ignored). Install `pypdf` (in `requirements.txt`) for PDF sources.

## Tuning
Edit `config.yaml`: `chunking.max_words`, `search.heading_weights`, `search.candidates`. Changing `embedding.model` triggers a full rebuild automatically.

## Note on OneDrive
This vault sits in a OneDrive folder. `_RAG/.venv` and `_RAG/index` are large and regenerable; consider excluding them from sync (OneDrive: right-click the folder, "Free up space", or move the vault out of OneDrive).
