"""Shared path setup for the re-read helper scripts.

Importing this module makes vault.py and fetch_source.py importable no matter where the script is run from,
and defines WORK, the folder where generated patch specs go (inside source_cache, so it stays local).
"""
import sys
from pathlib import Path

HELPERS = Path(__file__).resolve().parent
TOOLS = HELPERS.parent
RAG = TOOLS.parent
VAULT = RAG.parent
WORK = RAG / "source_cache" / "specs"

for _p in (str(TOOLS), str(RAG)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
