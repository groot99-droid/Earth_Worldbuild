#!/usr/bin/env python3
"""Register and validate AI-made material for the site (kept separate from sourced, licensed images).

  register-images <dir>   import the Higgsfield concept art (files 00.png .. 26.png, see MANIFEST) into images/,
                          with credits flagged ai=true (model, prompt, job id, date). Abstract notes (observer notes,
                          timelines, themes) get the AI image FIRST and any borrowed placeholder removed; eras get it
                          appended after their real photos. Index 26 is the site hero banner.
  validate-text <file>    check Gemini output (JSON) against each note's own Summary/Facts and write data/ai-text.json.
                          "No new facts" guard: every number and every capitalised name in an AI line must already
                          appear in the note text; anything else is dropped, not retried.

Everything AI-made is labelled in the UI ("AI illustration", "AI-written") and listed in the image credits.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

from PIL import Image

from common import DATA, IMAGES, SITE, load_json, save_json
import fetch_images as fi

MODEL = "Recraft V4.1 via Higgsfield"
DATE = "2026-09-26"
STYLE = ("Editorial illustration in the style of a vintage natural-history plate: fine ink linework with muted watercolor wash on "
         "warm parchment, restrained palette of ochre, umber, slate blue and muted crimson, soft paper grain, no text, no lettering, "
         "no people, no faces. Subject: ")

# index -> (note id or "hero", position, caption, subject prompt, job id)
MANIFEST = {
    0: ("observer-note/fire-then-everything", "first", "A single campfire in the dark, animals at the edge of the light", "a single campfire flame at the centre of a dark plain, sparks rising like stars, animal silhouettes gathered at the edge of the light.", "bad739db-c5ef-4cca-8287-e575404fdb01"),
    1: ("observer-note/frontiers-of-extraction", "first", "An open-pit mine at the frontier of a green valley", "a remote mountain range with thin glowing lines of railway and river converging on a vast open-pit mine at the frontier of a green valley, seen from afar.", "7906d767-9608-46ea-af1d-eb7c0bd3edf2"),
    2: ("observer-note/sanctioned-harm", "first", "Rows of empty helmets in a stone courtyard", "a vast empty stone courtyard with long neat rows of empty bronze helmets on plinths under a heavy grey sky, quiet and solemn.", "5f626a6d-b7dd-4d03-b2fe-48b97abb4412"),
    3: ("observer-note/second-chances-how-the-species-ran-the-experiment-again", "first", "Two islands, each with a stepped pyramid", "two separate distant islands across a calm sea, each with a similar stepped stone pyramid rising from jungle, mirrored composition, dawn light.", "2356b4a8-fb9f-4df8-95c2-67bde30f0958"),
    4: ("observer-note/story-glue-how-strangers-cooperate-at-scale", "first", "Lit windows joined by threads to one lantern", "a night skyline of many small lit windows joined by thousands of thin luminous threads that converge on one glowing lantern above the rooftops.", "7f945003-68d3-4d10-a9ac-d8aa4b31ea59"),
    5: ("observer-note/the-fiction-of-claim-lines", "first", "A survey line across a river valley", "an aerial view of a river valley crossed by a single straight dotted survey line, boundary stones and a brass surveyor's theodolite in the foreground.", "fa599d35-5bf6-4f69-8fdd-28c8c3ac9aa8"),
    6: ("observer-note/the-great-outsourcing-of-memory", "first", "A standing stone, tablet, scroll, book and glass slab", "five objects in a row on a wooden shelf, oldest to newest: a standing stone, a clay tablet, a rolled scroll, a bound book and a softly glowing glass slab.", "2a182667-8c0f-41f9-9cde-ecc978d9ae92"),
    7: ("observer-note/the-settling-and-its-bargain", "first", "A mud-brick village at the edge of the grassland", "a small early village of mud-brick houses with a golden wheat field at the edge of wild grassland, a lone gazelle leaving toward the horizon.", "48722eb6-b90c-42c1-8fbb-6243c9668c07"),
    8: ("observer-note/the-species-as-a-geological-force", "first", "A soil profile with a thin layer of bricks, glass and metal", "a cross-section of the ground showing thick layers of ancient rock below and a thin bright top layer of bricks, glass and metal fragments, like a soil profile.", "fcb4bf0a-19cb-49c2-b719-f16ad6024a49"),
    9: ("observer-note/who-writes-the-record", "first", "A quill and an open ledger before shelves of unwritten books", "a quill and ink pot on an open blank ledger, with tall dim shelves of unwritten books behind and only a few pages lit by a single lamp.", "f13ee0cc-1d41-4f37-974d-bb5e9d90830d"),
    10: ("observer-note/why-the-species-buries-its-dead", "first", "A burial mound at dusk with an ochre-lit chamber", "an ancient burial mound at dusk with an ochre-lit stone chamber entrance, scattered wildflower offerings and standing stones.", "5486d94b-7779-440d-8b83-a1ba7f214ee0"),
    11: ("timeline/deep-time-timeline", "first", "Rock strata from molten rock to a bird skeleton", "a cutaway of geological strata spiralling from molten rock through trilobite and fern fossils up to a bird skeleton, showing deep time.", "59a0a7ee-f304-48f2-9319-dc127af3dc77"),
    12: ("timeline/human-timeline", "first", "A road from a cave hearth to a modern skyline", "a long winding road leading from a cave hearth past a ziggurat, a pyramid, a temple and a cathedral spire toward a distant modern city skyline in morning mist.", "6acd7038-4cb9-48ef-854f-3dd4d6078697"),
    13: ("timeline/master-timeline", "first", "A ribbon of time around a globe", "a great curved ribbon of time with fine tick marks wrapping around a small globe, a sun and a moon at either end of the ribbon.", "a01b1b34-7dea-4c7b-b135-37c113e69d99"),
    14: ("theme/art-and-ritual", "first", "Painted bison and horse on a cave wall", "a cave wall with ochre painted bison and horse silhouettes, pigment pots, grinding stones and a burning lamp, painted marks in red and black.", "92dd420c-81af-4cb3-8697-db7aabf4d982"),
    15: ("theme/earth-systems-and-life", "first", "A cutaway globe with ferns and a coral reef", "a cutaway globe showing atmosphere, ocean, layered rock and mantle, with ferns and a coral reef blooming along the surface.", "57dafefe-78ef-4e18-a99f-c6c25f0c8883"),
    16: ("theme/kinship-and-society", "first", "A great oak with a village beneath its canopy", "a huge old oak tree with spreading roots and branches, and a cluster of round thatched houses nestled under its canopy.", "ca8f2857-6b7b-4b5f-8e76-f5797b1863d0"),
    17: ("theme/language-and-writing", "first", "A cuneiform tablet, papyrus and a stone tablet", "a clay cuneiform tablet, a papyrus fragment and a carved stone tablet arranged together, covered in abstract script-like marks, with a reed stylus and a knotted cord.", "1f8226dc-b5e8-4f9f-b355-a7bcf3f169e3"),
    18: ("theme/religion-and-belief", "first", "Silhouettes of sacred buildings at sunrise", "a sunrise horizon with the silhouettes of many sacred buildings side by side: a stone circle, a dome, a pagoda, a spire, a stupa and a ziggurat.", "64e133b8-9dfd-411f-bb58-2d64da707423"),
    19: ("theme/science", "first", "An astrolabe, telescope and magnifying glass", "a brass astrolabe, a refracting telescope and a magnifying glass over a leaf on a desk with star charts and a compass.", "60531a76-1cc2-45e1-9645-7f2d8f0d77eb"),
    20: ("theme/technology", "first", "Tools from a stone axe to a circuit board", "a workbench laid out with tools from oldest to newest: a stone hand axe, a bronze blade, iron gears, a steam valve and a circuit board.", "00b55718-fc26-47f5-b9de-9694f04afcce"),
    21: ("theme/trade-and-economy", "first", "A market harbour with camels, ships, scales and coins", "a market harbour where a camel caravan and sailing ships converge, with sacks, spice, scales and coins laid out on stone quays.", "693aaf05-97bc-46cb-b1c9-bbe375a90eb5"),
    22: ("theme/war-and-conflict", "first", "A weathered castle wall under storm clouds", "a weathered stone castle wall at dusk with tattered banners and storm clouds gathering above the battlements.", "ae2e6a94-16a0-4824-b97f-c5ccad3a54cc"),
    23: ("era/hadean-eon", "append", "A molten young Earth and a newborn Moon", "a young molten Earth glowing orange with cracked dark crust, a huge glowing planetary impact and a newborn Moon forming beside it in a black sky.", "d3605d79-5e47-42e0-90f9-f4cbc1525f49"),
    24: ("era/archean-eon", "append", "A dark ocean with volcanic islands and stromatolite mats", "a dark young ocean under an orange sky with black volcanic islands and pale mats of stromatolites forming in the shallows.", "00e001d9-1421-46f0-ab31-2808a9078cb9"),
    25: ("era/proterozoic-eon", "append", "Shallow seas with stromatolites and cyanobacteria", "shallow turquoise seas with domed stromatolites and green blooms of cyanobacteria, and the pale edge of a global ice sheet on the far horizon.", "13be0119-b6fe-4008-8906-654c43598bea"),
    26: ("hero", "hero", "Earth rising at dawn with a thin line of city lights", "planet Earth rising over a dark horizon at dawn with a thin line of city lights across its night side, a brass telescope silhouetted in the foreground, and a wide band of stars.", "c8a385ac-79b1-483a-a26e-0636f0465a9c"),
}


def _shift_up(rel_dir: str) -> None:
    """Rename n.jpg -> (n+1).jpg (images and thumbnails, credits keys), highest first, to make room at 1."""
    credits = load_json(DATA / "image-credits.json", {})
    d = IMAGES / rel_dir
    nums = sorted((int(p.stem) for p in d.glob("*.jpg")), reverse=True) if d.exists() else []
    for n in nums:
        for base in (IMAGES, IMAGES / "_t"):
            src = base / rel_dir / f"{n}.jpg"
            if src.exists():
                src.rename(base / rel_dir / f"{n + 1}.jpg")
        k, k2 = f"{rel_dir}/{n}.jpg", f"{rel_dir}/{n + 1}.jpg"
        if k in credits:
            credits[k2] = credits.pop(k)
    save_json(DATA / "image-credits.json", credits)


def register_images(src_dir: Path) -> int:
    credits = load_json(DATA / "image-credits.json", {})
    done = 0
    for i, (target, pos, caption, subject, job) in MANIFEST.items():
        f = src_dir / f"{i:02d}.png"
        if not f.exists():
            print(f"missing {f}")
            continue
        img = fi.prep_image(f.read_bytes())
        entry = {"ai": True, "model": MODEL, "prompt": STYLE + subject, "job_id": job, "generated": DATE, "caption": "AI illustration: " + caption,
                 "license": "AI-generated image (no third-party source); Higgsfield terms apply", "license_url": None, "source": None, "author": None,
                 "via": "higgsfield-ai", "w": img.size[0], "h": img.size[1]}
        if pos == "hero":
            out = IMAGES / "_hero"
            out.mkdir(parents=True, exist_ok=True)
            hero = Image.open(f).convert("RGB")
            hero.thumbnail((1600, 1600), Image.LANCZOS)
            hero.save(out / "hero.jpg", "JPEG", quality=78, optimize=True, progressive=True)
            og = Image.open(f).convert("RGB")
            w, h = og.size
            target_h = int(w * 630 / 1200)
            og = og.crop((0, (h - target_h) // 2, w, (h - target_h) // 2 + target_h)).resize((1200, 630), Image.LANCZOS)
            og.save(out / "og.jpg", "JPEG", quality=82, optimize=True)
            save_json(DATA / "hero.json", {**entry, "src": "images/_hero/hero.jpg", "og": "images/_hero/og.jpg"})
            done += 1
            continue
        typ, slug = target.split("/")
        rel_dir = f"{typ}/{slug}"
        if any(c.get("job_id") == job for c in credits.values()):        # already registered
            continue
        if pos == "first":
            # drop a borrowed placeholder first, then make room at position 1
            for k in [k for k, c in credits.items() if k.startswith(rel_dir + "/") and c.get("borrowed_from")]:
                for base in (IMAGES, IMAGES / "_t"):
                    (base / k).unlink(missing_ok=True)
                credits.pop(k)
            save_json(DATA / "image-credits.json", credits)
            _shift_up(rel_dir)
            credits = load_json(DATA / "image-credits.json", {})
            n = 1
        else:
            existing = [int(p.stem) for p in (IMAGES / rel_dir).glob("*.jpg")]
            n = max(existing, default=0) + 1
        rel = f"{rel_dir}/{n}.jpg"
        fi.save_img(img, IMAGES / rel)
        credits[rel] = entry
        save_json(DATA / "image-credits.json", credits)
        done += 1
    print(f"registered {done} AI images")
    return 0


# ------------------------------------------------------------------ Gemini text guard
NAME_RE = re.compile(r"\b[A-Z][a-z]{2,}\b")
NUM_RE = re.compile(r"\d[\d,\.]*")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s)


def no_new_facts(line: str, source: str) -> str | None:
    """None if the line only uses numbers and names present in the source, else the reason."""
    low = source.lower()
    for n in NUM_RE.findall(line):
        if n.strip(",.").lower() not in low:
            return f"number {n!r} not in source"
    words = NAME_RE.findall(line)
    for i, w in enumerate(words):
        if w.lower() not in low and not (i == 0 and line.startswith(w)):
            return f"name {w!r} not in source"
    return None


def note_source_text(nid: str) -> str:
    typ = nid.split("/")[0]
    d = load_json(DATA / f"notes-{typ}.json", {}).get(nid)
    if not d:
        return ""
    strip = lambda h: re.sub(r"<[^>]+>", " ", h or "")  # noqa: E731
    return _norm(" ".join([d["title"], strip(d["summary"]), *[strip(f) for f in d["facts"]], strip(d["context"])]))


def validate_text(path: Path) -> int:
    """Input JSON: {"briefs": {id: "line"}, "journeys": {jid: {"steps": {id: "line"}}}, "quiz": [{id,q,options,answer}]}"""
    raw = json.loads(path.read_text(encoding="utf-8"))
    out = load_json(DATA / "ai-text.json", {}) or {}
    out.setdefault("briefs", {})
    stats = {"kept": 0, "dropped": 0}
    dropped = []
    for nid, line in (raw.get("briefs") or {}).items():
        src = note_source_text(nid)
        line = _norm(str(line)).strip()
        why = None
        if not src:
            why = "unknown note"
        elif len(line.split()) > 30 or len(line) < 20:
            why = "bad length"
        else:
            why = no_new_facts(line, src)
        if why:
            stats["dropped"] += 1
            dropped.append((nid, why))
        else:
            out["briefs"][nid] = {"text": line, "model": raw.get("model", "gemini"), "date": DATE}
            stats["kept"] += 1
    for jid, j in (raw.get("journeys") or {}).items():
        keep = {}
        for nid, line in (j.get("steps") or {}).items():
            src = note_source_text(nid)
            if src and 15 <= len(str(line)) <= 260 and not no_new_facts(str(line), src):
                keep[nid] = _norm(str(line))
            else:
                dropped.append((f"journey:{nid}", "guard"))
        if keep:
            out.setdefault("journeys", {})[jid] = {"steps": keep}
    quiz = []
    for q in raw.get("quiz") or []:
        src = note_source_text(q.get("id", ""))
        opts = q.get("options") or []
        ans = q.get("answer")
        if src and len(opts) == 4 and isinstance(ans, int) and 0 <= ans < 4 and not no_new_facts(str(opts[ans]), src) and len(str(q.get("q", ""))) > 10:
            quiz.append({"id": q["id"], "q": q["q"], "options": [str(o) for o in opts], "answer": ans})
        else:
            dropped.append((f"quiz:{q.get('id')}", "guard"))
    if quiz:
        out["quiz"] = quiz
    save_json(DATA / "ai-text.json", out)
    print(f"briefs kept {stats['kept']}, dropped {stats['dropped']}; journeys {len(out.get('journeys', {}))}; quiz {len(out.get('quiz', []))}")
    for nid, why in dropped[:25]:
        print("  dropped", nid, "-", why)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("register-images"); r.add_argument("dir", type=Path)
    v = sub.add_parser("validate-text"); v.add_argument("file", type=Path)
    a = ap.parse_args()
    return register_images(a.dir) if a.cmd == "register-images" else validate_text(a.file)


if __name__ == "__main__":
    sys.exit(main())
