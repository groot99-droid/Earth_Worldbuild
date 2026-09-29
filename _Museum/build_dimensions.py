#!/usr/bin/env python3
"""Resolve the real-world size of every museum work -> _Museum/data/work-dimensions.json.

The viewer hangs paintings at their real size (scaled down only when a work would not fit
the wall), so every work needs a height and a width in metres. Sources, in order, recorded
per work in `source`:

  medium          "H × W cm|m" inside the Art-Talk `medium` string (height first)
  medium-height   only a height was given (or the stated size did not match the image's
                  aspect, i.e. the image is a detail); width from the image aspect
  wikidata:Q…     the Wikidata item whose image (P18) is the work's Commons file -> P2048 (height) / P2049 (width)
  search:Q…       Wikidata entity search by title, kept only when the item's creator is the artist
  default:<type>  a per-type default height (film still, print, manuscript folio, hanging
                  scroll, architecture photo ...), width from the image aspect

The result is cached in data/work-dimensions.json (committed, so builds are reproducible
and offline). Entries carrying `"lock": true` are never overwritten (hand corrections).

Usage:
  python3 _Museum/build_dimensions.py             resolve missing works (network), rewrite the cache
  python3 _Museum/build_dimensions.py --offline   never fetch; unresolved works get type defaults
  python3 _Museum/build_dimensions.py --refresh [id ...]   re-resolve everything (or the given ids)
  python3 _Museum/build_dimensions.py --check     exit 1 if a manifest work has no entry
  python3 _Museum/build_dimensions.py --report    print the source breakdown and notes

build_manifest.py imports `dims_for()` to attach `work.dims` (offline, cache or defaults).
"""
from __future__ import annotations

import json
import os
import re
import ssl
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

MUSEUM = Path(__file__).resolve().parent
ROOT = MUSEUM.parent
MANIFEST = MUSEUM / "data" / "museum-manifest.json"
CACHE = MUSEUM / "data" / "work-dimensions.json"
SCHEMA = "work-dimensions v1"

UA = "ChronicleMuseum/1.0 (https://github.com/groot99-droid/Earth_Worldbuild; groot99@icloud.com)"
SPARQL = "https://query.wikidata.org/sparql"
MIN_INTERVAL = 6.0      # s between requests: the Wikimedia edge allows a shared egress IP only a few per half minute
ATTEMPTS = 5            # tries per request (429/5xx back off between them)

# Display caps: a work taller/wider than this is shown at 1:N (the salon zone is 0.45–5.6 m
# on a 7 m wall; 4.8 m keeps the widest work inside one wall bay).
MAX_DISP_H = 3.8
MAX_DISP_W = 4.8
SCALE_STEPS = [1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20]

# Default heights (m) by work type; width follows the image aspect.
DEFAULT_H = {
    "painting": 1.0, "fresco": 2.4, "hanging-scroll": 1.6, "handscroll": 0.35, "screen": 1.7,
    "manuscript": 0.32, "book-page": 0.28, "print": 0.38, "poster": 1.0, "photo": 0.6,
    "film-still": 0.6, "architecture-photo": 1.0, "design-object": 0.55, "sculpture-photo": 1.2,
    "portrait-photo": 0.7,
}
# Types worth asking Wikidata about (the rest are photos of things whose size is not the image's).
NET_TYPES = {"painting", "fresco", "hanging-scroll", "handscroll", "screen", "manuscript", "print", "poster"}

DIM_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*[×x]\s*(\d+(?:[.,]\d+)?)(?:\s*[×x]\s*\d+(?:[.,]\d+)?)?\s*(cm|mm|m)\b", re.I)
TALL_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(cm|mm|m)\s+(?:tall|high)\b", re.I)
DIAM_RE = re.compile(r"diameter\s+(\d+(?:[.,]\d+)?)\s*(cm|mm|m)\b", re.I)


# ---------------------------------------------------------------- helpers ------------
def _num(s: str) -> float:
    return float(s.replace(",", "."))


