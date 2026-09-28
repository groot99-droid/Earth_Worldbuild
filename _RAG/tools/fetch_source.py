"""Fetch the raw text of a vault source, cache it, and check fact_checks against it.

WebFetch returns a model-written summary, and several hosts (Britannica, science.org, pnas.org, PMC and PubMed
web pages) refuse automated requests. This tool reads real text through routes that work, and records how:

  papers (DOI, PMC or PubMed id)  Europe PMC full text -> open-access PDF (via OpenAlex) -> publisher page ->
                                  PubMed abstract -> OpenAlex abstract -> Crossref metadata -> Wayback Machine
  Wikipedia                       MediaWiki API (raw wikitext plus revision id)
  Britannica, science.org, ...    Wayback Machine snapshot (closest to today)
  everything else                 direct request, then Wayback Machine

It never tries to get around a CAPTCHA, cookie wall or paywall: a wall page is logged and the next route is used.
A 403 is recorded once and not retried; 429 and 5xx back off and retry up to twice.

Usage:
  fetch_source.py fetch "Britannica on Timur" [--force]
  fetch_source.py fetch --url URL --slug NAME [--force]
  fetch_source.py claims "Britannica on Timur" [--missing-only] [--top 2] [--width 240]
  fetch_source.py grep "Britannica on Timur" "born 1336" [--width 240]
  fetch_source.py checks --tier 2 [--missing-only]         # each fact_check matched against ALL its cached cited sources
  fetch_source.py batch --tier 3 -n 10                    # fetch the next pending sources of a tier
  fetch_source.py queue build | status | next [--tier N] [-n 10] | mark TITLE STATUS [--note TEXT]

Cached raw text stays local in _RAG/source_cache/ (gitignored). The contact email comes from the
EARTH_FETCH_EMAIL environment variable or _RAG/fetch_config.local.json and is sent only to Crossref, OpenAlex,
NCBI E-utilities and Wikimedia, never to other hosts and never written into a note.
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import io
import json
import logging
import os
import re
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse

import requests

RAG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAG))
from vault import VAULT_ROOT, iter_notes, parse_note  # noqa: E402

CACHE = RAG / "source_cache"
CONFIG = RAG / "fetch_config.local.json"
QUEUE = CACHE / "queue.json"

UA_BASE = "EarthChronicleFetch/1.0 (personal fact-checking of a history knowledge base; non-commercial; low volume)"
POLITE_HOSTS = {"api.crossref.org", "api.openalex.org", "eutils.ncbi.nlm.nih.gov", "en.wikipedia.org"}
MIN_GAP = {"web.archive.org": 4.0}          # seconds between requests to one host; default 1.5
DEFAULT_GAP = 1.5
# Hosts that answer automated requests with 403 or a CAPTCHA: go straight to an archive or an API.
ARCHIVE_FIRST = ("britannica.com", "science.org", "pnas.org", "pubmed.ncbi.nlm.nih.gov", "pmc.ncbi.nlm.nih.gov",
                 "ncbi.nlm.nih.gov", "jstor.org")
JOURNAL_HOSTS = ("science.org", "nature.com", "pnas.org", "sciencedirect.com", "ncbi.nlm.nih.gov", "elifesciences.org",
                 "springer.com", "cell.com", "wiley.com", "tandfonline.com", "oup.com", "plos.org", "frontiersin.org",
                 "biorxiv.org", "royalsocietypublishing.org", "annualreviews.org", "jstor.org", "cambridge.org")
TIER1 = {"Britannica on Timur", "Pigati et al. 2023 White Sands Footprints", "PNAS 2024 Civil War Mortality Estimates",
         "Science 2021 Amazonian Reforestation Pollen Study"}
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"'<>?#]+", re.I)
WALL_RE = re.compile(r"captcha|are you a robot|verify you are (a )?human|just a moment|enable javascript and cookies|"
                     r"access denied|unusual traffic|checking your browser|attention required|request blocked", re.I)
LEVEL_RANK = {"full-text": 5, "archived-copy": 5, "reference-text": 5, "abstract": 3, "supplement": 2, "metadata": 1}
SUPP_NAME_RE = re.compile(r"(^|[_\-/. ])(si|supp|suppl|supplement|supplementary|supporting|appendix)([_\-. ]|\d|$)", re.I)

logging.getLogger("pypdf").setLevel(logging.ERROR)


def today() -> str:
    return date.today().isoformat()


def load_email() -> str | None:
    e = os.environ.get("EARTH_FETCH_EMAIL")
    if e and e.strip():
        return e.strip()
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8")).get("contact_email") or None
    except (OSError, ValueError):
        return None


def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()[:90] or "source"


def fold(s: str) -> str:
    """Lowercase, strip accents and number separators so claim text and page text compare equal."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = s.replace("’", "'").replace("–", "-").replace("—", "-").replace(" ", " ").replace(" ", " ")
    return re.sub(r"(?<=\d)[,  ](?=\d{3}\b)", "", s)


# ---------------------------------------------------------------------------------------------------------- HTTP

@dataclass
class Resp:
    status: int
    url: str
    headers: dict
    content: bytes
    error: str = ""

    def text(self) -> str:
        m = re.search(r"charset=([\w-]+)", self.headers.get("content-type", ""), re.I)
        enc = m.group(1) if m else None
        if not enc:
            m2 = re.search(rb"<meta[^>]+charset=[\"']?([\w-]+)", self.content[:4096], re.I)
            enc = m2.group(1).decode("ascii", "ignore") if m2 else "utf-8"
        try:
            return self.content.decode(enc, errors="replace")
        except LookupError:
            return self.content.decode("utf-8", errors="replace")

    @property
    def is_pdf(self) -> bool:
        return self.content[:5] == b"%PDF-"

    def json_safe(self) -> dict:
        try:
            return json.loads(self.content.decode("utf-8", errors="replace"))
        except ValueError:
            return {}


class Http:
    def __init__(self, email: str | None):
        self.s = requests.Session()
        self.email = email
        self.last: dict[str, float] = {}
        self.blocked: dict[str, int] = {}     # host -> number of 403 answers seen in this run
        self.log: list[dict] = []             # one entry per attempt; never contains the contact email

    def polite_params(self, host_key: str) -> dict:
        if not self.email:
            return {}
        return {"api.crossref.org": {"mailto": self.email}, "api.openalex.org": {"mailto": self.email},
                "eutils.ncbi.nlm.nih.gov": {"tool": "earth-chronicle-fetch", "email": self.email}}.get(host_key, {})

    def get(self, url: str, *, params: dict | None = None, timeout: int = 45, max_bytes: int = 60_000_000) -> Resp:
        host = urlparse(url).netloc.lower()
        ua = f"{UA_BASE} mailto:{self.email}" if self.email and host in POLITE_HOSTS else UA_BASE
        params = {**self.polite_params(host), **(params or {})}
        resp = Resp(0, url, {}, b"")
        for attempt in range(3):
            gap = MIN_GAP.get(host, DEFAULT_GAP)
            dt = time.monotonic() - self.last.get(host, 0.0)
            if dt < gap:
                time.sleep(gap - dt)
            self.last[host] = time.monotonic()
            try:
                r = self.s.get(url, params=params, headers={"User-Agent": ua, "Accept-Language": "en"},
                               timeout=timeout, allow_redirects=True, stream=True)
                body = b""
                for chunk in r.iter_content(65536):
                    body += chunk
                    if len(body) > max_bytes:
                        break
                final = re.sub(r"[?&](mailto|email)=[^&]*", "", r.url)
                resp = Resp(r.status_code, final, {k.lower(): v for k, v in r.headers.items()}, body)
            except requests.RequestException as e:
                self.log.append({"host": host, "url": url[:120], "status": 0, "error": type(e).__name__})
                resp = Resp(0, url, {}, b"", error=type(e).__name__)
                if isinstance(e, requests.TooManyRedirects):
                    return resp                     # a redirect loop will not fix itself
                if attempt < 2:
                    time.sleep(5 * 2 ** attempt)
                    continue
                return resp
            self.log.append({"host": host, "url": url[:120], "status": resp.status})
            if resp.status in (429, 502, 503, 504) and attempt < 2:
                ra = resp.headers.get("retry-after", "")
                wait = min(int(ra), 90) if ra.isdigit() else 8 * 2 ** attempt
                time.sleep(wait)
                continue
            if resp.status == 403:
                self.blocked[host] = self.blocked.get(host, 0) + 1
            return resp
        return resp


