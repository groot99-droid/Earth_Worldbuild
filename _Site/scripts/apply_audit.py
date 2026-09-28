#!/usr/bin/env python3
"""Apply the visual-review verdicts (data/audit/verdicts.json) to the image set. Reversible.

Codes:  D duplicate | O off-topic or misleading | Q unusable quality | X wrong subject (person/place mix-up, private
        individuals) | S distressing photograph, unsuitable as a card image  -> REMOVED (moved to _quarantine/, credit kept in
        data/audit/removed.json so it can be restored)
        W weak (tangential) | L not lead material (map, diagram, flag, document)  -> KEPT but moved behind better images

Extra automatic rules: of two identical images the non-source note keeps it; a borrowed copy goes when its donor image goes.
After moving things the remaining images of each affected note are renumbered 1..n (AI illustrations first, then good, then weak).
Writes data/audit/replacements-needed.json: non-source notes left with no image, or only weak/not-lead ones.

    python apply_audit.py --dry     # report only
    python apply_audit.py           # apply
    python apply_audit.py --restore # put everything in _quarantine back (renumbers to the end)
"""
from __future__ import annotations

import argparse
import shutil
from collections import defaultdict

from common import DATA, IMAGES, SITE, load_json, load_notes, save_json

REMOVE = {"D", "O", "Q", "X", "S"}
DEMOTE = {"W", "L"}
QUAR = SITE / "_quarantine"


def note_of(rel: str) -> str:
    t, s, _ = rel.split("/")
    return f"{t}/{s}"


def plan(credits, verdicts, audit):
    remove: dict[str, dict] = {}
    for rel, v in verdicts.items():
        if rel in credits and v["code"] in REMOVE:
            remove[rel] = {"code": v["code"], "reason": v["reason"], "auto": False}
    # identical images: the non-source note keeps it
    groups = defaultdict(list)
    for rel, f in audit.items():
        if rel in credits and not f["borrowed"]:
            groups[f["md5"]].append(rel)
    for g in groups.values():
        alive = [r for r in g if r not in remove]
        if len(alive) > 1:
            alive.sort(key=lambda r: (r.startswith("source/"), int(r.split("/")[-1].split(".")[0])))
            for r in alive[1:]:
                remove[r] = {"code": "D", "reason": f"identical to {alive[0]}", "auto": True}
    # near-duplicate of a non-source note's image sitting on a source note
    for rel, f in audit.items():
        if rel in credits and rel not in remove and rel.startswith("source/"):
            for fl in f["flags"]:
                if fl.startswith("dup-near-cross-note:") and not fl.split(":", 1)[1].startswith("source/") and fl.split(":", 1)[1] in credits and "(loose)" not in fl.split(":", 1)[0]:
                    other = fl.split(":", 1)[1]
                    if other not in remove:
                        remove[rel] = {"code": "D", "reason": f"near-duplicate of {other}", "auto": True}
    # borrowed copies follow their donor image
    gone_files = {credits[r].get("file") for r in remove if not credits[r].get("borrowed_from")}
    for rel, c in credits.items():
        if c.get("borrowed_from") and rel not in remove and c.get("file") in gone_files:
            remove[rel] = {"code": "D", "reason": f"borrowed copy of removed image from {c['borrowed_from']}", "auto": True}
    demote = {r for r, v in verdicts.items() if r in credits and r not in remove and v["code"] in DEMOTE}
    # a borrowed copy of a weak image is weak too
    weak_files = {credits[r].get("file") for r in demote if not credits[r].get("borrowed_from")}
    for rel, c in credits.items():
        if c.get("borrowed_from") and rel not in remove and c.get("file") in weak_files:
            demote.add(rel)
    return remove, demote


