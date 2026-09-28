#!/usr/bin/env python3
"""Build the data files for the Earth Chronicle site from the vault.

Writes to _Site/data/:
    notes-index.json      light record for every note (cards, filters, search, timeline)
    graph.json            edges between non-source notes
    notes-<type>.json     full detail per type, lazy loaded when a note is opened
    build-report.json     counts + problems

Usage:
    python build_site.py            # build
    python build_site.py --check    # build, then verify counts, image paths and wikilinks; exit 1 on problems
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from collections import Counter, defaultdict

from common import DATA, IMAGES, load_json, load_notes, save_json, slugify
import recommend
import vault
from PIL import Image

TYPE_LABEL = {
    "era": "Era", "event": "Event", "person": "Person", "place": "Place", "culture": "People & Culture",
    "technology": "Artifact / Technology", "species": "Species", "region": "Region", "theme": "Theme",
    "observer-note": "Observer Note", "timeline": "Timeline", "source": "Source",
}
AUTO_RE = re.compile(r"<!--\s*AUTO:.*?-->.*?<!--\s*/AUTO:[^>]*-->", re.S)
SECTION_KEYS = {"summary": "Summary", "facts": "Facts", "context": "Context & Connections",
                "observer": "Observer's Reading", "questions": "Open Questions"}


def fmt_year(y) -> str:
    if not isinstance(y, (int, float)):
        return str(y)
    a = abs(y)
    if y <= -1e9:
        return f"{a / 1e9:.4g} Ga"
    if y <= -1e6:
        return f"{a / 1e6:.4g} Ma"
    if y <= -1e4 - 1:
        return f"{a / 1e3:.4g} ka"
    if y < 0:
        return f"{int(a)} BCE"
    if y == 0:
        return "1 BCE"
    return f"{int(y)} CE" if y < 1000 else str(int(y))


_SIZES: dict[str, tuple[int, int]] = {}


def image_size(rel: str) -> tuple[int | None, int | None]:
    if rel not in _SIZES:
        try:
            with Image.open(IMAGES / rel) as im:
                _SIZES[rel] = im.size
        except Exception:  # noqa: BLE001
            _SIZES[rel] = (None, None)
    return _SIZES[rel]


def date_label(fm) -> str:
    s, e, prec = fm.get("date_start"), fm.get("date_end"), fm.get("date_precision")
    if s is None:
        return ""
    pre = "c. " if prec in ("approx", "decade", "century") else ""
    a = fmt_year(s)
    if e is None or e == s:
        return pre + a
    b = fmt_year(e)
    # collapse shared unit: "3300 BCE – 1200 BCE" -> "3300 – 1200 BCE"
    ua, ub = a.split(" ")[-1], b.split(" ")[-1]
    if ua == ub and ua in ("BCE", "CE", "ka", "Ma", "Ga"):
        a = a.rsplit(" ", 1)[0]
    return f"{pre}{a} – {b}"


class Renderer:
    def __init__(self, by_title):
        self.by_title = by_title
        self.unresolved: Counter = Counter()

    def inline(self, text: str, note_id: str) -> str:
        t = html.escape(text, quote=False)

        def link(m):
            target, alias = m.group(1).strip(), (m.group(2) or "").strip()
            tgt = self.by_title.get(target.split("#")[0].strip().lower())
            label = alias or target
            if not tgt:
                self.unresolved[(note_id, target)] += 1
                return html.escape(label, quote=False)
            return f'<a href="#/n/{tgt["id"]}" data-id="{tgt["id"]}">{label}</a>'
        t = re.sub(r"\[\[([^\]\|]+)(?:\|([^\]]*))?\]\]", lambda m: link(m), t)
        t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', t)
        t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
        t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", t)
        t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
        return t

    def block(self, text: str, note_id: str) -> str:
        out, para, items, rows = [], [], [], []

        def flush():
            nonlocal para, items, rows
            if para:
                out.append("<p>" + self.inline(" ".join(para), note_id) + "</p>")
            if items:
                out.append("<ul>" + "".join(f"<li>{self.inline(i, note_id)}</li>" for i in items) + "</ul>")
            if rows:
                body = [r for r in rows if not re.match(r"^\|?\s*:?-{2,}", r)]
                cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in body]
                if cells:
                    head, rest = cells[0], cells[1:]
                    out.append("<table><thead><tr>" + "".join(f"<th>{self.inline(c, note_id)}</th>" for c in head) + "</tr></thead><tbody>"
                               + "".join("<tr>" + "".join(f"<td>{self.inline(c, note_id)}</td>" for c in r) + "</tr>" for r in rest) + "</tbody></table>")
            para, items, rows = [], [], []

        for line in text.splitlines():
            s = line.strip()
            if not s:
                flush()
            elif s.startswith("|"):
                if para or items:
                    flush()
                rows.append(s)
            elif re.match(r"^[-*] ", s):
                if para or rows:
                    flush()
                items.append(s[2:].strip())
            elif s.startswith("###"):
                flush()
                out.append(f"<h4>{self.inline(s.lstrip('# ').strip(), note_id)}</h4>")
            else:
                if items or rows:
                    flush()
                para.append(s)
        flush()
        return "".join(out)

    def bullets(self, text: str, note_id: str) -> list[str]:
        return [self.inline(m.group(1).strip(), note_id) for m in re.finditer(r"^\s*[-*] (.+(?:\n(?!\s*[-*] ).+)*)", text, re.M)]


def sections(body: str) -> dict[str, str]:
    body = AUTO_RE.sub("", body)
    parts = re.split(r"^## +(.+?)\s*$", body, flags=re.M)
    out = {}
    for i in range(1, len(parts), 2):
        out[parts[i].strip()] = parts[i + 1].strip()
    return out


def plain_summary(html_text: str, n=240) -> str:
    t = re.sub(r"<[^>]+>", "", html_text)
    t = html.unescape(t)
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    notes = load_notes()
    byid = {n["id"]: n for n in notes}
    by_title = {}
    for n in notes:
        by_title[n["stem"].lower()] = n
        by_title.setdefault(n["title"].lower(), n)
    theme_by_slug = {str(n["fm"].get("slug")): n for n in notes if n["type"] == "theme"}
    for n in notes:                       # theme slugs used in notes: technology, trade, war, ...
        pass
    credits = load_json(DATA / "image-credits.json", {})
    imgs = defaultdict(list)
    for rel, c in credits.items():
        if (IMAGES / rel).exists():
            typ, slug, fn = rel.split("/")
            imgs[f"{typ}/{slug}"].append((int(fn.split(".")[0]), rel, c))

    theme_alias = {}
    for n in notes:
        if n["type"] == "theme":
            theme_alias[str(n["fm"].get("slug") or slugify(n["title"]))] = n["id"]
    theme_alias.update({"technology": theme_alias.get("technology"), })
    R = Renderer(by_title)

    def ref(v):
        for t in vault.links_in(v):
            m = by_title.get(t.lower())
            if m:
                return m["id"]
        return None

    index, detail, edges = [], defaultdict(dict), []
    problems = []
    for n in notes:
        fm, sec = n["fm"], sections(n["body"])
        nid = n["id"]
        images = []
        for _, rel, c in sorted(imgs.get(nid, [])):
            w, h = image_size(rel)
            t = "images/_t/" + rel if (IMAGES / "_t" / rel).exists() else None
            images.append({"src": "images/" + rel, "thumb": t, "caption": c.get("caption") or "", "author": c.get("author"),
                           "license": c.get("license"), "license_url": c.get("license_url"), "source": c.get("source"),
                           "via": c.get("via"), "w": w, "h": h, "ai": bool(c.get("ai")), "model": c.get("model")})
        themes = []
        for t in fm.get("themes") or []:
            tid = theme_alias.get(str(t))
            themes.append({"slug": str(t), "id": tid})
        summary_html = R.block(sec.get("Summary", ""), nid) if "Summary" in sec else ""
        if not summary_html:
            for k in ("Citation", "Question", "How to Read This"):
                if sec.get(k):
                    summary_html = R.block(sec[k], nid)
                    break
        rec = {
            "id": nid, "title": n["title"], "type": n["type"], "era": ref(fm.get("era")), "region": ref(fm.get("region")),
            "themes": [t["slug"] for t in themes], "ds": fm.get("date_start"), "de": fm.get("date_end"),
            "date": date_label(fm), "conf": str(fm.get("confidence") or ""), "status": str(fm.get("status") or ""),
            "sum": plain_summary(summary_html), "img": images[0]["src"] if images else None, "imt": (images[0]["thumb"] or images[0]["src"]) if images else None,
            "iw": images[0]["w"] if images else None, "ai": bool(images and images[0]["ai"]), "ih": images[0]["h"] if images else None, "ni": len(images),
            "nl": len(n["out"]) + len(n["inb"]),
            "search": (n["title"] + " " + plain_summary(summary_html, 1200) + " " + re.sub(r"<[^>]+>", " ", " ".join(R.bullets(sec.get("Facts", ""), nid)))).lower(),
        }
        if n["type"] == "era":
            rec["members_hint"] = True
        index.append(rec)
        extra = [{"title": k, "html": R.block(v, nid)} for k, v in sec.items()
                 if k not in SECTION_KEYS.values() and k not in ("Citation",) and v.strip()]
        sources = [byid[t]["id"] for t in [by_title[x.lower()]["id"] if x.lower() in by_title else None
                                            for x in vault.links_in(fm.get("sources"))] if t and t in byid]
        d = {
            "id": nid, "title": n["title"], "type": n["type"], "themes": themes, "summary": summary_html,
            "facts": R.bullets(sec.get("Facts", ""), nid), "context": R.block(sec.get("Context & Connections", ""), nid),
            "observer": R.block(sec.get("Observer's Reading", ""), nid),
            "questions": R.bullets(sec.get("Open Questions", ""), nid) or ([R.block(sec["Open Questions"], nid)] if sec.get("Open Questions") else []),
            "extra": extra, "sources": sources, "out": n["out"], "inb": n["inb"],
            "related": [byid[by_title[t.lower()]["id"]]["id"] for t in vault.links_in(fm.get("related")) if t.lower() in by_title],
            "fact_checks": [str(x) for x in (fm.get("fact_checks") or [])], "images": images,
            "path": n["path"], "date_precision": fm.get("date_precision"),
        }
        if n["type"] == "source":
            d["source"] = {k: (str(fm.get(k)) if fm.get(k) is not None else None) for k in
                           ("url", "source_kind", "reliability", "verified", "checked_on", "access", "read_on")}
            d["source"]["citation"] = sec.get("Citation", "")
            d["summary"] = R.block(sec.get("What It Is Used For", ""), nid) or summary_html
            rec["sum"] = plain_summary(d["summary"])
            d["extra"] = [e for e in extra if e["title"] != "What It Is Used For"]
            d["used_for"] = True
        detail[n["type"]][nid] = d
        if n["type"] != "source":
            for t in n["out"]:
                if byid[t]["type"] != "source":
                    edges.append([nid, t])

    for typ_d in list(detail.values()):
        for d in typ_d.values():
            for sid in d["sources"]:
                if sid in detail["source"]:
                    detail["source"][sid].setdefault("cited_by", []).append(d["id"])

    # notes lacking any content are a build problem
    for rec in index:
        if not rec["sum"] and rec["type"] not in ("timeline",):
            problems.append(f"no summary: {rec['id']}")

    index.sort(key=lambda r: (r["type"], r["title"]))
    docs = {r["id"]: (r["title"] + " ") * 2 + r["search"] for r in index}
    recs, featured, _eng = recommend.build(index, docs, [tuple(e) for e in edges])
    save_json(DATA / "recs.json", recs, indent=None)
    save_json(DATA / "featured.json", featured, indent=None)
    save_json(DATA / "notes-index.json", index, indent=None)
    save_json(DATA / "graph.json", edges, indent=None)
    save_json(DATA / "meta.json", {
        "themes": [{"slug": sl, "id": tid, "title": byid[tid]["title"]} for sl, tid in theme_alias.items() if tid],
        "type_label": TYPE_LABEL,
        "built": __import__("datetime").date.today().isoformat(),
    }, indent=None)
    for typ, d in detail.items():
        save_json(DATA / f"notes-{typ}.json", d, indent=None)
    report = {
        "notes": len(notes), "index": len(index), "detail": sum(len(d) for d in detail.values()),
        "by_type": dict(Counter(n["type"] for n in notes)), "images": sum(r["ni"] for r in index),
        "with_image": sum(1 for r in index if r["ni"]), "edges": len(edges),
        "unresolved_wikilinks": sorted({f"{a} -> {b}" for (a, b) in R.unresolved}), "problems": problems,
    }
    save_json(DATA / "build-report.json", report)
    print(f"notes {report['notes']}  index {report['index']}  detail {report['detail']}  images {report['images']} "
          f"(notes with image: {report['with_image']})  edges {report['edges']}  unresolved links {len(report['unresolved_wikilinks'])}")
    refresh_rewrite_layer()

    if args.check:
        bad = []
        if not (report["notes"] == report["index"] == report["detail"]):
            bad.append("index/detail counts differ from note count")
        expected = len([p for p in vault.iter_notes() if p.relative_to(vault.VAULT_ROOT).parts[0] not in ("00_Meta", "08_Canvas_Maps")
                        and (vault.parse_note(p)[0].get("type") in TYPE_LABEL)])
        if expected != report["notes"]:
            bad.append(f"vault has {expected} in-scope notes, built {report['notes']}")
        for r in index:
            for n_img in detail[r["type"]][r["id"]]["images"]:
                if not (DATA.parent / n_img["src"]).exists():
                    bad.append(f"missing image file {n_img['src']}")
                if not n_img["license"]:
                    bad.append(f"image without license {n_img['src']}")
        ids = {r["id"] for r in index}
        for a, b in edges:
            if a not in ids or b not in ids:
                bad.append(f"dangling edge {a} -> {b}")
        out_of_scope = {p.stem.lower() for p in (vault.VAULT_ROOT / "00_Meta").rglob("*.md")}
        real = [u for u in report["unresolved_wikilinks"] if u.split(" -> ")[1].lower() not in out_of_scope]
        if real:
            bad.append(f"{len(real)} unresolved wikilinks that are not 00_Meta notes (see build-report.json): {real[:5]}")
        bad += problems
        for b in bad[:40]:
            print("  CHECK FAIL:", b)
        print("check:", "FAILED" if bad else "OK")
        return 1 if bad else 0
    return 0


def refresh_rewrite_layer() -> None:
    """Republish the AI rewrite layer (_Rewrite/) so a note whose text changed drops its stale rewrite, and say what is pending."""
    import importlib.util
    path = DATA.parent.parent / "_Rewrite" / "rewrite_layer.py"
    if not path.exists():
        return
    spec = importlib.util.spec_from_file_location("rewrite_layer", path)
    rl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rl)
    rl.cmd_publish(None)
    n = len(rl.pending_ids("site", rl.SOURCES["site"]()))
    if n:
        print(f"rewrite layer: {n} notes not rewritten yet; ask the chronicle-rewriter agent for 'pending site'")


if __name__ == "__main__":
    sys.exit(main())
