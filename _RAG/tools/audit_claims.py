"""Claim-coverage audit: how many claim-bearing '## Facts' bullets are not covered by a fact_check.

A bullet is claim-bearing if it has a number of 3+ digits or at least two capitalised names. It counts as covered
when every such number, and at least half of such names, appear somewhere in the note's fact_checks line.

Usage:  python _RAG/tools/audit_claims.py [--root DIR] [--out uncovered.json] [--top 20]
Use --root to audit a copy of the vault, for a before/after comparison.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path

RAG = Path(__file__).resolve().parent.parent
STOP = set("The This That These Those With From After Before During Into Under Over About Also Some Many Most Other Its "
           "Their There When Where While Which Such Both Each Later Early Modern Old New First Second Third Today".split())
NUMTOK = re.compile(r"\d[\d,\.]*\d|\d")
HARM = re.compile(r"death toll|died|killed|casualt|famine|massacre|genocide|population|enslaved|epidemic|plague|contested|"
                  r"debated|estimate|million|billion|percent|%", re.I)


def norm(s: str) -> str:
    return s.replace(",", "").lower()


def tokens(b: str) -> tuple[set[str], set[str]]:
    nums = {norm(n) for n in NUMTOK.findall(b) if len(n.replace(",", "")) >= 3}
    caps = {w.lower() for w in re.findall(r"\b[A-Z][a-zA-ZÀ-ſ'-]{3,}\b", b) if w not in STOP}
    return nums, caps


def audit(root: Path) -> list[dict]:
    rows = []
    for d in ("01_Eras", "02_Regions", "03_Entities"):
        for p in (root / d).rglob("*.md"):
            t = p.read_text(encoding="utf-8", errors="replace")
            m = re.match(r"---\r?\n(.*?)\r?\n---\r?\n(.*)", t, re.S)
            if not m:
                continue
            fm, body = m.group(1), m.group(2)
            fcm = re.search(r"^fact_checks:\s*(.*)$", fm, re.M)
            fc = norm(fcm.group(1)) if fcm else ""
            facts = re.search(r"## Facts\r?\n(.*?)(?=\n## )", body, re.S)
            bullets = re.findall(r"^- (.*)$", facts.group(1), re.M) if facts else []
            unc, cov, qual = [], 0, 0
            for b in bullets:
                nums, caps = tokens(b)
                if not nums and len(caps) < 2:
                    qual += 1
                    continue
                ok_nums = all(n in fc for n in nums) if nums else True
                ok_caps = (sum(1 for c in caps if c in fc) >= max(1, len(caps) // 2)) if caps else True
                if ok_nums and ok_caps:
                    cov += 1
                else:
                    unc.append(b)
            risk = sum(3 if HARM.search(b) else 1 for b in unc) + sum(2 for b in unc if NUMTOK.search(b))
            rows.append(dict(name=p.stem, bullets=len(bullets), covered=cov, qualitative=qual, uncovered=unc, risk=risk))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(RAG.parent))
    ap.add_argument("--out")
    ap.add_argument("--top", type=int, default=0)
    args = ap.parse_args()
    rows = audit(Path(args.root))
    tb, tc = sum(r["bullets"] for r in rows), sum(r["covered"] for r in rows)
    tu, tq = sum(len(r["uncovered"]) for r in rows), sum(r["qualitative"] for r in rows)
    need = sorted((r for r in rows if r["uncovered"]), key=lambda r: -r["risk"])
    print(f"{len(rows)} notes; Facts bullets: {tb}; claim-bearing bullets covered: {tc}; UNCOVERED: {tu}; "
          f"qualitative: {tq}; notes with an uncovered bullet: {len(need)}")
    for r in need[: args.top]:
        print(f"  risk={r['risk']:3d} uncovered={len(r['uncovered'])}/{r['bullets']} {r['name']}")
    if args.out:
        Path(args.out).write_text(json.dumps(need, indent=1, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
