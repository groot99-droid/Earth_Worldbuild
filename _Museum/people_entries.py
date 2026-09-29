"""Earth Chronicle "People" entries for the Chronicle Museum (no geometry here).

Reads _Site/data/notes-person.json (203 people, 387 credited images) and returns one
artist-shaped manifest entry per person whose works are that person's images (globally
unique ids `people--<slug>--<n>`), assigned to era rooms. build_layout.py hangs them;
this module only decides who goes in which room and what the placards say.

Room ids (`people-<era>[-n]`) are stable: the rewrite layer and deep links depend on them.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

MUSEUM = Path(__file__).resolve().parent
ROOT = MUSEUM.parent
SITE = ROOT / "_Site"

WING_ID = "people"
ERA_ORDER = ["bronze-age", "iron-age", "classical-antiquity", "medieval-period",
             "early-modern-period", "industrial-age", "information-age"]

# (era, part, min width, min depth) in metres. Sizes are minimums: build_layout.py grows a
# room when its works need more wall. Eras with two parts split their people by birth year.
ROOM_PLAN = [
    ("bronze-age", 1, 12, 10),
    ("iron-age", 1, 12, 10),
    ("classical-antiquity", 1, 16, 14),
    ("medieval-period", 1, 20, 16),
    ("medieval-period", 2, 20, 16),
    ("early-modern-period", 1, 18, 14),
    ("early-modern-period", 2, 18, 14),
    ("industrial-age", 1, 24, 18),
    ("industrial-age", 2, 24, 18),
    ("information-age", 1, 12, 10),
]
ROMAN = {1: "I", 2: "II", 3: "III"}

# Numeric bounds of the eras (01_Eras/*.md front matter); the summary text gives the words.
ERA_YEARS = {
    "bronze-age": (-3300, -1200), "iron-age": (-1200, -500), "classical-antiquity": (-500, 500),
    "medieval-period": (500, 1500), "early-modern-period": (1500, 1800), "industrial-age": (1760, 1945),
    "information-age": (1945, None),
}


# ---------------------------------------------------------------- text ---------------
def strip_tags(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def tidy_caption(s: str) -> str:
    """Some site captions are Commons file stems ("Kleopatra-VII.-Altes-Museum-Berlin1"): make them readable."""
    s = strip_tags(s)
    if " " in s or not s:
        return s
    s = re.sub(r"[-_]+", " ", s)
    s = re.sub(r"\.(?=\s|$)", "", s)
    s = re.sub(r"(?<=[A-Za-z])\d$", "", s)   # trailing disambiguation digit
    return re.sub(r"\s+", " ", s).strip()


def parse_lifespan(summary_text: str):
    """First parenthetical containing a digit -> ("1815–1852", 1815). BCE years are negative."""
    m = re.search(r"\(([^()]*\d[^()]*)\)", summary_text)
    if not m:
        return None, None
    span = re.sub(r"\s+to\s+", "–", m.group(1).strip())
    nums = re.findall(r"\d{1,4}", span)
    if not nums:
        return span, None
    big = [n for n in nums if len(n) >= 3]
    born = int(big[0] if big else nums[0])
    if re.search(r"\b(BCE|BC)\b", span):
        born = -born
    return span, born


def fmt_year(y: int) -> str:
    return f"{-y} BCE" if y < 0 else str(y)


def era_years_label(era: str) -> str:
    a, b = ERA_YEARS.get(era, (None, None))
    if a is None:
        return ""
    return f"{fmt_year(a)} – {fmt_year(b) if b is not None else 'today'}"


def era_intro(era: str) -> dict:
    """{title, years, summary}: the room's title card, from the site's era note."""
    eras = json.loads((SITE / "data" / "notes-era.json").read_text(encoding="utf-8"))
    e = eras.get(f"era/{era}", {})
    summary = strip_tags(e.get("summary", ""))
    first = re.split(r"(?<=[.!?])\s+", summary)[0] if summary else ""
    return {"title": e.get("title") or era.replace("-", " ").title(), "years": era_years_label(era), "summary": first}


# ---------------------------------------------------------------- people -------------
def load_people() -> list[dict]:
    people = json.loads((SITE / "data" / "notes-person.json").read_text(encoding="utf-8"))
    eras = json.loads((SITE / "data" / "notes-era.json").read_text(encoding="utf-8"))
    regions = json.loads((SITE / "data" / "notes-region.json").read_text(encoding="utf-8"))
    out = []
    for pid, e in people.items():
        slug = pid.split("/", 1)[1]
        summary = strip_tags(e.get("summary", ""))
        lifespan, born = parse_lifespan(summary)
        era_id = next((o for o in e.get("out", []) if o.startswith("era/")), None)
        region_id = next((o for o in e.get("out", []) if o.startswith("region/")), None)
        era = {"slug": era_id.split("/", 1)[1], "title": eras.get(era_id, {}).get("title", era_id)} if era_id else None
        region = regions.get(region_id, {}).get("title") if region_id else None
        facts = [strip_tags(f) for f in (e.get("facts") or [])][:5]
        description = "\n\n".join([summary] + [f for f in facts if f]).strip()
        images = []
        for i, im in enumerate(e.get("images") or [], start=1):
            images.append({
                "n": i, "src": im.get("src"), "thumb": im.get("thumb") or im.get("src"),
                "caption": tidy_caption(im.get("caption", "")), "author": im.get("author"),
                "license": im.get("license"), "license_url": im.get("license_url"), "source": im.get("source"),
                "via": im.get("via"), "ai": bool(im.get("ai")), "model": im.get("model"),
                "w": im.get("w") or 3, "h": im.get("h") or 4,
            })
        if not images:
            continue
        out.append({
            "slug": slug, "id": pid, "name": e.get("title", slug), "lifespan": lifespan, "born": born,
            "era": era, "region": region,
            "themes": [{"slug": t.get("slug"), "title": (t.get("slug") or "").replace("-", " ").title()} for t in (e.get("themes") or [])],
            "description": description, "images": images,
        })
    out.sort(key=lambda p: (p["era"]["slug"] if p["era"] else "", p["born"] is None, p["born"] if p["born"] is not None else 0, p["name"]))
    return out


def room_id(era: str, part: int, parts: int) -> str:
    return f"people-{era}" + (f"-{part}" if parts > 1 else "")


def room_records() -> list[dict]:
    parts: dict[str, int] = {}
    for era, part, *_ in ROOM_PLAN:
        parts[era] = max(parts.get(era, 0), part)
    rooms = []
    for era, part, w, d in ROOM_PLAN:
        rooms.append({"id": room_id(era, part, parts[era]), "era": era, "part": part, "parts": parts[era],
                      "min_w": float(w), "min_d": float(d)})
    return rooms


def assign_rooms(people: list[dict], rooms: list[dict]) -> dict[str, list[dict]]:
    """Persons per room: each era's people (birth order) split into its rooms in contiguous chunks."""
    by_era: dict[str, list[dict]] = {}
    for p in people:
        by_era.setdefault(p["era"]["slug"] if p["era"] else "unknown", []).append(p)
    unknown = [p for p in people if not p["era"]]
    if unknown:
        raise SystemExit(f"{len(unknown)} people have no era link: {[p['slug'] for p in unknown][:5]}")
    assignment: dict[str, list[dict]] = {}
    for era in ERA_ORDER:
        era_rooms = [r for r in rooms if r["era"] == era]
        ps = by_era.pop(era, [])
        if not era_rooms:
            raise SystemExit(f"no room planned for era {era} ({len(ps)} people)")
        k = len(era_rooms)
        for i, r in enumerate(era_rooms):
            lo = round(i * len(ps) / k)
            hi = round((i + 1) * len(ps) / k)
            assignment[r["id"]] = ps[lo:hi]
    if by_era:
        raise SystemExit(f"eras without a room in ERA_ORDER: {sorted(by_era)}")
    return assignment


