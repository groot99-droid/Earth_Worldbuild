#!/usr/bin/env python3
"""Download artwork images for every artist from Wikimedia Commons.

For each work in an artist's front matter the image is found either from
``commons_file`` (an explicit Commons file name) or from ``wiki`` (an English
Wikipedia article whose lead image is used). Only freely licensed files hosted
on Commons are accepted. Images are resized and saved to
``images/<slug>/<work-id>.jpg`` and their credits recorded in
``data/image-credits.json``.

Usage:
    python scripts/fetch_images.py              # fetch anything missing
    python scripts/fetch_images.py --only hokusai monet
    python scripts/fetch_images.py --force      # re-download everything
"""

from __future__ import annotations

import argparse
import html
import io
import math
import re
import sys
import time

import requests
from PIL import Image

from common import IMAGES_DIR, MIN_WORKS, load_artists, load_credits, save_credits

API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "Art-Talk/1.0 (https://github.com/groot99-droid/Art-Talk; educational art timeline)"
BATCH = 50
# Standard Wikimedia thumbnail widths. Only these are served for thumbnails;
# other widths are refused, and downloading originals is heavily rate-limited.
BUCKETS = [250, 330, 500, 960, 1280]
MAX_SIDE = 1280
MAX_PIXELS = 1_000_000
DOWNLOAD_DELAY = 3.0
JPEG_QUALITY = 85

Image.MAX_IMAGE_PIXELS = None

session = requests.Session()
session.headers["User-Agent"] = USER_AGENT


class RateLimited(Exception):
    """The server asked us to wait longer than we are willing to."""


def get(url: str, params: dict | None = None, attempts: int = 6, max_wait: float = 900) -> requests.Response:
    """GET with retries. Wikimedia rate-limits and says how long to wait in
    Retry-After; honour that (up to max_wait), otherwise back off exponentially."""
    backoff = 2.0
    for attempt in range(attempts):
        try:
            r = session.get(url, params=params, timeout=60)
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
            retry_after = r.headers.get("Retry-After", "")
            wait = float(retry_after) + 5 if retry_after.isdigit() else backoff
            if wait > max_wait:
                raise RateLimited(f"HTTP {r.status_code}, Retry-After {retry_after}s")
            print(f"  HTTP {r.status_code}; retrying in {wait:.0f}s", file=sys.stderr)
        time.sleep(wait)
        backoff *= 2
    raise RuntimeError("unreachable")


def api(params: dict) -> dict:
    params = {"action": "query", "format": "json", "formatversion": "2", "maxlag": "5", **params}
    data = get(API, params).json()
    if "error" in data:
        raise RuntimeError(f"API error: {data['error']}")
    time.sleep(1.0)
    return data


def chunks(items: list, n: int):
    for i in range(0, len(items), n):
        yield items[i : i + n]


def normalize_title(title: str) -> str:
    title = title.replace("_", " ").strip()
    return title[:1].upper() + title[1:]


def resolve_lead_images(titles: list[str]) -> dict[str, str | None]:
    """Map Wikipedia article titles to the file name of their lead image."""
    result: dict[str, str | None] = {}
    for batch in chunks(sorted(set(titles)), BATCH):
        data = api({"prop": "pageimages", "piprop": "name", "pilicense": "any", "redirects": "1", "titles": "|".join(batch)})
        q = data.get("query", {})
        alias = {t: t for t in batch}
        for step in ("normalized", "redirects"):
            mapping = {m["from"]: m["to"] for m in q.get(step, [])}
            alias = {orig: mapping.get(cur, cur) for orig, cur in alias.items()}
        images = {p["title"]: p.get("pageimage") for p in q.get("pages", [])}
        for orig, final in alias.items():
            result[orig] = images.get(final)
    return result


def file_info(files: list[str]) -> dict[str, dict | None]:
    """Fetch imageinfo (URLs, size, license metadata) for Commons files."""
    result: dict[str, dict | None] = {}
    for batch in chunks(sorted(set(files)), BATCH):
        titles = ["File:" + f for f in batch]
        data = api({
            "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata",
            "iiurlwidth": "1280",
            "iiextmetadatafilter": "LicenseShortName|LicenseUrl|Artist|NonFree|Credit",
            "titles": "|".join(titles),
        })
        q = data.get("query", {})
        norm = {m["from"]: m["to"] for m in q.get("normalized", [])}
        pages = {p["title"]: p for p in q.get("pages", [])}
        for f, t in zip(batch, titles):
            page = pages.get(norm.get(t, t))
            info = None
            # Commons files have no local enwiki page, so they are reported as
            # "missing" but "known" and still carry imageinfo.
            if page and page.get("imageinfo"):
                info = dict(page["imageinfo"][0])
                info["repository"] = page.get("imagerepository")
                info["title"] = page["title"]
            result[f] = info
    return result


def meta_value(info: dict, key: str) -> str:
    return (info.get("extmetadata", {}).get(key) or {}).get("value", "") or ""


