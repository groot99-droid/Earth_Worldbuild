"""Lay out the Chronicle Museum: the Grand Hall hub and one scene per gallery room.

Output: _Museum/data/museum-layout.json, consumed by web/js/scenes.js + procroom.js. Every
scene is self-contained and built at its own origin (the viewer shows one scene at a time):

* a room: the hall door is centred at (0, 0) on the south wall, the room spans
  x ∈ [-W/2, W/2], y ∈ [0, D], floor at z = 0, 7 m tall; art hangs on the W, N and E walls in a
  salon grid at real size; a `DOOR-<next>` on the E wall leads to the next room in time;
* the hub: a hall x ∈ [0, L], y ∈ [-4, 4], 9 m tall, an entrance rotunda at (-7, 0) and an
  apse at x = L; Art-Talk gallery doors along the south wall, People-wing era doors along the
  north wall, both in chronological order; sculptures on column pedestals between the doors.

Coordinates are Blender Z-up metres (x east, y north, z up); the viewer converts (coords.js).
Every mesh record is named by the viewer's classification contract: names containing
`wall`/`outer` collide, `floor`/`landing`/`step` are walkable, `DOOR-<id>` is a clickable door,
`SCULPT-<id>` a clickable sculpture, `FX-` a light anchor; decorative names avoid those words
(work ids can contain them, so nothing is ever named after a work id).

`lint()` checks the result before build_manifest.py writes anything.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

MUSEUM = Path(__file__).resolve().parent
LAYOUT_OUT = MUSEUM / "data" / "museum-layout.json"

WALL_T = 0.4
ROOM_H = 7.0
HUB_H = 9.0
DOOR_W = 3.2
DOOR_H = 4.0
ART_OFFSET = 0.25          # art plane centre from the wall centre-line (0.05 proud of the face)
DOOR_SPAWN = 2.6           # m inside a door where a visitor arrives

# salon grid
Z_LO, Z_HI, EYE = 0.45, 5.6, 1.55
GAP_MIN, GAP_MAX, ROW_GAP, INSET = 0.25, 1.2, 0.30, 0.8
DOOR_CLEAR = 0.5
MAX_ROWS = 3
MIN_ROOM_SCALE = 0.7
MAX_GROW = 4               # room growth steps of 2 m

# hub
HUB_L = 80.0
HUB_HALF_W = 4.0
HUB_MARGIN = 6.0
ROTUNDA_C = (-7.0, 0.0)
ROTUNDA_R = 7.0
APSE_R = 4.0
SURROUND_W = 4.6

FRAME = {  # style -> (moulding width, depth) in metres
    "gilt-ornate": (0.12, 0.08), "gilt-simple": (0.07, 0.05), "dark-wood": (0.08, 0.05),
    "black-lacquer": (0.05, 0.04), "thin-metal": (0.02, 0.03), "none": (0.0, 0.0),
}

# Per-room look: door theme, wall paint, trim material, frame styles (large works / works on paper).
ROOM_STYLE = {
    "gallery-a": {"theme": "pointed-arch", "wall": "#8f6f52", "trim": "painted_trim", "frame": "gilt-simple", "frame_small": "dark-wood"},
    "gallery-b": {"theme": "round-arch-keystone", "wall": "#6d4a3a", "trim": "painted_trim", "frame": "gilt-ornate", "frame_small": "gilt-simple"},
    "gallery-c": {"theme": "baroque-pediment", "wall": "#5b2f2f", "trim": "painted_trim", "frame": "gilt-ornate", "frame_small": "dark-wood"},
    "gallery-d": {"theme": "doric-pediment", "wall": "#4f5a4c", "trim": "painted_trim", "frame": "gilt-ornate", "frame_small": "black-lacquer"},
    "gallery-e": {"theme": "cast-iron-glass", "wall": "#43536a", "trim": "painted_trim", "frame": "dark-wood", "frame_small": "dark-wood"},
    "gallery-f": {"theme": "art-deco", "wall": "#3b3b40", "trim": "painted_trim", "frame": "black-lacquer", "frame_small": "thin-metal"},
    "people-bronze-age": {"theme": "post-lintel-megalith", "wall": "#9a7a4e", "trim": "painted_trim", "frame": "dark-wood", "frame_small": "dark-wood"},
    "people-iron-age": {"theme": "post-lintel-timber", "wall": "#6e6a5e", "trim": "painted_trim", "frame": "dark-wood", "frame_small": "dark-wood"},
    "people-classical-antiquity": {"theme": "doric-pediment", "wall": "#8b3a2f", "trim": "painted_trim", "frame": "gilt-simple", "frame_small": "dark-wood"},
    "people-medieval-period-1": {"theme": "pointed-arch", "wall": "#4a5a7a", "trim": "painted_trim", "frame": "dark-wood", "frame_small": "gilt-simple"},
    "people-medieval-period-2": {"theme": "pointed-arch", "wall": "#4a5a7a", "trim": "painted_trim", "frame": "dark-wood", "frame_small": "gilt-simple"},
    "people-early-modern-period-1": {"theme": "round-arch-keystone", "wall": "#6b4b3e", "trim": "painted_trim", "frame": "gilt-ornate", "frame_small": "gilt-simple"},
    "people-early-modern-period-2": {"theme": "round-arch-keystone", "wall": "#6b4b3e", "trim": "painted_trim", "frame": "gilt-ornate", "frame_small": "gilt-simple"},
    "people-industrial-age-1": {"theme": "cast-iron-glass", "wall": "#4b5a52", "trim": "painted_trim", "frame": "dark-wood", "frame_small": "dark-wood"},
    "people-industrial-age-2": {"theme": "cast-iron-glass", "wall": "#4b5a52", "trim": "painted_trim", "frame": "dark-wood", "frame_small": "dark-wood"},
    "people-information-age": {"theme": "steel-glass", "wall": "#e8e4dc", "trim": "painted_trim", "frame": "thin-metal", "frame_small": "thin-metal"},
}
DEFAULT_STYLE = {"theme": "round-arch-keystone", "wall": "#8a7a66", "trim": "painted_trim", "frame": "gilt-simple", "frame_small": "dark-wood"}

# Sculptures and props: where each model stands. `hub:<bay>` = a pedestal bay in the hall
# (bays are numbered from the west, side N/S), `hub:rotunda`, `hub:apse`, or a room id.
PLACEMENTS = [
    ("si-greek-slave", "hub:rotunda", "column", 0.0),
    ("si-greenough-washington", "hub:apse", "plinth", 0.0),
    ("si-fangyi", "hub:N0", "column", 0.0),
    ("si-gong-ewer", "hub:N1", "column", 0.0),
    ("si-xianglu", "hub:N2", "column", 0.0),
    ("si-cosmic-buddha", "hub:N3", "plinth", 0.0),
    ("si-winged-monster", "hub:N4", "column", 0.0),
    ("si-temne-horn", "hub:N5", "column", 90.0),
    ("si-houdon-washington", "hub:N6", "column", 0.0),
    ("si-ravenna-washington", "hub:N7", "column", 0.0),
    ("si-old-arrow-maker", "hub:N8", "column", 0.0),
    ("ph-marble-bust", "hub:N9", "column", 0.0),
    ("ph-gothic-statue", "hub:S0", "plinth", 0.0),
    ("ph-bull-head", "hub:S1", "column", 0.0),
    ("si-kangxi-baluster-vase", "hub:S2", "column", 0.0),
    ("si-kangxi-beaker-vase", "hub:S3", "column", 0.0),
    ("ph-horse-head", "hub:S4", "column", 0.0),
    ("si-dying-tecumseh", "hub:S5", "plinth", 0.0),
    ("si-girl-skating", "hub:S6", "column", 0.0),
    ("si-wounded-scout", "gallery-e", "column", 0.0),
    ("si-waterston-bust", "people-industrial-age-1", "column", 0.0),
    ("si-lincoln-mills-mask", "people-industrial-age-1", "column", 0.0),
    ("si-garfield", "people-industrial-age-2", "column", 0.0),
    ("si-jackson-mills", "people-industrial-age-2", "column", 0.0),
    ("si-helen-keller", "people-information-age", "column", 0.0),
    ("si-kongo-tusk", "people-industrial-age-2", "column", 90.0),
    ("ph-ceramic-vase", "gallery-b", "column", 0.0),
    ("ph-brass-vase", "gallery-c", "column", 0.0),
]
WALL_RELIEFS = [  # (model, room, wall side)
    ("si-gathering-of-buddhas", "people-medieval-period-1", "S"),
    ("si-western-paradise", "people-medieval-period-2", "S"),
    ("si-roosevelt-relief", "people-industrial-age-2", "S"),
]


# ---------------------------------------------------------------- helpers ------------
def r3(v):
    return round(float(v), 3)


def box(name, x, y, z, material):
    return {"name": name, "x": [r3(x[0]), r3(x[1])], "y": [r3(y[0]), r3(y[1])], "z": [r3(z[0]), r3(z[1])], "material": material}


def style_for(rid: str) -> dict:
    return ROOM_STYLE.get(rid, DEFAULT_STYLE)


def frame_style(work_type: str, style: dict) -> str:
    if work_type in ("hanging-scroll", "handscroll", "fresco"):
        return "none"
    if work_type in ("film-still", "architecture-photo", "photo", "design-object", "sculpture-photo"):
        return "thin-metal"
    if work_type in ("print", "poster", "book-page", "manuscript"):
        return style["frame_small"]
    return style["frame"]


# ---------------------------------------------------------------- salon grid ---------
def _shelves(items, k, cap):
    """First-fit-decreasing by height into k rows (row 0 = eye row gets the largest). None on overflow."""
    order = sorted(items, key=lambda w: (-w["oh"], w["order"]))
    rows = [[] for _ in range(k)]
    used = [0.0] * k
    for w in order:
        for r in range(k):
            need = w["ow"] + (GAP_MIN if rows[r] else 0.0)
            if used[r] + need <= cap + 1e-9:
                rows[r].append(w)
                used[r] += need
                break
        else:
            return None
    rows = [sorted(r, key=lambda w: w["order"]) for r in rows if r]
    return rows


def _vertical(rows):
    """Per row: (mode, z) where the eye row centres works on EYE (tall works rest on Z_LO), rows above are
    bottom-aligned on a shared line, a row below is top-aligned under the eye row. None if it does not fit."""
    eye = rows[0]
    zc = {w["id"]: max(EYE, Z_LO + w["oh"] / 2) for w in eye}
    top = max(zc[w["id"]] + w["oh"] / 2 for w in eye)
    bottom = min(zc[w["id"]] - w["oh"] / 2 for w in eye)
    plan = [("eye", None)]
    line = top + ROW_GAP
    below = bottom - ROW_GAP
    for r in rows[1:]:
        h = max(w["oh"] for w in r)
        if line + h <= Z_HI + 1e-9:
            plan.append(("above", line))
            line += h + ROW_GAP
        elif below - h >= Z_LO - 1e-9:
            plan.append(("below", below))
            below -= h + ROW_GAP
        else:
            return None
    return plan, zc


def pack_wall(wall, items):
    """Rows of items on one wall or None. Each item gets `along` (position along the wall) and `z`."""
    if not items:
        return []
    lo, hi = wall["free"]
    cap = hi - lo
    for k in range(1, MAX_ROWS + 1):
        rows = _shelves(items, k, cap)
        if not rows:
            continue
        v = _vertical(rows)
        if not v:
            continue
        plan, zc = v
        out = []
        for (mode, line), row in zip(plan, rows):
            n = len(row)
            total = sum(w["ow"] for w in row)
            gap = max(GAP_MIN, min(GAP_MAX, (cap - total) / (n + 1)))
            run = total + gap * (n - 1)
            if run > cap + 1e-9:
                return None
            cursor = lo + (cap - run) / 2
            seq = row if not wall["reverse"] else list(reversed(row))
            for w in seq:
                along = cursor + w["ow"] / 2
                if mode == "eye":
                    z = zc[w["id"]]
                elif mode == "above":
                    z = line + w["oh"] / 2
                else:
                    z = line - w["oh"] / 2
                out.append({**w, "along": along, "z": z, "row": rows.index(row)})
                cursor += w["ow"] + gap
        return out
    return None


def pack_room(works, walls, scale=1.0, shrink=False):
    """Distribute works across the art walls (chronological order across walls, salon rows within).
    Returns (hangs_by_wall, scale) or (None, scale). With `shrink`, the works are scaled down in
    4 % steps (never below MIN_ROOM_SCALE) until they fit."""
    while scale >= MIN_ROOM_SCALE - 1e-9:
        items = [{**w, "ow": w["fw"] * scale, "oh": w["fh"] * scale} for w in works]
        caps = [wl["free"][1] - wl["free"][0] for wl in walls]
        capsum = sum(caps) or 1.0
        total = sum(it["ow"] * it["oh"] for it in items) or 1.0
        # contiguous split by area share
        bounds = []
        acc, gi = 0.0, 0
        for i, it in enumerate(items):
            acc += it["ow"] * it["oh"]
            if gi < len(walls) - 1 and acc >= total * caps[gi] / capsum:
                bounds.append(i + 1)
                gi += 1
                acc = 0.0
        while len(bounds) < len(walls) - 1:
            bounds.append(len(items))
        for _ in range(60):
            groups = []
            prev = 0
            for b in bounds + [len(items)]:
                groups.append(items[prev:b])
                prev = b
            packed = [pack_wall(wl, g) for wl, g in zip(walls, groups)]
            bad = [i for i, p in enumerate(packed) if p is None]
            if not bad:
                return packed, scale
            moved = False
            for i in bad:
                # give the boundary work to a neighbour that still packs afterwards
                for j in ([i - 1, i + 1] if i % 2 else [i + 1, i - 1]):
                    if j < 0 or j >= len(walls) or not groups[i]:
                        continue
                    nb = list(bounds)
                    if j == i + 1:
                        nb[i] -= 1
                    else:
                        nb[i - 1] += 1
                    if any(nb[k] > nb[k + 1] for k in range(len(nb) - 1)) or min(nb) < 0:
                        continue
                    # neighbour must accept the work
                    test_prev = 0
                    tg = []
                    for b in nb + [len(items)]:
                        tg.append(items[test_prev:b])
                        test_prev = b
                    if pack_wall(walls[j], tg[j]) is not None:
                        bounds = nb
                        moved = True
                        break
                if moved:
                    break
            if not moved:
                break
        if not shrink:
            return None, scale
        scale = round(scale * 0.96, 4)
    return None, scale


# ---------------------------------------------------------------- rooms --------------
def art_walls(W, D, has_next, has_prev=False):
    """W, N, E walls with their free interval (`next`/`prev` doors sit on the E/W walls at y 1.2–4.4)."""
    e_lo = 4.4 + DOOR_CLEAR if has_next else INSET
    w_lo = 4.4 + DOOR_CLEAR if has_prev else INSET
    return [
        {"side": "W", "axis": "y", "const": -W / 2, "lo": 0.0, "hi": D, "normal": [1.0, 0.0], "reverse": False, "free": [w_lo, D - INSET]},
        {"side": "N", "axis": "x", "const": D, "lo": -W / 2, "hi": W / 2, "normal": [0.0, -1.0], "reverse": False, "free": [-W / 2 + INSET, W / 2 - INSET]},
        {"side": "E", "axis": "y", "const": W / 2, "lo": 0.0, "hi": D, "normal": [-1.0, 0.0], "reverse": True, "free": [e_lo, D - INSET]},
    ]


def room_size_guess(works, min_w, min_d):
    need = sum(w["fw"] + GAP_MIN for w in works)
    per_wall = need / 2.2           # ~2 rows on average
    side = (per_wall + 6 * INSET) / 3
    side = math.ceil(side / 2) * 2
    return max(min_w, side), max(min_d, side)


def door_record(did, target, name, years, theme, pos, normal, w=DOOR_W, h=DOOR_H, hub_side=None):
    hx, hy = normal[0], normal[1]
    heading = math.degrees(math.atan2(hy, hx))
    return {"id": did, "target": target, "name": name, "years": years or "", "theme": theme,
            "pos": [r3(pos[0]), r3(pos[1]), 0.0], "normal": [float(hx), float(hy), 0.0], "w": w, "h": h,
            "spawn": [r3(pos[0] + hx * DOOR_SPAWN), r3(pos[1] + hy * DOOR_SPAWN), 0.0, r3(heading)],
            "hub_side": hub_side}


def moulding_runs(W, D, has_next, has_prev=False):
    """Wall runs (start, end, inward normal) for skirting/rails/cornice, split at the doors."""
    runs = []
    hw = W / 2
    # south wall (door at x -1.6..1.6), inward normal +y
    runs.append(([-hw, 0], [-DOOR_W / 2, 0], [0, 1]))
    runs.append(([DOOR_W / 2, 0], [hw, 0], [0, 1]))
    if has_prev:
        runs.append(([-hw, 0], [-hw, 1.2], [1, 0]))
        runs.append(([-hw, 4.4], [-hw, D], [1, 0]))
    else:
        runs.append(([-hw, 0], [-hw, D], [1, 0]))         # west, normal +x
    runs.append(([-hw, D], [hw, D], [0, -1]))         # north, normal -y
    if has_next:
        runs.append(([hw, 0], [hw, 1.2], [-1, 0]))
        runs.append(([hw, 4.4], [hw, D], [-1, 0]))
    else:
        runs.append(([hw, 0], [hw, D], [-1, 0]))
    return runs


def build_room(spec, works, dims_for_work, next_spec, prev_spec=None):
    """One gallery scene. `works` = manifest works in chronological order with their artist."""
    rid = spec["id"]
    style = style_for(rid)
    has_next = next_spec is not None
    has_prev = prev_spec is not None
    items = []
    for order, (work, artist) in enumerate(works):
        d = dims_for_work(work)
        fs = frame_style(d.get("type", "painting"), style)
        fw, fd = FRAME[fs]
        items.append({"id": work["id"], "order": order, "w": d["disp_w"], "h": d["disp_h"], "scale": d.get("scale", 1.0),
                      "fw": d["disp_w"] + 2 * fw + 0.02, "fh": d["disp_h"] + 2 * fw + 0.02, "frame": fs, "frame_w": fw, "frame_d": fd,
                      "type": d.get("type", "painting"), "slug": artist["slug"]})
    W, D = room_size_guess(items, spec.get("min_w", 12), spec.get("min_d", 10))
    packed, scale = None, 1.0
    for grow in range(MAX_GROW + 1):
        walls = art_walls(W, D, has_next, has_prev)
        packed, scale = pack_room(items, walls, 1.0)
        if packed is not None:
            break
        W += 2
        D += 2
    if packed is None:   # the room is as big as it gets: scale the works down (lint checks the floor)
        walls = art_walls(W, D, has_next, has_prev)
        packed, scale = pack_room(items, walls, 1.0, shrink=True)
        if packed is None:
            packed, scale = [[] for _ in walls], MIN_ROOM_SCALE

    hangs = {}
    for wall, lst in zip(walls, packed):
        for it in lst:
            nx, ny = wall["normal"]
            if wall["axis"] == "y":
                pos = [wall["const"] + ART_OFFSET * nx, it["along"], it["z"]]
            else:
                pos = [it["along"], wall["const"] + ART_OFFSET * ny, it["z"]]
            hangs[it["id"]] = {
                "id": it["id"], "room": rid, "wall": wall["side"], "along": r3(it["along"]), "row": it["row"],
                "pos": [r3(v) for v in pos], "normal": [nx, ny, 0.0],
                "w": r3(it["w"] * scale), "h": r3(it["h"] * scale), "scale": r3(it["scale"] * scale),
                "frame": {"style": it["frame"], "width": r3(it["frame_w"] * scale), "depth": it["frame_d"]},
                "type": it["type"],
            }

    hw = W / 2
    t = WALL_T / 2
    boxes = [
        box(f"GEO-{rid}_floor", (-hw - t, hw + t), (-t, D + t), (-0.2, 0.0), "parquet"),
        box(f"GEO-{rid}_ceiling", (-hw - t, hw + t), (-t, D + t), (ROOM_H, ROOM_H + 0.2), "plaster_ceiling"),
        box(f"GEO-{rid}_wallN_0", (-hw - t, hw + t), (D - t, D + t), (0, ROOM_H), "plaster_wall"),
        box(f"GEO-{rid}_wallS_0", (-hw - t, -DOOR_W / 2), (-t, t), (0, ROOM_H), "plaster_wall"),
        box(f"GEO-{rid}_wallS_1", (DOOR_W / 2, hw + t), (-t, t), (0, ROOM_H), "plaster_wall"),
        box(f"GEO-{rid}_transomS_0", (-DOOR_W / 2, DOOR_W / 2), (-t, t), (DOOR_H, ROOM_H), "plaster_wall"),
    ]
    if has_prev:
        boxes.append(box(f"GEO-{rid}_wallW_0", (-hw - t, -hw + t), (-t, 1.2), (0, ROOM_H), "plaster_wall"))
        boxes.append(box(f"GEO-{rid}_wallW_1", (-hw - t, -hw + t), (4.4, D + t), (0, ROOM_H), "plaster_wall"))
        boxes.append(box(f"GEO-{rid}_transomW_0", (-hw - t, -hw + t), (1.2, 4.4), (DOOR_H, ROOM_H), "plaster_wall"))
    else:
        boxes.append(box(f"GEO-{rid}_wallW_0", (-hw - t, -hw + t), (-t, D + t), (0, ROOM_H), "plaster_wall"))
    if has_next:
        boxes.append(box(f"GEO-{rid}_wallE_0", (hw - t, hw + t), (-t, 1.2), (0, ROOM_H), "plaster_wall"))
        boxes.append(box(f"GEO-{rid}_wallE_1", (hw - t, hw + t), (4.4, D + t), (0, ROOM_H), "plaster_wall"))
        boxes.append(box(f"GEO-{rid}_transomE_0", (hw - t, hw + t), (1.2, 4.4), (DOOR_H, ROOM_H), "plaster_wall"))
    else:
        boxes.append(box(f"GEO-{rid}_wallE_0", (hw - t, hw + t), (-t, D + t), (0, ROOM_H), "plaster_wall"))

    doors = [door_record("hub", "hub", "Grand Hall", "", "hall", (0.0, 0.0), (0.0, 1.0))]
    if has_prev:
        doors.append(door_record(prev_spec["id"], prev_spec["id"], prev_spec["name"], prev_spec.get("years"),
                                 style_for(prev_spec["id"])["theme"], (-hw, 2.8), (1.0, 0.0)))
    if has_next:
        doors.append(door_record(next_spec["id"], next_spec["id"], next_spec["name"], next_spec.get("years"),
                                 style_for(next_spec["id"])["theme"], (hw, 2.8), (-1.0, 0.0)))

    mouldings = []
    for prof, mat in (("skirting", style["trim"]), ("picture_rail", style["trim"]), ("cornice", style["trim"])):
        mouldings.append({"name": f"GEO-{rid}_{prof}", "profile": prof, "material": mat,
                          "runs": [[[r3(a[0]), r3(a[1]), 0.0], [r3(b[0]), r3(b[1]), 0.0], [float(n[0]), float(n[1]), 0.0]] for a, b, n in moulding_runs(W, D, has_next, has_prev)]})
    # door architraves (inside the room) for every door
    for d in doors:
        mouldings.append({"name": f"GEO-{rid}_architrave_{d['id']}", "profile": "architrave", "material": style["trim"],
                          "door": d["id"]})

    fx = [
        {"name": f"FX-{rid}_chandelier_0", "type": "chandelier", "pos": [0.0, r3(D / 2), 5.4], "color": "#ffd9a8", "intensity": 180, "distance": 18, "shadow": 1, "model": "ph-chandelier-01"},
        {"name": f"FX-{rid}_laylight_0", "type": "laylight", "pos": [0.0, r3(D / 2), ROOM_H - 0.2], "color": "#fff3e0", "intensity": 0.7, "distance": 0, "shadow": 1, "size": [r3(W * 0.5), r3(D * 0.5)]},
        {"name": f"FX-{rid}_sconce_0", "type": "sconce", "pos": [-DOOR_W / 2 - 1.0, 0.3, 2.6], "color": "#ffc98a", "intensity": 22, "distance": 6, "shadow": 0, "dir": [0, 1, 0]},
        {"name": f"FX-{rid}_sconce_1", "type": "sconce", "pos": [DOOR_W / 2 + 1.0, 0.3, 2.6], "color": "#ffc98a", "intensity": 22, "distance": 6, "shadow": 0, "dir": [0, 1, 0]},
    ]
    if W > 18 or D > 18:
        fx.append({"name": f"FX-{rid}_chandelier_1", "type": "chandelier", "pos": [0.0, r3(D * 0.25), 5.4], "color": "#ffd9a8", "intensity": 150, "distance": 16, "shadow": 0, "model": "ph-chandelier-01"})
        fx[0]["pos"][1] = r3(D * 0.72)
    # picture lights over large works
    n = 0
    for hg in hangs.values():
        if hg["w"] >= 1.4 or hg["h"] >= 1.4:
            nx, ny = hg["normal"][0], hg["normal"][1]
            top = hg["pos"][2] + hg["h"] / 2 + hg["frame"]["width"] + 0.25
            fx.append({"name": f"FX-{rid}_piclight_{n}", "type": "picture_light", "pos": [r3(hg["pos"][0] + nx * 0.25), r3(hg["pos"][1] + ny * 0.25), r3(top)],
                       "color": "#ffe2b8", "intensity": 8, "distance": 3.0, "shadow": 0, "dir": [0, 0, -1], "over": hg["id"]})
            n += 1

    props = []
    slots = [p for p in PLACEMENTS if p[1] == rid]
    for i, (model, _where, ped, yaw) in enumerate(slots):
        px = (i - (len(slots) - 1) / 2) * 3.0
        props.append({"name": f"SCULPT-{model}", "model": model, "pos": [r3(px), r3(D * 0.5), 0.0], "yaw_deg": yaw + 90.0,
                      "pedestal": {"kind": ped, "h": 1.1 if ped == "column" else 0.45, "r": 0.42, "material": "marble_white"}})
    for model, room, side in WALL_RELIEFS:
        if room != rid:
            continue
        # on the south wall beside the door, facing +y
        props.append({"name": f"SCULPT-{model}", "model": model, "pos": [r3(-hw + 2.4 + 1.9), 0.22, 1.6], "yaw_deg": 90.0, "mount": "wall", "normal": [0.0, 1.0, 0.0]})

    views = {
        f"{rid}_door": {"pos": [0.0, 2.2, 1.7], "target": [0.0, D * 0.6, 2.2], "fov_deg": 70},
        f"{rid}_corner": {"pos": [-hw + 2.5, 5.2, 1.7], "target": [hw * 0.3, D * 0.85, 2.2], "fov_deg": 70},
        f"{rid}_west": {"pos": [hw - 3.0, D * 0.55, 1.7], "target": [-hw, D * 0.35, 2.4], "fov_deg": 70},
    }
    scene = {
        "kind": "room", "id": rid, "name": spec["name"], "wing": spec["wing"], "intro": spec.get("intro"),
        "style": {"theme": style["theme"], "wall": style["wall"], "trim": style["trim"]},
        "floor": {"x": [-hw, hw], "y": [0.0, D]}, "size": [W, D], "height": ROOM_H,
        "spawn": doors[0]["spawn"], "boxes": boxes, "mouldings": mouldings, "walls": walls, "doors": doors,
        "hangs": hangs, "fx": fx, "props": props, "views": views,
        "stats": {"works": len(items), "scale": scale, "rows": [max([h["row"] for h in lst], default=-1) + 1 for lst in packed],
                  "fill": [r3(sum(it["ow"] for it in lst) / max(0.1, wl["free"][1] - wl["free"][0])) for wl, lst in zip(walls, packed)]},
    }
    return scene


# ---------------------------------------------------------------- hub ----------------
def build_hub(art_rooms, people_rooms):
    L = HUB_L
    hw = HUB_HALF_W
    t = WALL_T / 2
    x_open = ROTUNDA_C[0] + math.sqrt(ROTUNDA_R ** 2 - hw ** 2)   # where the drum meets the hall walls
    boxes = [
        box("GEO-hub_floor", (x_open - 0.5, L), (-hw - t, hw + t), (-0.2, 0.0), "marble_white"),
        box("GEO-hub_ceiling", (x_open - 0.5, L), (-hw - t, hw + t), (HUB_H, HUB_H + 0.2), "plaster_ceiling"),
    ]
    doors = []
    bays = {"N": [], "S": []}

    def wall_with_doors(side, const, specs):
        n = len(specs)
        pitch = (L - 2 * HUB_MARGIN) / max(1, n - 1)
        xs = [HUB_MARGIN + i * pitch for i in range(n)]
        cursor = x_open - 0.3
        k = 0
        for x, spec in zip(xs, specs):
            lo, hi = x - DOOR_W / 2, x + DOOR_W / 2
            if lo > cursor:
                boxes.append(box(f"GEO-hub_wall{side}_{k}", (cursor, lo), (const - t, const + t), (0, HUB_H), "plaster_wall"))
                k += 1
            boxes.append(box(f"GEO-hub_transom{side}_{k}", (lo, hi), (const - t, const + t), (DOOR_H, HUB_H), "plaster_wall"))
            normal = (0.0, 1.0) if side == "S" else (0.0, -1.0)
            doors.append(door_record(spec["id"], spec["id"], spec["name"], spec.get("years"), style_for(spec["id"])["theme"], (x, const), normal, hub_side=side))
            cursor = hi
        boxes.append(box(f"GEO-hub_wall{side}_{k}", (cursor, L), (const - t, const + t), (0, HUB_H), "plaster_wall"))
        # pedestal bays: between consecutive surrounds, and before the first / after the last
        edges = [0.0] + xs + [L]
        for i in range(len(edges) - 1):
            a, b = edges[i], edges[i + 1]
            lo_b = a + (SURROUND_W / 2 if i > 0 else 1.5)
            hi_b = b - (SURROUND_W / 2 if i < len(edges) - 2 else 1.5)
            if hi_b - lo_b >= 1.6:
                bays[side].append(((lo_b + hi_b) / 2, const - (0.9 if side == "N" else -0.9)))
        return xs

    xs_s = wall_with_doors("S", -hw, art_rooms)
    xs_n = wall_with_doors("N", hw, people_rooms)

    # rotunda (west): drum split at the hall opening, floor disc, dome; apse (east)
    cx, cy = ROTUNDA_C
    open_half = math.degrees(math.asin(hw / ROTUNDA_R))
    shapes = [
        {"name": "GEO-hub_wall_drum", "kind": "lathe", "center": [cx, cy, 0.0], "segments": 48,
         "phi": [open_half, 360.0 - open_half],
         "profile_rz": [[ROTUNDA_R + t, 0.0], [ROTUNDA_R + t, HUB_H + 1.0], [ROTUNDA_R - t, HUB_H + 1.0], [ROTUNDA_R - t, 0.0]],
         "material": "plaster_wall"},
        # coffered dome ending in an open 2.4 m oculus (the sky backdrop shows through; FX-hub_oculus_0 is its light)
        {"name": "GEO-hub_dome", "kind": "lathe", "center": [cx, cy, HUB_H + 1.0], "segments": 48, "phi": [0.0, 360.0],
         "profile_rz": [[ROTUNDA_R - t, 0.0]] + [[(ROTUNDA_R - t) * math.cos(math.radians(a)), (ROTUNDA_R - t) * 0.85 * math.sin(math.radians(a))] for a in range(10, 81, 10)] + [[1.2, (ROTUNDA_R - t) * 0.85 * math.sin(math.radians(80))], [1.2, (ROTUNDA_R - t) * 0.85 * math.sin(math.radians(80)) + 0.4]],
         "material": "plaster_ceiling"},
        {"name": "GEO-hub_floor_rotunda", "kind": "disc", "center": [cx, cy, 0.0], "radius": ROTUNDA_R + t, "segments": 48, "phi": [0.0, 360.0], "z": [-0.2, 0.0], "material": "marble_white"},
        {"name": "GEO-hub_wall_apse", "kind": "lathe", "center": [L, 0.0, 0.0], "segments": 32, "phi": [-90.0, 90.0],
         "profile_rz": [[APSE_R + t, 0.0], [APSE_R + t, HUB_H], [APSE_R - t, HUB_H], [APSE_R - t, 0.0]], "material": "plaster_wall"},
        {"name": "GEO-hub_apse_dome", "kind": "lathe", "center": [L, 0.0, HUB_H - 0.01], "segments": 32, "phi": [-90.0, 90.0],
         "profile_rz": [[APSE_R - t, 0.0]] + [[(APSE_R - t) * math.cos(math.radians(a)), (APSE_R - t) * math.sin(math.radians(a))] for a in range(15, 91, 15)], "material": "plaster_ceiling"},
        {"name": "GEO-hub_floor_apse", "kind": "disc", "center": [L, 0.0, 0.0], "radius": APSE_R + t, "segments": 32, "phi": [-90.0, 90.0], "z": [-0.2, 0.0], "material": "marble_white"},
    ]
    # caps that close the drum's cut edges where it meets the hall walls
    boxes.append(box("GEO-hub_wallW_0", (x_open - 0.6, x_open - 0.1), (hw - t, hw + t), (0, HUB_H + 1.0), "plaster_wall"))
    boxes.append(box("GEO-hub_wallW_1", (x_open - 0.6, x_open - 0.1), (-hw - t, -hw + t), (0, HUB_H + 1.0), "plaster_wall"))

    fx = []
    for i, x in enumerate([8.0 + 8.0 * k for k in range(9)]):
        fx.append({"name": f"FX-hub_chandelier_{i}", "type": "chandelier", "pos": [r3(x), 0.0, 6.6], "color": "#ffd9a8", "intensity": 200, "distance": 22, "shadow": 1 if i % 3 == 1 else 0, "model": "ph-chandelier-02"})
        fx.append({"name": f"FX-hub_laylight_{i}", "type": "laylight", "pos": [r3(x), 0.0, HUB_H - 0.2], "color": "#fff3e0", "intensity": 0.6, "distance": 0, "shadow": 1, "size": [6.0, 5.0]})
    fx.append({"name": "FX-hub_oculus_0", "type": "oculus", "pos": [cx, cy, HUB_H + 6.0], "color": "#fff1dc", "intensity": 1.2, "distance": 0, "shadow": 1, "dir": [0.15, 0.05, -1.0]})
    fx.append({"name": "FX-hub_chandelier_rotunda", "type": "chandelier", "pos": [cx, cy, 7.5], "color": "#ffd9a8", "intensity": 240, "distance": 24, "shadow": 1, "model": "ph-chandelier-02"})
    fx.append({"name": "FX-hub_chandelier_apse", "type": "chandelier", "pos": [L + 1.5, 0.0, 6.6], "color": "#ffd9a8", "intensity": 160, "distance": 18, "shadow": 0, "model": "ph-lantern-chandelier"})
    for i, x in enumerate(xs_s):
        for j, dx in enumerate((-2.4, 2.4)):
            fx.append({"name": f"FX-hub_sconceS_{i}_{j}", "type": "sconce", "pos": [r3(x + dx), -hw + 0.3, 3.2], "color": "#ffc98a", "intensity": 20, "distance": 6, "shadow": 0, "dir": [0, 1, 0]})
    for i, x in enumerate(xs_n):
        for j, dx in enumerate((-2.4, 2.4)):
            fx.append({"name": f"FX-hub_sconceN_{i}_{j}", "type": "sconce", "pos": [r3(x + dx), hw - 0.3, 3.2], "color": "#ffc98a", "intensity": 20, "distance": 6, "shadow": 0, "dir": [0, -1, 0]})

    props = []
    for model, where, ped, yaw in PLACEMENTS:
        if not where.startswith("hub"):
            continue
        slot = where.split(":", 1)[1]
        if slot == "rotunda":
            pos, y = [cx, cy, 0.0], 0.0
        elif slot == "apse":
            pos, y = [L + 1.4, 0.0, 0.0], 180.0
        else:
            side, idx = slot[0], int(slot[1:])
            if idx >= len(bays[side]):
                continue
            bx, by = bays[side][idx]
            pos, y = [r3(bx), r3(by), 0.0], (-90.0 if side == "N" else 90.0)
        props.append({"name": f"SCULPT-{model}", "model": model, "pos": pos, "yaw_deg": yaw + y,
                      "pedestal": {"kind": ped, "h": 1.1 if ped == "column" else 0.45, "r": 0.45, "material": "marble_dark" if slot in ("rotunda", "apse") else "marble_white"}})
    for i, x in enumerate([20.0, 40.0, 60.0]):
        props.append({"name": f"GEO-hub_bench_{i}", "model": "ph-bench", "pos": [x, 0.0, 0.0], "yaw_deg": 0.0})

    mouldings = []
    runs = []
    for side, const in (("S", -hw), ("N", hw)):
        xs = xs_s if side == "S" else xs_n
        nrm = [0, 1, 0] if side == "S" else [0, -1, 0]
        cursor = x_open - 0.1
        for x in xs:
            lo = x - DOOR_W / 2
            if lo - cursor > 0.3:
                runs.append([[r3(cursor), const, 0.0], [r3(lo), const, 0.0], nrm])
            cursor = x + DOOR_W / 2
        runs.append([[r3(cursor), const, 0.0], [L, const, 0.0], nrm])
    for prof in ("skirting", "dado", "cornice_hub"):
        mouldings.append({"name": f"GEO-hub_{prof}", "profile": prof, "material": "marble_dark" if prof == "skirting" else "painted_trim", "runs": runs})
    for d in doors:
        mouldings.append({"name": f"GEO-hub_architrave_{d['id']}", "profile": "architrave", "material": "painted_trim", "door": d["id"]})
    # pilasters between the door surrounds (giant order)
    pilasters = []
    for side, const in (("S", -hw), ("N", hw)):
        for bx, _by in bays[side]:
            pilasters.append([r3(bx), const, 0.0])
    views = {
        "hub_west": {"pos": [-4.0, -1.5, 1.7], "target": [30.0, 0.0, 3.0], "fov_deg": 70},
        "hub_rotunda": {"pos": [1.0, 2.0, 1.7], "target": [cx, cy, 6.0], "fov_deg": 70},
        "hub_east": {"pos": [L - 22.0, 1.5, 1.7], "target": [L + 1.4, 0.0, 2.6], "fov_deg": 70},
        "hub_bays": {"pos": [18.0, -2.5, 1.7], "target": [30.0, 4.0, 2.4], "fov_deg": 70},
        "hub_rotunda_east": {"pos": [cx - 4.0, cy + 1.0, 1.7], "target": [6.0, 0.0, 3.0], "fov_deg": 70},
        "hub_rotunda_wall": {"pos": [cx + 1.0, cy - 1.0, 1.7], "target": [cx - 6.0, cy + 3.0, 4.0], "fov_deg": 70},
    }
    intro = {"title": "The Grand Hall", "years": "", "summary": "Doors to the Art-Talk galleries on the south side and to the Earth Chronicle eras on the north, each in order of time."}
    scene = {
        "kind": "hub", "id": "hub", "name": "Grand Hall", "wing": None, "intro": intro,
        "style": {"theme": "hall", "wall": "#d9cbb2", "trim": "painted_trim"},
        "floor": {"x": [cx - ROTUNDA_R, L + APSE_R], "y": [-ROTUNDA_R, ROTUNDA_R]}, "size": [L, 2 * hw], "height": HUB_H,
        "rotunda": {"center": [cx, cy], "r": ROTUNDA_R}, "apse": {"center": [L, 0.0], "r": APSE_R},
        "spawn": [cx + 1.0, cy, 0.0, 0.0], "boxes": boxes, "shapes": shapes, "mouldings": mouldings, "pilasters": pilasters,
        "doors": doors, "hangs": {}, "fx": fx, "props": props, "views": views, "bays": bays,
    }
    return scene


# ---------------------------------------------------------------- build --------------
def build(room_specs, artists, dims_for_work):
    """room_specs: ordered list (Art-Talk then People) of {id, name, wing, years, intro, min_w, min_d};
    artists: manifest artists with `room` and `works`. Returns {"layout", "rooms" (manifest), "stats"}."""
    works_by_room = {}
    for a in sorted(artists, key=lambda a: a.get("order", 0)):
        for w in a["works"]:
            works_by_room.setdefault(a["room"], []).append((w, a))
    scenes = {}
    manifest_rooms = []
    order_ids = [s["id"] for s in room_specs]
    for i, spec in enumerate(room_specs):
        nxt = room_specs[i + 1] if i + 1 < len(room_specs) else None
        prv = room_specs[i - 1] if i > 0 else None
        sc = build_room(spec, works_by_room.get(spec["id"], []), dims_for_work, nxt, prv)
        scenes[spec["id"]] = sc
        W, D = sc["size"]
        doors = {"hub": [0.0, 0.0, 0.05]}
        connects = ["hub"]
        if nxt:
            doors[nxt["id"]] = [W / 2, 2.8, 0.05]
            connects.append(nxt["id"])
        if prv:
            doors[prv["id"]] = [-W / 2, 2.8, 0.05]
            connects.append(prv["id"])
        manifest_rooms.append({
            "id": spec["id"], "name": spec["name"], "era": spec.get("era"), "years": spec.get("years", ""), "kind": "gallery",
            "wing": spec["wing"], "scene": spec["id"], "connects_to": connects,
            "position": [0.0, r3(D / 2), 0.05], "spawn": [0.0, 2.6, 0.05], "doors": doors,
            "intro": spec.get("intro"), "theme": style_for(spec["id"])["theme"],
        })
    art_rooms = [s for s in room_specs if s["wing"] == "art-talk"]
    people_rooms = [s for s in room_specs if s["wing"] == "people"]
    hub = build_hub(art_rooms, people_rooms)
    scenes = {"hub": hub, **scenes}
    hub_doors = {d["id"]: [d["pos"][0], d["pos"][1], 0.05] for d in hub["doors"]}
    manifest_rooms.insert(0, {
        "id": "hub", "name": "Grand Hall", "kind": "hub", "wing": None, "scene": "hub",
        "connects_to": order_ids, "position": [HUB_L / 2, 0.0, 0.05], "spawn": [hub["spawn"][0], hub["spawn"][1], 0.05],
        "doors": hub_doors, "intro": hub["intro"],
    })
    layout = {"units": "blender", "version": 2, "wall_t": WALL_T, "door": {"w": DOOR_W, "h": DOOR_H},
              "order": order_ids, "scenes": scenes}
    stats = {rid: sc["stats"] for rid, sc in scenes.items() if sc["kind"] == "room"}
    return {"layout": layout, "rooms": manifest_rooms, "stats": stats}


# ---------------------------------------------------------------- lint ---------------
STRUCT_WORDS = ("wall", "outer", "floor", "landing", "step")


def _overlap1(a, b, margin=0.0):
    return a[0] < b[1] - margin and b[0] < a[1] - margin


def lint(result: dict, artists: list[dict], models: dict | None = None) -> list[str]:
    errors: list[str] = []
    layout = result["layout"]
    expected = {}
    for a in artists:
        for w in a["works"]:
            expected.setdefault(a["room"], set()).add(w["id"])
    for rid, sc in layout["scenes"].items():
        names = [b["name"] for b in sc.get("boxes", [])] + [s["name"] for s in sc.get("shapes", [])] + [m["name"] for m in sc.get("mouldings", [])] + [p["name"] for p in sc.get("props", [])]
        for n in names:
            low = n.lower()
            is_struct = any(k in low for k in STRUCT_WORDS)
            if n.startswith("SCULPT-") or n.startswith("FX-") or n.startswith("DOOR-"):
                continue
            if not n.startswith("GEO-"):
                errors.append(f"{rid}: mesh name without GEO- prefix: {n}")
            part = low.split("_", 1)[1] if "_" in low else ""
            deco = any(k in part for k in ("skirting", "rail", "cornice", "dado", "architrave", "frame", "bench", "dome", "oculus", "pilaster"))
            if deco and is_struct and "wall_plinth" not in low:
                errors.append(f"{rid}: decorative piece named like structure: {n}")
        if len(set(names)) != len(names):
            errors.append(f"{rid}: duplicate mesh names")
        for b in sc.get("boxes", []):
            low = b["name"].lower()
            if b["material"] == "plaster_wall" and "wall" not in low and "transom" not in low:
                errors.append(f"{rid}: wall box without 'wall' in its name: {b['name']}")
        if sc["kind"] != "room":
            continue
        # every work hung once
        ids = set(sc["hangs"])
        exp = expected.get(rid, set())
        if ids != exp:
            errors.append(f"{rid}: hang set mismatch: {len(exp - ids)} missing, {len(ids - exp)} extra")
        # per wall: inside the free interval, inside the height zone, no overlaps
        walls = {w["side"]: w for w in sc["walls"]}
        by_wall: dict[str, list] = {}
        for h in sc["hangs"].values():
            by_wall.setdefault(h["wall"], []).append(h)
        for side, lst in by_wall.items():
            wl = walls.get(side)
            if not wl:
                errors.append(f"{rid}: hang on a non-art wall {side}")
                continue
            lo, hi = wl["free"]
            rects = []
            for h in lst:
                fw = h["frame"]["width"] + 0.01
                a0, a1 = h["along"] - h["w"] / 2 - fw, h["along"] + h["w"] / 2 + fw
                z0, z1 = h["pos"][2] - h["h"] / 2 - fw, h["pos"][2] + h["h"] / 2 + fw
                if a0 < lo - 0.01 or a1 > hi + 0.01:
                    errors.append(f"{rid} {side}: {h['id']} outside the free wall span")
                if z0 < Z_LO - 0.01 or z1 > Z_HI + 0.01:
                    errors.append(f"{rid} {side}: {h['id']} outside {Z_LO}–{Z_HI} m (z {z0:.2f}–{z1:.2f})")
                rects.append((a0, a1, z0, z1, h["id"]))
            for i in range(len(rects)):
                for j in range(i + 1, len(rects)):
                    a, b = rects[i], rects[j]
                    if _overlap1((a[0], a[1]), (b[0], b[1]), 0.24) and _overlap1((a[2], a[3]), (b[2], b[3]), 0.2):
                        errors.append(f"{rid} {side}: {a[4]} and {b[4]} overlap")
        st = sc["stats"]
        if st["scale"] < MIN_ROOM_SCALE - 1e-9:
            errors.append(f"{rid}: works scaled to {st['scale']} (< {MIN_ROOM_SCALE}); enlarge the room")
        # doors: opening clear of wall boxes at 1.2 m, and a 3 m path through it
        for d in sc["doors"]:
            px, py = d["pos"][0], d["pos"][1]
            nx, ny = d["normal"][0], d["normal"][1]
            if abs(ny) > 0.5:
                gap_x, gap_y = (px - DOOR_W / 2 + 0.01, px + DOOR_W / 2 - 0.01), (py - 0.3, py + 0.3)
                path_x, path_y = (px - 0.3, px + 0.3), (py - 1.5, py + 1.5)
            else:
                gap_x, gap_y = (px - 0.3, px + 0.3), (py - DOOR_W / 2 + 0.01, py + DOOR_W / 2 - 0.01)
                path_x, path_y = (px - 1.5, px + 1.5), (py - 0.3, py + 0.3)
            for b in sc["boxes"]:
                if "wall" not in b["name"].lower():
                    continue
                if _overlap1(b["x"], gap_x) and _overlap1(b["y"], gap_y) and b["z"][0] < 1.2 < b["z"][1]:
                    errors.append(f"{rid}: door {d['id']} blocked by {b['name']}")
                if _overlap1(b["x"], path_x) and _overlap1(b["y"], path_y) and b["z"][0] < 1.2 < b["z"][1]:
                    errors.append(f"{rid}: path through door {d['id']} crosses {b['name']}")
        for p in sc.get("props", []):
            if models is not None and p["model"] not in models:
                errors.append(f"{rid}: prop model not in models.json: {p['model']}")
    hub = layout["scenes"]["hub"]
    room_ids = {rid for rid, sc in layout["scenes"].items() if sc["kind"] == "room"}
    hub_targets = [d["target"] for d in hub["doors"]]
    if set(hub_targets) != room_ids:
        errors.append(f"hub doors {sorted(set(hub_targets) ^ room_ids)} do not match the rooms")
    for side in ("N", "S"):
        xs = sorted(d["pos"][0] for d in hub["doors"] if d["hub_side"] == side)
        for a, b in zip(xs, xs[1:]):
            if b - a < SURROUND_W:
                errors.append(f"hub: {side} doors at {a} and {b} closer than a surround ({SURROUND_W} m)")
    for p in hub.get("props", []):
        if models is not None and p["model"] not in models:
            errors.append(f"hub: prop model not in models.json: {p['model']}")
    return errors


def write_layout(result: dict) -> Path:
    LAYOUT_OUT.write_text(json.dumps(result["layout"], ensure_ascii=False, indent=0), encoding="utf-8")
    return LAYOUT_OUT


def report(result: dict) -> str:
    lines = []
    for rid, st in result["stats"].items():
        sc = result["layout"]["scenes"][rid]
        lines.append(f"  {rid:30s} {sc['size'][0]:4.0f}×{sc['size'][1]:<4.0f} works {st['works']:3d}  rows {st['rows']}  fill {st['fill']}  scale {st['scale']}")
    return "\n".join(lines)


if __name__ == "__main__":
    print("build_layout.py is driven by build_manifest.py (python3 _Museum/build_manifest.py [--lint])")
