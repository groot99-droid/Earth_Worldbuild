"""Build the mechanical part of the Tier 2 patch (access fields + Caveats) from the fetch metadata.

Usage: python t2_build.py TIER [--print]   -> writes tier<N>_auto.json with source_updates
Manual additions live in tier<N>_manual.json: {"<source title>": {"extra": "...", "used": "...", "citation": "...",
"replace": [...], "access_override": {...}, "skip": true, "cut_note": "..."}} and are merged in (extra is appended to the Caveats).
A citation that contains " Also ..." is cut back to the text before it (or to the manual "citation"), and the cut part (or "cut_note")
is recorded in the Caveats as pages not read.
"""
import json, re, sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import _paths
import fetch_source as fs

WORK = _paths.WORK
WORK.mkdir(parents=True, exist_ok=True)
SP = WORK
tier = int(sys.argv[1])
manual_p = SP / f"tier{tier}_manual.json"
manual = json.loads(manual_p.read_text(encoding="utf-8")) if manual_p.exists() else {}
q = fs.load_queue()
notes = fs.source_notes()

BOILER = re.compile(r"search[- ]result|web search|not (necessarily )?read in full|was not opened|was not read|not opened|"
                    r"re-verify before citing|consulted (only )?(via|through)|a direct fetch|fetch of the|returned http 403|page returned", re.I)


def snap_date(s):
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if s and len(s) >= 8 else "an unrecorded date"


def sentences(text):
    text = text.replace('et al.', 'et al')
    return [s.strip().replace('', '.') for s in re.split(r"(?<=[.!?])\s+(?=[A-Z'(])", text.strip()) if s.strip()]


def build(title, meta):
    lvl, route, read_on = meta["level"], meta["route"], meta["retrieved"]
    chars = f"{meta['chars']:,}"
    host = urlparse(meta.get("requested_url", "")).netloc.removeprefix("www.")
    tried = [t.split(":")[0] for t in meta.get("route_trace", []) if t.endswith("none")]
    seen403 = sorted({a["host"] for a in meta.get("attempts", []) if a.get("status") == 403})
    b403 = f" ({', '.join(seen403)} answered HTTP 403 to automated requests)" if seen403 else ""
    if route == "europepmc-fulltext":
        pm = meta.get("x_pmcid")
        lic = meta.get("x_licence")
        ar = f"Europe PMC full-text XML of the open-access copy ({pm}{', ' + lic if lic else ''})"
        cav = f"Read in full on {read_on} from the Europe PMC full-text XML of the open-access copy ({pm}; {chars} characters)."
    elif route.startswith("openalex-oa-pdf"):
        h = route.split("(")[1].rstrip(")")
        ver = meta.get("x_oa_version") or "repository"
        ar = f"open-access PDF from {h} ({ver} version)"
        cav = (f"Read in full on {read_on} from the open-access PDF at {h} ({ver} version, {chars} characters), so wording, figures "
               f"or pagination may differ slightly from the published version.")
    elif route == "wayback":
        ar = f"Wayback Machine snapshot of {snap_date(meta.get('snapshot'))}"
        full = "in full " if lvl == "archived-copy" else ""
        cav = (f"Read {full}on {read_on} as raw text from a Wayback Machine snapshot dated {snap_date(meta.get('snapshot'))} of {host}"
               f"{b403}; the snapshot may differ from the current page ({chars} characters).")
        if lvl == "abstract":
            cav += " Only the abstract-level text on the page was available."
    elif route == "direct":
        ar = "the publisher page, fetched directly"
        cav = f"Read {'in full ' if lvl == 'full-text' else ''}on {read_on} from {host} fetched directly ({chars} characters)."
    elif route == "wikipedia-api":
        rid = meta.get("revid")
        ar = f"MediaWiki API raw wikitext, revision {rid}" if rid else "MediaWiki API raw wikitext"
        cav = (f"Read in full on {read_on} as raw wikitext from the MediaWiki API, revision {rid} ({chars} characters converted from wikitext markup). "
               f"Wikipedia is not authoritative and this revision may have since been edited.")
    elif route == "pubmed-abstract":
        pid = meta.get("x_pmid")
        ar = f"PubMed abstract (PMID {pid}) through NCBI E-utilities"
        cav = (f"Only the abstract was read (the PubMed record, fetched on {read_on}). The full text was not reachable by any route that works "
               f"for automated requests: routes tried without success were {', '.join(tried) or 'none'}{b403}, and no CAPTCHA, cookie wall or "
               f"paywall was bypassed. This source therefore confirms only what the abstract states.")
    elif route == "openalex-abstract":
        ar = "OpenAlex abstract record"
        cav = (f"Only the abstract was read (OpenAlex record, fetched on {read_on}). Routes tried without success: {', '.join(tried) or 'none'}{b403}. "
               f"This source confirms only what the abstract states.")
    elif route == "crossref":
        ar = "Crossref metadata record"
        cav = f"Only bibliographic metadata was read (Crossref, {read_on}); no abstract or full text was reachable. Routes tried without success: {', '.join(tried)}{b403}."
    else:
        ar, cav = route, f"Read on {read_on} via {route}."
    if meta.get("x_supplement_url"):
        cav += f" The repository copy of the supplementary materials ({meta['x_supplement_chars']:,} characters) was also read."
    return ar, cav