def _metres(v: float, unit: str) -> float:
    u = unit.lower()
    return v / 100 if u == "cm" else v / 1000 if u == "mm" else v


def image_size(path: Path):
    """(w, h) pixels of a JPEG or PNG without PIL, or None."""
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = struct.unpack(">II", data[16:24])
        return w, h
    if data[:2] != b"\xff\xd8":
        return None
    i = 2
    n = len(data)
    while i + 4 <= n:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker == 0xFF:
            i += 1
            continue
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        if marker == 0xD9:
            break
        seg = struct.unpack(">H", data[i + 2:i + 4])[0]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            h, w = struct.unpack(">HH", data[i + 5:i + 9])
            return w, h
        i += 2 + seg
    return None


def work_type(work: dict, artist: dict) -> str:
    """Classify a work from its medium string and the artist's discipline."""
    if (artist.get("wing") or "art-talk") == "people":
        return "portrait-photo"
    m = (work.get("medium") or "").lower()
    disc = " ".join(artist.get("discipline") or []).lower()
    if "film" in m and ("35mm" in m or "silent" in m or "sound film" in m or "minute" in m):
        return "film-still"
    if "performance" in m or "ceremony" in m:
        return "photo"
    if "fresco" in m or "mural" in m or "ceiling" in m:
        return "fresco"
    if "hand scroll" in m or "handscroll" in m or "emaki" in m:
        return "handscroll"
    if "hanging scroll" in m:
        return "hanging-scroll"
    if "folding screen" in m or "screens" in m:
        return "screen"
    if "title page" in m or ("book" in m and "print" in m and "wood" not in m) or "volumes" in m:
        return "book-page"
    if "poster" in m:
        return "poster"
    if any(k in m for k in ("woodblock", "lithograph", "etching", "engraving", "woodcut", "drypoint", "print,", "print ")) or m.startswith("print"):
        return "print"
    if any(k in m for k in ("manuscript", "folio", "album page", "from a *", "from a ", "illuminat", "miniature")):
        return "manuscript"
    if "opaque watercolour" in m and "paper" in m:
        return "manuscript"
    if any(k in m for k in ("marble,", "marble ", "bronze,", "bronze ", "statue", "sculpture")) and any(k in m for k in ("tall", "high", "cm")) and "canvas" not in m and "panel" not in m:
        return "sculpture-photo"
    if "architecture" in disc and "canvas" not in m and "paper" not in m and "panel" not in m and "glass," not in m:
        return "architecture-photo"
    if any(k in m for k in ("brick", "stone", "stucco", "facade", "façade", "concrete", "masonry", "dome", "bell tower", "steel frame", "render over")):
        return "architecture-photo"
    if any(k in m for k in ("silver", "glass", "earthenware", "ebony", "wallpaper", "textile", "cotton", "oak", "furniture", "chair", "lamp", "vase", "teapot", "metal", "letterpress", "mosaic")):
        return "design-object"
    return "painting"


def parse_medium(medium: str):
    """(h_m, w_m, note) from the medium string; w may be None (only a height given)."""
    if not medium:
        return None
    m = DIM_RE.search(medium)
    if m:
        h, w = _metres(_num(m.group(1)), m.group(3)), _metres(_num(m.group(2)), m.group(3))
        note = None
        low = medium.lower()
        for q in ("each", "whole scroll", "whole frieze", "open", "about", "overall", "part of"):
            if q in low:
                note = f"medium says '{q}'"
        return h, w, note
    m = DIAM_RE.search(medium)
    if m:
        d = _metres(_num(m.group(1)), m.group(2))
        return d, d, "diameter"
    m = TALL_RE.search(medium)
    if m:
        return _metres(_num(m.group(1)), m.group(2)), None, "height only"
    return None


def scale_for(h: float, w: float):
    for n in SCALE_STEPS:
        if h / n <= MAX_DISP_H and w / n <= MAX_DISP_W:
            return 1.0 / n
    return 1.0 / SCALE_STEPS[-1]