# ---------------------------------------------------------------- build --------------
def build() -> dict:
    """{"rooms": [manifest room stubs], "artists": [...], "wing": {...}, "people": n, "images": n}"""
    people = load_people()
    rooms = room_records()
    assignment = assign_rooms(people, rooms)
    era_titles = {p["era"]["slug"]: p["era"]["title"] for p in people if p["era"]}

    manifest_rooms = []
    artists = []
    order = 1000
    n_images = 0
    for room in rooms:
        persons = assignment.get(room["id"], [])
        title = era_titles.get(room["era"], room["era"].replace("-", " ").title())
        name = title + (f" {ROMAN[room['part']]}" if room["parts"] > 1 else "")
        intro = era_intro(room["era"])
        intro["title"] = name
        manifest_rooms.append({
            "id": room["id"], "name": name, "era": title, "years": era_years_label(room["era"]), "kind": "gallery",
            "wing": WING_ID, "intro": intro, "min_w": room["min_w"], "min_d": room["min_d"], "era_slug": room["era"],
        })
        for p in persons:
            works = []
            for im in p["images"]:
                works.append({
                    "id": f"people--{p['slug']}--{im['n']}", "title": p["name"], "year": None,
                    "medium": (im["caption"][:77] + "…") if len(im["caption"]) > 80 else im["caption"],
                    "location": None, "description": p["description"],
                    "image": im["src"], "thumb": im["thumb"], "w": im["w"], "h": im["h"],
                    "credit": {"work": im["caption"], "file": im["src"], "source": im["source"], "author": im["author"],
                               "license": im["license"], "license_url": im["license_url"], "via": im["via"],
                               "ai": im["ai"], "model": im["model"]},
                })
                n_images += 1
            artists.append({
                "slug": p["slug"], "name": p["name"], "short_name": p["name"], "lifespan": p["lifespan"], "born": p["born"],
                "region": p["region"], "country": None, "movements": [], "discipline": ["portrait"], "wikipedia": None,
                "cover": p["images"][0]["thumb"], "room": room["id"], "order": order, "wing": WING_ID,
                "person_id": p["id"], "era": p["era"], "themes": p["themes"], "works": works,
            })
            order += 1

    born = [p["born"] for p in people if p["born"] is not None]
    wing = {
        "id": WING_ID, "name": "Earth Chronicle People", "image_base": "_Site/",
        "nouns": ["people", "portraits"], "years": f"{fmt_year(min(born))}–{fmt_year(max(born))}",
        "rooms": [r["id"] for r in rooms],
    }
    return {"rooms": manifest_rooms, "artists": artists, "wing": wing, "people": len(people), "images": n_images}


if __name__ == "__main__":
    res = build()
    print(f"{res['people']} people, {res['images']} images, {len(res['rooms'])} rooms")
    for r in res["rooms"]:
        n = sum(len(a["works"]) for a in res["artists"] if a["room"] == r["id"])
        print(f"  {r['id']:32s} {r['name']:24s} {r['years']:22s} works {n:3d}  min {r['min_w']:.0f}×{r['min_d']:.0f}")
        print(f"      {r['intro']['summary'][:110]}")
