#!/usr/bin/env python3
"""Collect freely licensed images for every note in the Earth Chronicle vault.

Adapted from Art-Talk-main/scripts/fetch_images.py (Retry-After backoff, lead-image
resolution, imageinfo licence filter, standard thumbnail buckets, polite delays).

Pipeline (each phase caches under data/cache/ so the run is resumable):
  1. wiki      resolve each note title to an English Wikipedia article; verify the
               article matches the note type (disambiguation / category / description
               checks) or fall back to Wikipedia search; grab lead image + article images
  2. commons   Commons file search for notes whose article gave too few candidates
  3. info      Commons imageinfo (licence, size, author) for every candidate file
  4. download  per note: walk candidates, accept free licences only, resize (max 960 px,
               JPEG q80), dedupe, save images/<type>/<slug>/<n>.jpg, record credits
  5. fallback  shortfalls: NASA Images, Smithsonian Open Access (needs SI_API_KEY),
               Met Open Access
  6. borrow    notes with no image of their own (observer notes, timelines, themes,
               regions) reuse the first image of their most-linked note, flagged as such
  7. report    data/image-gaps.json

Usage:
    python fetch_images.py --sample 20          # mixed-type trial
    python fetch_images.py                      # everything not yet done
    python fetch_images.py --only "Hokusai" bronze-age
    python fetch_images.py --types person event --limit 50
    python fetch_images.py --force              # redo chosen notes
    python fetch_images.py --retry-gaps         # revisit notes that fell short
    python fetch_images.py --phase discover     # only phases 1-3
"""
from __future__ import annotations

import argparse
import hashlib
import html
import io
import math
import os
import re
import shutil
import sys
import time
from collections import Counter, defaultdict

import requests
from PIL import Image

from common import CACHE, DATA, IMAGES, SITE, load_json, load_notes, save_json

WP = "https://en.wikipedia.org/w/api.php"
COMMONS = "https://commons.wikimedia.org/w/api.php"
BUCKETS = [250, 330, 500, 960, 1280]
MAX_SIDE = 960
JPEG_QUALITY = 80
API_DELAY = 0.6
DOWNLOAD_DELAY = 1.2
MIN_SIDE = 300
BATCH = 50
Image.MAX_IMAGE_PIXELS = None

def _contact() -> str:
    cfg = load_json(SITE.parent / "_RAG" / "fetch_config.local.json", {})
    return cfg.get("contact_email") or "unknown"

session = requests.Session()
session.headers["User-Agent"] = f"EarthChronicle/1.0 (educational vault site; contact: {_contact()}) python-requests"


class RateLimited(Exception):
    pass


def get(url, params=None, attempts=6, max_wait=900, **kw) -> requests.Response:
    """GET with retries; honours Retry-After (up to max_wait), else exponential backoff."""
    backoff = 2.0
    for attempt in range(attempts):
        try:
            r = session.get(url, params=params, timeout=60, **kw)
        except requests.RequestException as exc:
            if attempt == attempts - 1:
                raise
            wait = backoff
            print(f"  network error ({exc}); retrying in {wait:.0f}s", file=sys.stderr)
        else:
            if r.status_code == 200:
                return r
            if r.status_code not in (429, 500, 502, 503, 504) or attempt == attempts - 1:
                r.raise_for_status()
            ra = r.headers.get("Retry-After", "")
            wait = float(ra) + 5 if ra.isdigit() else backoff
            if wait > max_wait:
                raise RateLimited(f"HTTP {r.status_code}, Retry-After {ra}s")
            print(f"  HTTP {r.status_code}; retrying in {wait:.0f}s", file=sys.stderr)
        time.sleep(wait)
        backoff *= 2
    raise RuntimeError("unreachable")


def api(endpoint: str, params: dict) -> dict:
    p = {"action": "query", "format": "json", "formatversion": "2", "maxlag": "5", **params}
    data = get(endpoint, p).json()
    if "error" in data:
        raise RuntimeError(f"API error: {data['error']}")
    time.sleep(API_DELAY)
    return data


def api_all(endpoint: str, params: dict) -> list[dict]:
    """Run a query following `continue` until exhausted; return the list of responses."""
    out, cont = [], {}
    while True:
        data = api(endpoint, {**params, **cont})
        out.append(data)
        cont = data.get("continue")
        if not cont:
            return out


def chunks(items, n):
    items = list(items)
    for i in range(0, len(items), n):
        yield items[i:i + n]


# ---------------------------------------------------------------- text helpers
STOP = {"the", "of", "and", "a", "an", "in", "to", "for", "on", "de", "la", "le", "et", "al", "or", "from", "at", "by"}


def sig_tokens(s: str) -> set[str]:
    s = re.sub(r"\(.*?\)", " ", s.lower())
    return {t for t in re.findall(r"[a-z0-9]+", s) if t not in STOP and len(t) > 1}


