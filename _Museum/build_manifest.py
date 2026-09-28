"""Build _Museum/data/museum-manifest.json from Art-Talk-main artist profiles.

Parses each Art-Talk-main/artists/*.md frontmatter (name, lifespan, region,
movements, discipline, works[]) plus Art-Talk-main/data/image-credits.json,
assigns each artist to a gallery room per ROOM_PLAN (chronological grouping
from Art-Talk-main/TIMELINE.md), and writes one manifest consumed by both the
Blender build script (_Museum/blender/build_museum.py) and the web viewer
(_Museum/web/js/main.js).

Reuses _RAG/vault.py's frontmatter parser rather than reimplementing it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

MUSEUM = Path(__file__).resolve().parent
ROOT = MUSEUM.parent
ART_TALK = ROOT / "Art-Talk-main"

sys.path.insert(0, str(ROOT / "_RAG"))
import vault  # noqa: E402 (reused, not modified)

# Gallery grouping by birth-year order, per Art-Talk-main/TIMELINE.md.
ROOM_PLAN = [
    ("gallery-a", "Early Masters", "900s-1400s", [
        "murasaki-shikibu", "rumi", "amir-khusrau", "giotto", "van-eyck",
    ]),
    ("gallery-b", "Renaissance & Islamic Golden Age", "1400s-1500s", [
        "sesshu", "shen-zhou", "bosch", "behzad", "leonardo-da-vinci",
        "durer", "michelangelo", "mimar-sinan", "andrea-palladio",
    ]),
    ("gallery-c", "Baroque & Golden Ages", "1500s-1600s", [
        "bruegel", "sofonisba-anguissola", "basawan", "caravaggio",
        "artemisia-gentileschi", "velazquez", "rembrandt",
        "christopher-wren", "vermeer", "jeong-seon",
    ]),
    ("gallery-d", "Romanticism & Ukiyo-e", "1700s", [
        "goya", "hokusai", "turner", "jane-austen", "hiroshige",
    ]),
    ("gallery-e", "19th-Century Movements", "1800s (core)", [
        "leo-tolstoy", "christopher-dresser", "william-morris", "monet",
        "velasco", "mary-cassatt", "louis-comfort-tiffany",
        "raja-ravi-varma", "antoni-gaudi", "van-gogh",
        "henry-ossawa-tanner",
    ]),
    ("gallery-f", "Avant-Garde & Early Cinema", "late 1800s-1900s", [
        "alphonse-mucha", "georges-melies", "lumiere-brothers", "klimt",
        "hilma-af-klint", "munch", "kandinsky", "frank-lloyd-wright",
        "charles-rennie-mackintosh", "alice-guy-blache", "buster-keaton",
        "sergei-eisenstein", "amrita-sher-gil",
    ]),
]

# Rotunda + mezzanine + a stubbed future-wing doorway tie the galleries together
# as one linear enfilade (Grand Rotunda -> A -> B -> C -> D -> up to Mezzanine ->
# E -> F), matching the physical spine-hall floor plan built in Blender.
#
# `position` is each room's center (floor level + 0.05, for a ground-hugging
# waypoint trail), and `doors` maps a neighbor room id -> the world position of
# the physical doorway shared with that neighbor (matching the exact
# coordinates used in _Museum/blender/build_museum.py). A straight line between
# two consecutive doors is always open corridor space in this floor plan, so
# room -> door -> door -> room is enough to route the trail without cutting
# through walls; the mezzanine is the one special case (its two doors sit at
# different levels, since one is the foot of the stairs and the other the
# landing above).
ROOMS = [
    {"id": "rotunda", "name": "Grand Rotunda", "kind": "entry",
     "connects_to": ["gallery-a", "future-wing-1"],
     "position": [0.0, 0.0, 0.05],
     "doors": {"gallery-a": [7.0, 0.0, 0.05], "future-wing-1": [-7.0, 0.0, 0.05]}},
    {"id": "gallery-a", "name": "Early Masters", "era": "900s-1400s", "kind": "gallery",
     "connects_to": ["rotunda", "gallery-b"],
     "position": [20.0, 10.0, 0.05],
     "doors": {"rotunda": [20.0, 3.0, 0.05], "gallery-b": [20.0, 3.0, 0.05]}},
    {"id": "gallery-b", "name": "Renaissance & Islamic Golden Age", "era": "1400s-1500s", "kind": "gallery",
     "connects_to": ["gallery-a", "gallery-c"],
     "position": [36.0, -11.0, 0.05],
     "doors": {"gallery-a": [36.0, -3.0, 0.05], "gallery-c": [36.0, -3.0, 0.05]}},
    {"id": "gallery-c", "name": "Baroque & Golden Ages", "era": "1500s-1600s", "kind": "gallery",
     "connects_to": ["gallery-b", "gallery-d"],
     "position": [54.0, 12.0, 0.05],
     "doors": {"gallery-b": [54.0, 3.0, 0.05], "gallery-d": [54.0, 3.0, 0.05]}},
    {"id": "gallery-d", "name": "Romanticism & Ukiyo-e", "era": "1700s", "kind": "gallery",
     "connects_to": ["gallery-c", "mezzanine"],
     "position": [70.0, -9.0, 0.05],
     "doors": {"gallery-c": [70.0, -3.0, 0.05], "mezzanine": [70.0, -3.0, 0.05]}},
    {"id": "mezzanine", "name": "Grand Staircase & Mezzanine", "kind": "level",
     "connects_to": ["gallery-d", "gallery-e"],
     "position": [91.0, 0.0, 7.05],
     "doors": {"gallery-d": [84.0, 0.0, 0.05], "gallery-e": [64.0, 3.0, 7.05]}},
    {"id": "gallery-e", "name": "19th-Century Movements", "era": "1800s (core)", "kind": "gallery",
     "connects_to": ["mezzanine", "gallery-f"],
     "position": [64.0, 12.0, 7.05],
     "doors": {"mezzanine": [64.0, 3.0, 7.05], "gallery-f": [64.0, 3.0, 7.05]}},
    {"id": "gallery-f", "name": "Avant-Garde & Early Cinema", "era": "late 1800s-1900s", "kind": "gallery",
     "connects_to": ["gallery-e"],
     "position": [18.0, 0.0, 7.05],
     "doors": {"gallery-e": [28.0, 0.0, 7.05]}},
    {"id": "future-wing-1", "name": "Future Wing (reserved)", "kind": "stub",
     "connects_to": ["rotunda"],
     "position": [-11.5, 0.0, 0.05],
     "doors": {"rotunda": [-7.0, 0.0, 0.05]}},
]


def load_credits() -> dict:
    return json.loads((ART_TALK / "data" / "image-credits.json").read_text(encoding="utf-8"))


def build() -> dict:
    credits = load_credits()
    slug_to_room = {}
    for room_id, _name, _era, slugs in ROOM_PLAN:
        for slug in slugs:
            if slug in slug_to_room:
                raise SystemExit(f"slug {slug!r} assigned to two rooms")
            slug_to_room[slug] = room_id

    artist_files = sorted((ART_TALK / "artists").glob("*.md"))
    found_slugs = {p.stem for p in artist_files}
    planned_slugs = set(slug_to_room)
    missing_from_plan = found_slugs - planned_slugs
    missing_files = planned_slugs - found_slugs
    if missing_from_plan:
        # Art-Talk-main grew past the original 53 (see _RAG/handoff/HANDOFF_Art_Section_Expansion.md);
        # the museum only hangs the artists that ROOM_PLAN places, so skip the rest.
        print(f"warning: {len(missing_from_plan)} artist files have no room in ROOM_PLAN and are skipped: "
              f"{', '.join(sorted(missing_from_plan)[:8])}{' ...' if len(missing_from_plan) > 8 else ''}")
        artist_files = [p for p in artist_files if p.stem in planned_slugs]
    if missing_files:
        raise SystemExit(f"ROOM_PLAN references artist files that don't exist: {sorted(missing_files)}")

    # Preserve TIMELINE.md's birth-year order: ROOM_PLAN lists rooms/artists in that order already.
    order_index = {slug: i for i, slug in enumerate(slug_to_room)}

    artists = []
    for path in artist_files:
        fm, _body = vault.parse_note(path)
        slug = fm.get("slug") or path.stem
        works = []
        for w in fm.get("works", []):
            image_rel = f"images/{slug}/{w['id']}.jpg"
            credit = credits.get(image_rel)
            works.append({
                "id": w.get("id"),
                "title": w.get("title"),
                "year": w.get("year"),
                "medium": w.get("medium"),
                "location": w.get("location"),
                "description": (w.get("description") or "").strip(),
                "image": image_rel,
                "credit": credit,
            })
        room_id = slug_to_room[path.stem]
        artists.append({
            "slug": slug,
            "name": fm.get("name"),
            "short_name": fm.get("short_name") or fm.get("name"),
            "lifespan": fm.get("lifespan"),
            "region": fm.get("region"),
            "country": fm.get("country"),
            "movements": fm.get("movements") or [],
            "discipline": fm.get("discipline") or [],
            "wikipedia": fm.get("wikipedia"),
            "cover": fm.get("cover"),
            "room": room_id,
            "order": order_index[path.stem],
            "works": works,
        })
    artists.sort(key=lambda a: a["order"])

    return {"rooms": ROOMS, "artists": artists}


def main() -> None:
    manifest = build()
    out = MUSEUM / "data" / "museum-manifest.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    n_artists = len(manifest["artists"])
    n_works = sum(len(a["works"]) for a in manifest["artists"])
    print(f"Wrote {out} — {n_artists} artists, {n_works} works, {len(manifest['rooms'])} rooms.")
    refresh_rewrite_layer()


def refresh_rewrite_layer() -> None:
    """Republish the AI rewrite layer (_Rewrite/) so a placard whose text changed drops its stale rewrite, and say what is pending."""
    import importlib.util
    path = ROOT / "_Rewrite" / "rewrite_layer.py"
    if not path.exists():
        return
    spec = importlib.util.spec_from_file_location("rewrite_layer", path)
    rl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rl)
    rl.cmd_publish(None)
    n = len(rl.pending_ids("museum", rl.SOURCES["museum"]()))
    if n:
        print(f"rewrite layer: {n} placards not rewritten yet; ask the chronicle-rewriter agent for 'pending museum'")


if __name__ == "__main__":
    main()
