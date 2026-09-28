"""Build _Museum/data/museum-manifest.json and _Museum/data/museum-layout.json.

Sources:
  Art-Talk-main/artists/*.md (+ data/image-credits.json)   the Art-Talk wing: 53 artists, 299 works
  _Site/data/notes-person.json (via people_entries.py)      the Earth Chronicle People wing: 203 people, 387 portraits
  data/work-dimensions.json (via build_dimensions.py)       real-world sizes (cached; defaults when missing)

Outputs:
  data/museum-manifest.json   rooms (the Grand Hall hub + 16 galleries), wings, artists and works
                              (with `dims`), the contract every viewer module reads
  data/museum-layout.json     the geometry of every scene (build_layout.py), read by scenes.js

Run: python3 _Museum/build_manifest.py [--lint]   (--lint: check only, write nothing)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

MUSEUM = Path(__file__).resolve().parent
ROOT = MUSEUM.parent
ART_TALK = ROOT / "Art-Talk-main"

sys.path.insert(0, str(ROOT / "_RAG"))
sys.path.insert(0, str(MUSEUM))
import vault  # noqa: E402 (reused, not modified)
import build_dimensions  # noqa: E402
import build_layout  # noqa: E402
import people_entries  # noqa: E402

# Gallery grouping by birth-year order, per Art-Talk-main/TIMELINE.md. Minimum room sizes
# come from the original Blender footprints (blender/scripts/rooms_v2.json); build_layout.py
# grows a room when its works need more wall.
ROOM_PLAN = [
    ("gallery-a", "Early Masters", "900s–1400s", 16, 14, [
        "murasaki-shikibu", "rumi", "amir-khusrau", "giotto", "van-eyck",
    ]),
    ("gallery-b", "Renaissance & Islamic Golden Age", "1400s–1500s", 16, 16, [
        "sesshu", "shen-zhou", "bosch", "behzad", "leonardo-da-vinci",
        "durer", "michelangelo", "mimar-sinan", "andrea-palladio",
    ]),
    ("gallery-c", "Baroque & Golden Ages", "1500s–1600s", 18, 18, [
        "bruegel", "sofonisba-anguissola", "basawan", "caravaggio",
        "artemisia-gentileschi", "velazquez", "rembrandt",
        "christopher-wren", "vermeer", "jeong-seon",
    ]),
    ("gallery-d", "Romanticism & Ukiyo-e", "1700s", 14, 12, [
        "goya", "hokusai", "turner", "jane-austen", "hiroshige",
    ]),
    ("gallery-e", "19th-Century Movements", "1800s", 18, 18, [
        "leo-tolstoy", "christopher-dresser", "william-morris", "monet",
        "velasco", "mary-cassatt", "louis-comfort-tiffany",
        "raja-ravi-varma", "antoni-gaudi", "van-gogh",
        "henry-ossawa-tanner",
    ]),
    ("gallery-f", "Avant-Garde & Early Cinema", "late 1800s–1900s", 20, 20, [
        "alphonse-mucha", "georges-melies", "lumiere-brothers", "klimt",
        "hilma-af-klint", "munch", "kandinsky", "frank-lloyd-wright",
        "charles-rennie-mackintosh", "alice-guy-blache", "buster-keaton",
        "sergei-eisenstein", "amrita-sher-gil",
    ]),
]
ART_INTROS = {
    "gallery-a": "Court scrolls, Persian poetry, Giotto's frescoes and the first oil masters, from the 900s to the 1400s.",
    "gallery-b": "The Renaissance in Italy and the golden ages of Persian, Ottoman and East Asian art.",
    "gallery-c": "Baroque drama, the Dutch Golden Age and the Mughal and Korean courts of the 1500s and 1600s.",
    "gallery-d": "Romantic painting and the Japanese woodblock print in the 1700s and early 1800s.",
    "gallery-e": "Impressionism, Arts and Crafts, the Mexican and Indian academies and the new design of the 1800s.",
    "gallery-f": "Art Nouveau, Expressionism, abstraction, modern architecture and the birth of cinema.",
}


def load_credits() -> dict:
    return json.loads((ART_TALK / "data" / "image-credits.json").read_text(encoding="utf-8"))


def art_talk_artists() -> tuple[list[dict], list[dict]]:
    credits = load_credits()
    slug_to_room = {}
    for room_id, _name, _era, _w, _d, slugs in ROOM_PLAN:
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
        # Art-Talk-main grew past the original 53; the museum only hangs the artists ROOM_PLAN places.
        print(f"warning: {len(missing_from_plan)} artist files have no room in ROOM_PLAN and are skipped: "
              f"{', '.join(sorted(missing_from_plan)[:8])}{' ...' if len(missing_from_plan) > 8 else ''}")
        artist_files = [p for p in artist_files if p.stem in planned_slugs]
    if missing_files:
        raise SystemExit(f"ROOM_PLAN references artist files that don't exist: {sorted(missing_files)}")

    order_index = {slug: i for i, slug in enumerate(slug_to_room)}
    artists = []
    for path in artist_files:
        fm, _body = vault.parse_note(path)
        slug = fm.get("slug") or path.stem
        works = []
        for w in fm.get("works", []):
            image_rel = f"images/{slug}/{w['id']}.jpg"
            works.append({
                "id": w.get("id"), "title": w.get("title"), "year": w.get("year"), "medium": w.get("medium"),
                "location": w.get("location"), "description": (w.get("description") or "").strip(),
                "image": image_rel, "credit": credits.get(image_rel),
            })
        artists.append({
            "slug": slug, "name": fm.get("name"), "short_name": fm.get("short_name") or fm.get("name"),
            "lifespan": fm.get("lifespan"), "region": fm.get("region"), "country": fm.get("country"),
            "movements": fm.get("movements") or [], "discipline": fm.get("discipline") or [],
            "wikipedia": fm.get("wikipedia"), "cover": fm.get("cover"), "room": slug_to_room[path.stem],
            "order": order_index[path.stem], "wing": "art-talk", "works": works,
        })
    artists.sort(key=lambda a: a["order"])
    specs = [{"id": rid, "name": name, "era": era, "years": era, "wing": "art-talk", "min_w": w, "min_d": d,
              "intro": {"title": name, "years": era, "summary": ART_INTROS.get(rid, "")}}
             for rid, name, era, w, d, _slugs in ROOM_PLAN]
    return artists, specs


def build() -> dict:
    artists, art_specs = art_talk_artists()
    people = people_entries.build()
    artists += people["artists"]
    people_specs = [{"id": r["id"], "name": r["name"], "era": r["era"], "years": r["years"], "wing": "people",
                     "min_w": r["min_w"], "min_d": r["min_d"], "intro": r["intro"]} for r in people["rooms"]]

    # real-world sizes (cache; type defaults for anything not resolved yet)
    cache = build_dimensions.load_cache()
    wings_by_id = {"art-talk": {"image_base": "Art-Talk-main/"}, "people": {"image_base": "_Site/"}}
    dims_index = {}
    for a in artists:
        for w in a["works"]:
            e = build_dimensions.dims_for(w, a, cache, wings_by_id)
            dims_index[w["id"]] = e
            w["dims"] = build_dimensions.public_dims(e)

    result = build_layout.build(art_specs + people_specs, artists, lambda w: dims_index[w["id"]])
    wings = [
        {"id": "art-talk", "name": "Art-Talk Wing", "image_base": "Art-Talk-main/", "rooms": [s["id"] for s in art_specs]},
        people["wing"],
    ]
    manifest = {"rooms": result["rooms"], "artists": artists, "wings": wings}
    return {"manifest": manifest, "layout_result": result, "artists": artists, "people": people}


def main(argv: list[str]) -> int:
    lint_only = "--lint" in argv
    out = build()
    manifest, result = out["manifest"], out["layout_result"]
    models = None
    try:
        models = json.loads((MUSEUM / "assets" / "models.json").read_text(encoding="utf-8"))["models"]
    except (OSError, ValueError, KeyError):
        pass
    errors = build_layout.lint(result, out["artists"], models)
    print(build_layout.report(result))
    if errors:
        print("LINT FAILED:")
        for e in errors[:60]:
            print("  -", e)
        return 1
    if lint_only:
        print("lint ok")
        return 0
    path = MUSEUM / "data" / "museum-manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    layout_path = build_layout.write_layout(result)
    n_artists = len(manifest["artists"])
    n_works = sum(len(a["works"]) for a in manifest["artists"])
    n_hangs = sum(len(sc["hangs"]) for sc in result["layout"]["scenes"].values())
    print(f"Wrote {path} — {n_artists} artists, {n_works} works, {len(manifest['rooms'])} rooms, {len(manifest['wings'])} wings.")
    print(f"Wrote {layout_path} — {len(result['layout']['scenes'])} scenes, {n_hangs} hangs.")
    print(f"People wing: {out['people']['people']} people, {out['people']['images']} portraits")
    refresh_rewrite_layer()
    return 0


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
    raise SystemExit(main(sys.argv[1:]))