def plain(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def source_subject(title: str) -> str | None:
    """Sources: the article a source is about (Britannica on X -> X); None if it is a paper."""
    if "et al" in title:
        return None
    m = re.match(r"^(.+?) \((?:[^)]*Search Summaries[^)]*)\)$", title)
    if m:
        return m.group(1)
    m = re.match(r"^.+? on (?:the )?(.+?)(?: \([^)]*\))?$", title)
    if m:
        return m.group(1)
    return re.sub(r"\s*\([^)]*\)\s*$", "", title)


def query_title(note) -> str:
    if note["type"] in ("observer-note", "timeline"):
        return ""
    if note["type"] == "source":
        return source_subject(note["title"]) or ""
    return note["title"]


TYPE_RE = {
    "person": r"\b(born|died|births|deaths|people|painter|king|queen|emperor|empress|ruler|writer|poet|scientist|philosopher|pharaoh|general|saint|prophet|explorer|activist|artist|physician|mathematician|architect|composer|monarch|leader|politician|priest|scholar|inventor|astronomer|sultan|caliph|revolutionary|sculptor|author|author|physicist|chemist|biologist|naturalist|reformer|warrior|khan|shah|regent|mystic|teacher|traveller|traveler|navigator|engineer|singer|filmmaker|designer|photographer|novelist|playwright|dramatist|historian|geographer|economist|theologian|monk|nun|princess|prince|dictator|president|minister|commander|admiral|conqueror|founder|emir|lord|chief|princess|goddess|queen|scribe|lawgiver|patriarch|pope|bishop|sage|hero|rebel|slave|enslaved|abolitionist|nobel|princess|mathematics|linguist|anthropologist)\b|\d{3,4}\s*[â€“\-â€”]\s*\d{0,4}",
    "species": r"(species|genus|extinct|fossil|dinosaur|hominin|homo\b|animal|plant|mammal|bird|reptile|taxon|taxa|bacteri|organism|evolution|primate|ape\b|fish|tree|crop|domestic|breed|wolf|horse|human|cyano|amphib|insect|archaea|mollusc|arthropod|hominid|australopith|trilobite|vertebrate|lineage|clade|family of|order of|subspecies|hybrid|cereal|grass|wheat|maize|rice|dog|cat\b|cattle|pig|sheep|goat|virus)",
    "place": r"(city|town|village|site|ruins|archaeological|river|mountain|island|desert|lake|valley|temple|palace|monument|heritage|capital|port|province|region|cave|fortress|tomb|necropolis|pyramid|complex|settlement|geograph|coordinates|located|sea\b|strait|plateau|mosque|cathedral|church|wall|harbo|country|municipality|district|state|area|ancient|hill|mound|earthwork|stone|megalith|citadel|fort\b|castle|park|monastery|ocean|peninsula|volcano|canyon|bay|coast|delta|basin|oasis|route|road|gulf|street|square|mine|quarry|dam|canal|bridge|gate|garden|lands|territory|kingdom|building|structure|shrine|pilgrimage|cemetery|burial|zone|ridge|range|falls|crater|reef|forest|jungle|steppe|tundra|glacier)",
    "culture": r"(people|culture|civili[sz]ation|empire|kingdom|dynasty|ethnic|tribe|state|society|nation|archaeological|period|language|caliphate|sultanate|republic|confederation|polity|realm|khanate|group|tradition|history|ancient|hunter|gatherer|farmers|nomad|pastoral|city-state|league|movement|religion|order|clan|lineage|family|federation|sphere|network|colony|colonial|province|territory|country|region|urban|settlement|complex|horizon|phase|speaking|descend|inhabit|indigenous|native|aboriginal|community|communities|hominin|human|migration|diaspora)",
    "event": r"(war|battle|revolution|treaty|event|disaster|pandemic|epidemic|extinction|eruption|massacre|conquest|expedition|rebellion|uprising|migration|exchange|movement|era\b|period|age\b|collapse|invasion|siege|crisis|reform|discovery|invention|founding|expansion|spread|agreement|declaration|famine|earthquake|impact|glaciation|transition|genocide|campaign|trade|independence|abolition|landing|launch|ratification|coup|conference|congress|council|history|origin|emergence|formation|domestication|settlement|colonization|colonisation|process|phase|conflict|dispute|incident|reign|rule|development|beginning|rise|fall|decline|shift|change|treaty|accord|pact|peace|alliance|union|federation|empire|dynasty|kingdom|state|republic|unification|partition|separation|exodus|voyage|circumnavigation|survey|census|law|code|act|edict|charter|constitution|trial|execution|assassination|coronation|founded|established|opened|completed|built|constructed|erupt|explosion|bomb|attack|raid|revolt|mutiny|strike|protest|march|riot|holocaust|slavery|slave|plague|flu|virus|disease|outbreak|ice|climate|warming|oxygen|evolution|bombardment|supercontinent|orogeny|drift|magnetic|reversal|snowball|greenhouse|mass|dispersal|out of africa|arrival|contact|encounter|meeting|exploration)",
    "era": r"(period|epoch|era\b|age\b|eon|history|geolog|prehistor|time|stage|phase|interval|millennium|century|ice|epipaleolithic|paleolithic|mesolithic|neolithic|antiquity|medieval|modern|early|late)",
    "technology": r"(technology|tool|invention|device|machine|system|writing|material|metal|method|technique|instrument|vehicle|weapon|craft|engineering|architecture|structure|medicine|drug|energy|fuel|process|language|script|alphabet|calendar|agriculture|crop|road|ship|boat|wheel|clock|money|coin|paper|printing|practice|art\b|cooking|fire|fabric|textile|glass|ceramic|pottery|stone|bronze|iron|steel|gunpowder|compass|telescope|computer|internet|electric|antibiotic|vaccine|aqueduct|sewer|sanitation|irrigation|plough|plow|domestication|farming|brewing|fermentation|dye|ink|book|codex|map|number|numeral|mathematic|zero|sail|canoe|wagon|chariot|bridge|dam|canal|lighthouse|monument|architecture|building|construction|fortification|sanitary|hygiene|plastic|nuclear|rocket|satellite|radio|television|telegraph|telephone|engine|steam|railway|railroad|aircraft|airplane|automobile|car\b|bicycle|camera|photograph|film|sound|recording|music|instrument|mechanism|apparatus|equipment|implement|utensil|container|vessel|jar|pot|pipe|wire|cable|network|web|software|algorithm|code|program)",
}
NO_SEARCH = {"observer-note", "timeline", "theme"}   # abstract notes: no article to find; they borrow images later
NO_CHECK = {"region", "theme", "observer-note", "timeline", "source"}

SPACE_RE = re.compile(r"\b(moon|lunar|solar system|apollo|space|sputnik|mars|comet|asteroid|planet|earth|hadean|archean|meteor|impact|big bang|universe|eclipse|satellite|cosmic|sun|volcan|ice age|glacia|atmospher|climate|extinction|oxygen|orbit|telescope|rocket)", re.I)


def type_ok(ntype: str, page: dict) -> bool:
    if page.get("disambig") or page.get("missing"):
        return False
    if ntype in NO_CHECK:
        return True
    blob = " ".join([page.get("desc") or "", (page.get("extract") or "")[:400], " ".join(page.get("cats") or [])]).lower()
    return bool(re.search(TYPE_RE[ntype], blob))


# ---------------------------------------------------------------- phase 1: Wikipedia
def wiki_resolve(titles: list[str], cache: dict) -> None:
    """Fill cache[title] = {title,desc,extract,cats,disambig,lead,missing} for every requested title."""
    todo = [t for t in dict.fromkeys(titles) if t and t not in cache]
    for batch in chunks(todo, 20):
        params = {
            "prop": "pageimages|description|pageprops|extracts|categories", "titles": "|".join(batch),
            "redirects": "1", "piprop": "name", "pilicense": "free", "ppprop": "disambiguation",
            "exintro": "1", "explaintext": "1", "exsentences": "3", "exlimit": "max",
            "cllimit": "max", "clshow": "!hidden",
        }
        pages: dict[str, dict] = {}
        norm: dict[str, str] = {}
        redirs: dict[str, str] = {}
        for data in api_all(WP, params):
            q = data.get("query", {})
            for m in q.get("normalized", []):
                norm[m["from"]] = m["to"]
            for m in q.get("redirects", []):
                redirs[m["from"]] = m["to"]
            for p in q.get("pages", []):
                d = pages.setdefault(p["title"], {"title": p["title"], "cats": [], "disambig": False, "missing": bool(p.get("missing"))})
                if p.get("pageimage"):
                    d["lead"] = p["pageimage"]
                if p.get("description"):
                    d["desc"] = p["description"]
                if p.get("extract"):
                    d["extract"] = p["extract"]
                if "disambiguation" in (p.get("pageprops") or {}):
                    d["disambig"] = True
                d["cats"].extend(c["title"].replace("Category:", "") for c in p.get("categories", []))
        for t in batch:
            cur = norm.get(t, t)
            cur = redirs.get(cur, cur)
            cache[t] = pages.get(cur) or {"title": cur, "missing": True, "cats": [], "disambig": False}
        save_json(CACHE / "wiki.json", cache, indent=None)
        print(f"  wiki: {min(len(cache), len(todo))}/{len(todo)} titles resolved", flush=True)


def wiki_search(query: str, cache: dict) -> list[str]:
    key = "search:" + query
    if key not in cache:
        data = api(WP, {"list": "search", "srsearch": query, "srlimit": "6", "srnamespace": "0"})
        cache[key] = [r["title"] for r in data["query"]["search"]]
    return cache[key]


def resolve_notes(notes, wiki: dict) -> dict[str, dict | None]:
    """note id -> verified article record (or None)."""
    wiki_resolve([query_title(n) for n in notes], wiki)
    result: dict[str, dict | None] = {}
    failed = []
    for n in notes:
        q = query_title(n)
        page = wiki.get(q)
        if page and type_ok(n["type"], page):
            result[n["id"]] = {**page, "how": "title"}
        else:
            failed.append(n)
    # precision fallback: search, then require the type check and token overlap with the note title
    for n in failed:
        q = query_title(n)
        if not q or n["type"] in NO_SEARCH:
            result[n["id"]] = None
            continue
        hint = {"species": "species", "place": "", "person": "", "culture": "", "event": ""}.get(n["type"], "")
        cands = wiki_search(f"{q} {hint}".strip(), wiki)
        wiki_resolve(cands, wiki)
        pick = None
        for c in cands:
            page = wiki.get(c)
            qt = sig_tokens(q)
            if page and type_ok(n["type"], page) and len(qt & sig_tokens(page["title"])) >= max(1, math.ceil(0.5 * len(qt))):
                pick = {**page, "how": "search"}
                break
        result[n["id"]] = pick
    save_json(CACHE / "wiki.json", wiki, indent=None)
    return result


BAD_NAME = re.compile(r"(^|[ _\-(])(flag|coat of arms|logo|icon|symbol|commons-|wiki|ambox|question|padlock|edit-|locator|location[ _]map|blank|stub|folder|disambig|increase|decrease|steady|red pog|nuvola|crystal|gnome|portal|sister|wikt|text document|oojs|p vip|semi-protection|lock-|emblem|signature|autograph|seal of|speaker icon|loudspeaker|ambox|merge|split|arrow|star|cscr|button|barnstar|award|sound|audio|video|clock|cc-|cc by|by-sa|pd-|public domain mark|no image|image missing|replace|nuvola)", re.I)
GOOD_EXT = (".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff")


def good_filename(f: str) -> bool:
    return f.lower().endswith(GOOD_EXT) and not BAD_NAME.search(f)


def article_images(pages: dict[str, dict], cache: dict) -> None:
    """cache[title] = list of file names used in the article (order preserved)."""
    todo = [t for t in pages if t not in cache]
    for batch in chunks(todo, BATCH):
        params = {"prop": "images", "titles": "|".join(batch), "imlimit": "max", "redirects": "1"}
        acc: dict[str, list[str]] = defaultdict(list)
        for data in api_all(WP, params):
            for p in data.get("query", {}).get("pages", []):
                acc[p["title"]].extend(i["title"].replace("File:", "", 1) for i in p.get("images", []))
        for t in batch:
            cache[t] = acc.get(t, [])
        save_json(CACHE / "article-images.json", cache, indent=None)
        print(f"  article images: {len(cache)}", flush=True)


def commons_search(title: str, cache: dict, limit=25) -> list[str]:
    key = title
    if key not in cache:
        data = api(COMMONS, {"list": "search", "srsearch": f"{title} filetype:bitmap", "srnamespace": "6", "srlimit": str(limit)})
        toks = sig_tokens(title)
        need = max(1, math.ceil(0.6 * len(toks)))
        out = []
        for r in data["query"]["search"]:
            name = r["title"].replace("File:", "", 1)
            if good_filename(name) and len(sig_tokens(name.rsplit(".", 1)[0]) & toks) >= need:
                out.append(name)
        cache[key] = out
    return cache[key]


def norm_file(f: str) -> str:
    f = f.replace("_", " ").strip()
    return f[:1].upper() + f[1:]


# ---------------------------------------------------------------- phase 3: imageinfo
def file_info(files: list[str], cache: dict) -> None:
    todo = [f for f in dict.fromkeys(files) if f not in cache]
    for batch in chunks(todo, BATCH):
        titles = ["File:" + f for f in batch]
        data = api(COMMONS, {
            "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata", "iiurlwidth": str(MAX_SIDE),
            "iiextmetadatafilter": "LicenseShortName|LicenseUrl|Artist|NonFree|Credit|ImageDescription|Restrictions",
            "titles": "|".join(titles),
        })
        q = data.get("query", {})
        norm = {m["from"]: m["to"] for m in q.get("normalized", [])}
        pages = {p["title"]: p for p in q.get("pages", [])}
        for f, t in zip(batch, titles):
            page = pages.get(norm.get(t, t))
            info = None
            if page and page.get("imageinfo"):
                ii = page["imageinfo"][0]
                md = ii.get("extmetadata", {})
                mv = lambda k: (md.get(k) or {}).get("value", "") or ""  # noqa: E731
                info = {
                    "title": page["title"], "url": (ii.get("url") or "").split("?", 1)[0],
                    "thumburl": (ii.get("thumburl") or "").split("?", 1)[0], "page": ii.get("descriptionurl"),
                    "w": ii.get("width") or 0, "h": ii.get("height") or 0, "mime": ii.get("mime"),
                    "license": plain(mv("LicenseShortName")), "license_url": mv("LicenseUrl") or None,
                    "author": plain(mv("Artist")) or None, "nonfree": mv("NonFree").strip().lower() in ("true", "1", "yes"),
                    "restrictions": plain(mv("Restrictions")),
                    "desc": plain(mv("ImageDescription"))[:300],
                }
            cache[f] = info
        save_json(CACHE / "fileinfo.json", cache, indent=None)
        print(f"  fileinfo: {len(cache)}", flush=True)


def license_ok(info: dict) -> tuple[bool, str]:
    if info["nonfree"]:
        return False, "nonfree"
    if info["mime"] not in ("image/jpeg", "image/png", "image/tiff", "image/webp"):
        return False, f"mime {info['mime']}"
    lic = info["license"].lower()
    if re.search(r"(^|[\s\-])(nc|nd)([\s\-\d]|$)|noncommercial|non-commercial|no derivative", lic):
        return False, f"license {lic}"
    free = ("public domain" in lic or lic.startswith("pd") or lic.startswith("cc0") or lic.startswith("cc by")
            or lic.startswith("cc-by") or "no restrictions" in lic or lic.startswith("attribution"))
    if not free:
        return False, f"license {lic or 'unknown'}"
    if min(info["w"], info["h"]) < MIN_SIDE or info["w"] * info["h"] < 160_000:
        return False, "too small"
    if max(info["w"], info["h"]) / max(1, min(info["w"], info["h"])) > 4.5:
        return False, "extreme aspect"
    return True, lic


# ---------------------------------------------------------------- image handling
def thumb_url(original: str, width: int, mime: str | None) -> str:
    base, name = original.rsplit("/", 1)
    base = base.replace("/wikipedia/commons/", "/wikipedia/commons/thumb/", 1)
    suffix = ".jpg" if mime in ("image/tiff", "application/pdf") else ""
    return f"{base}/{name}/{width}px-{name}{suffix}"


def download_urls(info: dict) -> list[str]:
    w, h = info["w"], info["h"]
    original = info["url"]
    if max(w, h) <= MAX_SIDE and info["mime"] in ("image/jpeg", "image/png", "image/webp"):
        # small enough to fetch the original, but originals are rate limited: prefer a bucket below if w big
        pass
    scale = min(1.0, MAX_SIDE / max(w, h))
    need = w * scale
    usable = [b for b in BUCKETS if b < w]
    if not usable:
        return [original]
    best = next((b for b in usable if b >= need), usable[-1])
    order = [best] + [b for b in reversed(usable) if b < best]
    return [thumb_url(original, b, info["mime"]) for b in order]


def ahash(img: Image.Image) -> int:
    g = img.convert("L").resize((8, 8), Image.LANCZOS)
    px = list(g.tobytes())
    avg = sum(px) / 64
    return sum(1 << i for i, p in enumerate(px) if p >= avg)


def prep_image(content: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(content))
    img = img.convert("RGB")
    w, h = img.size
    scale = min(1.0, MAX_SIDE / max(w, h))
    if scale < 1.0:
        img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)
    return img


