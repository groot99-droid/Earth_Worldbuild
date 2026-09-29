#!/usr/bin/env python3
"""Download the third-party 3D models listed in assets/models.json into assets/models/<id>/.

Sources:
  smithsonian  Voyager packages on 3d-api.si.edu (CC0). The package's document.json lists
               derivatives; we take the Web3D derivative of the requested quality (Thumb ≈ 200 KB,
               Low ≈ 1 MB, Medium ≈ 2 MB; all Draco-compressed GLBs) plus the thumbnail image.
  polyhaven    api.polyhaven.com (CC0): the glTF at the requested resolution plus its .bin and
               textures, relative paths preserved so GLTFLoader resolves them.
  local        a file dropped in by hand (e.g. a Scan the World scan converted to GLB); only
               validated.

For every model the script records file, bytes and the model's bounding box in metres (from
the GLB's POSITION accessor min/max, or the Voyager scene's boundingBox + units) so the viewer
can scale it to `target_h` exactly. It also rewrites the Models section of assets/CREDITS.md.

Usage: fetch_models.py [--check] [--force] [id ...]
"""
from __future__ import annotations

import json
import os
import re
import ssl
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

MUSEUM = Path(__file__).resolve().parent
ASSETS = MUSEUM / "assets"
MODELS_JSON = ASSETS / "models.json"
MODELS_DIR = ASSETS / "models"
CREDITS = ASSETS / "CREDITS.md"
UA = "ChronicleMuseum/1.0 (https://github.com/groot99-droid/Earth_Worldbuild; groot99@icloud.com)"
SI_DOC = "https://3d-api.si.edu/content/document/{package}/document.json"
SI_FILE = "https://3d-api.si.edu/content/document/{package}/{uri}"
PH_FILES = "https://api.polyhaven.com/files/{asset}"

_ctx = None


def ctx():
    global _ctx
    if _ctx is None:
        cafile = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
        _ctx = ssl.create_default_context(cafile=cafile) if cafile else ssl.create_default_context()
    return _ctx


def fetch(url: str, dest: Path | None = None, retries: int = 3) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=120, context=ctx()) as r:
                data = r.read()
            if dest is not None:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
            return data
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt >= retries:
                raise
            print(f"  retry {attempt + 1} after {e}", file=sys.stderr)
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("unreachable")


# ---------------------------------------------------------------- glb inspection -----
def glb_json(data: bytes) -> dict:
    magic, version, length = struct.unpack("<III", data[:12])
    if magic != 0x46546C67:
        raise ValueError("not a GLB")
    clen, ctype = struct.unpack("<II", data[12:20])
    return json.loads(data[20:20 + clen])


def _node_world_scale(nodes: list, idx: int, parents: dict) -> list[float]:
    s = [1.0, 1.0, 1.0]
    i = idx
    seen = 0
    while i is not None and seen < 64:
        n = nodes[i]
        if "scale" in n:
            s = [a * b for a, b in zip(s, n["scale"])]
        if "matrix" in n:
            m = n["matrix"]
            s = [s[0] * (m[0] ** 2 + m[1] ** 2 + m[2] ** 2) ** 0.5, s[1] * (m[4] ** 2 + m[5] ** 2 + m[6] ** 2) ** 0.5,
                 s[2] * (m[8] ** 2 + m[9] ** 2 + m[10] ** 2) ** 0.5]
        i = parents.get(i)
        seen += 1
    return s


def glb_bbox(j: dict):
    """Axis-aligned bounds (min, max) over all mesh instances from POSITION accessor min/max, scaled by node scales."""
    nodes = j.get("nodes", [])
    parents = {}
    for pi, n in enumerate(nodes):
        for c in n.get("children", []):
            parents[c] = pi
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    found = False
    for ni, n in enumerate(nodes):
        if "mesh" not in n:
            continue
        sc = _node_world_scale(nodes, ni, parents)
        for prim in j["meshes"][n["mesh"]].get("primitives", []):
            acc = j["accessors"][prim["attributes"]["POSITION"]]
            if "min" not in acc or "max" not in acc:
                continue
            found = True
            for k in range(3):
                lo[k] = min(lo[k], acc["min"][k] * sc[k], acc["max"][k] * sc[k])
                hi[k] = max(hi[k], acc["min"][k] * sc[k], acc["max"][k] * sc[k])
    return (lo, hi) if found else None