def finish(entry: dict) -> dict:
    h, w = entry["h_m"], entry["w_m"]
    s = scale_for(h, w)
    entry["scale"] = s
    entry["disp_h"] = round(h * s, 4)
    entry["disp_w"] = round(w * s, 4)
    entry["h_m"] = round(h, 4)
    entry["w_m"] = round(w, 4)
    return entry


def default_entry(work: dict, artist: dict, t: str, aspect: float, px) -> dict:
    h = DEFAULT_H.get(t, 1.0)
    if t == "print" and aspect > 1.2:
        h = 0.27                       # landscape ōban
    if t == "portrait-photo" and str(work.get("id", "")).endswith("--1"):
        h = 0.9                        # a person's first image is their main portrait
    w = h * aspect
    if t == "portrait-photo" and w > 1.5:
        w = 1.5
        h = w / aspect
    return finish({"h_m": h, "w_m": w, "px": px, "type": t, "source": f"default:{t}"})


# ---------------------------------------------------------------- network ------------
class Net:
    def __init__(self, enabled: bool):
        self.enabled = enabled
        self.last = 0.0
        cafile = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
        self.ctx = ssl.create_default_context(cafile=cafile) if cafile else ssl.create_default_context()
        self.calls = 0
        self.failures = 0   # requests given up on (rate limit, outage): the work is not marked as tried

    def get(self, url: str, params: dict | None = None, accept: str = "application/json"):
        if not self.enabled:
            return None
        if params:
            url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
        wait = MIN_INTERVAL - (time.monotonic() - self.last)
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
        for attempt in range(ATTEMPTS):
            self.last = time.monotonic()
            self.calls += 1
            try:
                with urllib.request.urlopen(req, timeout=45, context=self.ctx) as r:
                    return r.read().decode("utf-8", "replace")
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503, 504) and attempt < ATTEMPTS - 1:
                    # The edge's 429 carries a canned Retry-After (1000 s); a short back-off is what
                    # actually clears it, so the wait is bounded.
                    retry_after = e.headers.get("Retry-After") if e.headers else None
                    pause = float(retry_after) if retry_after and retry_after.isdigit() else 20.0 * (attempt + 1)
                    time.sleep(min(60.0, max(20.0, pause)))
                    continue
                self.failures += 1
                print(f"  ! HTTP {e.code} for {url[:100]}", file=sys.stderr)
                return None
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                if attempt < ATTEMPTS - 1:
                    time.sleep(3 * (attempt + 1))
                    continue
                self.failures += 1
                print(f"  ! {e} for {url[:100]}", file=sys.stderr)
                return None
        return None

    def json(self, url: str, params: dict | None = None, accept: str = "application/json"):
        t = self.get(url, params, accept=accept)
        if not t:
            return None
        try:
            return json.loads(t)
        except ValueError:
            return None


def sparql(net: Net, query: str):
    return net.json(SPARQL, {"query": query}, accept="application/sparql-results+json")


def _collect_dims(j) -> tuple[list[str], dict]:
    """Bindings of ?item ?h ?w ?creatorLabel ?classLabel -> (item order, {qid: {"h", "w", "creators", "classes"}})."""
    order, out = [], {}
    for b in (j or {}).get("results", {}).get("bindings", []):
        qid = b["item"]["value"].rsplit("/", 1)[-1]
        if qid not in out:
            order.append(qid)
        e = out.setdefault(qid, {"h": None, "w": None, "creators": set(), "classes": set()})
        if "h" in b and e["h"] is None:
            e["h"] = float(b["h"]["value"])
        if "w" in b and e["w"] is None:
            e["w"] = float(b["w"]["value"])
        if "creatorLabel" in b:
            e["creators"].add(b["creatorLabel"]["value"])
        if "classLabel" in b:
            e["classes"].add(b["classLabel"]["value"])
    return order, out