def save_img(img: Image.Image, dest) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)


def clean_caption(fname: str) -> str:
    n = re.sub(r"\.[A-Za-z]+$", "", fname.replace("File:", "", 1)).replace("_", " ")
    return re.sub(r"\s+", " ", n).strip()


# ---------------------------------------------------------------- run state
class State:
    def __init__(self):
        self.credits: dict = load_json(DATA / "image-credits.json", {})
        self.progress: dict = load_json(DATA / "image-progress.json", {})
        self.hashes: dict[str, list[int]] = defaultdict(list)     # note id -> ahashes of saved images
        self.used_files = Counter(c.get("file") for c in self.credits.values() if c.get("file"))

    def save(self):
        save_json(DATA / "image-credits.json", self.credits)
        save_json(DATA / "image-progress.json", self.progress)

    def have(self, note) -> int:
        d = IMAGES / note["type"] / note["slug"]
        return len(list(d.glob("*.jpg"))) if d.exists() else 0

    def add(self, note, img: Image.Image, credit: dict) -> str:
        n = self.have(note) + 1
        rel = f'{note["type"]}/{note["slug"]}/{n}.jpg'
        save_img(img, IMAGES / rel)
        self.credits[rel] = credit
        self.hashes[note["id"]].append(ahash(img))
        self.used_files[credit.get("file")] += 1
        self.save()
        return rel


