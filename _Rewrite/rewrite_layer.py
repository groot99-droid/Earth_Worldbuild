#!/usr/bin/env python3
"""Creative rewrite layer for the Earth Chronicle site (_Site) and the Chronicle Museum (_Museum).

The vault notes and the museum manifest stay the source of truth and are never edited. This tool keeps a
separate, labelled layer of rewritten text in the four voices of the creative-writing tool
(Pipelines/creative-writing), checks every rewrite against its source, and publishes the layer to both sites.

  python _Rewrite/rewrite_layer.py status
  python _Rewrite/rewrite_layer.py export --target site|museum [--chars 36000] [--all] [--ids ID ...]
  python _Rewrite/rewrite_layer.py todo _Rewrite/batches/<batch>.md       # items in a batch not yet merged
  python _Rewrite/rewrite_layer.py validate _Rewrite/incoming/<batch>.md
  python _Rewrite/rewrite_layer.py merge _Rewrite/incoming/<batch>.md   # keeps passing items, then publishes
  python _Rewrite/rewrite_layer.py publish

Batches are plain sectioned text (see VOICES.md, "Batch format"), not JSON, so a writer never has to escape
quotes. export only picks notes that have no rewrite yet or whose source changed since it was rewritten
("pending"), which is how new additions are found. publish drops stale rewrites, so a changed note shows its
original text until it is rewritten again.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SITE_DATA = ROOT / "_Site" / "data"
MUSEUM_MANIFEST = ROOT / "_Museum" / "data" / "museum-manifest.json"
MUSEUM_OUT = ROOT / "_Museum" / "data" / "placard-rewrite.json"
STORE = HERE / "store"
BATCHES = HERE / "batches"
INCOMING = HERE / "incoming"
TARGETS = ("site", "museum")
MODES = ("essay-self-help", "horror-prose", "epic-fantasy", "confessional-poetry")
TODAY = date.today().isoformat()


# ------------------------------------------------------------------ small helpers
def load_json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def save_json(p: Path, obj, indent=None) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=indent), encoding="utf-8")
    for attempt in range(20):                                   # Windows: OneDrive or a server may hold the file briefly
        try:
            os.replace(tmp, p)
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.5)


class Lock:
    """Cross-process lock so parallel writers can merge into the same store."""

    def __init__(self, path: Path, timeout=120):
        self.path, self.timeout = path, timeout

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        t0 = time.time()
        while True:
            try:
                self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                return self
            except FileExistsError:
                if time.time() - self.path.stat().st_mtime > 600:      # stale lock from a crashed run
                    self.path.unlink(missing_ok=True)
                    continue
                if time.time() - t0 > self.timeout:
                    raise SystemExit(f"store is locked ({self.path}); try again")
                time.sleep(0.5)

    def __exit__(self, *a):
        os.close(self.fd)
        self.path.unlink(missing_ok=True)


def digest(obj) -> str:
    return hashlib.sha1(json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:12]


# ------------------------------------------------------------------ HTML <-> markup
A_RE = re.compile(r'<a href="#/n/([^"]+)"[^>]*>(.*?)</a>', re.S)
LINK_RE = re.compile(r"\[\[([^\]|]+)\|([^\]]*)\]\]")
TAG_RE = re.compile(r"</?[a-zA-Z][^>]*>")


def to_markup(h: str) -> str:
    """Site HTML (p, ul/li, a, strong, em, code) -> the plain markup writers work in."""
    if not h:
        return ""
    t = A_RE.sub(lambda m: f"[[{m.group(1)}|{TAG_RE.sub('', m.group(2))}]]", h)
    t = re.sub(r"<strong>(.*?)</strong>", r"**\1**", t, flags=re.S)
    t = re.sub(r"<em>(.*?)</em>", r"*\1*", t, flags=re.S)
    t = re.sub(r"<code>(.*?)</code>", r"`\1`", t, flags=re.S)
    t = re.sub(r"<li>(.*?)</li>", lambda m: "- " + m.group(1).strip() + "\n", t, flags=re.S)
    t = re.sub(r"</?ul>", "\n\n", t)
    t = re.sub(r"</p>\s*", "\n\n", t)
    t = TAG_RE.sub("", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t]+\n", "\n", t)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def render_inline(t: str, known: set[str]) -> str:
    t = html.escape(t, quote=False)

    def link(m):
        nid, label = m.group(1).strip(), m.group(2).strip()
        return f'<a href="#/n/{nid}" data-id="{nid}">{label}</a>' if nid in known else label
    t = LINK_RE.sub(link, t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    return t


def render_block(text: str, known: set[str]) -> str:
    out, para, items = [], [], []

    def flush():
        nonlocal para, items
        if para:
            out.append("<p>" + render_inline(" ".join(para), known) + "</p>")
        if items:
            out.append("<ul>" + "".join(f"<li>{render_inline(i, known)}</li>" for i in items) + "</ul>")
        para, items = [], []

    for line in text.splitlines():
        s = line.strip()
        if not s:
            flush()
        elif re.match(r"^- ", s):
            if para:
                flush()
            items.append(s[2:].strip())
        else:
            if items:
                flush()
            para.append(s)
    flush()
    return "".join(out)


def plain(markup: str) -> str:
    t = LINK_RE.sub(lambda m: m.group(2), markup)
    t = re.sub(r"[*`]", "", t)
    t = re.sub(r"^- ", "", t, flags=re.M)
    return re.sub(r"\s+", " ", t).strip()


def plain_summary(markup: str, n=240) -> str:
    t = plain(markup)
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"


# ------------------------------------------------------------------ sources
def site_sources() -> dict[str, dict]:
    """id -> {title, type, date, themes, fields{summary, facts[], context, observer, questions[], extra[]}} from _Site/data."""
    idx = {r["id"]: r for r in load_json(SITE_DATA / "notes-index.json", [])}
    out = {}
    for p in sorted(SITE_DATA.glob("notes-*.json")):
        if p.name == "notes-index.json":
            continue
        for nid, d in load_json(p, {}).items():
            r = idx.get(nid, {})
            fields = {
                "summary": to_markup(d.get("summary") or ""),
                "facts": [to_markup(f) for f in d.get("facts") or []],
                "context": to_markup(d.get("context") or ""),
                "observer": to_markup(d.get("observer") or ""),
                "questions": [to_markup(q) for q in d.get("questions") or []],
                "extra": [{"title": e.get("title", ""), "text": to_markup(e.get("html", ""))} for e in d.get("extra") or []],
            }
            out[nid] = {"id": nid, "title": d.get("title") or r.get("title", nid), "type": d.get("type") or nid.split("/")[0],
                        "date": r.get("date", ""), "ds": r.get("ds"), "themes": [t.get("slug") for t in d.get("themes", [])],
                        "era": r.get("era"), "region": r.get("region"),
                        "era_title": idx.get(r.get("era"), {}).get("title", ""),
                        "region_title": idx.get(r.get("region"), {}).get("title", ""), "fields": fields}
            out[nid]["src"] = digest({"title": out[nid]["title"], "fields": fields})
    return out


def museum_sources() -> dict[str, dict]:
    m = load_json(MUSEUM_MANIFEST, {"artists": []})
    out = {}
    for a in m["artists"]:
        for w in a.get("works", []):
            item = {"id": w["id"], "title": str(w.get("title", "")), "artist": a.get("name", ""),
                    "lifespan": str(a.get("lifespan", "")), "year": str(w.get("year", "") or ""),
                    "medium": str(w.get("medium", "") or ""), "location": str(w.get("location", "") or ""),
                    "discipline": a.get("discipline", []), "movements": a.get("movements", []),
                    "country": str(a.get("country", "") or ""), "region": str(a.get("region", "") or ""),
                    "fields": {"description": w.get("description", "") or ""}}
            item["src"] = digest({"title": item["title"], "fields": item["fields"]})
            out[w["id"]] = item
    return out


SOURCES = {"site": site_sources, "museum": museum_sources}


def store_path(target: str) -> Path:
    return STORE / f"{target}.json"


# ------------------------------------------------------------------ mode suggestions (a hint; the writer decides)
CATASTROPHE = re.compile(r"extinction|asteroid|impact|plague|pandemic|epidemic|black death|famine|eruption|volcan|collapse|"
                         r"snowball|glaciation|ice age|earthquake|tsunami|flood|drought|smallpox|influenza|cholera|disease", re.I)
VIOLENCE = re.compile(r"genocide|holocaust|slave|massacre|\bwars?\b|conquest|coloni|atomic|nuclear|invasion|crusade|siege|"
                      r"battle|revolt|terror|execution|potemkin|strike|columbian", re.I)
BUILT = re.compile(r"architect|building|mosque|church|chapel|cathedral|basilica|house|villa|hall|palace|temple|museum|school|"
                   r"tower|bridge|theatre|hospital|observatory|monument|headquarters|tearoom|furniture|chair|glass|ceramic|"
                   r"earthenware|lamp|textile|wallpaper|silver|metalwork|decanter|kettle|teapot|toast|vase|poster|book design|"
                   r"typeface|print(?:ed)? book", re.I)
DARK_ART = re.compile(r"death|dead|devour|saturn|behead|holofernes|judith|scream|vampire|melencolia|judg|entomb|lament|medusa|"
                      r"devil|sleep of reason|sins|fools|babel|crows|temptation|jael", re.I)
INTIMATE = re.compile(r"portrait|child|mother|family|bath|baby|girl|woman|kiss|bride|loge|pearl|milkmaid|papa|feeding|"
                      r"strangers|letter|young hare|madonna", re.I)


ATROCITY = re.compile(r"genocide|holocaust|slaver|enslave|massacre|concentration camp|extermination|auschwitz|atrocit|"
                      r"ethnic cleansing", re.I)


def suggest_site(n: dict) -> tuple[str, str]:
    t, text = n["type"], n["title"] + " " + plain(n["fields"]["summary"])
    if ATROCITY.search(text):
        body = "essay-self-help"                                # restraint: human atrocity is never epic or horror
    elif t == "event":
        if VIOLENCE.search(text):
            body = "essay-self-help"
        elif CATASTROPHE.search(text):
            # modern human catastrophes (living memory) get the restrained essay voice, not horror
            body = "essay-self-help" if (n.get("ds") or 0) >= 1900 else "horror-prose"
        elif (n.get("ds") is not None) and n["ds"] < 1500:
            body = "epic-fantasy"
        else:
            body = "essay-self-help"
    elif t in ("era", "region", "timeline", "place", "culture", "species"):
        body = "horror-prose" if CATASTROPHE.search(n["title"]) else "epic-fantasy"
    else:
        body = "essay-self-help"
    th = set(n.get("themes") or [])
    obs = "confessional-poetry" if (t in ("person", "observer-note") or th & {"art", "kinship", "religion"}) and "war" not in th \
        and not ATROCITY.search(text) else "essay-self-help"
    return body, obs


def suggest_museum(w: dict) -> str:
    text = f"{w['title']} {w['fields']['description']}"
    disc = set(w.get("discipline") or [])  # noqa: F841
    if VIOLENCE.search(w["title"]) or re.search(r"slave|third of may|second of may|massacre|firing squad", text, re.I):
        return "essay-self-help"
    if disc and disc <= {"Architecture", "Design"} or BUILT.search(w.get("medium", "")):
        return "essay-self-help"
    if DARK_ART.search(w["title"]):
        return "horror-prose"
    if INTIMATE.search(w["title"]):
        return "confessional-poetry"
    return "epic-fantasy"


# ------------------------------------------------------------------ batch format
def site_sections(fields: dict) -> list[tuple[str, str]]:
    secs = []
    if fields["summary"]:
        secs.append(("summary", fields["summary"]))
    secs += [(f"fact {i + 1}", f) for i, f in enumerate(fields["facts"])]
    if fields["context"]:
        secs.append(("context", fields["context"]))
    if fields["observer"]:
        secs.append(("observer", fields["observer"]))
    secs += [(f"question {i + 1}", q) for i, q in enumerate(fields["questions"])]
    secs += [(f"extra {i + 1}: {e['title']}", e["text"]) for i, e in enumerate(fields["extra"])]
    return secs


def write_batch(target: str, name: str, items: list[dict]) -> Path:
    lines = [f"<!-- batch {name} · target {target} · {len(items)} items · rules: _Rewrite/VOICES.md -->", ""]
    for it in items:
        lines.append(f"=== {it['id']}")
        if target == "site":
            body, obs = suggest_site(it)
            lines += [f"title: {it['title']}", f"type: {it['type']}", f"date: {it['date']}",
                      f"themes: {', '.join(it['themes'])}", f"src: {it['src']}", f"mode: {body}", f"observer_mode: {obs}"]
            secs = site_sections(it["fields"])
        else:
            lines += [f"title: {it['title']}", f"artist: {it['artist']} ({it['lifespan']})", f"year: {it['year']}",
                      f"medium: {it['medium']}", f"location: {it['location']}", f"src: {it['src']}",
                      f"mode: {suggest_museum(it)}"]
            secs = [("description", it["fields"]["description"])]
        for head, text in secs:
            lines += [f"--- {head}", text.strip()]
        lines.append("")
    p = BATCHES / f"{name}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def parse_batch(path: Path) -> tuple[str | None, list[dict]]:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"target (site|museum)", text[:300])
    target = m.group(1) if m else None
    items = []
    for block in re.split(r"^=== ", text, flags=re.M)[1:]:
        head, _, rest = block.partition("\n")
        it = {"id": head.strip(), "meta": {}, "sections": []}
        parts = re.split(r"^--- (.+?)\s*$", rest, flags=re.M)
        for line in parts[0].splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                it["meta"][k.strip()] = v.strip()
        for i in range(1, len(parts), 2):
            it["sections"].append((parts[i].strip(), parts[i + 1].strip()))
        items.append(it)
    return target, items


def sections_to_fields(target: str, secs: list[tuple[str, str]]) -> tuple[dict, list[str]]:
    errs = []
    if target == "museum":
        d = dict(secs)
        return {"description": d.get("description", "")}, errs
    f = {"summary": "", "facts": [], "context": "", "observer": "", "questions": [], "extra": []}
    for head, text in secs:
        if head in ("summary", "context", "observer"):
            f[head] = text
        elif m := re.match(r"fact (\d+)$", head):
            f["facts"].append((int(m.group(1)), text))
        elif m := re.match(r"question (\d+)$", head):
            f["questions"].append((int(m.group(1)), text))
        elif m := re.match(r"extra (\d+):\s*(.*)$", head):
            f["extra"].append((int(m.group(1)), {"title": m.group(2).strip(), "text": text}))
        else:
            errs.append(f"unknown section '--- {head}'")
    for k in ("facts", "questions", "extra"):
        nums = [n for n, _ in f[k]]
        if nums != list(range(1, len(nums) + 1)):
            errs.append(f"{k} are not numbered 1..{len(nums)} in order")
        f[k] = [v for _, v in f[k]]
    return f, errs


# ------------------------------------------------------------------ checks
NUM_RE = re.compile(r"(?<![\w.])(\d+(?:[.,]\d+)*)(?:\s*(thousand|million|billion|trillion)\b)?(?:\s*(BCE|BC|CE|AD)\b)?", re.I)
WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿĀ-žḀ-ỿ][\w'’\-]*")
# Hedges by kind: where the source hedges in one way, the rewrite must hedge the same way (a dropped "debated" cannot be
# covered by an unrelated "about").
HEDGES = {
    "approximation": r"about|around|approximately|roughly|nearly|almost|circa|c\.|at least|more than|fewer than|less than|"
                     r"up to|estimated?|estimates|or so",
    "doubt": r"debated?|disputed|contested|controvers\w*|uncertain(?:ty)?|unclear|unknown|unproven|doubt\w*|speculat\w*|"
             r"conjectur\w*|hypothes\w*|whether|not known|little is known|disagree\w*",
    "probability": r"perhaps|possibl[ey]|possibility|probabl[ey]|(?:un)?likely|may|might|could|suggest\w*|seems?|"
                   r"apparently|plausibl\w*",
    "attribution": r"traditional(?:ly)?|traditions?|reportedly|according to|claim(?:s|ed)?|attributed|legend\w*|regarded|"
                   r"thought|believed?|argued?|argues|arguably|interpret\w*|often|widely|considered|said to",
}
SMALL_COUNTS = {"two", "three", "half"}   # restating "Earth and the Moon" as "two" is not a new quantity
HEDGE_RES = {k: re.compile(rf"(?<!\w)(?:{v})(?!\w)", re.I) for k, v in HEDGES.items()}
NUMWORDS = {"two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen",
            "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
            "eighty", "ninety", "hundred", "thousand", "million", "billion", "trillion", "dozen", "half", "quarter"}
ALLOW_NAMES = {"i", "i'm", "i've", "i'd", "i'll", "observer", "earth", "o"}
META_RE = re.compile(r"\b(as an ai|in the style of|this rewrite|the original (?:note|text)|rewritten (?:in|as|by)|"
                     r"here(?:'s| is) (?:a|the|my) (?:rewrite|version))\b", re.I)
SENT_END = tuple(".!?:;\"“”‘’(…")


def nums(text: str) -> tuple[set[str], set[tuple[str, str, str]]]:
    bare, qual = set(), set()
    for m in NUM_RE.finditer(text):
        n = m.group(1).replace(",", "")
        n = n.rstrip(".")
        bare.add(n)
        sc, era = (m.group(2) or "").lower(), (m.group(3) or "").upper()
        if sc or era:
            qual.add((n, sc, era))
    return bare, qual


def numwords(words) -> set[str]:
    """Number words ("ten", "thousands", "half") in a text or an iterable of lowercase words, singularised."""
    if isinstance(words, str):
        words = re.findall(r"[^\W\d_]+", words.lower())
    out = set()
    for w in words:
        w = w[:-1] if w.endswith("s") and w[:-1] in NUMWORDS else w
        if w in NUMWORDS:
            out.add(w)
    return out


def vocab(text: str) -> set[str]:
    words = set()
    for w in WORD_RE.findall(text):
        w = re.sub(r"['’]s$", "", w).lower()
        words.add(w)
        words.update(p for p in re.split(r"[-']", w) if p)
    return words


def new_names(rew: str, voc: set[str]) -> list[str]:
    """Capitalised words that are not at a sentence or line start and do not occur anywhere in the source note."""
    bad = []
    for line in LINK_RE.sub(" ", rew).splitlines():
        line = re.sub(r"^\s*-\s+", "", re.sub(r"[*`]", "", line))
        for m in WORD_RE.finditer(line):
            w = m.group(0)
            if not w[0].isupper():
                continue
            before = line[:m.start()].rstrip()
            if not before or before.endswith(SENT_END):
                continue                                        # sentence or line start
            base = re.sub(r"['’]s$", "", w).lower()
            parts = [p for p in re.split(r"[-'’]", base) if p]
            if base in voc or base in ALLOW_NAMES or all(p in voc or p in ALLOW_NAMES for p in parts):
                continue
            bad.append(w)
    return sorted(set(bad))


def check_element(src: str, rew: str, label: str, note_nums: set[str], voc: set[str], short_ok: bool = False) -> list[str]:
    errs = []
    if not rew.strip():
        return [f"{label}: empty"]
    if TAG_RE.search(rew):
        errs.append(f"{label}: contains HTML tags; use the markup in VOICES.md")
    if META_RE.search(rew) and not META_RE.search(src):
        errs.append(f"{label}: meta-commentary ('{META_RE.search(rew).group(0)}')")
    s_links = set(LINK_RE.findall(src))
    r_links = set(LINK_RE.findall(rew))
    if s_links != r_links:
        miss = [f"[[{a}|{b}]]" for a, b in s_links - r_links]
        extra = [f"[[{a}|{b}]]" for a, b in r_links - s_links]
        if miss:
            errs.append(f"{label}: missing link token(s) {', '.join(miss)}")
        if extra:
            errs.append(f"{label}: link token(s) not in the source {', '.join(extra)}")
    sp, rp = plain(src), plain(rew)
    sb, sq = nums(sp)
    rb, rq = nums(rp)
    if sb - rb:
        errs.append(f"{label}: dropped number(s) {sorted(sb - rb)}")
    if rb - note_nums:
        errs.append(f"{label}: number(s) not in the source note {sorted(rb - note_nums)}")
    if sq - rq:
        errs.append(f"{label}: keep these exactly: {sorted(' '.join(x for x in q if x) for q in sq - rq)}")
    names = new_names(rew, voc)
    if names:
        errs.append(f"{label}: capitalised word(s) not in the source note {names} (no new names; lowercase common words)")
    sw, rw = numwords(sp), numwords(rp)
    if sw - rw:
        errs.append(f"{label}: dropped number word(s) {sorted(sw - rw)} (keep the source's own form)")
    new_w = rw - numwords(voc) - SMALL_COUNTS
    if new_w:
        errs.append(f"{label}: number word(s) not in the source note {sorted(new_w)} "
                    f"(don't restate a quantity in other words)")
    for kind, rx in HEDGE_RES.items():
        m = rx.search(sp)
        if m and not rx.search(rp):
            errs.append(f"{label}: the source hedges by {kind} ('{m.group(0)}'); keep a hedge of that kind")
    if sp.rstrip().endswith("?") and "?" not in rp:
        errs.append(f"{label}: the source is a question; keep it a question")
    ls, lr = len(sp), len(rp)
    if ls:
        if short_ok or ls < 90:
            lo, hi = ls * 0.4, ls * 3.5
        else:                                                   # a floor so short fields keep room for the voice's shape
            lo, hi = ls * 0.6, max(ls * 1.8, ls + 200)
        if lr < lo or lr > hi:
            errs.append(f"{label}: length {lr} chars vs source {ls} (allowed {int(lo)}-{int(hi)})")
    return errs


def validate_item(target: str, item: dict, src: dict | None) -> tuple[dict | None, list[str]]:
    iid = item["id"]
    if src is None:
        return None, [f"{iid}: not a known {target} id"]
    errs = []
    meta = item["meta"]
    if meta.get("src") != src["src"]:
        errs.append(f"{iid}: src {meta.get('src')!r} does not match the current source {src['src']!r} (re-export)")
    mode = meta.get("mode", "")
    if mode not in MODES:
        errs.append(f"{iid}: mode {mode!r} is not one of {', '.join(MODES)}")
    obs_mode = meta.get("observer_mode", "")
    if target == "site" and src["fields"]["observer"] and obs_mode not in MODES:
        errs.append(f"{iid}: observer_mode {obs_mode!r} is not one of {', '.join(MODES)}")
    fields, ferr = sections_to_fields(target, item["sections"])
    errs += [f"{iid}: {e}" for e in ferr]
    sf = src["fields"]
    if target == "site":
        all_src = " ".join([src["title"], src.get("date", ""), " ".join(src.get("themes") or []),
                            src.get("era_title", ""), src.get("region_title", ""),
                            *[plain(t) for _, t in site_sections(sf)]])
    else:
        all_src = " ".join([src["title"], src["artist"], src["lifespan"], src["year"], src["medium"], src["location"],
                            src["country"], src["region"], " ".join(src["movements"]), " ".join(src["discipline"]),
                            plain(sf["description"])])
    note_nums, _ = nums(all_src)
    voc = vocab(all_src)
    if target == "museum":
        errs += [f"{iid}: {e}" for e in check_element(sf["description"], fields["description"], "description", note_nums, voc)]
    else:
        for k in ("summary", "context", "observer"):
            if bool(sf[k]) != bool(fields[k]):
                errs.append(f"{iid}: {k} must be {'present' if sf[k] else 'absent'} (as in the source)")
            elif sf[k]:
                errs += [f"{iid}: {e}" for e in check_element(sf[k], fields[k], k, note_nums, voc)]
        for k, lab in (("facts", "fact"), ("questions", "question")):
            if len(sf[k]) != len(fields[k]):
                errs.append(f"{iid}: {len(fields[k])} {k}, the source has {len(sf[k])} (rewrite each one, one-to-one)")
                continue
            for i, (a, b) in enumerate(zip(sf[k], fields[k])):
                errs += [f"{iid}: {e}" for e in check_element(a, b, f"{lab} {i + 1}", note_nums, voc, short_ok=True)]
        if len(sf["extra"]) != len(fields["extra"]):
            errs.append(f"{iid}: {len(fields['extra'])} extra sections, the source has {len(sf['extra'])}")
        else:
            for i, (a, b) in enumerate(zip(sf["extra"], fields["extra"])):
                if a["title"] != b["title"]:
                    errs.append(f"{iid}: extra {i + 1} title must stay {a['title']!r}")
                errs += [f"{iid}: {e}" for e in check_element(a["text"], b["text"], f"extra {i + 1}", note_nums, voc)]
    entry = {"src": src["src"], "mode": mode, "fields": fields, "date": TODAY}
    if target == "site" and sf["observer"]:
        entry["observer_mode"] = obs_mode
    return entry, errs


def validate_file(path: Path) -> tuple[str, dict, list[str], int]:
    target, items = parse_batch(path)
    if target not in TARGETS:
        raise SystemExit(f"{path}: first line must say 'target site' or 'target museum' (copy the batch header)")
    sources = SOURCES[target]()
    good, errors, seen = {}, [], set()
    for it in items:
        if it["id"] in seen:
            errors.append(f"{it['id']}: appears twice")
            continue
        seen.add(it["id"])
        entry, errs = validate_item(target, it, sources.get(it["id"]))
        if errs:
            errors += errs
        else:
            good[it["id"]] = entry
    return target, good, errors, len(items)


# ------------------------------------------------------------------ commands
def pending_ids(target: str, sources: dict) -> list[str]:
    store = load_json(store_path(target), {}) or {}
    return [i for i, s in sources.items() if store.get(i, {}).get("src") != s["src"]]


def cmd_status(_a) -> int:
    for target in TARGETS:
        sources = SOURCES[target]()
        store = load_json(store_path(target), {}) or {}
        fresh = [i for i, s in sources.items() if store.get(i, {}).get("src") == s["src"]]
        stale = [i for i in sources if i in store and i not in fresh]
        modes: dict[str, int] = {}
        for i in fresh:
            modes[store[i]["mode"]] = modes.get(store[i]["mode"], 0) + 1
        print(f"{target}: {len(sources)} items, {len(fresh)} rewritten, {len(stale)} stale, "
              f"{len(sources) - len(fresh) - len(stale)} not yet rewritten; modes {modes}")
    waiting = sorted(p.name for p in INCOMING.glob("*.md")) if INCOMING.exists() else []
    if waiting:
        print("incoming, not merged yet:", ", ".join(waiting))
    return 0


def cmd_export(a) -> int:
    sources = SOURCES[a.target]()
    if a.ids:
        ids = [i for i in a.ids if i in sources]
        missing = set(a.ids) - set(ids)
        if missing:
            print("unknown ids:", ", ".join(sorted(missing)))
    elif a.all:
        ids = list(sources)
    else:
        ids = pending_ids(a.target, sources)
    if a.target == "site":
        order = {t: i for i, t in enumerate(["era", "region", "timeline", "species", "place", "culture", "event", "person",
                                              "technology", "theme", "observer-note", "source"])}
        ids.sort(key=lambda i: (order.get(sources[i]["type"], 99), sources[i]["title"].lower()))
    if not ids:
        print(f"{a.target}: nothing pending")
        return 0
    # never reuse a batch number: count old batches, superseded ones and every incoming/merged part file
    seen = [*BATCHES.rglob(f"{a.target}-*.md"), *INCOMING.rglob(f"{a.target}-*.md")]
    existing = [int(m.group(1)) for p in seen if (m := re.match(rf"{a.target}-(\d+)", p.name))]
    n = max(existing, default=0)
    size = lambda i: sum(len(plain(t)) for _, t in (site_sections(sources[i]["fields"]) if a.target == "site"  # noqa: E731
                                                   else [("d", sources[i]["fields"]["description"])]))
    batches, cur, cur_chars = [], [], 0
    for i in ids:
        s = size(i)
        if cur and (cur_chars + s > a.chars or len(cur) >= a.max_items):
            batches.append(cur)
            cur, cur_chars = [], 0
        cur.append(i)
        cur_chars += s
    if cur:
        batches.append(cur)
    for b in batches:
        n += 1
        name = f"{a.target}-{n:03d}"
        p = write_batch(a.target, name, [sources[i] for i in b])
        print(f"{p.relative_to(ROOT)}  {len(b)} items, {sum(size(i) for i in b)} chars")
    return 0


def cmd_todo(a) -> int:
    """Items of a batch that still need a rewrite, so a retried batch skips what an earlier run already merged."""
    target, items = parse_batch(Path(a.file))
    sources = SOURCES[target]()
    pend = set(pending_ids(target, sources))
    todo = [it["id"] for it in items if it["id"] in pend]
    print(f"{a.file}: {len(todo)} of {len(items)} items still to rewrite")
    for i in todo:
        print(" ", i)
    return 0


def cmd_validate(a) -> int:
    target, good, errors, n = validate_file(Path(a.file))
    print(f"{a.file}: {len(good)}/{n} items pass")
    for e in errors:
        print("  ERROR", e)
    return 1 if errors else 0


def cmd_merge(a) -> int:
    path = Path(a.file)
    target, good, errors, n = validate_file(path)
    with Lock(STORE / ".lock"):
        store = load_json(store_path(target), {}) or {}
        for iid, entry in good.items():
            entry["batch"] = path.stem
            store[iid] = entry
        save_json(store_path(target), store, indent=1)
    print(f"merged {len(good)}/{n} items from {path.name} into store/{target}.json")
    for e in errors:
        print("  REJECTED", e)
    if not errors:
        done = INCOMING / "merged"
        done.mkdir(parents=True, exist_ok=True)
        os.replace(path, done / path.name)
    cmd_publish(a)
    return 1 if errors else 0


def cmd_publish(_a) -> int:
    with Lock(STORE / ".lock"):
        # site
        sources = site_sources()
        known = {r["id"] for r in load_json(SITE_DATA / "notes-index.json", [])}
        store = load_json(store_path("site"), {}) or {}
        by_type: dict[str, dict] = {}
        index = {}
        for nid, s in sources.items():
            e = store.get(nid)
            if not e or e["src"] != s["src"]:
                continue
            f = e["fields"]
            out = {
                "summary": render_block(f["summary"], known) if f["summary"] else "",
                "facts": [render_inline(x, known) for x in f["facts"]],
                "context": render_block(f["context"], known) if f["context"] else "",
                "observer": render_block(f["observer"], known) if f["observer"] else "",
                "questions": [render_inline(x, known) for x in f["questions"]],
                "extra": [{"title": x["title"], "html": render_block(x["text"], known)} for x in f["extra"]],
                "voice": {"mode": e["mode"], "observer_mode": e.get("observer_mode", ""), "date": e.get("date", "")},
            }
            by_type.setdefault(s["type"], {})[nid] = out
            index[nid] = {"sum": plain_summary(f["summary"]) if f["summary"] else "", "mode": e["mode"]}
        types = {s["type"] for s in sources.values()}
        for t in types:
            save_json(SITE_DATA / f"rewrite-{t}.json", by_type.get(t, {}))
        save_json(SITE_DATA / "rewrite-index.json", index)
        # museum
        msrc = museum_sources()
        mstore = load_json(store_path("museum"), {}) or {}
        placards = {wid: {"description": e["fields"]["description"], "mode": e["mode"], "date": e.get("date", "")}
                    for wid, e in mstore.items() if wid in msrc and msrc[wid]["src"] == e["src"]}
        save_json(MUSEUM_OUT, placards)
    print(f"published: site {len(index)}/{len(sources)} notes, museum {len(placards)}/{len(msrc)} placards")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    e = sub.add_parser("export")
    e.add_argument("--target", choices=TARGETS, required=True)
    e.add_argument("--chars", type=int, default=36000, help="plain-text budget per batch")
    e.add_argument("--max-items", type=int, default=60)
    e.add_argument("--all", action="store_true", help="export everything, not just pending")
    e.add_argument("--ids", nargs="*")
    e.set_defaults(fn=cmd_export)
    td = sub.add_parser("todo", help="items of a batch still pending")
    td.add_argument("file")
    td.set_defaults(fn=cmd_todo)
    v = sub.add_parser("validate")
    v.add_argument("file")
    v.set_defaults(fn=cmd_validate)
    m = sub.add_parser("merge")
    m.add_argument("file")
    m.set_defaults(fn=cmd_merge)
    sub.add_parser("publish").set_defaults(fn=cmd_publish)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
