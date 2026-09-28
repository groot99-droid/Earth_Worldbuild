"""Build the Earth Chronicle "People" wing of the Chronicle Museum, without Blender.

Reads _Site/data/notes-person.json (203 people, 387 credited images) and produces:

* manifest additions (returned to build_manifest.py): ten era rooms plus a spine hall
  west of the rotunda's vestibule, and one artist-shaped entry per person whose works
  are that person's images (globally unique ids `people--<slug>--<n>`), so the viewer's
  placards, minimap, go-to menu, guided tour and the rewrite layer need no changes;
* _Museum/data/people-wing.json: the procedural geometry the viewer builds at load time
  (web/js/procwing.js) — every wall/floor/ceiling/trim box and every hang position.

Coordinates are Blender Z-up metres (x east, y north, z up), like the manifest; the
viewer converts with coords.js. Rooms are bounded by their wall centre-lines (walls are
0.4 thick, the interior face 0.2 inward), art planes hang 0.25 from the centre-line
(0.05 proud of the face), exactly like the exported galleries. Each person gets one
"salon column": their 1-3 images stacked, so a room's wall holds a chronological row of
people. `lint()` checks the result before build_manifest.py writes anything.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

MUSEUM = Path(__file__).resolve().parent
ROOT = MUSEUM.parent
SITE = ROOT / "_Site"
LAYOUT_OUT = MUSEUM / "data" / "people-wing.json"

WING_ID = "people"
WALL_T = 0.4
HEIGHT = 7.0
DOOR_W = 3.2
DOOR_H = 3.8
INSET = 1.0          # m of wall left free at each end
ART_OFFSET = 0.25    # plane centre from the wall centre-line
H_MAX = 1.1          # image height (m) for stacks of 1-2
H_MAX3 = 1.05        # ... for stacks of 3
W_MAX = 1.4
GAP_MIN, GAP_MAX = 0.5, 1.2
ROW_Z = {1: [1.7], 2: [1.2, 2.5], 3: [0.95, 2.15, 3.35]}   # image centre heights above the floor
MIN_SCALE = 0.85     # lint: never shrink images below this to make them fit

ERA_ORDER = ["bronze-age", "iron-age", "classical-antiquity", "medieval-period",
             "early-modern-period", "industrial-age", "information-age"]

# Room plan. `side` N rooms open south onto the spine hall (y -3..3); S rooms open north.
# (era, part, side, x0, x1, y0, y1)   bounds = wall centre-lines
ROOM_PLAN = [
    ("bronze-age", 1, "N", -28, -18, 3, 11),
    ("iron-age", 1, "S", -40, -28, -11, -3),
    ("classical-antiquity", 1, "N", -45, -29, 3, 17),
    ("medieval-period", 1, "S", -61, -41, -19, -3),
    ("medieval-period", 2, "N", -66, -46, 3, 19),
    ("early-modern-period", 1, "S", -78, -62, -17, -3),
    ("early-modern-period", 2, "N", -83, -67, 3, 17),
    ("industrial-age", 1, "S", -103, -79, -23, -3),
    ("industrial-age", 2, "N", -108, -84, 3, 23),
    ("information-age", 1, "S", -114, -104, -11, -3),
]
SPINE_X = (-116.0, -16.0)
SPINE_Y = (-3.0, 3.0)
VESTIBULE_OPENING = (-1.8, 1.8)   # the stub's interior width at x = -16
ROMAN = {1: "I", 2: "II", 3: "III"}

# v1 stub meshes the viewer hides so the vestibule opens west into the spine hall
HIDDEN = ["GEO-futurewing_wallW_0", "GEO-futurewing_baseboard_west_0", "GEO-futurewing_picturerail_west_0"]


# ---------------------------------------------------------------- people -------------
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
            "era": era, "region": region, "themes": [{"slug": t.get("slug"), "title": (t.get("slug") or "").replace("-", " ").title()} for t in (e.get("themes") or [])],
            "description": description, "images": images,
        })
    out.sort(key=lambda p: (p["era"]["slug"] if p["era"] else "", p["born"] is None, p["born"] if p["born"] is not None else 0, p["name"]))
    return out


# ---------------------------------------------------------------- rooms --------------
def room_id(era: str, part: int, parts: int) -> str:
    return f"people-{era}" + (f"-{part}" if parts > 1 else "")


def room_records():
    parts = {}
    for era, part, *_ in ROOM_PLAN:
        parts[era] = max(parts.get(era, 0), part)
    rooms = []
    for era, part, side, x0, x1, y0, y1 in ROOM_PLAN:
        rid = room_id(era, part, parts[era])
        cx = (x0 + x1) / 2
        door_y = 3.0 if side == "N" else -3.0
        rooms.append({"id": rid, "era": era, "part": part, "parts": parts[era], "side": side,
                      "x": [float(x0), float(x1)], "y": [float(y0), float(y1)],
                      "center": [cx, (y0 + y1) / 2], "door": [cx, door_y]})
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


# ---------------------------------------------------------------- hanging ------------
def art_walls(room: dict):
    """Three art walls, in the order a visitor reads them after turning left at the door."""
    x0, x1 = room["x"]
    y0, y1 = room["y"]
    if room["side"] == "N":   # door on the south wall (y0)
        return [
            {"side": "W", "axis": "y", "const": x0, "lo": y0, "hi": y1, "normal": [1.0, 0.0], "reverse": False},
            {"side": "N", "axis": "x", "const": y1, "lo": x0, "hi": x1, "normal": [0.0, -1.0], "reverse": False},
            {"side": "E", "axis": "y", "const": x1, "lo": y0, "hi": y1, "normal": [-1.0, 0.0], "reverse": True},
        ]
    return [                  # door on the north wall (y1); facing south, left is east
        {"side": "E", "axis": "y", "const": x1, "lo": y0, "hi": y1, "normal": [-1.0, 0.0], "reverse": True},
        {"side": "S", "axis": "x", "const": y0, "lo": x0, "hi": x1, "normal": [0.0, 1.0], "reverse": True},
        {"side": "W", "axis": "y", "const": x0, "lo": y0, "hi": y1, "normal": [1.0, 0.0], "reverse": False},
    ]


def column_sizes(person: dict, scale: float = 1.0):
    n = len(person["images"])
    hmax = (H_MAX3 if n >= 3 else H_MAX) * scale
    sizes = []
    for im in person["images"]:
        aspect = max(0.2, min(5.0, im["w"] / max(1, im["h"])))
        h = hmax
        w = h * aspect
        if w > W_MAX * scale:
            w = W_MAX * scale
            h = w / aspect
        sizes.append((round(w, 3), round(h, 3)))
    return sizes


def hang_room(room: dict, persons: list[dict]) -> tuple[list[dict], dict]:
    walls = art_walls(room)
    usable = [w["hi"] - w["lo"] - 2 * INSET for w in walls]
    n = len(persons)
    if n == 0:
        return [], {"scale": 1.0, "fill": [0, 0, 0]}
    total = sum(usable)
    counts = [max(0, round(n * u / total)) for u in usable]
    order = sorted(range(3), key=lambda i: -usable[i])
    i = 0
    while sum(counts) != n:
        j = order[i % 3]
        if sum(counts) < n:
            counts[j] += 1
        elif counts[j] > 0:
            counts[j] -= 1
        i += 1

    scale = 1.0
    for _attempt in range(40):
        # columns per wall in reading order
        groups, k = [], 0
        for c in counts:
            groups.append(persons[k:k + c])
            k += c
        widths = [[max(w for w, _h in column_sizes(p, scale)) for p in g] for g in groups]
        need = [sum(ws) + GAP_MIN * max(0, len(ws) - 1) for ws in widths]
        over = [i for i in range(3) if need[i] > usable[i]]
        if not over:
            break
        moved = False
        for i in over:
            # give a column to the neighbour wall with the most spare room
            spare = [(usable[j] - need[j], j) for j in range(3) if j != i and counts[j] < n]
            spare.sort(reverse=True)
            if spare and spare[0][0] > 1.6 and counts[i] > 1:
                j = spare[0][1]
                counts[i] -= 1
                counts[j] += 1
                moved = True
                break
        if not moved:
            scale = round(min(usable[i] / need[i] for i in over) * 0.98, 3)
            if scale < MIN_SCALE:
                scale = MIN_SCALE
                break
    groups, k = [], 0
    for c in counts:
        groups.append(persons[k:k + c])
        k += c

    hangs = []
    fill = []
    for wall, group in zip(walls, groups):
        if not group:
            fill.append(0.0)
            continue
        cols = [column_sizes(p, scale) for p in group]
        widths = [max(w for w, _h in c) for c in cols]
        u = wall["hi"] - wall["lo"] - 2 * INSET
        gap = max(GAP_MIN, min(GAP_MAX, (u - sum(widths)) / (len(widths) + 1)))
        run = sum(widths) + gap * (len(widths) - 1)
        if run > u:   # lint will flag; keep geometry consistent anyway
            gap = max(0.1, (u - sum(widths)) / max(1, len(widths) - 1))
            run = sum(widths) + gap * (len(widths) - 1)
        fill.append(round(run / u, 3))
        cursor = wall["lo"] + INSET + (u - run) / 2
        if wall["reverse"]:
            cursor = wall["hi"] - INSET - (u - run) / 2
        for person, sizes, colw in zip(group, cols, widths):
            centre = cursor + colw / 2 if not wall["reverse"] else cursor - colw / 2
            rows = ROW_Z[min(3, len(sizes))]
            for (w, h), row_z, im in zip(sizes, rows, person["images"]):
                if wall["axis"] == "y":
                    pos = [wall["const"] + ART_OFFSET * wall["normal"][0], centre, row_z]
                else:
                    pos = [centre, wall["const"] + ART_OFFSET * wall["normal"][1], row_z]
                hangs.append({
                    "id": f"people--{person['slug']}--{im['n']}", "person": person["slug"], "room": room["id"],
                    "wall": wall["side"], "along": round(centre, 3), "pos": [round(v, 3) for v in pos],
                    "normal": [wall["normal"][0], wall["normal"][1], 0.0], "w": w, "h": h,
                    "row": rows.index(row_z), "rows": len(sizes),
                })
            cursor = cursor + colw + gap if not wall["reverse"] else cursor - colw - gap
    return hangs, {"scale": scale, "fill": fill, "counts": counts}


# ---------------------------------------------------------------- geometry -----------
def box(name, x, y, z, material):
    return {"name": name, "x": [round(x[0], 3), round(x[1], 3)], "y": [round(y[0], 3), round(y[1], 3)],
            "z": [round(z[0], 3), round(z[1], 3)], "material": material}


def door_frame(prefix, axis, centre, face, height=DOOR_H):
    """Jambs + lintel plates on the spine-side face (mirrors GEO-df_spine1_to_a_*)."""
    t = (face - 0.02, face + 0.02)
    half = DOOR_W / 2
    out = []
    if axis == "x":   # door runs along x (in a wall at const y = face±)
        out.append(box(f"{prefix}_jambL", (centre - half - 0.04, centre - half + 0.04), t, (-0.04, height + 0.04), "trim"))
        out.append(box(f"{prefix}_jambR", (centre + half - 0.04, centre + half + 0.04), t, (-0.04, height + 0.04), "trim"))
        out.append(box(f"{prefix}_lintel", (centre - half - 0.04, centre + half + 0.04), t, (height, height + 0.08), "trim"))
    else:             # door runs along y (in a wall at const x)
        out.append(box(f"{prefix}_jambL", t, (centre - half - 0.04, centre - half + 0.04), (-0.04, height + 0.04), "trim"))
        out.append(box(f"{prefix}_jambR", t, (centre + half - 0.04, centre + half + 0.04), (-0.04, height + 0.04), "trim"))
        out.append(box(f"{prefix}_lintel", t, (centre - half - 0.04, centre + half + 0.04), (height, height + 0.08), "trim"))
    return out


def room_boxes(room: dict) -> list[dict]:
    rid = room["id"]
    x0, x1 = room["x"]
    y0, y1 = room["y"]
    h = WALL_T / 2
    out = [box(f"GEO-{rid}_floor", (x0, x1), (y0, y1), (-0.1, 0.1), "floor"),
           box(f"GEO-{rid}_ceiling", (x0, x1), (y0, y1), (HEIGHT - 0.1, HEIGHT + 0.1), "ceiling")]
    # the three art walls (the door wall belongs to the spine hall)
    for w in art_walls(room):
        side = w["side"]
        if w["axis"] == "y":
            out.append(box(f"GEO-{rid}_wall{side}_0", (w["const"] - h, w["const"] + h), (y0 - h, y1 + h), (0, HEIGHT), "wall"))
            d = w["normal"][0]
            tx = (w["const"] + d * 0.02, w["const"] + d * 0.43) if d > 0 else (w["const"] + d * 0.43, w["const"] + d * 0.02)
            out.append(box(f"GEO-{rid}_baseboard_{side}_0", tx, (y0 + h, y1 - h), (0, 0.18), "trim"))
            out.append(box(f"GEO-{rid}_picturerail_{side}_0", tx, (y0 + h, y1 - h), (6.25, 6.37), "trim"))
        else:
            out.append(box(f"GEO-{rid}_wall{side}_0", (x0 - h, x1 + h), (w["const"] - h, w["const"] + h), (0, HEIGHT), "wall"))
            d = w["normal"][1]
            ty = (w["const"] + d * 0.02, w["const"] + d * 0.43) if d > 0 else (w["const"] + d * 0.43, w["const"] + d * 0.02)
            out.append(box(f"GEO-{rid}_baseboard_{side}_0", (x0 + h, x1 - h), ty, (0, 0.18), "trim"))
            out.append(box(f"GEO-{rid}_picturerail_{side}_0", (x0 + h, x1 - h), ty, (6.25, 6.37), "trim"))
    return out


def spine_boxes(rooms: list[dict]) -> list[dict]:
    sid = "people-spine"
    x0, x1 = SPINE_X
    y0, y1 = SPINE_Y
    h = WALL_T / 2
    out = [box(f"GEO-{sid}_floor", (x0, x1), (y0, y1), (-0.1, 0.1), "floor"),
           box(f"GEO-{sid}_ceiling", (x0, x1), (y0, y1), (HEIGHT - 0.1, HEIGHT + 0.1), "ceiling"),
           box(f"GEO-{sid}_wallW_0", (x0 - h, x0 + h), (y0 - h, y1 + h), (0, HEIGHT), "wall")]
    for side, const in (("N", y1), ("S", y0)):
        doors = sorted(r["door"][0] for r in rooms if r["side"] == side)
        cursor = x0 - h
        n = 0
        for c in doors:
            lo, hi = c - DOOR_W / 2, c + DOOR_W / 2
            if lo > cursor:
                out.append(box(f"GEO-{sid}_wall{side}_{n}", (cursor, lo), (const - h, const + h), (0, HEIGHT), "wall"))
                n += 1
            out.append(box(f"GEO-{sid}_transom{side}_{n}", (lo, hi), (const - h, const + h), (DOOR_H, HEIGHT), "wall"))
            cursor = hi
        if cursor < x1 + h:
            out.append(box(f"GEO-{sid}_wall{side}_{n}", (cursor, x1 + h), (const - h, const + h), (0, HEIGHT), "wall"))
        # door frames on the spine side face, one per gallery door
        for r in rooms:
            if r["side"] != side:
                continue
            face = const - 0.2 if side == "N" else const + 0.2
            out += door_frame(f"GEO-df_{sid}_to_{r['id']}", "x", r["door"][0], face)
    # east end: return walls beside the vestibule opening, a transom over it, and its frame
    vy0, vy1 = VESTIBULE_OPENING
    out.append(box(f"GEO-{sid}_wallE_0", (x1 - h, x1 + h), (y0 - h, vy0), (0, HEIGHT), "wall"))
    out.append(box(f"GEO-{sid}_wallE_1", (x1 - h, x1 + h), (vy1, y1 + h), (0, HEIGHT), "wall"))
    out.append(box(f"GEO-{sid}_transomE_0", (x1 - h, x1 + h), (vy0, vy1), (DOOR_H + 0.04, HEIGHT), "wall"))
    out += door_frame(f"GEO-df_vestibule_to_{sid}", "y", 0.0, x1 + 0.22)
    # baseboards / picture rails along the spine's long walls (between doors)
    for side, const in (("N", y1), ("S", y0)):
        d = -1 if side == "N" else 1
        ty = (const + d * 0.43, const + d * 0.02) if d < 0 else (const + d * 0.02, const + d * 0.43)
        doors = sorted(r["door"][0] for r in rooms if r["side"] == side)
        cursor = x0 + h
        n = 0
        for c in doors + [x1 - h + DOOR_W / 2]:
            lo = c - DOOR_W / 2
            if lo - cursor > 0.5:
                out.append(box(f"GEO-{sid}_baseboard_{side}_{n}", (cursor, lo), ty, (0, 0.18), "trim"))
                out.append(box(f"GEO-{sid}_picturerail_{side}_{n}", (cursor, lo), ty, (6.25, 6.37), "trim"))
                n += 1
            cursor = c + DOOR_W / 2
    return out


# ---------------------------------------------------------------- build --------------
def build(existing_rooms: list[dict]) -> dict:
    """Returns {"rooms", "artists", "wing", "layout", "stub_patch", "stats"}."""
    people = load_people()
    rooms = room_records()
    assignment = assign_rooms(people, rooms)
    era_titles = {p["era"]["slug"]: p["era"]["title"] for p in people if p["era"]}

    manifest_rooms = []
    artists = []
    hangs = {}
    stats = {}
    order = 1000
    for room in rooms:
        persons = assignment.get(room["id"], [])
        room_hangs, info = hang_room(room, persons)
        stats[room["id"]] = {"people": len(persons), "images": len(room_hangs), **info}
        for hg in room_hangs:
            hangs[hg["id"]] = hg
        title = era_titles.get(room["era"], room["era"].replace("-", " ").title())
        name = title + (f" {ROMAN[room['part']]}" if room["parts"] > 1 else "")
        manifest_rooms.append({
            "id": room["id"], "name": name, "era": title, "kind": "gallery", "wing": WING_ID,
            "connects_to": ["people-spine"],
            "position": [room["center"][0], room["center"][1], 0.05],
            "doors": {"people-spine": [room["door"][0], room["door"][1], 0.05]},
        })
        for p in persons:
            works = []
            for im, (w, h) in zip(p["images"], column_sizes(p, info["scale"])):
                works.append({
                    "id": f"people--{p['slug']}--{im['n']}", "title": p["name"], "year": None,
                    "medium": (im["caption"][:77] + "…") if len(im["caption"]) > 80 else im["caption"],
                    "location": None, "description": p["description"],
                    "image": im["src"], "thumb": im["thumb"], "w": im["w"], "h": im["h"],
                    "credit": {"work": im["caption"], "file": im["src"], "source": im["source"], "author": im["author"],
                               "license": im["license"], "license_url": im["license_url"], "via": im["via"],
                               "ai": im["ai"], "model": im["model"]},
                })
            artists.append({
                "slug": p["slug"], "name": p["name"], "short_name": p["name"], "lifespan": p["lifespan"], "born": p["born"],
                "region": p["region"], "country": None, "movements": [], "discipline": ["portrait"], "wikipedia": None,
                "cover": p["images"][0]["thumb"], "room": room["id"], "order": order, "wing": WING_ID,
                "person_id": p["id"], "era": p["era"], "themes": p["themes"], "works": works,
            })
            order += 1

    spine = {
        "id": "people-spine", "name": "People Wing Hall", "kind": "spine", "wing": WING_ID,
        "connects_to": ["future-wing-1"] + [r["id"] for r in rooms],
        "position": [(SPINE_X[0] + SPINE_X[1]) / 2, 0.0, 0.05],
        "doors": {"future-wing-1": [SPINE_X[1], 0.0, 0.05], **{r["id"]: [r["door"][0], r["door"][1], 0.05] for r in rooms}},
    }
    manifest_rooms.insert(0, spine)

    boxes = spine_boxes(rooms)
    for room in rooms:
        boxes += room_boxes(room)
    layout = {
        "units": "blender", "wall_t": WALL_T, "height": HEIGHT, "wing": WING_ID, "hidden": HIDDEN,
        "rooms": {r["id"]: {"x": r["x"], "y": r["y"], "z0": 0.0, "side": r["side"], "door": r["door"]} for r in rooms},
        "spine": {"x": list(SPINE_X), "y": list(SPINE_Y), "z0": 0.0},
        "boxes": boxes, "hangs": hangs,
    }
    born = [p["born"] for p in people if p["born"] is not None]
    wing = {
        "id": WING_ID, "name": "Earth Chronicle People", "image_base": "_Site/",
        "nouns": ["people", "portraits"], "years": f"{fmt_year(min(born))}–{fmt_year(max(born))}",
        "rooms": ["future-wing-1", "people-spine"] + [r["id"] for r in rooms],
    }
    stub_patch = {"name": "People Wing Vestibule", "kind": "vestibule", "connects_to": ["rotunda", "people-spine"],
                  "doors": {"people-spine": [SPINE_X[1], 0.0, 0.05]}}
    return {"rooms": manifest_rooms, "artists": artists, "wing": wing, "layout": layout, "stub_patch": stub_patch,
            "stats": stats, "people": len(people), "images": len(hangs)}


def fmt_year(y: int) -> str:
    return f"{-y} BCE" if y < 0 else str(y)


# ---------------------------------------------------------------- lint ---------------
def _overlap1(a, b, margin=0.0):
    return a[0] < b[1] - margin and b[0] < a[1] - margin


def lint(result: dict, existing_rooms: list[dict], art_talk_work_ids: set[str]) -> list[str]:
    errors: list[str] = []
    layout = result["layout"]
    hangs = list(layout["hangs"].values())
    # ids unique and disjoint from the Art-Talk wing
    ids = [h["id"] for h in hangs]
    if len(ids) != len(set(ids)):
        errors.append("duplicate hang ids")
    clash = set(ids) & art_talk_work_ids
    if clash:
        errors.append(f"work ids clash with the Art-Talk wing: {sorted(clash)[:5]}")
    # every image once
    people = load_people()
    expected = {f"people--{p['slug']}--{im['n']}" for p in people for im in p["images"]}
    missing = expected - set(ids)
    extra = set(ids) - expected
    if missing or extra:
        errors.append(f"hang set mismatch: {len(missing)} missing, {len(extra)} extra")
    # per wall: columns inside the inset span, no overlaps; rows don't overlap vertically
    by_wall: dict[tuple, list[dict]] = {}
    for h in hangs:
        by_wall.setdefault((h["room"], h["wall"]), []).append(h)
    for (rid, side), lst in by_wall.items():
        room = layout["rooms"][rid]
        lo, hi = (room["y"] if side in "EW" else room["x"])
        cols: dict[str, list[dict]] = {}
        for h in lst:
            cols.setdefault(h["person"], []).append(h)
        spans = []
        for person, imgs in cols.items():
            w = max(i["w"] for i in imgs)
            c = imgs[0]["along"]
            if c - w / 2 < lo + INSET - 1e-6 or c + w / 2 > hi - INSET + 1e-6:
                errors.append(f"{rid} {side}: column {person} outside the wall span")
            spans.append((c - w / 2, c + w / 2, person))
            zs = sorted((i["pos"][2] - i["h"] / 2, i["pos"][2] + i["h"] / 2) for i in imgs)
            for a, b in zip(zs, zs[1:]):
                if a[1] > b[0] - 0.08:
                    errors.append(f"{rid} {side}: stacked images of {person} overlap vertically")
            for i in imgs:
                if i["pos"][2] - i["h"] / 2 < 0.35 or i["pos"][2] + i["h"] / 2 > 6.0:
                    errors.append(f"{rid} {side}: image of {person} outside 0.35–6.0 m")
        spans.sort()
        for a, b in zip(spans, spans[1:]):
            if a[1] > b[0] - 0.1 + 1e-6:
                errors.append(f"{rid} {side}: columns {a[2]} and {b[2]} overlap or are closer than 0.1 m")
    for rid, st in result["stats"].items():
        if st["scale"] < MIN_SCALE - 1e-9:
            errors.append(f"{rid}: images scaled to {st['scale']} (< {MIN_SCALE})")
    # door gaps: no wall box crosses a door opening below the lintel; a 3 m path through the door is clear at 1.2 m
    walls = [b for b in layout["boxes"] if b["material"] == "wall"]
    doors = [(r["door"], r["side"]) for r in layout["rooms"].values()] + [([SPINE_X[1], 0.0], "E")]
    for (cx, cy), side in doors:
        if side in "NS":
            gap_x = (cx - DOOR_W / 2 + 0.01, cx + DOOR_W / 2 - 0.01)
            gap_y = (cy - 0.3, cy + 0.3)
        else:
            gap_x = (cx - 0.3, cx + 0.3)
            gap_y = (VESTIBULE_OPENING[0] + 0.01, VESTIBULE_OPENING[1] - 0.01)
        for b in walls:
            if _overlap1(b["x"], gap_x) and _overlap1(b["y"], gap_y) and b["z"][0] < 1.2 < b["z"][1]:
                errors.append(f"door at ({cx}, {cy}) blocked by {b['name']}")
        path_x = gap_x if side in "NS" else (cx - 1.5, cx + 1.5)
        path_y = (cy - 1.5, cy + 1.5) if side in "NS" else gap_y
        if side in "NS":
            path_x = (cx - 0.3, cx + 0.3)
        for b in walls:
            if _overlap1(b["x"], path_x) and _overlap1(b["y"], path_y) and b["z"][0] < 1.2 < b["z"][1]:
                errors.append(f"path through door at ({cx}, {cy}) crosses {b['name']}")
    # rooms pairwise disjoint (walls may share up to 0.4 m), and clear of the existing building
    footprints = [(rid, r["x"], r["y"]) for rid, r in layout["rooms"].items()]
    footprints.append(("people-spine", layout["spine"]["x"], layout["spine"]["y"]))
    for i in range(len(footprints)):
        for j in range(i + 1, len(footprints)):
            a, b = footprints[i], footprints[j]
            if _overlap1(a[1], b[1], WALL_T) and _overlap1(a[2], b[2], WALL_T):
                errors.append(f"rooms {a[0]} and {b[0]} overlap")
    existing = [("rotunda", (-7.0, 7.0), (-7.0, 7.0)), ("futurewing", (-16.0, -7.0), (-2.0, 2.0))]
    for er in existing_rooms:
        if "x" in er and "y" in er:
            existing.append((er["id"], tuple(er["x"]), tuple(er["y"])))
    for rid, x, y in footprints:
        for eid, ex, ey in existing:
            if rid == "people-spine" and eid == "futurewing":
                continue  # they meet at x = -16 by design
            if _overlap1(x, ex, WALL_T) and _overlap1(y, ey, WALL_T):
                errors.append(f"{rid} overlaps existing {eid}")
    # names respect the viewer's classification contract
    for b in layout["boxes"]:
        n = b["name"].lower()
        struct = any(k in n for k in ("wall", "floor", "outer", "landing", "step"))
        if b["material"] == "trim" and struct:
            errors.append(f"decorative box named like structure: {b['name']}")
        if b["material"] == "wall" and "wall" not in n and "transom" not in n:
            errors.append(f"wall box without 'wall' in its name: {b['name']}")
        if "transom" in n and "wall" in n:
            pass
    return errors


def load_rooms_v2() -> list[dict]:
    p = MUSEUM / "blender" / "scripts" / "rooms_v2.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("rooms", [])
    except (OSError, ValueError):
        return []


def write_layout(result: dict) -> Path:
    LAYOUT_OUT.write_text(json.dumps(result["layout"], ensure_ascii=False, indent=0), encoding="utf-8")
    return LAYOUT_OUT


def report(result: dict) -> str:
    lines = [f"People wing: {result['people']} people, {result['images']} portraits, {len(result['rooms']) - 1} rooms + hall"]
    for rid, st in result["stats"].items():
        lines.append(f"  {rid:32s} people {st['people']:3d}  images {st['images']:3d}  fill {st['fill']}  scale {st['scale']}")
    return "\n".join(lines)


if __name__ == "__main__":
    res = build([])
    errs = lint(res, load_rooms_v2(), set())
    print(report(res))
    if errs:
        print("LINT FAILED:")
        for e in errs:
            print("  -", e)
        raise SystemExit(1)
    print("lint ok (dry run; build_manifest.py writes the files)")