def renumber(credits, changed_notes, demote):
    """Order: AI first, then good, then weak; rename files/thumbs to 1..n and rekey credits."""
    for nid in sorted(changed_notes):
        items = sorted((int(k.split("/")[-1].split(".")[0]), k) for k in credits if note_of(k) == nid)
        order = sorted(items, key=lambda x: (0 if credits[x[1]].get("ai") else (2 if x[1] in demote else 1), x[0]))
        moves = [(old, f"{nid}/{i}.jpg") for i, (_, old) in enumerate(order, 1)]
        if all(a == b for a, b in moves):
            continue
        tmp = {}
        for old, new in moves:                                # two-phase to avoid name clashes
            for base in (IMAGES, IMAGES / "_t"):
                p = base / old
                if p.exists():
                    t = p.with_name(p.name + ".tmp")
                    p.rename(t)
                    tmp[(base, new)] = t
            tmp[("credit", new)] = credits.pop(old)
        for (base, new), t in tmp.items():
            if base == "credit":
                credits[new] = t
            else:
                t.rename(base / new)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--restore", action="store_true")
    args = ap.parse_args()
    credits = load_json(DATA / "image-credits.json", {})
    removed_log = load_json(DATA / "audit" / "removed.json", {})

    if args.restore:
        for rel, r in list(removed_log.items()):
            q = QUAR / "images" / rel
            if q.exists():
                nid = note_of(rel)
                n = max([int(k.split("/")[-1].split(".")[0]) for k in credits if note_of(k) == nid] or [0]) + 1
                new = f"{nid}/{n}.jpg"
                (IMAGES / new).parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(q), str(IMAGES / new))
                credits[new] = r["credit"]
                removed_log.pop(rel)
        save_json(DATA / "image-credits.json", credits)
        save_json(DATA / "audit" / "removed.json", removed_log)
        print("restored; run make_thumbs.py")
        return 0

    verdicts = load_json(DATA / "audit" / "verdicts.json", {})
    audit = load_json(DATA / "audit" / "image-audit.json", {})
    remove, demote = plan(credits, verdicts, audit)
    notes = {n["id"]: n for n in load_notes()}
    changed = {note_of(r) for r in remove} | {note_of(r) for r in demote}

    # what would each note look like afterwards
    after = defaultdict(list)
    for k in credits:
        if k not in remove:
            after[note_of(k)].append(k)
    need = {}
    for nid in changed:
        n = notes.get(nid)
        if not n or n["type"] == "source":
            continue
        left = after.get(nid, [])
        good = [k for k in left if k not in demote]
        if not left:
            need[nid] = {"title": n["title"], "type": n["type"], "why": "no image left", "removed": [remove[r]["reason"] for r in remove if note_of(r) == nid]}
        elif not good:
            need[nid] = {"title": n["title"], "type": n["type"], "why": "only weak or not-lead images left", "removed": [remove[r]["reason"] for r in remove if note_of(r) == nid]}
    by_code = defaultdict(int)
    for r in remove.values():
        by_code[r["code"]] += 1
    print(f"remove {len(remove)} images {dict(by_code)}; demote {len(demote)}; notes touched {len(changed)}")
    print(f"non-source notes needing a replacement: {len(need)} ({sum(1 for v in need.values() if v['why'] == 'no image left')} with no image, "
          f"{sum(1 for v in need.values() if v['why'] != 'no image left')} weak-only)")
    src_left0 = sum(1 for nid in changed if nid.startswith("source/") and not after.get(nid))
    print(f"source notes left with no image: {src_left0} (sources stay image-less rather than get AI art)")
    if args.dry:
        for nid, v in sorted(need.items()):
            print(f"  {nid:60s} {v['why']}")
        return 0

    for rel, r in remove.items():
        q = QUAR / "images" / rel
        q.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(IMAGES / rel), str(q))
        (IMAGES / "_t" / rel).unlink(missing_ok=True)
        removed_log[rel] = {**r, "note": note_of(rel), "credit": credits.pop(rel)}
    renumber(credits, changed, demote)
    save_json(DATA / "image-credits.json", credits)
    save_json(DATA / "audit" / "removed.json", removed_log)
    save_json(DATA / "audit" / "replacements-needed.json", need)
    print("applied. quarantine:", QUAR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