out, review = [], []
for t, e in sorted(q.items()):
    if e["tier"] != tier:
        continue
    m = manual.get(t, {})
    if m.get("skip"):
        continue
    if m.get("blocked"):
        oldc = re.search(r"## Caveats\s*(.*)", notes[t][2], re.S).group(1).strip()
        cav = m["blocked"] + " " + " ".join(s for s in sentences(oldc) if not BOILER.search(s))
        out.append({"title": t, "set": {"access": "summary-only", "access_route": "none: no readable copy could be obtained"},
                    "caveats": cav.strip() + " The only text seen earlier was search-result summaries.", "mark": "blocked"})
        review.append(f"{t}\n   [summary-only] blocked\n   CAVEATS: {out[-1]['caveats']}")
        continue
    slug = fs.pick_slug(t)
    mp = fs.cache_paths(slug)[1]
    if not mp.exists():
        review.append(f"NOT FETCHED: {t}")
        continue
    meta = json.loads(mp.read_text(encoding="utf-8"))
    if not meta.get("level"):
        review.append(f"FAILED (no text): {t}  {meta.get('route_trace')}")
        continue
    ar, cav = build(t, meta)
    old = re.search(r"## Caveats\s*(.*)", notes[t][2], re.S).group(1).strip()
    keep = [] if m.get("drop_old") else [s for s in sentences(old) if not BOILER.search(s)]
    # A citation that bundles other pages ("... Also Wikipedia, 'X'.") is cut back to the page actually read; the cut-off part
    # is recorded in the Caveats so nothing looks confirmed by this source that it does not contain.
    cit_old = str(notes[t][1].get("citation") or "")
    cit_new, dropped = m.get("citation"), None
    if cit_new is None and " Also " in cit_old:
        cit_new, dropped = cit_old.split(" Also ", 1)[0].strip(), cit_old.split(" Also ", 1)[1].strip()
    elif cit_new is not None and cit_new != cit_old and m.get("cut_note"):
        dropped = m["cut_note"]
    cut = [f"The earlier citation also named: {dropped} Those pages were not read here, so nothing taken from them is confirmed by this source."] if dropped else []
    caveats = " ".join([cav] + ([m["extra"]] if m.get("extra") else []) + cut + keep).strip()
    if meta["level"] == "abstract":
        caveats += " An abstract-only source never moves a note toward reviewed."
    upd = {"title": t, "set": {"access": meta["level"] if meta["level"] != "metadata" else "abstract",
                               "access_route": ar, "read_on": meta["retrieved"], "checked_on": meta["retrieved"]},
           "caveats": caveats, "mark": "done"}
    upd["set"].update(m.get("access_override", {}))
    if cit_new is not None and cit_new != cit_old:
        upd["citation"] = cit_new
    for k in ("used", "replace"):
        if k in m:
            upd[k] = m[k]
    out.append(upd)
    review.append(f"{t}\n   [{upd['set']['access']}] {ar}\n   CAVEATS: {caveats}" + (f"\n   (kept old sentences: {keep})" if keep else ""))
(SP / f"tier{tier}_auto.json").write_text(json.dumps({"date": date.today().isoformat(), "source_updates": out}, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"{len(out)} source updates built")
if "--print" in sys.argv:
    print("\n".join(review))