def sparql_dims(net: Net, qids: list[str]):
    """{qid: {"h", "w", "creators": [labels], "classes": [labels]}}"""
    if not qids:
        return {}
    values = " ".join(f"wd:{q}" for q in qids)
    q = f"""SELECT ?item ?h ?w ?creatorLabel ?classLabel WHERE {{
  VALUES ?item {{ {values} }}
  OPTIONAL {{ ?item p:P2048/psn:P2048/wikibase:quantityAmount ?h }}
  OPTIONAL {{ ?item p:P2049/psn:P2049/wikibase:quantityAmount ?w }}
  OPTIONAL {{ ?item wdt:P170 ?creator }}
  OPTIONAL {{ ?item wdt:P31 ?class }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}"""
    return _collect_dims(sparql(net, q))[1]


def sparql_search_dims(net: Net, title: str, limit: int = 8) -> list[tuple[str, dict]]:
    """Entity search by title (the indexed search behind the query service) joined with each
    hit's size and creator, in search order: one request instead of a label scan plus a
    dimensions query. Only items that carry both a height and a width come back."""
    t = title.replace("\\", "\\\\").replace('"', '\\"')
    q = f"""SELECT ?item ?ord ?h ?w ?creatorLabel ?classLabel WHERE {{
  SERVICE wikibase:mwapi {{
    bd:serviceParam wikibase:api "EntitySearch"; wikibase:endpoint "www.wikidata.org";
                    mwapi:search "{t}"; mwapi:language "en"; mwapi:limit "{limit}" .
    ?item wikibase:apiOutputItem mwapi:item .
    ?ord wikibase:apiOrdinal true .
  }}
  ?item p:P2048/psn:P2048/wikibase:quantityAmount ?h .
  ?item p:P2049/psn:P2049/wikibase:quantityAmount ?w .
  OPTIONAL {{ ?item wdt:P170 ?creator }}
  OPTIONAL {{ ?item wdt:P31 ?class }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}} ORDER BY ?ord"""
    order, out = _collect_dims(sparql(net, q))
    return [(qid, out[qid]) for qid in order]


def _file_urls(file_title: str) -> list[str]:
    name = file_title[5:] if file_title.lower().startswith("file:") else file_title
    base = "http://commons.wikimedia.org/wiki/Special:FilePath/"
    variants = {name, name.replace("_", " "), name.replace(" ", "_")}
    return [base + urllib.parse.quote(v, safe="()',!*;:@&=+$-_.~/") for v in variants]


def sparql_by_image(net: Net, file_title: str):
    """Wikidata item whose image (P18) is this Commons file, via the query service (indexed lookup)."""
    values = " ".join(f"<{u}>" for u in _file_urls(file_title))
    q = f"SELECT ?item WHERE {{ VALUES ?img {{ {values} }} ?item wdt:P18 ?img }} LIMIT 3"
    j = sparql(net, q)
    for b in (j or {}).get("results", {}).get("bindings", []):
        return b["item"]["value"].rsplit("/", 1)[-1]
    return None


def _tokens(s: str):
    return {t for t in re.split(r"[^a-z0-9]+", (s or "").lower()) if len(t) >= 3}


def creator_matches(creators, artist: dict) -> bool:
    names = _tokens(artist.get("name", "")) | _tokens(artist.get("short_name", "")) | _tokens(artist.get("slug", ""))
    stop = {"the", "and", "von", "van", "der", "del", "brothers", "school"}
    names -= stop
    for c in creators:
        ct = _tokens(c) - stop
        if names & ct:
            return True
    return False


def clean_title(title: str) -> str:
    t = re.sub(r"\s*[—–-]\s*.*$", "", title or "")     # drop " — Hakubyō scroll fragment"
    t = re.sub(r"\s*\([^)]*\)\s*$", "", t)              # drop trailing parentheticals
    return t.strip() or (title or "")