UNIT_M = {"mm": 0.001, "cm": 0.01, "m": 1.0, "in": 0.0254, "ft": 0.3048, "km": 1000.0}


# ---------------------------------------------------------------- sources ------------
def si_url(package: str, uri: str) -> str:
    """Voyager asset URIs are relative to the package, or (newer packages) absolute CDN URLs."""
    if uri.startswith("http://") or uri.startswith("https://"):
        return uri
    return SI_FILE.format(package=package, uri=urllib.parse.quote(uri))


def fetch_smithsonian(mid: str, rec: dict, out: Path, force: bool) -> dict:
    doc = json.loads(fetch(SI_DOC.format(package=rec["package"])).decode("utf-8"))
    quality = rec.get("quality", "Low")
    model = doc["models"][0]
    chosen = None
    for dv in model.get("derivatives", []):
        if dv.get("usage") != "Web3D" or dv.get("quality") != quality:
            continue
        for a in dv.get("assets", []):
            if a.get("type") == "Model":
                chosen = a
    if not chosen:
        raise RuntimeError(f"{mid}: no Web3D/{quality} derivative in {rec['package']}")
    thumb = None
    for dv in model.get("derivatives", []):
        if dv.get("usage") == "Image2D" and dv.get("quality") == "Low":
            for a in dv.get("assets", []):
                thumb = a.get("uri")
    dest = out / "model.glb"
    if force or not dest.exists() or dest.stat().st_size != chosen.get("byteSize", -1):
        print(f"  {mid}: downloading {chosen['uri']} ({chosen.get('byteSize', '?')} B)")
        data = fetch(si_url(rec["package"], chosen["uri"]), dest)
    else:
        data = dest.read_bytes()
    if thumb and (force or not (out / "preview.jpg").exists()):
        try:
            fetch(si_url(rec["package"], thumb), out / "preview.jpg")
        except Exception as e:  # noqa: BLE001
            print(f"  {mid}: preview failed: {e}", file=sys.stderr)
    j = glb_json(data)
    units = model.get("units", "m")
    k = UNIT_M.get(units, 1.0)
    bb = glb_bbox(j)
    if bb:
        lo, hi = bb
        bbox = [round((hi[i] - lo[i]) * k, 4) for i in range(3)]
        base = [round(lo[i] * k, 4) for i in range(3)]
    else:
        b = model.get("boundingBox", {})
        bbox = [round((b["max"][i] - b["min"][i]) * k, 4) for i in range(3)]
        base = [round(b["min"][i] * k, 4) for i in range(3)]
    # Voyager stores the scene's model transform separately (rotation/translation on the model
    # record); the GLB itself is usually y-up but scans can lie on a side. Record both so the
    # viewer can re-measure after applying the same rotation.
    return {"file": "model.glb", "bytes": len(data), "units": units, "bbox_m": bbox, "bbox_min_m": base,
            "voyager_rotation": model.get("rotation"), "draco": "KHR_draco_mesh_compression" in (j.get("extensionsRequired") or []),
            "faces": chosen.get("numFaces"), "image_size": chosen.get("imageSize"), "preview": "preview.jpg" if thumb else None}


def fetch_polyhaven(mid: str, rec: dict, out: Path, force: bool) -> dict:
    files = json.loads(fetch(PH_FILES.format(asset=rec["asset"])).decode("utf-8"))
    res = rec.get("res", "1k")
    g = files["gltf"][res]["gltf"]
    main = out / Path(urllib.parse.urlparse(g["url"]).path).name
    total = 0
    if force or not main.exists():
        print(f"  {mid}: downloading {main.name} + {len(g.get('include', {}))} files")
        data = fetch(g["url"], main)
    else:
        data = main.read_bytes()
    total += len(data)
    for rel, inc in (g.get("include") or {}).items():
        dest = out / rel
        if force or not dest.exists():
            fetch(inc["url"], dest)
        total += dest.stat().st_size
    j = json.loads(data.decode("utf-8"))
    bb = glb_bbox(j)
    lo, hi = bb if bb else ([0, 0, 0], [0, 0, 0])
    return {"file": main.name, "bytes": total, "units": "m", "bbox_m": [round(hi[i] - lo[i], 4) for i in range(3)],
            "bbox_min_m": [round(v, 4) for v in lo], "draco": False}