def plain(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def license_ok(info: dict) -> tuple[bool, str]:
    if info.get("repository") != "shared":
        return False, "not hosted on Wikimedia Commons (likely non-free)"
    if meta_value(info, "NonFree").strip().lower() in ("true", "1", "yes"):
        return False, "flagged NonFree"
    lic = plain(meta_value(info, "LicenseShortName")).lower()
    free = (
        "public domain" in lic
        or lic.startswith("pd")
        or lic.startswith("cc0")
        or lic.startswith("cc by")
        or lic.startswith("cc-by")
        or "no restrictions" in lic
    )
    return (True, lic) if free else (False, f"license not allowed: {lic or 'unknown'}")


def strip_tracking(url: str) -> str:
    return url.split("?", 1)[0]


def thumb_url(original: str, width: int, mime: str | None) -> str:
    """Thumbnail URL for a Commons original, e.g.
    .../commons/a/ab/Name.jpg -> .../commons/thumb/a/ab/Name.jpg/960px-Name.jpg"""
    base, name = original.rsplit("/", 1)
    base = base.replace("/wikipedia/commons/", "/wikipedia/commons/thumb/", 1)
    suffix = ".jpg" if mime in ("image/tiff", "application/pdf") else ""
    return f"{base}/{name}/{width}px-{name}{suffix}"


def download_urls(info: dict) -> list[str]:
    """Candidate thumbnail URLs, best first.

    Originals are heavily rate-limited and non-standard widths are refused, so
    only standard bucket widths smaller than the original are used: the
    smallest one big enough for the final resize, then every smaller size as a
    fallback (small sizes used by Wikipedia articles are usually cached)."""
    w, h = info.get("width") or 0, info.get("height") or 0
    original = strip_tracking(info["url"])
    if not w or not h:
        return [strip_tracking(info.get("thumburl") or original)]
    scale = min(1.0, MAX_SIDE / max(w, h), math.sqrt(MAX_PIXELS / (w * h)))
    need = w * scale
    usable = [b for b in BUCKETS if b < w] or BUCKETS[:1]
    best = next((b for b in usable if b >= need), usable[-1])
    order = [best] + [b for b in reversed(usable) if b < best]
    return [thumb_url(original, b, info.get("mime")) for b in order]


def save_image(content: bytes, dest) -> None:
    img = Image.open(io.BytesIO(content))
    img = img.convert("RGB")
    w, h = img.size
    scale = min(1.0, MAX_SIDE / max(w, h), math.sqrt(MAX_PIXELS / (w * h)))
    if scale < 1.0:
        img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="*", help="artist slugs to process")
    ap.add_argument("--force", action="store_true", help="re-download existing images")
    ap.add_argument("--max-wait", type=float, default=60,
                    help="longest Retry-After (seconds) to wait for before skipping a file")
    args = ap.parse_args()

    artists = load_artists()
    if args.only:
        artists = [a for a in artists if a.slug in args.only]
    credits = load_credits()

    wiki_titles = [w["wiki"] for a in artists for w in a.works if not w.get("commons_file") and w.get("wiki")]
    lead = resolve_lead_images(wiki_titles) if wiki_titles else {}

    wanted: dict[tuple[str, str], str | None] = {}
    for a in artists:
        for w in a.works:
            f = w.get("commons_file") or lead.get(w.get("wiki", ""))
            wanted[(a.slug, w["id"])] = normalize_title(f) if f else None
    infos = file_info([f for f in wanted.values() if f])

    problems: list[str] = []
    short: list[str] = []
    for a in artists:
        ok = 0
        for w in a.works:
            key = a.image_rel(w)
            dest = a.image_path(w)
            f = wanted[(a.slug, w["id"])]
            if not f:
                problems.append(f"{a.slug}/{w['id']}: no image found (wiki={w.get('wiki')!r})")
                continue
            info = infos.get(f)
            if not info:
                problems.append(f"{a.slug}/{w['id']}: file not found: {f}")
                continue
            allowed, lic = license_ok(info)
            if not allowed:
                problems.append(f"{a.slug}/{w['id']}: {f}: {lic}")
                continue
            prev = credits.get(key)
            if dest.exists() and prev and prev.get("file") == info["title"] and not args.force:
                ok += 1
                continue
            print(f"downloading {key} <- {info['title']}")
            content, error = None, None
            for url in download_urls(info):
                try:
                    content = get(url, max_wait=args.max_wait).content
                    break
                except Exception as exc:  # noqa: BLE001 - try the next size
                    error = exc
                    print(f"  failed ({exc}); trying a smaller size", file=sys.stderr)
                    time.sleep(DOWNLOAD_DELAY)
            if content is None:
                problems.append(f"{a.slug}/{w['id']}: download failed: {error} (re-run later)")
                continue
            save_image(content, dest)
            time.sleep(DOWNLOAD_DELAY)
            credits[key] = {
                "work": w["title"],
                "file": info["title"],
                "source": info.get("descriptionurl"),
                "author": plain(meta_value(info, "Artist")) or None,
                "license": plain(meta_value(info, "LicenseShortName")),
                "license_url": meta_value(info, "LicenseUrl") or None,
            }
            save_credits(credits)
            ok += 1
        print(f"{a.slug:28s} {ok}/{len(a.works)} images")
        if ok < MIN_WORKS:
            short.append(f"{a.slug} ({ok})")

    # Drop credits for images that no longer exist.
    live = {a.image_rel(w) for a in load_artists() for w in a.works}
    credits = {k: v for k, v in credits.items() if k in live and (IMAGES_DIR.parent / k).exists()}
    save_credits(credits)

    if problems:
        print("\nProblems:")
        for p in problems:
            print("  - " + p)
    if short:
        print(f"\nArtists with fewer than {MIN_WORKS} images: {', '.join(short)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