# ---------------------------------------------------------------- resolve ------------
def image_path(work: dict, artist: dict, wings_by_id: dict) -> Path:
    wing = wings_by_id.get(artist.get("wing") or "art-talk") or {}
    base = wing.get("image_base") or "Art-Talk-main/"
    return ROOT / base / (work.get("image") or "")


def resolve_one(work: dict, artist: dict, wings_by_id: dict, net: Net) -> dict:
    t = work_type(work, artist)
    px = None
    if work.get("w") and work.get("h"):
        px = [int(work["w"]), int(work["h"])]
    else:
        s = image_size(image_path(work, artist, wings_by_id))
        px = [s[0], s[1]] if s else None
    aspect = (px[0] / max(1, px[1])) if px else 1.0
    aspect = max(0.15, min(8.0, aspect))

    # A building's or a film's stated size is not the image's: photos of those use defaults.
    parsed = None if t in ("architecture-photo", "film-still", "design-object", "photo") else parse_medium(work.get("medium") or "")
    if parsed:
        h, w, note = parsed
        if w is None:
            return finish({"h_m": h, "w_m": h * aspect, "px": px, "type": t, "source": "medium-height", "note": note})
        ratio = (w / h) / aspect
        if abs(ratio - 1) > 0.15 and abs((h / w) / aspect - 1) <= 0.15:
            h, w = w, h
            note = (note + "; " if note else "") + "swapped to match the image aspect"
            ratio = (w / h) / aspect
        if abs(ratio - 1) > 0.35:
            return finish({"h_m": h, "w_m": h * aspect, "px": px, "type": t, "source": "medium-height",
                           "note": (note + "; " if note else "") + f"stated {h:.2f}×{w:.2f} m does not match the image aspect (detail/crop?)"})
        e = {"h_m": h, "w_m": w, "px": px, "type": t, "source": "medium"}
        if note:
            e["note"] = note
        return finish(e)

    if t in NET_TYPES and net.enabled:
        qid, how = None, None
        credit = work.get("credit") or {}
        if credit.get("file"):
            qid = sparql_by_image(net, credit["file"])
            how = "P18" if qid else None
        if qid:
            d = sparql_dims(net, [qid]).get(qid)
            if d and d["h"] and d["w"] and (not d["creators"] or creator_matches(d["creators"], artist) or how == "P18"):
                e = {"h_m": d["h"], "w_m": d["w"], "px": px, "type": t, "source": f"wikidata:{qid}", "qid": qid}
                if abs((d["w"] / d["h"]) / aspect - 1) > 0.35:
                    e["source"] = "medium-height"
                    e["w_m"] = d["h"] * aspect
                    e["note"] = f"wikidata {qid} size does not match the image aspect (detail/crop?)"
                return finish(e)
        raw_title = work.get("title") or ""
        title = clean_title(raw_title)
        if title:
            hits = sparql_search_dims(net, raw_title)
            if not hits and title != raw_title:
                hits = sparql_search_dims(net, title)
            for q, d in hits:
                if not d["h"] or not d["w"] or not creator_matches(d["creators"], artist):
                    continue
                e = {"h_m": d["h"], "w_m": d["w"], "px": px, "type": t, "source": f"search:{q}", "qid": q}
                if abs((d["w"] / d["h"]) / aspect - 1) > 0.35:
                    e["w_m"] = d["h"] * aspect
                    e["source"] = "medium-height"
                    e["note"] = f"wikidata {q} size does not match the image aspect (detail/crop?)"
                return finish(e)
    return default_entry(work, artist, t, aspect, px)


def load_cache() -> dict:
    try:
        j = json.loads(CACHE.read_text(encoding="utf-8"))
        return j.get("works", {}) if isinstance(j, dict) else {}
    except (OSError, ValueError):
        return {}


def save_cache(works: dict) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    out = {"_schema": SCHEMA, "built": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
           "notes": "Real-world sizes in metres (h_m × w_m); disp_* is what the museum hangs (scale < 1 = shown at 1:N). "
                    "Add \"lock\": true to an entry to keep a hand correction.",
           "works": dict(sorted(works.items()))}
    CACHE.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