def check_local(mid: str, rec: dict, out: Path) -> dict:
    f = out / rec.get("file", "model.glb")
    if not f.exists():
        raise RuntimeError(f"{mid}: local file {f} missing")
    data = f.read_bytes()
    info = {"file": f.name, "bytes": len(data), "units": rec.get("units", "m")}
    if f.suffix.lower() == ".glb":
        j = glb_json(data)
        bb = glb_bbox(j)
        if bb:
            lo, hi = bb
            k = UNIT_M.get(info["units"], 1.0)
            info["bbox_m"] = [round((hi[i] - lo[i]) * k, 4) for i in range(3)]
            info["bbox_min_m"] = [round(lo[i] * k, 4) for i in range(3)]
        info["draco"] = "KHR_draco_mesh_compression" in (j.get("extensionsRequired") or [])
    return info


# ---------------------------------------------------------------- credits ------------
def write_credits(models: dict) -> None:
    lines = ["## Models", "",
             "Third-party 3D models placed in the museum (fetched by `_Museum/fetch_models.py` from `assets/models.json`).", "",
             "| id | title | maker / date | museum / source | licence | file |", "|---|---|---|---|---|---|"]
    for mid, r in sorted(models.items()):
        maker = " · ".join(x for x in [r.get("artist"), r.get("date")] if x)
        lines.append(f"| `{mid}` | [{r.get('title', mid)}]({r.get('url', '')}) | {maker} | {r.get('museum', r.get('source'))} | {r.get('license', '?')} | `{r.get('file', '?')}` ({(r.get('bytes') or 0) // 1024} KB) |")
    lines += ["", "Smithsonian models are CC0 releases of the Smithsonian Open Access programme (3d.si.edu); "
              "Poly Haven assets are CC0 (polyhaven.com). Local drop-ins (Scan the World, CC BY-NC 4.0) carry their own credit line.", ""]
    block = "\n".join(lines)
    text = CREDITS.read_text(encoding="utf-8") if CREDITS.exists() else "# Asset credits\n\n"
    if "## Models" in text:
        text = re.sub(r"## Models.*?(?=\n## |\Z)", block, text, flags=re.S)
    else:
        text = text.rstrip() + "\n\n" + block
    CREDITS.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------- main ---------------
def main(argv: list[str]) -> int:
    check = "--check" in argv
    force = "--force" in argv
    only = {a for a in argv if not a.startswith("--")}
    doc = json.loads(MODELS_JSON.read_text(encoding="utf-8"))
    models = doc["models"]
    budget = (doc.get("budget_mb") or 40) * 1024 * 1024
    failures = []
    for mid, rec in models.items():
        if only and mid not in only:
            continue
        out = MODELS_DIR / mid
        try:
            if check:
                f = out / rec.get("file", "model.glb")
                if not f.exists():
                    failures.append(f"{mid}: {f} missing")
                continue
            if rec["source"] == "smithsonian":
                info = fetch_smithsonian(mid, rec, out, force)
            elif rec["source"] == "polyhaven":
                info = fetch_polyhaven(mid, rec, out, force)
            elif rec["source"] == "local":
                info = check_local(mid, rec, out)
            else:
                raise RuntimeError(f"{mid}: unknown source {rec['source']}")
            rec.update(info)
            h = info.get("bbox_m", [0, 0, 0])
            print(f"  {mid:28s} {info['bytes'] / 1024:7.0f} KB  bbox {h}  target_h {rec.get('target_h')}")
        except Exception as e:  # noqa: BLE001
            failures.append(f"{mid}: {e}")
            print(f"  ! {mid}: {e}", file=sys.stderr)
    total = sum((r.get("bytes") or 0) for r in models.values())
    print(f"total {total / 1024 / 1024:.1f} MB of {budget / 1024 / 1024:.0f} MB budget")
    if total > budget:
        failures.append(f"model budget exceeded: {total / 1024 / 1024:.1f} MB")
    if not check:
        MODELS_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
        write_credits(models)
    if failures:
        print("FAILURES:\n  " + "\n  ".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