def is_dup(state: State, note, img) -> bool:
    h = ahash(img)
    return any(bin(h ^ o).count("1") <= 4 for o in state.hashes.get(note["id"], []))


def try_download(urls: list[str], max_wait: float):
    err = None
    for url in urls:
        try:
            content = get(url, max_wait=max_wait).content
            time.sleep(DOWNLOAD_DELAY)
            return content, None
        except Exception as exc:  # noqa: BLE001 - try the next size
            err = exc
            print(f"    failed ({str(exc)[:80]}); trying next", file=sys.stderr)
            time.sleep(DOWNLOAD_DELAY)
    return None, err


# ---------------------------------------------------------------- candidates
def build_candidates(note, page, art_imgs: dict, csearch: dict, sample_files: set[str] | None = None) -> list[tuple[str, str]]:
    """Ordered [(file, via)] candidates for a note."""
    out: list[tuple[str, str]] = []
    seen = set()

    def add(f, via):
        f = norm_file(f)
        if f not in seen and good_filename(f):
            seen.add(f)
            out.append((f, via))

    if page:
        if page.get("lead"):
            add(page["lead"], "wikipedia-lead")
        for f in art_imgs.get(page["title"], []):
            add(f, "wikipedia-article")
    q = query_title(note)
    if q:
        for f in csearch.get(q, []):
            add(f, "commons-search")
    return out