# ---------------------------------------------------------------------------------------------- text extraction

class _HTMLText(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "template", "iframe", "nav", "footer"}
    BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "main", "ul", "ol",
             "table", "blockquote", "pre", "dd", "dt", "figcaption", "header", "aside", "hr"}
    META = {"description", "dc.description", "dc.title", "citation_title", "citation_doi", "citation_abstract",
            "citation_journal_title", "citation_publication_date", "citation_author", "og:title", "og:description",
            "dc.identifier"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = self.art = self.main = 0
        self.all: list[str] = []
        self.art_parts: list[str] = []
        self.main_parts: list[str] = []
        self.title = ""
        self._in_title = False
        self.meta: dict[str, list[str]] = {}

    def _emit(self, s: str):
        self.all.append(s)
        if self.art:
            self.art_parts.append(s)
        if self.main:
            self.main_parts.append(s)

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            a = {k.lower(): (v or "") for k, v in attrs}
            key = (a.get("name") or a.get("property") or "").lower()
            if key in self.META and a.get("content"):
                self.meta.setdefault(key, []).append(a["content"].strip())
        if tag == "article":
            self.art += 1
        if tag == "main":
            self.main += 1
        if tag in self.BLOCK and not self.skip:
            self._emit("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        if tag == "title":
            self._in_title = False
        if tag == "article" and self.art:
            self.art -= 1
        if tag == "main" and self.main:
            self.main -= 1
        if tag in self.BLOCK and not self.skip:
            self._emit("\n")
        if tag in ("td", "th") and not self.skip:
            self._emit(" | ")

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if not self.skip:
            self._emit(data)


def _clean_lines(parts: list[str]) -> str:
    text = "".join(parts).replace(" ", " ")
    lines = [re.sub(r"[ \t]+", " ", ln).strip(" |") for ln in text.split("\n")]
    out: list[str] = []
    for ln in lines:
        if ln or (out and out[-1]):
            out.append(ln)
    return "\n".join(out).strip()


def html_to_text(html_src: str) -> tuple[str, str, dict]:
    """Return (page title, body text, selected <meta> values). Prefers <article>, then <main>, then the whole page."""
    p = _HTMLText()
    try:
        p.feed(html_src)
        p.close()
    except Exception:  # malformed markup: keep what was parsed
        pass
    art, main, whole = _clean_lines(p.art_parts), _clean_lines(p.main_parts), _clean_lines(p.all)
    body = art if len(art) >= 800 else main if len(main) >= 800 else whole
    return re.sub(r"\s+", " ", p.title).strip(), body, p.meta


def with_header(title: str, meta: dict, body: str) -> str:
    head = []
    if title:
        head.append(f"[page title] {title}")
    for k, vals in meta.items():
        for v in vals[:8]:
            head.append(f"[meta {k}] {v}")
    return ("\n".join(head) + "\n\n" + body) if head else body


def looks_walled(text: str) -> bool:
    return len(text) < 2500 and bool(WALL_RE.search(text))


PAYWALL_RE = re.compile(r"access options|access through your (institution|organi[sz]ation)|subscribe to (read|continue)|"
                        r"rent or buy|purchase access|check access|log in to read|to read the full|register and access|"
                        r"create a free account|^section snippets$", re.I | re.M)
HEADING_RE = re.compile(r"(\d+\.?\s*)?(introduction|main|methods|materials and methods|results|results and discussion|"
                        r"discussion|conclusions?)", re.I)


def is_paywalled(text: str) -> bool:
    return bool(PAYWALL_RE.search(text))


def looks_like_fulltext(text: str) -> bool:
    """A real article body: no paywall or login notice (a paywalled page shows the abstract, snippets and the reference
    list), and either two section headings on their own lines or ten long paragraphs."""
    if len(text) < 8000 or is_paywalled(text):
        return False
    lines = text.split("\n")
    heads = sum(1 for ln in lines if HEADING_RE.fullmatch(ln.strip()))
    return heads >= 2 or sum(1 for ln in lines if len(ln) >= 400) >= 10


def pdf_to_text(content: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(content))
    pages = []
    for i, page in enumerate(reader.pages[:250], 1):
        pages.append(f"[page {i}]\n{page.extract_text() or ''}")
    return "\n\n".join(pages)


def _local(tag) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _inline(el) -> str:
    parts = [el.text or ""]
    for ch in el:
        n = _local(ch.tag)
        if n == "xref" and ch.get("ref-type") == "bibr":
            pass
        elif n == "sup":
            parts.append("^" + _inline(ch))
        elif n == "sub":
            parts.append("_" + _inline(ch))
        else:
            parts.append(_inline(ch))
        parts.append(ch.tail or "")
    return re.sub(r"\s+", " ", "".join(parts)).strip()


def jats_to_text(xml_bytes: bytes) -> tuple[str, str]:
    """Europe PMC / PMC JATS full text -> (article title, plain text with headings, tables and captions)."""
    root = ET.fromstring(xml_bytes)
    lines: list[str] = []
    title = ""
    first = next((e for e in root.iter() if _local(e.tag) == "article-title"), None)
    if first is not None:
        title = _inline(first)
        lines.append(f"# {title}")
    names = []
    for c in root.iter():
        if _local(c.tag) == "contrib" and c.get("contrib-type") == "author":
            sn = next((_inline(x) for x in c.iter() if _local(x.tag) == "surname"), "")
            gn = next((_inline(x) for x in c.iter() if _local(x.tag) == "given-names"), "")
            if sn:
                names.append(f"{gn} {sn}".strip())
    if names:
        lines.append("Authors: " + "; ".join(names))

    def walk(el):
        n = _local(el.tag)
        if n in ("ref-list", "journal-meta", "permissions", "funding-group", "aff", "contrib-group", "graphic",
                 "supplementary-material", "inline-formula", "title-group", "pub-history", "author-notes"):
            return
        if n == "sec" or n == "abstract" or n == "app":
            t = next((c for c in el if _local(c.tag) == "title"), None)
            head = _inline(t) if t is not None else ("Abstract" if n == "abstract" else "")
            if head:
                lines.append(f"\n## {head}")
            for c in el:
                if _local(c.tag) != "title":
                    walk(c)
        elif n in ("p", "list-item"):
            txt = _inline(el)
            if txt:
                lines.append(txt)
        elif n in ("table-wrap", "fig", "boxed-text"):
            label = next((_inline(c) for c in el if _local(c.tag) == "label"), "")
            cap = next((_inline(c) for c in el if _local(c.tag) == "caption"), "")
            if label or cap:
                lines.append(f"\n[{n}] {label} {cap}".rstrip())
            for tr in el.iter():
                if _local(tr.tag) == "tr":
                    cells = [_inline(c) for c in tr if _local(c.tag) in ("td", "th")]
                    if any(cells):
                        lines.append(" | ".join(cells))
            for c in el:
                if _local(c.tag) in ("table-wrap-foot", "p"):
                    walk(c)
        else:
            for c in el:
                walk(c)

    walk(root)
    return title, "\n".join(lines).strip()


def pubmed_xml_to_text(xml_bytes: bytes) -> tuple[str, str]:
    root = ET.fromstring(xml_bytes)
    art = next((e for e in root.iter() if _local(e.tag) == "Article"), None)
    if art is None:
        return "", ""
    title = _inline(next((e for e in art if _local(e.tag) == "ArticleTitle"), ET.Element("x")))
    journal = next((_inline(e) for e in art.iter() if _local(e.tag) == "Title"), "")
    year = next((_inline(e) for e in art.iter() if _local(e.tag) in ("Year", "MedlineDate")), "")
    authors = []
    for a in art.iter():
        if _local(a.tag) == "Author":
            ln = next((_inline(x) for x in a if _local(x.tag) == "LastName"), "")
            fn = next((_inline(x) for x in a if _local(x.tag) == "ForeName"), "")
            if ln:
                authors.append(f"{fn} {ln}".strip())
    lines = [f"# {title}", f"{journal}, {year}", "Authors: " + "; ".join(authors), "\n## Abstract"]
    for at in art.iter():
        if _local(at.tag) == "AbstractText":
            label = at.get("Label")
            lines.append((f"{label}: " if label else "") + _inline(at))
    return title, "\n".join(lines)


def wikitext_plain(t: str) -> str:
    """Rough plain-text rendering of wikitext for matching (the cached file keeps the raw wikitext)."""
    t = re.sub(r"<ref[^>]*/>", "", t)
    t = re.sub(r"<ref[^>]*>.*?</ref>", "", t, flags=re.S)
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    for _ in range(6):                       # innermost templates first: keep their arguments, drop the name
        t2 = re.sub(r"\{\{([^{}]*)\}\}", lambda m: " ".join(x.split("=", 1)[-1].strip() for x in m.group(1).split("|")[1:]), t)
        if t2 == t:
            break
        t = t2
    t = re.sub(r"\[\[(?:File|Image|Category):[^\]]*\]\]", "", t, flags=re.I)
    t = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", t)
    t = re.sub(r"\[https?://\S+ ([^\]]*)\]", r"\1", t)
    t = re.sub(r"'{2,}", "", t)
    t = re.sub(r"</?[a-z][^>]*>", "", t)
    return t


# ------------------------------------------------------------------------------------------------- resolvers

@dataclass
class Result:
    text: str
    level: str                       # full-text | archived-copy | reference-text | abstract | metadata
    route: str
    final_url: str
    status: int
    snapshot: str | None = None
    revid: int | None = None
    page_title: str | None = None
    extra: dict = field(default_factory=dict)


def identify(url: str) -> dict:
    u = urlparse(url)
    host = u.netloc.lower().removeprefix("www.")
    path = unquote(u.path)
    ident = {"host": host, "kind": "page", "doi": None, "pmcid": None, "pmid": None, "pii": None, "title_guess": None}
    if host.endswith("wikipedia.org"):
        ident["kind"] = "wiki"
        return ident
    if host in ("pubmed.ncbi.nlm.nih.gov",):
        m = re.search(r"/(\d+)", path)
        ident.update(kind="paper", pmid=m.group(1) if m else None)
        return ident
    if host in ("pmc.ncbi.nlm.nih.gov", "ncbi.nlm.nih.gov") and re.search(r"PMC\d+", path):
        ident.update(kind="paper", pmcid=re.search(r"PMC\d+", path).group(0))
        return ident
    m = DOI_RE.search(path) or DOI_RE.search(url)
    if host == "nature.com" and path.startswith("/articles/"):
        m = None
        ident["doi"] = "10.1038/" + path.split("/")[2].removesuffix(".pdf")
    if host == "elifesciences.org" and path.startswith("/articles/"):
        m = None
        ident["doi"] = "10.7554/eLife." + path.split("/")[2]
    jm = re.search(r"/(rspb|rstb|rspa|rsif|rsbl|rsos)/article/\d+/\d+/(\d{4})(\d+)/", path) if host == "royalsocietypublishing.org" else None
    if jm:
        m = None
        ident["doi"] = f"10.1098/{jm.group(1)}.{jm.group(2)}.{jm.group(3)}"
    if m:
        ident["doi"] = m.group(0).rstrip(".,);").removesuffix(".pdf")
    if not ident["doi"]:
        pm = re.search(r"/pii/(S[0-9A-Za-z]+)", path) or re.search(r"/fulltext/(S[\d\-]+\(\d\d\)[\d\-]+)", path)
        if pm:                                        # Elsevier/Cell PII: the DOI is looked up in Crossref
            ident["pii"] = re.sub(r"[^0-9A-Za-z]", "", pm.group(1))
        elif host.endswith("cambridge.org") and "/article/" in path:
            slug = path.split("/article/", 1)[1].split("/")[0]
            if slug.count("-") >= 3:                  # a title slug: the DOI is looked up by title in Crossref
                ident["title_guess"] = slug.replace("-", " ")
    if (ident["doi"] or "").startswith("10.1038/d41586"):
        ident["doi"] = None                           # a Nature news item, not a paper: read the page itself
        return ident
    if ident["doi"] or ident["pii"] or ident["title_guess"]:
        ident["kind"] = "paper"
    return ident


class Ctx:
    """Shared state for one fetch: HTTP client, identifiers, and cached API answers."""

    def __init__(self, http: Http, url: str):
        self.http, self.url = http, url
        self.ident = identify(url)
        self._epmc = self._oa = None
        self.paper = self.ident["kind"] == "paper"

    def resolve_doi(self) -> None:
        """Find the DOI of a paper whose URL has none (Elsevier PII or a Cambridge title slug) through Crossref."""
        i = self.ident
        if i["doi"] or not (i["pii"] or i["title_guess"]):
            return
        params = ({"filter": f"alternative-id:{i['pii']}"} if i["pii"] else {"query.bibliographic": i["title_guess"]})
        r = self.http.get("https://api.crossref.org/works", params={**params, "rows": 1, "select": "DOI,title"})
        items = ((r.json_safe().get("message") or {}).get("items") or []) if r.status == 200 else []
        if not items:
            return
        if i["title_guess"]:                          # accept a title match only when most words agree
            want = set(re.findall(r"[a-z]{4,}", fold(i["title_guess"])))
            got = set(re.findall(r"[a-z]{4,}", fold((items[0].get("title") or [""])[0])))
            if not want or len(want & got) / len(want) < 0.7:
                return
        i["doi"] = items[0]["DOI"]

    # Europe PMC record (ids, abstract, licence)
    def epmc(self) -> dict:
        if self._epmc is None:
            self.resolve_doi()
            i = self.ident
            q = (f'DOI:"{i["doi"]}"' if i["doi"] else f'PMCID:{i["pmcid"]}' if i["pmcid"]
                 else f'EXT_ID:{i["pmid"]} AND SRC:MED' if i["pmid"] else None)
            self._epmc = {}
            if q:
                r = self.http.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                                  params={"query": q, "format": "json", "resultType": "core", "pageSize": 1})
                if r.status == 200:
                    res = (r.json_safe().get("resultList") or {}).get("result") or []
                    self._epmc = res[0] if res else {}
            for k_src, k_dst in (("doi", "doi"), ("pmcid", "pmcid"), ("pmid", "pmid")):
                if not self.ident[k_dst] and self._epmc.get(k_src):
                    self.ident[k_dst] = self._epmc[k_src]
        return self._epmc

    def openalex(self) -> dict:
        if self._oa is None:
            self._oa = {}
            self.epmc()
            i = self.ident
            key = f"doi:{i['doi']}" if i["doi"] else f"pmid:{i['pmid']}" if i["pmid"] else None
            if key:
                r = self.http.get(f"https://api.openalex.org/works/{key}")
                if r.status == 200:
                    self._oa = r.json_safe()
        return self._oa


def r_europepmc_fulltext(c: Ctx) -> Result | None:
    c.epmc()
    pmcid = c.ident["pmcid"]
    if not pmcid:
        return None
    r = c.http.get(f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML")
    if r.status != 200 or b"<" not in r.content[:200]:
        return None
    title, text = jats_to_text(r.content)
    if len(text) < 1500:
        return None
    lic = c._epmc.get("license") or ("open access" if c._epmc.get("isOpenAccess") == "Y" else "")
    return Result(text, "full-text", "europepmc-fulltext", f"https://europepmc.org/article/PMC/{pmcid.removeprefix('PMC')}",
                  r.status, page_title=title, extra={"pmcid": pmcid, "licence": lic})


def r_openalex_pdf(c: Ctx) -> Result | None:
    w = c.openalex()
    cands: list[tuple[str, dict]] = []
    for loc in [w.get("best_oa_location") or {}] + (w.get("locations") or []):
        u = loc.get("pdf_url")
        if u and loc.get("is_oa", True) and u not in [x[0] for x in cands]:
            cands.append((u, loc))
    oa = (w.get("open_access") or {}).get("oa_url")
    if oa and oa.lower().endswith(".pdf") and oa not in [x[0] for x in cands]:
        cands.append((oa, {}))
    title_words = [t for t in re.findall(r"[a-z]{5,}", fold(w.get("title") or ""))][:8]
    for u, loc in cands[:3]:
        host = urlparse(u).netloc.lower()
        if c.http.blocked.get(host, 0) >= 1:
            continue
        r = c.http.get(u)
        if r.status != 200 or not r.is_pdf:
            continue
        try:
            text = pdf_to_text(r.content)
        except Exception:
            continue
        head = fold(text[:6000])
        if len(text) < 3000 or (title_words and sum(t in head for t in title_words) < max(2, len(title_words) // 2)):
            continue
        is_supp = bool(SUPP_NAME_RE.search(urlparse(u).path.rsplit("/", 1)[-1])) or bool(
            re.search(r"supplementary (materials|information)|supporting information", head[:1500]))
        if not is_supp and not looks_like_fulltext(text):
            continue                               # a stub, a poster or an abstract page, not the paper
        return Result(text, "supplement" if is_supp else "full-text", f"openalex-oa-pdf ({host})", r.url, r.status,
                      extra={"oa_version": loc.get("version"), "licence": loc.get("license")})
    return None


def r_publisher_direct(c: Ctx) -> Result | None:
    host = c.ident["host"]
    if any(host.endswith(h) for h in ARCHIVE_FIRST) or c.http.blocked.get(urlparse(c.url).netloc.lower(), 0) >= 1:
        return None
    r = c.http.get(c.url)
    if r.status != 200:
        return None
    if r.is_pdf:
        try:
            text = pdf_to_text(r.content)
        except Exception:
            return None
        return Result(text, "full-text", "direct-pdf", r.url, r.status)
    title, body, meta = html_to_text(r.text())
    text = with_header(title, meta, body)
    if looks_walled(text) or len(body) < 300:
        c.http.log[-1]["wall"] = True
        return None
    level = ("full-text" if looks_like_fulltext(body) else "abstract") if c.paper else (
        "abstract" if is_paywalled(body) else "full-text")
    return Result(text, level, "direct", r.url, r.status, page_title=title)


def r_pubmed_abstract(c: Ctx) -> Result | None:
    c.epmc()
    pmid = c.ident["pmid"]
    if not pmid and c.ident["doi"]:
        r = c.http.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                       params={"db": "pubmed", "term": f"{c.ident['doi']}[AID]", "retmode": "json"})
        ids = ((r.json_safe().get("esearchresult") or {}).get("idlist") or []) if r.status == 200 else []
        pmid = ids[0] if ids else None
    if not pmid:
        return None
    r = c.http.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
                   params={"db": "pubmed", "id": pmid, "retmode": "xml"})
    if r.status != 200:
        return None
    title, text = pubmed_xml_to_text(r.content)
    if "## Abstract" not in text or len(text) < 400:
        return None
    return Result(text, "abstract", "pubmed-abstract", f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/", r.status,
                  page_title=title, extra={"pmid": pmid})


def r_openalex_abstract(c: Ctx) -> Result | None:
    w = c.openalex()
    inv = w.get("abstract_inverted_index")
    if not inv:
        return None
    words = sorted((pos, word) for word, poss in inv.items() for pos in poss)
    authors = "; ".join((a.get("author") or {}).get("display_name", "") for a in (w.get("authorships") or []))
    text = (f"# {w.get('title')}\nYear: {w.get('publication_year')}\nAuthors: {authors}\n\n## Abstract\n"
            + " ".join(x for _, x in words))
    return Result(text, "abstract", "openalex-abstract", f"https://openalex.org/{w.get('id', '').rsplit('/', 1)[-1]}", 200,
                  page_title=w.get("title"))


def r_crossref(c: Ctx) -> Result | None:
    c.epmc()
    if not c.ident["doi"]:
        return None
    r = c.http.get(f"https://api.crossref.org/works/{quote(c.ident['doi'], safe='/')}")
    if r.status != 200:
        return None
    m = r.json_safe().get("message") or {}
    authors = "; ".join(f"{a.get('given', '')} {a.get('family', '')}".strip() for a in m.get("author", []))
    issued = (m.get("issued") or {}).get("date-parts", [[None]])[0]
    ttl = (m.get("title") or [""])[0]
    text = (f"# {ttl}\n{(m.get('container-title') or [''])[0]}, {'-'.join(str(x) for x in issued if x)}\n"
            f"Authors: {authors}\nDOI: {c.ident['doi']}\n")
    level = "metadata"
    if m.get("abstract"):
        text += "\n## Abstract\n" + re.sub(r"<[^>]+>", " ", m["abstract"])
        level = "abstract"
    return Result(text, level, "crossref", f"https://doi.org/{c.ident['doi']}", 200, page_title=ttl)


def r_wayback(c: Ctx) -> Result | None:
    r = c.http.get(f"https://web.archive.org/web/2id_/{c.url}")
    if r.status != 200:
        # The closest-snapshot redirect failed (a loop or an error page): ask the CDX index for the newest capture
        # that the archive itself recorded as HTTP 200, and fetch that one.
        idx = c.http.get("https://web.archive.org/cdx/search/cdx?" + urlencode(
            [("url", c.url), ("output", "json"), ("fl", "timestamp"), ("filter", "statuscode:200"),
             ("filter", "mimetype:text/html|application/pdf"), ("limit", "-1")]))
        rows = idx.json_safe() if idx.status == 200 and idx.content[:1] == b"[" else []
        if not isinstance(rows, list) or len(rows) < 2:
            return None
        r = c.http.get(f"https://web.archive.org/web/{rows[-1][0]}id_/{c.url}")
        if r.status != 200:
            return None
    m = re.search(r"/web/(\d{14})", r.url)
    snap = m.group(1) if m else None
    if r.is_pdf:
        try:
            body = pdf_to_text(r.content)
        except Exception:
            return None
        title, meta = "", {}
    else:
        title, body, meta = html_to_text(r.text())
    text = with_header(title, meta, body)
    if looks_walled(text) or len(body) < 300:
        c.http.log[-1]["wall"] = True
        return None
    level = ("archived-copy" if looks_like_fulltext(body) else "abstract") if c.paper else (
        "abstract" if is_paywalled(body) else "archived-copy")
    return Result(text, level, "wayback", r.url, r.status, snapshot=snap, page_title=title)


def r_wikipedia(c: Ctx) -> Result | None:
    u = urlparse(c.url)
    qs = parse_qs(u.query)
    title = qs["title"][0] if "title" in qs else unquote(u.path.split("/wiki/", 1)[1]) if "/wiki/" in u.path else None
    if not title:
        return None
    api = f"https://{u.netloc}/w/api.php"
    r = c.http.get(api, params={"action": "query", "prop": "revisions", "titles": title.replace("_", " "),
                                "rvprop": "ids|timestamp|content", "rvslots": "main", "format": "json",
                                "formatversion": "2", "redirects": "1"})
    if r.status == 200:
        pages = (r.json_safe().get("query") or {}).get("pages") or []
        revs = (pages[0].get("revisions") if pages else None) or []
        if revs:
            rev = revs[0]
            content = (rev.get("slots") or {}).get("main", {}).get("content") or ""
            if content:
                return Result(content, "reference-text", "wikipedia-api", f"https://{u.netloc}/wiki/{quote(pages[0]['title'].replace(' ', '_'))}",
                              200, revid=rev.get("revid"), page_title=pages[0]["title"], extra={"revision_time": rev.get("timestamp")})
    r = c.http.get(f"https://{u.netloc}/w/index.php", params={"title": title, "action": "raw"})
    if r.status == 200 and len(r.content) > 200:
        return Result(r.text(), "reference-text", "wikipedia-raw", r.url, r.status, page_title=title)
    return None


def routes_for(c: Ctx) -> list[tuple[str, callable]]:
    kind, host = c.ident["kind"], c.ident["host"]
    if kind == "wiki":
        return [("wikipedia", lambda: r_wikipedia(c))]
    if kind == "paper":
        chain = [("europepmc-fulltext", r_europepmc_fulltext), ("openalex-oa-pdf", r_openalex_pdf),
                 ("publisher-direct", r_publisher_direct), ("pubmed-abstract", r_pubmed_abstract),
                 ("openalex-abstract", r_openalex_abstract), ("crossref", r_crossref), ("wayback", r_wayback)]
        return [(n, (lambda f=f: f(c))) for n, f in chain]
    if any(host.endswith(h) for h in ARCHIVE_FIRST):
        return [("wayback", lambda: r_wayback(c))]
    return [("direct", lambda: r_publisher_direct(c)), ("wayback", lambda: r_wayback(c))]


def resolve(http: Http, url: str) -> tuple[Result | None, list[dict], dict]:
    c = Ctx(http, url)
    best: Result | None = None
    supp: Result | None = None
    tried: list[str] = []
    for name, fn in routes_for(c):
        start = len(http.log)
        try:
            res = fn()
        except Exception as e:                      # one broken route must not stop the chain
            http.log.append({"host": name, "url": "", "status": 0, "error": f"{type(e).__name__}: {str(e)[:80]}"})
            res = None
        tried.append(f"{name}: {'ok ' + res.level if res else 'none'}")
        if res and res.level == "supplement":      # supplementary material is not the paper: keep it, keep looking
            supp = supp or res
            continue
        if res and LEVEL_RANK[res.level] >= 5:
            best = res
            break
        if res and (best is None or LEVEL_RANK[res.level] > LEVEL_RANK[best.level]):
            best = res
    if supp:
        if best is None:
            best = supp
        elif best.level not in ("full-text", "archived-copy"):
            best.text += (f"\n\n==== SUPPLEMENTARY MATERIAL (not the paper itself): {supp.final_url} ====\n\n" + supp.text)
            best.extra.update(supplement_url=supp.final_url, supplement_chars=len(supp.text))
    return best, http.log, {"identified": {k: v for k, v in c.ident.items() if v}, "route_trace": tried}


# ---------------------------------------------------------------------------------------------- cache and notes

def source_notes() -> dict[str, tuple[Path, dict, str]]:
    return {p.stem: (p, *parse_note(p)) for p in iter_notes() if p.parent.name == "07_Sources"}


def cache_paths(slug: str) -> tuple[Path, Path]:
    return CACHE / f"{slug}.txt", CACHE / f"{slug}.meta.json"


def pick_slug(title: str) -> str:
    slug = slugify(title)
    _, mp = cache_paths(slug)
    if mp.exists():
        try:
            if json.loads(mp.read_text(encoding="utf-8")).get("title") not in (title, None):
                slug += "-" + hashlib.sha1(title.encode()).hexdigest()[:6]
        except ValueError:
            pass
    return slug


def write_cache(slug: str, title: str | None, url: str, res: Result | None, http_log: list[dict], info: dict) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    tp, mp = cache_paths(slug)
    meta = {"title": title, "slug": slug, "requested_url": url, "retrieved": today(), **info,
            "attempts": http_log[-40:]}
    if res:
        data = res.text.encode("utf-8")
        tp.write_bytes(data.replace(b"\r\n", b"\n"))
        meta.update(route=res.route, final_url=res.final_url, http_status=res.status, level=res.level,
                    sha256=hashlib.sha256(data).hexdigest(), chars=len(res.text), snapshot=res.snapshot,
                    revid=res.revid, page_title=res.page_title, **{f"x_{k}": v for k, v in res.extra.items()})
    else:
        meta.update(route=None, level=None, chars=0)
        if tp.exists():
            tp.unlink()
    mp.write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
    return meta


def do_fetch(http: Http, title: str | None, url: str, slug: str, force: bool) -> dict:
    tp, mp = cache_paths(slug)
    if mp.exists() and not force:
        m = json.loads(mp.read_text(encoding="utf-8"))
        m["_cached"] = True
        return m
    http.log.clear()
    res, log, info = resolve(http, url)
    meta = write_cache(slug, title, url, res, log, info)
    doi = (info.get("identified") or {}).get("doi")
    if res and doi:
        meta["biblio"] = fetch_biblio(http, doi)
        cache_paths(slug)[1].write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
    update_queue_entry(title, meta)
    return meta


def fetch_biblio(http: Http, doi: str) -> dict | None:
    """Bibliographic record from Crossref: the real title, year, journal and authors of a DOI."""
    r = http.get(f"https://api.crossref.org/works/{quote(doi, safe='/')}")
    if r.status != 200:
        return None
    m = r.json_safe().get("message") or {}
    dp = ((m.get("issued") or {}).get("date-parts") or [[None]])[0] or []
    return {"doi": doi, "title": (m.get("title") or [""])[0], "year": dp[0] if dp else None,
            "date": "-".join(str(x) for x in dp if x), "journal": (m.get("container-title") or [""])[0],
            "volume": m.get("volume"), "issue": m.get("issue"), "page": m.get("page"),
            "authors": [a.get("family") for a in m.get("author", [])][:8], "n_authors": len(m.get("author", []))}


def cmd_biblio(args) -> int:
    """Add the Crossref bibliographic record to cached papers that lack one."""
    http = Http(load_email())
    n = 0
    for mp in sorted(CACHE.glob("*.meta.json")):
        m = json.loads(mp.read_text(encoding="utf-8"))
        doi = (m.get("identified") or {}).get("doi")
        if not doi or not m.get("level") or (m.get("biblio") and not args.force):
            continue
        m["biblio"] = fetch_biblio(http, doi)
        mp.write_text(json.dumps(m, indent=1, ensure_ascii=False), encoding="utf-8")
        b = m["biblio"] or {}
        print(f"{b.get('year')} | {(b.get('journal') or '')[:22]:22} | {(b.get('title') or 'NO RECORD')[:80]}  <- {m.get('title')}")
        n += 1
    print(f"{n} record(s) added.")
    return 0


def report(meta: dict, preview: int = 260) -> None:
    ok = bool(meta.get("level"))
    tag = "CACHED " if meta.get("_cached") else ""
    print(f"{tag}{'OK ' if ok else 'FAILED'} {meta.get('title') or meta['slug']}")
    print(f"  url:     {meta['requested_url']}")
    if ok:
        print(f"  route:   {meta['route']}   level: {meta['level']}   chars: {meta['chars']:,}"
              + (f"   snapshot: {meta['snapshot']}" if meta.get("snapshot") else "")
              + (f"   revid: {meta['revid']}" if meta.get("revid") else ""))
        print(f"  final:   {meta['final_url']}")
    print(f"  trace:   {'; '.join(meta.get('route_trace', []))}")
    bad = [f"{a['host']} {a['status']}" for a in meta.get("attempts", []) if a.get("status") not in (200,)]
    if bad:
        print(f"  non-200: {', '.join(bad)}")
    if ok:
        txt = cache_paths(meta["slug"])[0].read_text(encoding="utf-8")
        print("  text:    " + re.sub(r"\s+", " ", txt[:preview]).strip() + "...")
        print(f"  cache:   {cache_paths(meta['slug'])[0]}")


# ------------------------------------------------------------------------------------------ claims and grep

STOP = set("The This That These Those With From After Before During Into Under Over About Also Some Many Most Other Its "
           "Their There When Where While Which Such Both Each Later Early Modern Old New First Second Third Today "
           "Traditional Called Only Between Through Among Since Until Although However Because Around Nearly Roughly".split())
NUM_RE = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)(?![\w])")


def claim_keys(atom: str) -> list[tuple[str, str]]:
    """Numbers (2+ digits, decimals, comma groups) and capitalised names worth finding in the source text."""
    keys: list[tuple[str, str]] = []
    for m in NUM_RE.finditer(atom):
        n = m.group(1)
        if len(n.replace(",", "").replace(".", "")) >= 2 or "." in n:
            keys.append(("num", n))
    words = re.findall(r"[A-Za-zÀ-ſ][\w'’-]*", atom)
    for i, w in enumerate(words):
        if w[0].isupper() and len(w) >= 4 and w not in STOP and not (i == 0):
            keys.append(("name", w))
    for q in re.findall(r"[\"'‘“]([^\"'’”]{4,60})[\"'’”]", atom):
        keys.append(("phrase", q))
    seen, out = set(), []
    for k in keys:
        if k[1].lower() not in seen:
            seen.add(k[1].lower())
            out.append(k)
    return out


def load_matchable(slug: str) -> tuple[str, dict]:
    tp, mp = cache_paths(slug)
    meta = json.loads(mp.read_text(encoding="utf-8"))
    text = tp.read_text(encoding="utf-8")
    if (meta.get("route") or "").startswith("wikipedia"):
        text = wikitext_plain(text)
    if "pdf" in (meta.get("route") or ""):           # PDF text breaks every line: rejoin wrapped lines so sentences match
        text = re.sub(r"-\n(?=[a-z])", "", text)
        text = re.sub(r"(?<![.!?:;])\n(?=[a-z0-9(\[‘“\"'])", " ", text)
        text = re.sub(r"[­ﬁﬂ]", lambda m: {"­": "", "ﬁ": "fi", "ﬂ": "fl"}[m.group(0)], text)
    b = meta.get("biblio")
    if b:                                            # so publication years and titles can be matched like any other text
        text += (f"\n[bibliographic] {b.get('year')} {b.get('date')} {b.get('journal')} {b.get('volume') or ''} "
                 f"{b.get('issue') or ''} {b.get('page') or ''} {b.get('title')} {' '.join(a for a in b.get('authors', []) if a)}")
    return text, meta


def segments(text: str) -> list[str]:
    segs: list[str] = []
    for ln in text.split("\n"):
        ln = ln.strip()
        if not ln:
            continue
        segs.extend(s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\[\"'])", ln) if s.strip())
    return segs


@functools.lru_cache(maxsize=4096)
def key_re(k: str) -> re.Pattern:
    """Regex for a claim term. A number also matches its scientific shorthand: 315,000 -> 315 ka, 12,900 -> 12.9 ka,
    66,000,000 -> 66 Ma, and 4.52 billion -> 4.52 Ga."""
    fk = fold(k)
    pats = [re.escape(fk)]
    months = {"january": "jan", "february": "feb", "march": "mar", "april": "apr", "august": "aug", "september": "sept?",
              "october": "oct", "november": "nov", "december": "dec"}
    if fk in months:                                 # Britannica writes "Nov. 3" for "3 November"
        pats.append(months[fk] + r"\.?")
    if re.fullmatch(r"\d+", fk):
        v = int(fk)
        unit_k = r"(?:ka|kyr|kya|ky|kiloyears?|thousand(?: years)?|k)"
        unit_m = r"(?:ma|myr|mya|my|million(?: years)?)"
        if v >= 1000 and v % 1000 == 0:
            pats.append(rf"{v // 1000}\s?{unit_k}")
        elif v >= 1000 and v % 100 == 0:
            pats.append(re.escape(f"{v / 1000:g}") + rf"\s?{unit_k}")
        if v >= 1_000_000 and v % 100_000 == 0:
            pats.append(re.escape(f"{v / 1_000_000:g}") + rf"\s?{unit_m}")
    return re.compile(r"(?<![\w.])(?:" + "|".join(pats) + r")(?![\w])")


def count_hits(keys: list[tuple[str, str]], text_folded: str) -> dict[str, int]:
    return {k: len(key_re(k).findall(text_folded)) for _, k in keys}


def snippet(seg: str, keys: list[tuple[str, str]], width: int) -> str:
    seg = re.sub(r"\s+", " ", seg)
    if len(seg) <= width:
        return seg
    fs_ = fold(seg)
    pos = min((mm.start() for _, k in keys for mm in [key_re(k).search(fs_)] if mm), default=0)
    start = max(0, pos - width // 3)
    return ("..." if start else "") + seg[start:start + width] + ("..." if start + width < len(seg) else "")


def citing_checks(title: str) -> tuple[list[tuple[str, str]], list[str]]:
    checks, listed = [], []
    for p in iter_notes():
        fm, _ = parse_note(p)
        if fm.get("type") == "source":
            continue
        cited = False
        for x in fm.get("fact_checks") or []:
            m = re.search(r"\[([^\]]+)\]\s*$", str(x))
            if m and title in [s.strip() for s in m.group(1).split(";")]:
                checks.append((p.stem, str(x)))
                cited = True
        if not cited and any(f"[[{title}]]" in str(s) for s in (fm.get("sources") or [])):
            listed.append(p.stem)
    return checks, listed


def cmd_claims(args) -> int:
    notes = source_notes()
    title = args.title
    if title not in notes:
        print(f"no source note titled {title!r}")
        return 2
    slug = pick_slug(title)
    if not cache_paths(slug)[1].exists() or not cache_paths(slug)[0].exists():
        print(f"nothing cached for {title!r}; run: fetch {title!r}")
        return 2
    text, meta = load_matchable(slug)
    tf = fold(text)
    segs = segments(text)
    sfold = [fold(s) for s in segs]
    print(f"== {title}  [{meta.get('level')} via {meta.get('route')}, {meta['chars']:,} chars, retrieved {meta['retrieved']}"
          + (f", snapshot {meta['snapshot']}" if meta.get("snapshot") else "") + (f", revid {meta['revid']}" if meta.get("revid") else "") + "]")
    checks, listed = citing_checks(title)
    fm, body = notes[title][1], notes[title][2]
    used = re.search(r"## What It Is Used For\s*(.*?)(?=\n## |\Z)", body, re.S)
    items = [("source note, What It Is Used For", used.group(1).strip() + f" [{title}]")] if used else []
    items += checks
    if not items:
        print("  (no fact_checks cite this source)")
    n_missing = 0
    for note, claim in items:
        core = re.sub(r"^\d{4}-\d{2}-\d{2}:\s*", "", claim)
        core = re.sub(r"\s*\[[^\]]+\]\s*$", "", core)
        print(f"\n[{note}] {core}")
        for atom in [a.strip() for a in re.split(r";|(?<=\.)\s+(?=[A-Z])", core) if a.strip()]:
            keys = claim_keys(atom)
            if not keys:
                if not args.missing_only:
                    print(f"  - {atom[:110]}: (no numbers or names to match; read the source)")
                continue
            hits = count_hits(keys, tf)
            missing = [k for _, k in keys if hits[k] == 0]
            n_missing += bool(missing)
            if args.missing_only and not missing:
                continue
            found = ", ".join(f"{k}({hits[k]})" for _, k in keys if hits[k])
            print(f"  - {atom[:150]}")
            print(f"      found: {found or '-'}   MISSING: {', '.join(missing) or '-'}")
            scored = sorted(((sum(1 for _, k in keys if hits[k] and key_re(k).search(sf)), i) for i, sf in enumerate(sfold)), reverse=True)
            for sc, i in scored[: args.top]:
                if sc:
                    print(f"      > {snippet(segs[i], keys, args.width)}")
    if listed:
        print(f"\nNotes that list this source but have no fact_check citing it: {', '.join(listed)}")
    print(f"\n{n_missing} claim part(s) with at least one term not found in the text.")
    return 0


def cmd_grep(args) -> int:
    slug = pick_slug(args.title)
    if not cache_paths(slug)[0].exists():
        print(f"nothing cached for {args.title!r}")
        return 2
    text, meta = load_matchable(slug)
    pat = re.compile(re.escape(fold(args.text)) if not args.regex else args.text, re.I)
    n = 0
    for seg in segments(text):
        if pat.search(fold(seg)):
            n += 1
            print(f"> {snippet(seg, [('x', args.text)], args.width)}")
    print(f"{n} matching segment(s) in {meta.get('level')} text ({meta.get('route')}).")
    return 0 if n else 1


# ------------------------------------------------------------------------------------------------------ queue

def tier_of(title: str, fm: dict) -> int:
    url = fm.get("url") or ""
    host = urlparse(url).netloc.lower().removeprefix("www.")
    if title in TIER1:
        return 1
    if "(Search Summaries)" in title or fm.get("source_kind") == "book" or not url:
        return 6
    if any(host.endswith(h) for h in JOURNAL_HOSTS) or (fm.get("source_kind") in ("paper", "journal") and DOI_RE.search(url)):
        return 2
    if host.endswith("britannica.com"):
        return 3
    if host.endswith("wikipedia.org"):
        return 4
    return 5


def load_queue() -> dict:
    try:
        return json.loads(QUEUE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_queue(q: dict) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    QUEUE.write_text(json.dumps(q, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def update_queue_entry(title: str | None, meta: dict) -> None:
    q = load_queue()
    if title and title in q:
        e = q[title]
        e["route"], e["level"], e["fetched"] = meta.get("route"), meta.get("level"), meta["retrieved"]
        if e["status"] == "pending":
            e["status"] = "fetched" if meta.get("level") else "blocked"
        save_queue(q)


def cmd_checks(args) -> int:
    """Match every fact_check that cites a source in scope against ALL of its cached cited sources together."""
    q = load_queue()
    cache: dict[str, tuple | None] = {}

    def load(title: str):
        if title not in cache:
            slug = pick_slug(title)
            if cache_paths(slug)[0].exists() and cache_paths(slug)[1].exists():
                text, meta = load_matchable(slug)
                segs = segments(text)
                cache[title] = (fold(text), segs, [fold(s) for s in segs], meta.get("level"))
            else:
                cache[title] = None
        return cache[title]

    n_checks = n_bad = 0
    for p in iter_notes():
        fm, _ = parse_note(p)
        if fm.get("type") == "source":
            continue
        for x in fm.get("fact_checks") or []:
            m = re.search(r"\[([^\]]+)\]\s*$", str(x))
            if not m:
                continue
            srcs = [s.strip() for s in m.group(1).split(";")]
            if args.source and args.source not in srcs:
                continue
            if args.tier is not None and not any(q.get(s, {}).get("tier") == args.tier for s in srcs):
                continue
            n_checks += 1
            got = [(i, s, load(s)) for i, s in enumerate(srcs, 1)]
            have = [(i, s, c) for i, s, c in got if c]
            pending = [f"{i}={s}" for i, s, c in got if not c]
            if args.complete_only and pending:
                continue
            core = re.sub(r"\s*\[[^\]]+\]\s*$", "", re.sub(r"^\d{4}-\d{2}-\d{2}:\s*", "", str(x)))
            lines, bad = [], False
            for atom in [a.strip() for a in re.split(r";|(?<=\.)\s+(?=[A-Z])", core) if a.strip()]:
                keys = claim_keys(atom)
                if not keys:
                    continue
                per = {i: count_hits(keys, c[0]) for i, _, c in have}
                missing = [k for _, k in keys if not any(per[i][k] for i in per)]
                bad |= bool(missing)
                if args.missing_only and not missing:
                    continue
                found = ", ".join(f"{k}[{''.join(str(i) for i in per if per[i][k])}]" for _, k in keys if any(per[i][k] for i in per))
                lines.append(f"  - {atom[:150]}\n      found: {found or '-'}   MISSING: {', '.join(missing) or '-'}")
                best = []
                for i, _, c in have:
                    for sc, j in sorted(((sum(1 for _, k in keys if per[i][k] and key_re(k).search(sf)), j) for j, sf in enumerate(c[2])), reverse=True)[: args.top]:
                        if sc:
                            best.append((sc, i, c[1][j]))
                for sc, i, seg in sorted(best, key=lambda b: -b[0])[: args.top]:
                    lines.append(f"      > [{i}] {snippet(seg, keys, args.width)}")
            n_bad += bad
            if lines or not args.missing_only:
                levels = ", ".join(f"{i}={c[3]}" for i, _, c in have)
                print(f"\n[{p.stem}] {core[:230]}\n  cites: {'; '.join(f'{i}={s}' for i, s in enumerate(srcs, 1))}   read: {levels or 'none'}"
                      + (f"   NOT CACHED: {', '.join(pending)}" if pending else ""))
                print("\n".join(lines))
    print(f"\n{n_checks} check(s) in scope; {n_bad} with at least one term missing from every cached cited source.")
    return 0


def cmd_relevel(args) -> int:
    """Recompute the level of cached direct and Wayback copies with the current full-text test."""
    q = load_queue()
    changed = 0
    for mp in sorted(CACHE.glob("*.meta.json")):
        m = json.loads(mp.read_text(encoding="utf-8"))
        tp = mp.with_name(mp.name.replace(".meta.json", ".txt"))
        if m.get("route") not in ("direct", "wayback") or not m.get("level") or not tp.exists():
            continue
        text = tp.read_text(encoding="utf-8")
        paper = (m.get("identified") or {}).get("kind") == "paper"
        full = "full-text" if m["route"] == "direct" else "archived-copy"
        new = (full if looks_like_fulltext(text) else "abstract") if paper else ("abstract" if is_paywalled(text) else full)
        if new != m["level"]:
            print(f"{m['level']:>13} -> {new:<13} {m.get('title') or m['slug']}")
            m["level"] = new
            mp.write_text(json.dumps(m, indent=1, ensure_ascii=False), encoding="utf-8")
            if m.get("title") in q:
                q[m["title"]]["level"] = new
            changed += 1
    save_queue(q)
    print(f"{changed} cached source(s) re-levelled.")
    return 0


def cmd_queue(args) -> int:
    q = load_queue()
    if args.action == "build":
        notes = source_notes()
        for title, (p, fm, body) in notes.items():
            e = q.get(title, {"status": "pending", "route": None, "level": None, "discrepancies": []})
            e.update(tier=tier_of(title, fm), url=fm.get("url") or "", kind=fm.get("source_kind"),
                     verified=fm.get("verified"), access=fm.get("access"))
            q[title] = e
        for gone in [t for t in q if t not in notes]:
            del q[gone]
        save_queue(q)
        print(f"queue built: {len(q)} sources -> {QUEUE}")
        args.action = "status"
    if args.action == "status":
        tiers = sorted({e["tier"] for e in q.values()})
        stat = sorted({e["status"] for e in q.values()})
        print(f"{'tier':>5} " + " ".join(f"{s:>8}" for s in stat) + "   total")
        for t in tiers:
            row = [sum(1 for e in q.values() if e["tier"] == t and e["status"] == s) for s in stat]
            print(f"{t:>5} " + " ".join(f"{n:>8}" for n in row) + f"   {sum(row)}")
        return 0
    if args.action == "next":
        rows = [(t, e) for t, e in sorted(q.items()) if e["status"] in ("pending", "fetched") and (args.tier is None or e["tier"] == args.tier)]
        for t, e in rows[: args.n]:
            print(f"[tier {e['tier']}] {e['status']:8} {t}\n           {e['url']}")
        print(f"{len(rows)} not yet done in scope.")
        return 0
    if args.action == "mark":
        if args.title not in q:
            print("unknown source title")
            return 2
        q[args.title]["status"] = args.status
        if args.note:
            q[args.title].setdefault("discrepancies", []).append(args.note)
        save_queue(q)
        print(f"{args.title}: {args.status}")
        return 0
    return 2


def cmd_batch(args) -> int:
    q = load_queue()
    if not q:
        print("queue is empty; run: queue build")
        return 2
    http = Http(load_email())
    todo = [(t, e) for t, e in sorted(q.items()) if e["status"] == "pending" and e["tier"] == args.tier and e["url"]][: args.n]
    for title, e in todo:
        meta = do_fetch(http, title, e["url"], pick_slug(title), args.force)
        report(meta, preview=140)
        print()
    return 0


def cmd_fetch(args) -> int:
    http = Http(load_email())
    if args.url:
        title, url, slug = None, args.url, args.slug or slugify(urlparse(args.url).netloc + urlparse(args.url).path)
    else:
        notes = source_notes()
        if args.title not in notes:
            print(f"no source note titled {args.title!r}")
            return 2
        title, url = args.title, (notes[args.title][1].get("url") or "")
        slug = pick_slug(title)
        if not url:
            print("source note has no url")
            return 2
    meta = do_fetch(http, title, url, slug, args.force)
    report(meta)
    return 0 if meta.get("level") else 1


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("title", nargs="?")
    f.add_argument("--url")
    f.add_argument("--slug")
    f.add_argument("--force", action="store_true")
    c = sub.add_parser("claims")
    c.add_argument("title")
    c.add_argument("--missing-only", action="store_true")
    c.add_argument("--top", type=int, default=2)
    c.add_argument("--width", type=int, default=240)
    g = sub.add_parser("grep")
    g.add_argument("title")
    g.add_argument("text")
    g.add_argument("--regex", action="store_true")
    g.add_argument("--width", type=int, default=240)
    b = sub.add_parser("batch")
    b.add_argument("--tier", type=int, required=True)
    b.add_argument("-n", type=int, default=10)
    b.add_argument("--force", action="store_true")
    sub.add_parser("relevel")
    bp = sub.add_parser("biblio")
    bp.add_argument("--force", action="store_true")
    ch = sub.add_parser("checks")
    ch.add_argument("--tier", type=int)
    ch.add_argument("--source")
    ch.add_argument("--missing-only", action="store_true")
    ch.add_argument("--complete-only", action="store_true", help="only checks whose cited sources are all cached")
    ch.add_argument("--top", type=int, default=1)
    ch.add_argument("--width", type=int, default=170)
    qp = sub.add_parser("queue")
    qp.add_argument("action", choices=["build", "status", "next", "mark"])
    qp.add_argument("title", nargs="?")
    qp.add_argument("status", nargs="?", choices=["pending", "fetched", "done", "blocked"])
    qp.add_argument("--tier", type=int)
    qp.add_argument("-n", type=int, default=10)
    qp.add_argument("--note")
    args = ap.parse_args()
    if args.cmd == "fetch" and not (args.title or args.url):
        ap.error("fetch needs a source title or --url")
    return {"fetch": cmd_fetch, "claims": cmd_claims, "grep": cmd_grep, "batch": cmd_batch, "checks": cmd_checks, "relevel": cmd_relevel, "biblio": cmd_biblio,
            "queue": cmd_queue}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
