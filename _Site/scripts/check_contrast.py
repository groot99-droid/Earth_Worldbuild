#!/usr/bin/env python3
"""WCAG contrast gate for the site's colour tokens (light and dark).

Reads the custom properties from styles.css and checks the text pairs the UI actually uses,
with contrast_ratio() from the ui-design plugin (used read-only; set UI_DESIGN_DIR to override).
Text pairs need 4.5:1, large or bold-display text 3:1. Exit 1 on any failure.

    python check_contrast.py           # report
    python check_contrast.py --fix     # suggest the nearest passing colour for each failing token
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from common import SITE

PLUGIN = Path(os.environ.get("UI_DESIGN_DIR", str(SITE.parent.parent / "Pipelines" / "plugins" / "ui-design")))
sys.path.insert(0, str(PLUGIN / "catalog" / "scripts"))
from contrast import contrast_ratio  # noqa: E402

TYPES = ["era", "event", "person", "place", "culture", "technology", "species", "region", "theme", "observer-note", "source", "timeline"]


def blocks(css: str) -> dict[str, dict[str, str]]:
    """Return {'light': {...}, 'dark': {...}} from :root and the explicit [data-theme="dark"] block."""
    def props(body):
        return {m.group(1): m.group(2).strip() for m in re.finditer(r"--([\w-]+)\s*:\s*(#[0-9a-fA-F]{6})\b", body)}
    root = re.search(r":root\s*\{(.*?)\n\}", css, re.S)
    dark = re.search(r':root\[data-theme="dark"\]\s*\{(.*?)\n\}', css, re.S)
    light = props(root.group(1))
    return {"light": light, "dark": {**light, **props(dark.group(1))}}


def pairs(t: dict[str, str]):
    out = [
        ("text on bg", t["text"], t["bg"], 4.5), ("text on surface", t["text"], t["surface"], 4.5),
        ("muted on bg", t["muted"], t["bg"], 4.5), ("muted on surface", t["muted"], t["surface"], 4.5),
        ("muted on surface-2", t["muted"], t["surface-2"], 4.5),
        ("accent on bg", t["accent"], t["bg"], 4.5), ("accent on surface", t["accent"], t["surface"], 4.5),
        ("text on accent-soft", t["text"], t["accent-soft"], 4.5),
        ("obs label on obs-bg", t["obs-line"], t["obs-bg"], 4.5), ("text on obs-bg", t["text"], t["obs-bg"], 4.5),
        ("text on chip (pressed)", t["bg"], t["text"], 4.5),
    ]
    for ty in TYPES:
        k = f"c-{ty}"
        if k in t:
            out.append((f"{ty} label on surface", t[k], t["surface"], 4.5))
            out.append((f"{ty} label on bg", t[k], t["bg"], 4.5))
    for ty in TYPES:                       # solid type badge: --on-c text on --c-<type>
        k = f"c-{ty}"
        if k in t and "on-c" in t:
            out.append((f"badge text on {ty}", t["on-c"], t[k], 4.5))
            out.append((f"{ty} placeholder glyph on surface-2 (large text)", t[k], t["surface-2"], 3.0))
    out += [
        ("AI badge", t["ai-text"], t["ai-bg"], 4.5), ("text on AI brief", t["text"], t["ai-bg"], 4.5),
        ("danger on surface", t["danger"], t["surface"], 4.5), ("danger on bg", t["danger"], t["bg"], 4.5),
        ("focus ring on bg (non-text)", t["focus"], t["bg"], 3.0), ("focus ring on surface (non-text)", t["focus"], t["surface"], 3.0),
        ("focus ring on surface-2 (non-text)", t["focus"], t["surface-2"], 3.0),
    ]
    return out


def main() -> int:
    css = (SITE / "styles.css").read_text(encoding="utf-8")
    fails = 0
    for mode, t in blocks(css).items():
        for name, fg, bg, need in pairs(t):
            r = contrast_ratio(fg, bg)
            ok = r is not None and r >= need
            if not ok:
                fails += 1
                print(f"FAIL [{mode}] {name}: {fg} on {bg} = {r:.2f}:1 (needs {need}:1)")
    print(f"contrast: {'FAILED' if fails else 'OK'} ({fails} failing pairs)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