def iter_works(manifest: dict):
    for artist in manifest["artists"]:
        for work in artist["works"]:
            yield work, artist


def dims_for(work: dict, artist: dict, cache: dict, wings_by_id: dict | None = None) -> dict:
    """Offline lookup used by build_manifest.py: cache entry, else a type default (no network)."""
    e = cache.get(work["id"])
    if e and "disp_h" in e:
        return e
    return resolve_one(work, artist, wings_by_id or {}, Net(False))


def public_dims(entry: dict) -> dict:
    return {k: entry[k] for k in ("h_m", "w_m", "disp_h", "disp_w", "scale", "source", "type") if k in entry}


# ---------------------------------------------------------------- main ---------------
def main(argv: list[str]) -> int:
    offline = "--offline" in argv
    check = "--check" in argv
    report = "--report" in argv or not (offline or check)
    refresh_all = "--refresh" in argv and all(a.startswith("--") for a in argv[argv.index("--refresh") + 1:])
    refresh_ids = set(a for a in argv[argv.index("--refresh") + 1:] if not a.startswith("--")) if "--refresh" in argv else set()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    wings_by_id = {w["id"]: w for w in manifest.get("wings", [])}
    cache = load_cache()
    if check:
        missing = [w["id"] for w, _a in iter_works(manifest) if w["id"] not in cache]
        print(f"{len(cache)} cached entries; {len(missing)} manifest works without one")
        return 1 if missing else 0

    net = Net(not offline)
    n_new = 0
    t0 = time.time()
    for i, (work, artist) in enumerate(iter_works(manifest)):
        wid = work["id"]
        old = cache.get(wid)
        if old and old.get("lock"):
            continue
        need = old is None or refresh_all or wid in refresh_ids
        if not need and not offline and old.get("source", "").startswith("default:") and old.get("type") in NET_TYPES and "tried" not in old:
            need = True   # a default that was never looked up online
        if not need:
            continue
        failures = net.failures
        e = resolve_one(work, artist, wings_by_id, net)
        if not offline and e["source"].startswith("default:") and e["type"] in NET_TYPES and net.failures == failures:
            e["tried"] = True   # looked up online with no usable answer; a failed request leaves it for the next run
        if old and old.get("lock"):
            continue
        cache[wid] = e
        n_new += 1
        if not offline or n_new % 50 == 0:
            save_cache(cache)   # every work: a killed run keeps its progress
        if n_new % 25 == 0:
            print(f"  … {n_new} resolved ({net.calls} requests, {time.time() - t0:.0f}s)", flush=True)
    save_cache(cache)

    if report:
        by_source: dict[str, int] = {}
        for e in cache.values():
            k = e["source"].split(":")[0]
            by_source[k] = by_source.get(k, 0) + 1
        print(f"Wrote {CACHE} — {len(cache)} works, {n_new} (re)resolved, {net.calls} requests")
        for k, v in sorted(by_source.items(), key=lambda kv: -kv[1]):
            print(f"  {k:14s} {v}")
        by_type: dict[str, int] = {}
        for e in cache.values():
            by_type[e["type"]] = by_type.get(e["type"], 0) + 1
        print("  types: " + ", ".join(f"{k} {v}" for k, v in sorted(by_type.items(), key=lambda kv: -kv[1])))
        scaled = [(wid, e) for wid, e in cache.items() if e.get("scale", 1) < 1]
        print(f"  shown at reduced scale: {len(scaled)}")
        for wid, e in sorted(scaled, key=lambda kv: kv[1]["scale"])[:12]:
            print(f"    {wid:34s} {e['h_m']:.2f} × {e['w_m']:.2f} m  1:{round(1 / e['scale'])}")
        notes = [(wid, e["note"]) for wid, e in cache.items() if e.get("note")]
        if notes:
            print(f"  notes ({len(notes)}):")
            for wid, n in notes[:40]:
                print(f"    {wid:34s} {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