# ---------------------------------------------------------------- fallbacks
def nasa_candidates(note, want_space: bool):
    q = re.sub(r"\(.*?\)", "", note["title"]).strip()
    r = get("https://images-api.nasa.gov/search", {"q": q, "media_type": "image", "page_size": "12"}).json()
    time.sleep(API_DELAY)
    toks = sig_tokens(q)
    for it in r.get("collection", {}).get("items", []):
        d = it["data"][0]
        blob = f"{d.get('title', '')} {d.get('description', '')}"[:600].lower()
        need = max(1, math.ceil(0.6 * len(toks)))
        if len({t for t in toks if t in blob}) < need:
            continue
        try:
            assets = get(f"https://images-api.nasa.gov/asset/{d['nasa_id']}").json()
            time.sleep(API_DELAY)
            hrefs = [i["href"] for i in assets["collection"]["items"]]
        except Exception:  # noqa: BLE001
            continue
        pick = next((h for h in hrefs if "~large" in h and h.lower().endswith((".jpg", ".jpeg"))), None) or \
               next((h for h in hrefs if "~medium" in h and h.lower().endswith((".jpg", ".jpeg"))), None)
        if pick:
            yield pick.replace(" ", "%20"), {
                "file": f"NASA {d['nasa_id']}", "caption": plain(d.get("title", "")), "source": f"https://images.nasa.gov/details/{d['nasa_id']}",
                "author": d.get("photographer") or d.get("secondary_creator") or d.get("center") or "NASA", "license": "NASA media (public domain)",
                "license_url": "https://www.nasa.gov/nasa-brand-center/images-and-media/", "via": "nasa-images"}


