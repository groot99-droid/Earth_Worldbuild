# Obsidian setup

Open the vault folder (`Earth _WorldBuilding`) via **Open folder as vault**. The core settings are pre-configured in `.obsidian/`: wikilinks (shortest paths), templates folder `_Templates`, `_RAG/` and `_Templates/` hidden from search, and graph colour groups by folder (eras, regions, events, people, cultures, species, themes, essays).

Community plugins cannot be installed automatically. Install these from **Settings > Community plugins > Browse**:

| Plugin | Why | Notes |
|---|---|---|
| **Smart Connections** | Semantic search and chat inside Obsidian (its own embeddings) | Independent of `_RAG/`; point it at the vault, exclude `_RAG/` and `_Templates/` in its settings. |
| **Dataview** | Live tables and queries from frontmatter | Optional: the generated timelines already work without it. |
| **Templater** | Richer templates | Optional: the core Templates plugin already reads `_Templates/`. |

## Handy Dataview queries (require the Dataview plugin)
Events in an era:
```dataview
TABLE date_start AS "Start", region
FROM "03_Entities/Events"
WHERE contains(string(era), "Paleolithic")
SORT date_start ASC
```
Low-confidence notes needing review:
```dataview
LIST
WHERE confidence = "low" OR status = "seed"
SORT type ASC
```

## Two search systems, one vault
- `_RAG/` (this project's index) powers the MCP server used by Claude Code and scripts.
- Smart Connections powers in-app semantic search. They do not share an index; both read the same Markdown files.
