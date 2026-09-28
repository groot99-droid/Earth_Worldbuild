#!/usr/bin/env python3
"""Build everything that is generated from the artist Markdown files.

Outputs:
    artists/*.md          the "Key Works" block between the works markers
    TIMELINE.md           chronological index, grouped by century
    rag/art-talk.jsonl    retrieval chunks (one JSON object per line)
    rag/art-talk.md       every artist in one Markdown file
    index.html            static timeline page

Usage:
    python scripts/build.py           # build all outputs
    python scripts/build.py --check   # validate only; non-zero exit on problems
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

from common import (
    MIN_WORKS,
    PROSE_SECTIONS,
    RAG_DIR,
    REQUIRED_SECTIONS,
    ROOT,
    WORKS_END,
    WORKS_START,
    Artist,
    load_artists,
    load_credits,
)

REPO_URL = "https://github.com/groot99-droid/Art-Talk"
TEMPLATE = ROOT / "scripts" / "templates" / "timeline.html"
# Schema v2: the original five regions and six disciplines stay valid; Africa, Southeast Asia,
# Oceania and the performing/craft disciplines were added for the expansion.
REGION_ORDER = ["Europe", "West & Central Asia", "Africa", "South Asia", "East Asia",
                "Southeast Asia", "Oceania", "Americas"]
DISCIPLINE_ORDER = ["Painting", "Sculpture", "Architecture", "Design", "Craft", "Calligraphy",
                    "Photography", "Film", "Literature", "Music", "Dance", "Theatre"]


# ---------------------------------------------------------------- helpers

def md_to_text(md: str) -> str:
    """Flatten Markdown to plain text for retrieval chunks."""
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", md)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"(\*\*|__|\*|_)(\S.*?\S|\S)\1", r"\2", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.M)
    text = re.sub(r"^\s*[-*]\s+", "- ", text, flags=re.M)
    paragraphs = []
    for para in re.split(r"\n\s*\n", text.strip()):
        lines = [l.strip() for l in para.splitlines() if l.strip()]
        if lines and all(l.startswith("- ") for l in lines):
            paragraphs.append("\n".join(lines))
        elif lines:
            paragraphs.append(" ".join(lines))
    return "\n\n".join(paragraphs)


def inline_html(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    text = re.sub(r"\*\*(\S.*?\S|\S)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*(\S.*?\S|\S)\*(?![\w*])", r"<em>\1</em>", text)
    return text


def md_to_html(md: str) -> str:
    """A deliberately small Markdown converter: paragraphs, lists, emphasis, links."""
    out: list[str] = []
    for block in re.split(r"\n\s*\n", md.strip()):
        lines = [l for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        if all(re.match(r"\s*[-*]\s+", l) for l in lines):
            items = [inline_html(re.sub(r"^\s*[-*]\s+", "", l)) for l in lines]
            out.append("<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>")
        elif lines[0].startswith("### "):
            out.append(f"<h4>{inline_html(lines[0][4:])}</h4>")
            if lines[1:]:
                out.append(f"<p>{inline_html(' '.join(lines[1:]))}</p>")
        else:
            out.append(f"<p>{inline_html(' '.join(l.strip() for l in lines))}</p>")
    return "\n".join(out)


def century_label(year: int) -> str:
    """Century heading for a sort year; negative years are BCE ("700s BCE" = 700-601 BCE)."""
    if year < 1:
        return f"{((-year - 1) // 100 + 1) * 100}s BCE"
    return f"{(year // 100) * 100}s"


def format_year(year: int) -> str:
    return f"{-year} BCE" if year < 1 else str(year)


def cover_work(a: Artist) -> dict:
    cid = a.meta.get("cover")
    return next((w for w in a.works if w["id"] == cid), a.works[0])


def credit_line(credit: dict | None) -> str:
    if not credit:
        return "Image: not yet downloaded"
    parts = [f"[Wikimedia Commons]({credit['source']})" if credit.get("source") else credit["file"]]
    if credit.get("author"):
        parts.append(credit["author"])
    lic = credit.get("license") or "unknown license"
    parts.append(f"[{lic}]({credit['license_url']})" if credit.get("license_url") else lic)
    return "Image: " + " · ".join(parts)


# ---------------------------------------------------------------- artist files

def render_works_block(a: Artist, credits: dict) -> str:
    lines = [WORKS_START, ""]
    for i, w in enumerate(a.works, 1):
        lines += [
            f"### {i}. {w['title']} ({w['year']})",
            "",
            f"![{w['title']}](../{a.image_rel(w)})",
            "",
            f"*{w['medium']} · {w['location']}*",
            "",
            w["description"].strip(),
            "",
            f"<sub>{credit_line(credits.get(a.image_rel(w)))}</sub>",
            "",
        ]
    lines.append(WORKS_END)
    return "\n".join(lines)


def update_artist_file(a: Artist, credits: dict) -> bool:
    text = a.path.read_text(encoding="utf-8")
    block = render_works_block(a, credits)
    if WORKS_START in text:
        new = re.sub(re.escape(WORKS_START) + r".*?" + re.escape(WORKS_END), lambda _: block, text, flags=re.S)
    else:
        new = re.sub(r"(^## Key Works\s*\n)", lambda m: m.group(1) + "\n" + block + "\n", text, count=1, flags=re.M)
    if new != text:
        a.path.write_text(new, encoding="utf-8")
        return True
    return False


# ---------------------------------------------------------------- TIMELINE.md

def build_timeline_md(artists: list[Artist]) -> str:
    regions = Counter(a.meta["region"] for a in artists)
    disciplines = Counter(d for a in artists for d in a.meta.get("discipline", []))
    out = [
        "# Art-Talk Timeline",
        "",
        f"{len(artists)} artists from {format_year(artists[0].meta['born'])} to {format_year(max(a.meta['died'] for a in artists))}, "
        f"with {sum(len(a.works) for a in artists)} artworks. Artists are ordered by birth year; "
        "each name links to a full profile with images of their key works.",
        "",
        "Regions: " + " · ".join(f"{r} ({regions[r]})" for r in REGION_ORDER if r in regions),
        "",
        "Disciplines: " + " · ".join(f"{d} ({disciplines[d]})" for d in DISCIPLINE_ORDER if d in disciplines),
        "",
        "An interactive version of this timeline is in [`index.html`](index.html).",
        "",
        "## Lifespans at a glance",
        "",
        "```mermaid",
        "gantt",
        "    dateFormat YYYY",
        "    axisFormat %Y",
    ]
    for region in REGION_ORDER:
        # mermaid's YYYY date format cannot express BCE years, so those artists are listed
        # in the tables below but left off the chart.
        members = [a for a in artists if a.meta["region"] == region and a.meta["born"] >= 1]
        if not members:
            continue
        out.append(f"    section {region}")
        for a in members:
            label = re.sub(r"[:#;,]", "", a.meta.get("short_name", a.name))
            out.append(f"    {label} : {a.meta['born']}, {a.meta['died']}")
    out += ["```", ""]
    bce = sum(1 for a in artists if a.meta["born"] < 1)
    if bce:
        out += [f"*The chart starts in year 1 CE; the {bce} artists born earlier appear in the tables below.*", ""]

    current = None
    for a in artists:
        c = century_label(a.meta["born"])
        if c != current:
            current = c
            out += ["", f"## Born in the {c}", "",
                    "| Lifespan | Artist | Where | Movement | Signature work |",
                    "|---|---|---|---|---|"]
        cw = cover_work(a)
        out.append(
            f"| {a.meta['lifespan']} | [{a.name}](artists/{a.path.name}) | {a.meta['country']} "
            f"| {', '.join(a.meta['movements'])} | *{cw['title']}* ({cw['year']}) |"
        )
    out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------- RAG

def is_approximate(a: Artist) -> bool:
    """True when born/died are sort years rather than exact dates."""
    return bool(re.search(r"\bc\.|active|fl\.", a.meta["lifespan"]))


def base_record(a: Artist) -> dict:
    return {
        "artist": a.name,
        "slug": a.slug,
        "lifespan": a.meta["lifespan"],
        "born": a.meta["born"],
        "died": a.meta["died"],
        "dates_approximate": is_approximate(a),
        "region": a.meta["region"],
        "country": a.meta["country"],
        "movements": a.meta["movements"],
        "discipline": a.meta.get("discipline", []),
        "source_file": f"artists/{a.path.name}",
        "url": a.meta.get("wikipedia"),
    }


def build_rag_chunks(artists: list[Artist], credits: dict) -> list[dict]:
    chunks: list[dict] = []
    for a in artists:
        ctx = a.context()
        works_list = "; ".join(f"{w['title']} ({w['year']})" for w in a.works)
        chunks.append({
            "id": f"{a.slug}#profile", "type": "profile", **base_record(a), "section": "Profile",
            "text": f"{ctx}: {md_to_text(a.summary)} Region: {a.meta['region']}. Key works: {works_list}.",
        })
        for sec in PROSE_SECTIONS:
            body = md_to_text(a.sections.get(sec, ""))
            if body:
                sid = re.sub(r"[^a-z]+", "-", sec.lower()).strip("-")
                chunks.append({
                    "id": f"{a.slug}#{sid}", "type": "section", **base_record(a), "section": sec,
                    "text": f"{ctx}: {sec}: {body}",
                })
        for w in a.works:
            credit = credits.get(a.image_rel(w)) or {}
            chunks.append({
                "id": f"{a.slug}#work-{w['id']}", "type": "artwork", **base_record(a), "section": "Key Works",
                "title": w["title"], "year": str(w["year"]), "medium": w["medium"], "location": w["location"],
                "image": a.image_rel(w), "image_license": credit.get("license"),
                "text": (f"{ctx}: Artwork: {w['title']} ({w['year']}). {w['medium']}. {w['location']}. "
                         f"{md_to_text(w['description'])}"),
            })

    first = min(a.meta["born"] for a in artists) // 100 * 100
    last = max(a.meta["died"] for a in artists)
    for start in range(first, last + 1, 100):
        active = [a for a in artists if a.meta["born"] < start + 100 and a.meta["died"] >= start]
        if not active:
            continue
        names = "; ".join(f"{a.name} ({a.meta['lifespan']}, {a.meta['country']}, {', '.join(a.meta['movements'])})"
                          for a in active)
        label = century_label(start) if start < 0 else f"{start}s"
        span = f"{-start}–{-start - 99} BCE" if start < 0 else f"{start}–{start + 99}"
        chunks.append({
            "id": f"century#{label.replace(' ', '-')}", "type": "century", "artist": None, "slug": None,
            "section": label, "born": None, "died": None, "dates_approximate": None,
            "region": None, "country": None,
            "movements": sorted({m for a in active for m in a.meta["movements"]}),
            "lifespan": None, "source_file": "TIMELINE.md", "url": None,
            "text": f"Artists in this collection who were alive during the {label} ({span}): {names}.",
        })
    return chunks


def build_rag_md(artists: list[Artist], credits: dict) -> str:
    out = [
        "# Art-Talk: Artist Knowledge Base",
        "",
        "Every artist in the Art-Talk timeline in one file, in chronological order by birth year. "
        "Generated by `scripts/build.py` from the files in `artists/`; do not edit by hand.",
        "",
        "## Contents",
        "",
    ]
    for a in artists:
        out.append(f"- {a.name} ({a.meta['lifespan']}), {a.meta['country']}, {', '.join(a.meta['movements'])}")
    for a in artists:
        out += [
            "", "---", "",
            f"## {a.name} ({a.meta['lifespan']})",
            "",
            f"**Region:** {a.meta['region']} · **Country:** {a.meta['country']} · "
            f"**Discipline:** {', '.join(a.meta.get('discipline', []))} · "
            f"**Movements:** {', '.join(a.meta['movements'])}",
            "",
            md_to_text(a.summary),
        ]
        for sec in PROSE_SECTIONS:
            out += ["", f"### {sec}", "", a.sections.get(sec, "").strip()]
        out += ["", "### Key Works"]
        for w in a.works:
            credit = credits.get(a.image_rel(w)) or {}
            out += [
                "",
                f"#### {w['title']} ({w['year']})",
                "",
                f"{w['medium']} · {w['location']}",
                "",
                w["description"].strip(),
                "",
                f"Image: `{a.image_rel(w)}` ({credit.get('license', 'license unknown')})",
            ]
        sources = a.sections.get("Sources", "").strip()
        if sources:
            out += ["", "### Sources", "", sources]
    out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------- index.html

def build_site_data(artists: list[Artist], credits: dict) -> list[dict]:
    data = []
    for a in artists:
        works = []
        for w in a.works:
            credit = credits.get(a.image_rel(w)) or {}
            works.append({
                "id": w["id"], "title": w["title"], "year": str(w["year"]),
                "medium": w["medium"], "location": w["location"],
                "description": md_to_html(w["description"]),
                "image": a.image_rel(w),
                "credit": {k: credit.get(k) for k in ("file", "source", "author", "license", "license_url")},
            })
        data.append({
            "slug": a.slug, "name": a.name, "lifespan": a.meta["lifespan"],
            "born": a.meta["born"], "died": a.meta["died"],
            "year_label": str(a.meta.get("year_label", a.meta["born"])),
            "region": a.meta["region"], "country": a.meta["country"], "movements": a.meta["movements"],
            "discipline": a.meta.get("discipline", []),
            "summary": inline_html(md_to_text(a.summary)),
            "sections": [{"title": s, "html": md_to_html(a.sections.get(s, ""))} for s in PROSE_SECTIONS],
            "cover": cover_work(a)["id"],
            "wikipedia": a.meta.get("wikipedia"),
            "source": f"{REPO_URL}/blob/main/artists/{a.path.name}",
            "works": works,
        })
    return data


def build_index_html(artists: list[Artist], credits: dict) -> str:
    payload = json.dumps(
        {"artists": build_site_data(artists, credits),
         "regions": [r for r in REGION_ORDER if any(a.meta["region"] == r for a in artists)],
         "disciplines": [d for d in DISCIPLINE_ORDER
                          if any(d in a.meta.get("discipline", []) for a in artists)],
         "repo": REPO_URL},
        ensure_ascii=False, separators=(",", ":"),
    ).replace("</", "<\\/")
    return TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/null", payload)


# ---------------------------------------------------------------- checks

def check(artists: list[Artist], credits: dict) -> list[str]:
    problems = []
    slugs = Counter(a.slug for a in artists)
    for s, n in slugs.items():
        if n > 1:
            problems.append(f"duplicate slug: {s}")
    for a in artists:
        where = a.path.relative_to(ROOT)
        if a.path.stem != a.slug:
            problems.append(f"{where}: file name does not match slug {a.slug!r}")
        for key in ("name", "slug", "born", "died", "lifespan", "region", "country", "movements", "discipline", "works"):
            if key not in a.meta:
                problems.append(f"{where}: missing front matter field {key!r}")
        if a.meta.get("region") not in REGION_ORDER:
            problems.append(f"{where}: region {a.meta.get('region')!r} not in {REGION_ORDER}")
        for d in a.meta.get("discipline") or []:
            if d not in DISCIPLINE_ORDER:
                problems.append(f"{where}: discipline {d!r} not in {DISCIPLINE_ORDER}")
        for sec in REQUIRED_SECTIONS:
            if sec not in a.sections:
                problems.append(f"{where}: missing section '## {sec}'")
        if not a.summary:
            problems.append(f"{where}: missing one-line summary under the title")
        if len(a.works) < MIN_WORKS:
            problems.append(f"{where}: only {len(a.works)} works (need {MIN_WORKS})")
        ids = Counter(w.get("id") for w in a.works)
        for i, n in ids.items():
            if n > 1:
                problems.append(f"{where}: duplicate work id {i!r}")
        for w in a.works:
            for key in ("id", "title", "year", "medium", "location", "description"):
                if not w.get(key):
                    problems.append(f"{where}: work {w.get('id')!r} missing {key!r}")
            if not (w.get("wiki") or w.get("commons_file")):
                problems.append(f"{where}: work {w.get('id')!r} needs 'wiki' or 'commons_file'")
            if not a.image_path(w).exists():
                problems.append(f"{where}: missing image {a.image_rel(w)}")
            elif a.image_rel(w) not in credits:
                problems.append(f"{where}: no credit recorded for {a.image_rel(w)}")
        text = a.path.read_text(encoding="utf-8")
        for target in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text):
            if not (a.path.parent / target).resolve().exists():
                problems.append(f"{where}: broken image link {target}")
        if WORKS_START not in text:
            problems.append(f"{where}: works block not generated yet (run build.py)")
    jsonl = RAG_DIR / "art-talk.jsonl"
    if jsonl.exists():
        for n, line in enumerate(jsonl.read_text(encoding="utf-8").splitlines(), 1):
            try:
                json.loads(line)
            except json.JSONDecodeError as exc:
                problems.append(f"rag/art-talk.jsonl:{n}: {exc}")
    else:
        problems.append("rag/art-talk.jsonl missing (run build.py)")
    return problems


# ---------------------------------------------------------------- main

def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    old = path.read_text(encoding="utf-8") if path.exists() else None
    if old != content:
        path.write_text(content, encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="validate only, do not write files")
    args = ap.parse_args()

    credits = load_credits()
    artists = load_artists()
    if not artists:
        print("no artists found in artists/")
        return 1

    if not args.check:
        for a in artists:
            if update_artist_file(a, credits):
                print(f"updated works in {a.path.relative_to(ROOT)}")
        artists = load_artists()
        chunks = build_rag_chunks(artists, credits)
        write(ROOT / "TIMELINE.md", build_timeline_md(artists))
        write(RAG_DIR / "art-talk.jsonl", "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in chunks))
        write(RAG_DIR / "art-talk.md", build_rag_md(artists, credits))
        write(ROOT / "index.html", build_index_html(artists, credits))
        counts = Counter(c["type"] for c in chunks)
        print(f"{len(artists)} artists, {sum(len(a.works) for a in artists)} works, "
              f"{len(chunks)} RAG chunks ({', '.join(f'{k}: {v}' for k, v in sorted(counts.items()))})")

    problems = check(artists, credits)
    if problems:
        print(f"\n{len(problems)} problem(s):")
        for p in problems:
            print("  - " + p)
        return 1
    print("check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