def met_candidates(note):
    q = re.sub(r"\(.*?\)", "", note["title"]).strip()
    r = get("https://collectionapi.metmuseum.org/public/collection/v1/search", {"q": q, "hasImages": "true", "title": "true"}).json()
    time.sleep(0.4)
    ids = (r.get("objectIDs") or [])[:10]
    toks = sig_tokens(q)
    fm = note["fm"]
    ds, de = fm.get("date_start"), fm.get("date_end", fm.get("date_start"))
    for oid in ids:
        try:
            o = get(f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{oid}").json()
        except Exception:  # noqa: BLE001
            continue
        time.sleep(0.4)
        if not o.get("isPublicDomain") or not o.get("primaryImage"):
            continue
        blob = " ".join(str(o.get(k, "")) for k in ("title", "culture", "period", "objectName", "dynasty", "tags")).lower()
        if len({t for t in toks if t in blob}) < max(1, math.ceil(0.6 * len(toks))):
            continue
        if isinstance(ds, (int, float)) and o.get("objectBeginDate") is not None and o.get("objectEndDate") is not None:
            lo, hi = min(ds, de if isinstance(de, (int, float)) else ds), max(ds, de if isinstance(de, (int, float)) else ds)
            if o["objectEndDate"] < lo - 100 or o["objectBeginDate"] > hi + 100:
                continue
        yield o["primaryImage"], {
            "file": f"Met {oid}", "caption": o.get("title", ""), "source": o.get("objectURL"),
            "author": o.get("artistDisplayName") or o.get("culture") or "The Metropolitan Museum of Art",
            "license": "CC0 (Met Open Access)", "license_url": "https://www.metmuseum.org/about-the-met/policies-and-documents/open-access", "via": "met-open-access"}


def smithsonian_candidates(note):
    key = os.environ.get("SI_API_KEY")
    if not key:
        return
    q = re.sub(r"\(.*?\)", "", note["title"]).strip()
    r = get("https://api.si.edu/openaccess/api/v1.0/search", {"q": f'{q} AND online_media_type:"Images"', "rows": "10", "api_key": key}).json()
    time.sleep(API_DELAY)
    toks = sig_tokens(q)
    for row in r.get("response", {}).get("rows", []):
        c = row.get("content", {})
        dn = c.get("descriptiveNonRepeating", {})
        title = (dn.get("title") or {}).get("content", "") or row.get("title", "")
        if (dn.get("metadata_usage") or {}).get("access") != "CC0":
            continue
        if len({t for t in toks if t in title.lower()}) < max(1, math.ceil(0.6 * len(toks))):
            continue
        media = (dn.get("online_media") or {}).get("media") or []
        img = next((m for m in media if m.get("type") == "Images" and m.get("content")), None)
        if img:
            yield img["content"] + ("&max=960" if "ids.si.edu" in img["content"] else ""), {
                "file": f"SI {row.get('id')}", "caption": title, "source": dn.get("record_link") or dn.get("guid"),
                "author": (dn.get("data_source") or "Smithsonian Institution"), "license": "CC0 (Smithsonian Open Access)",
                "license_url": "https://www.si.edu/openaccess", "via": "smithsonian-open-access"}


FALLBACKS = {
    # type -> ordered fallback archives
    "era": ["nasa", "met", "smithsonian"], "event": ["nasa", "smithsonian", "met"], "species": ["nasa", "smithsonian"],
    "technology": ["smithsonian", "met", "nasa"], "culture": ["met", "smithsonian"], "place": ["met", "smithsonian"],
    "person": ["met"], "region": [], "theme": [], "observer-note": [], "timeline": [], "source": [],
}


def run_fallbacks(state: State, note, want: int, max_wait: float) -> list[str]:
    tried = []
    space = bool(SPACE_RE.search(note["title"] + " " + note["body"][:300]))
    for name in FALLBACKS.get(note["type"], []):
        if state.have(note) >= want:
            break
        if name == "nasa" and not space:
            continue
        gen = {"nasa": nasa_candidates, "met": met_candidates, "smithsonian": smithsonian_candidates}[name]
        tried.append(name)
        try:
            for url, credit in gen(note) if name != "nasa" else gen(note, True):
                if state.have(note) >= want:
                    break
                content, _ = try_download([url], max_wait)
                if not content:
                    continue
                try:
                    img = prep_image(content)
                except Exception:  # noqa: BLE001
                    continue
                if min(img.size) < MIN_SIDE or is_dup(state, note, img):
                    continue
                state.add(note, img, credit)
                print(f"    + {name}: {credit['caption'][:60]}", flush=True)
        except RateLimited as exc:
            print(f"    {name} rate limited: {exc}", file=sys.stderr)
        except Exception as exc:  # noqa: BLE001
            print(f"    {name} failed: {str(exc)[:100]}", file=sys.stderr)
    return tried


# ---------------------------------------------------------------- borrow
BORROW_TYPES = {"observer-note", "timeline", "theme", "region"}


def borrow(state: State, notes, byid, plan):
    reuse = Counter(c.get("borrowed_from") for c in state.credits.values() if c.get("borrowed_from"))
    for n in notes:
        if n["type"] not in BORROW_TYPES or state.have(n):
            continue
        # most-linked outbound note (by inbound links count) that has images of its own
        opts = [byid[t] for t in n["out"] if byid[t]["type"] in ("event", "era", "place", "culture", "person") and state.have(byid[t])]
        if not opts:
            continue
        opts.sort(key=lambda m: (reuse[m["id"]], -len(m["inb"])))
        src = opts[0]
        rel = f'{src["type"]}/{src["slug"]}/1.jpg'
        if rel not in state.credits:
            continue
        new = f'{n["type"]}/{n["slug"]}/1.jpg'
        (IMAGES / new).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(IMAGES / rel, IMAGES / new)
        state.credits[new] = {**state.credits[rel], "via": f"borrowed from note: {src['title']}", "borrowed_from": src["id"]}
        reuse[src["id"]] += 1
    state.save()


# ---------------------------------------------------------------- main
def pick_sample(notes, n):
    bytype = defaultdict(list)
    for x in notes:
        bytype[x["type"]].append(x)
    out = []
    types = list(bytype)
    i = 0
    while len(out) < n:
        t = types[i % len(types)]
        lst = bytype[t]
        k = (i // len(types)) * 7
        if k < len(lst) and lst[k] not in out:
            out.append(lst[k])
        i += 1
        if i > 10 * n:
            break
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace"); sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="*", help="note ids / slugs / title substrings")
    ap.add_argument("--types", nargs="*")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--sample", type=int, help="mixed-type sample of N notes")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--retry-gaps", action="store_true")
    ap.add_argument("--phase", choices=["all", "discover"], default="all")
    ap.add_argument("--max-wait", type=float, default=90)
    args = ap.parse_args()

    plan = load_json(DATA / "image-plan.json", None)
    if not plan:
        sys.exit("run plan_images.py first")
    allnotes = load_notes()
    byid = {n["id"]: n for n in allnotes}
    notes = [n for n in allnotes if n["id"] in plan]
    if args.types:
        notes = [n for n in notes if n["type"] in args.types]
    if args.only:
        keys = [k.lower() for k in args.only]
        notes = [n for n in notes if any(k == n["id"] or k == n["slug"] or k in n["title"].lower() for k in keys)]
    if args.sample:
        notes = pick_sample(notes, args.sample)
    state = State()
    if not args.force:
        def pending(n):
            p = state.progress.get(n["id"])
            if not p or not p.get("done"):
                return True
            return args.retry_gaps and p["got"] < p["want"]
        notes = [n for n in notes if pending(n)]
    if args.limit:
        notes = notes[:args.limit]
    print(f"{len(notes)} notes to process", flush=True)
    if not notes:
        return 0

    t0 = time.time()
    wiki = load_json(CACHE / "wiki.json", {})
    art = load_json(CACHE / "article-images.json", {})
    csearch = load_json(CACHE / "commons-search.json", {})
    finfo = load_json(CACHE / "fileinfo.json", {})

    print("phase 1: Wikipedia articles", flush=True)
    resolved = resolve_notes(notes, wiki)
    print(f"  matched {sum(1 for v in resolved.values() if v)}/{len(notes)} ("
          f"{sum(1 for v in resolved.values() if v and v['how'] == 'search')} via search)", flush=True)
    article_images({v["title"]: v for v in resolved.values() if v}, art)

    print("phase 2: Commons search", flush=True)
    for i, n in enumerate(notes):
        want = plan[n["id"]]["count"]
        pool = build_candidates(n, resolved[n["id"]], art, {})
        q = query_title(n)
        if q and len(pool) < want + 4:
            commons_search(q, csearch)
            if i % 25 == 0:
                save_json(CACHE / "commons-search.json", csearch, indent=None)
                print(f"  commons search {i}/{len(notes)}", flush=True)
    save_json(CACHE / "commons-search.json", csearch, indent=None)

    cands = {n["id"]: build_candidates(n, resolved[n["id"]], art, csearch)[:16] for n in notes}
    print("phase 3: file info", flush=True)
    file_info([f for c in cands.values() for f, _ in c], finfo)
    print(f"discovery done in {time.time() - t0:.0f}s", flush=True)
    if args.phase == "discover":
        return 0

    print("phase 4/5: download + fallbacks", flush=True)
    problems = 0
    for idx, n in enumerate(notes, 1):
        want = plan[n["id"]]["count"]
        if args.force:
            shutil.rmtree(IMAGES / n["type"] / n["slug"], ignore_errors=True)
            state.credits = {k: v for k, v in state.credits.items() if not k.startswith(f'{n["type"]}/{n["slug"]}/')}
        have0 = state.have(n)
        rejected = Counter()
        page = resolved[n["id"]]
        for pass_no in (1, 2):
            for f, via in cands[n["id"]]:
                if state.have(n) >= want:
                    break
                if pass_no == 2 and state.have(n):
                    break
                info = finfo.get(f)
                if not info:
                    rejected["no-info"] += 1
                    continue
                if pass_no == 1 and state.used_files[info["title"]] and not have0:
                    rejected["used-elsewhere"] += 1
                    continue
                ok, why = license_ok(info)
                if not ok:
                    rejected[why[:40]] += 1
                    continue
                content, err = try_download(download_urls(info), args.max_wait)
                if content is None:
                    rejected["download-failed"] += 1
                    continue
                try:
                    img = prep_image(content)
                except Exception:  # noqa: BLE001
                    rejected["bad-image"] += 1
                    continue
                if is_dup(state, n, img):
                    rejected["duplicate"] += 1
                    continue
                state.add(n, img, {
                    "file": info["title"], "caption": clean_caption(info["title"]), "source": info["page"], "author": info["author"],
                    "license": info["license"], "license_url": info["license_url"], "via": via,
                    "w": img.size[0], "h": img.size[1]})
        tried = []
        if state.have(n) < want:
            tried = run_fallbacks(state, n, want, args.max_wait)
        got = state.have(n)
        state.progress[n["id"]] = {"done": True, "got": got, "want": want, "wiki": (page or {}).get("title"),
                                   "wiki_how": (page or {}).get("how"), "candidates": len(cands[n["id"]]),
                                   "rejected": dict(rejected), "fallbacks": tried}
        state.save()
        if got < want:
            problems += 1
        print(f"[{idx}/{len(notes)}] {n['id']:52s} {got}/{want}  wiki={(page or {}).get('title')!r}" + (f" rejected={dict(rejected)}" if rejected else ""), flush=True)

    print("phase 6: borrow", flush=True)
    borrow(state, [n for n in notes if n["type"] in BORROW_TYPES] if args.only or args.sample or args.types or args.limit else allnotes, byid, plan)

    write_gaps(state, allnotes, plan)
    print(f"done in {(time.time() - t0) / 60:.1f} min; {problems} notes short of plan")
    return 0


def write_gaps(state: State, notes, plan) -> None:
    gaps = {}
    for n in notes:
        p = plan.get(n["id"])
        if not p:
            continue
        have = state.have(n)
        if have < p["count"]:
            pr = state.progress.get(n["id"], {})
            gaps[n["id"]] = {"title": n["title"], "type": n["type"], "want": p["count"], "got": have,
                             "wiki": pr.get("wiki"), "wiki_how": pr.get("wiki_how"), "candidates": pr.get("candidates"),
                             "rejected": pr.get("rejected"), "fallbacks": pr.get("fallbacks"),
                             "best_effort": n["type"] == "source" or (p["count"] > 1 and have >= 1)}
    save_json(DATA / "image-gaps.json", gaps)


if __name__ == "__main__":
    sys.exit(main())
