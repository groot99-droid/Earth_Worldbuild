"""MCP server exposing the Earth Chronicle vault to Claude (stdio transport).

Tools: search_vault, get_note, get_neighbors, list_timeline, reindex.
Register it via the project-level `.mcp.json` at the vault root. Nothing may be printed to stdout
here: stdout carries the MCP protocol.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:  # mcp >= 2
    from mcp.server.mcpserver import MCPServer as Server
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as Server

from build_index import build  # noqa: E402
from search import VaultSearch  # noqa: E402

mcp = Server(
    "earth-chronicle",
    instructions=(
        "Search tool for the Earth Chronicle vault: a history of Earth from planetary formation to today, "
        "written with an 'Observer' (outside anthropologist) lens. Each note separates neutral FACTS from an "
        "'Observer's Reading' interpretation, so cite facts from '## Facts'/'## Summary' and treat "
        "'Observer's Reading' as interpretation. Notes marked status=seed are unreviewed; state uncertainty "
        "when confidence is medium or low. Use search_vault first, then get_note for full text."
    ),
)

_vs: VaultSearch | None = None


def vs() -> VaultSearch:
    global _vs
    if _vs is None:
        _vs = VaultSearch()
    return _vs


def _fmt_results(results: list[dict]) -> str:
    if not results:
        return "No results."
    out = []
    for r in results:
        meta = f"{r['type']}" + (f", {r['date']}" if r["date"] else "") + f" | confidence={r['confidence']} status={r['status']}"
        out.append(f"### {r['rank']}. {r['title']} - {r['heading']}\n({meta}; era={r['era']}; region={r['region']}; path={r['path']})\n\n{r['text']}")
        if r.get("neighbors"):
            out.append("Linked notes: " + ", ".join(f"{n['title']} [{n['type']}]" for n in r["neighbors"]))
    return "\n\n".join(out)


@mcp.tool()
def search_vault(
    query: str,
    k: int = 8,
    type: str | None = None,
    era: str | None = None,
    region: str | None = None,
    theme: str | None = None,
    date_from: int | None = None,
    date_to: int | None = None,
    expand: bool = False,
) -> str:
    """Hybrid (semantic + keyword) search over the vault. Returns the best-matching note sections.

    Filters (all optional): type = event|person|place|culture|species|technology|era|region|theme|observer-note;
    era / region = exact note title (e.g. "Paleolithic", "Mesopotamia"); theme = science|technology|religion|war|
    trade|kinship|language|art|earth-systems; date_from / date_to = years relative to 1 CE (negative = BCE,
    e.g. -66000000 for 66 million years ago). expand=True also lists notes linked from the top hits.
    """
    return _fmt_results(vs().search(query, k=k, expand=expand, type=type, era=era, region=region,
                                    theme=theme, date_from=date_from, date_to=date_to))


@mcp.tool()
def get_note(name: str) -> str:
    """Return the full markdown (frontmatter and body) of a note, by title (e.g. "Control of Fire") or vault path."""
    return vs().read_note(name)


@mcp.tool()
def get_neighbors(name: str) -> str:
    """List notes a note links to (outgoing) and notes that link to it (incoming), with one-line summaries."""
    res = vs().neighbors(name)
    if "error" in res:
        return res["error"]

    def lines(items):
        return "\n".join(f"- {n['title']} [{n['type']}] {n.get('date', '')}: {n.get('summary', '')[:160]}" for n in items) or "(none)"

    return f"# {res['title']}\n\n## Outgoing links\n{lines(res['outgoing'])}\n\n## Incoming links\n{lines(res['incoming'])}"


@mcp.tool()
def list_timeline(
    start: int | None = None,
    end: int | None = None,
    theme: str | None = None,
    types: list[str] | None = None,
) -> str:
    """Chronological list of notes between two years (relative to 1 CE; negative = BCE), optionally by theme.

    types defaults to ["event"]; other options: era, person, culture, place, species, technology.
    """
    rows = vs().timeline(start=start, end=end, theme=theme, types=tuple(types or ["event"]))
    if not rows:
        return "No notes in that range."
    return "\n".join(f"- {r['date']}: {r['title']} [{r['type']}] (era: {r['era']}; region: {r['region']})" for r in rows)


@mcp.tool()
def reindex(force: bool = False) -> str:
    """Re-scan the vault and update the search index (run after adding or editing notes)."""
    stats = build(force=force, verbose=False)
    vs().reload()
    return f"Index updated: {stats}"


if __name__ == "__main__":
    mcp.run()
