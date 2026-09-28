#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pack_textures.py - Chronicle Museum v2 texture packer (desktop Python + PIL + numpy; NOT Blender).

Run:
    "<M>/../_RAG/.venv/Scripts/python.exe" "<M>/blender/scripts/tools/pack_textures.py" [options]

    --sets parquet,marble      only these sets (default: all four)
    --placeholder              ignore texture_downloads.json, always build procedural placeholders
    --no-preview               skip the 2x2 preview sheets in blender/renders/dev/textures/
    --seed N                   placeholder random seed (default 20260927; same seed -> identical bytes)
    --downloads PATH           alternative downloads json   (default M/assets/texture_downloads.json)
    --out-dir DIR              alternative output folder    (default M/assets/textures)
    --map-json PATH            alternative texture_map.json (default M/assets/texture_map.json)
    --preview-dir DIR          alternative preview folder   (default M/blender/renders/dev/textures)
    --budget-mb F              packed size target, warns above it (default 12)

Outputs per texture set <set> in {parquet, marble, plaster, metal}   (contract V2_CONTRACT.md section 5):
    M/assets/textures/v2_<set>_albedo.jpg   sRGB base colour                        (JPEG q~88, 4:2:0)
    M/assets/textures/v2_<set>_normal.jpg   tangent-space normal, OpenGL (+Y = +V)  (JPEG q~92, 4:4:4, Non-Color)
    M/assets/textures/v2_<set>_orm.jpg      R = AO, G = roughness, B = metalness    (JPEG q~88, 4:4:4, Non-Color)
    M/assets/texture_map.json               set table + placeholder params + last-run provenance + stats +
                                            suggested per-slot glTF factors (see "slots" in that file)
The files are only rewritten when their bytes change (deterministic output -> safe, idempotent re-runs).
The script never writes texture_downloads.json or textures_src/ (orchestrator-owned).

Image orientation: array row 0 = top of the image = V = 1 (glTF/Blender convention). Normal maps are OpenGL style:
green = +V (up in the image). All placeholders are exactly periodic (FFT noise, wrap-around sampling, lattice
patterns sized to divide the tile), so they tile seamlessly at the per-set tile_m world size.

Source priority per set:
  (1) an enabled entry in texture_downloads.json with at least an albedo file that exists, else
  (2) a seamless procedural placeholder (see PLACEHOLDER docs in DEFAULT_SETS below).

----------------------------------------------------------------------------------------------------------------
texture_downloads.json schema (owned by the orchestrator; this script only reads it)
----------------------------------------------------------------------------------------------------------------
{
  "_doc": "free text",
  "sets": {                                   # the "sets" wrapper is optional: {"parquet": {...}} also works
    "parquet": {
      "enabled": true,                        # optional (default true); false -> placeholder
      "source": "ambientCG",                  # informational: ambientCG | polyhaven | other
      "asset": "WoodFloor064",                # informational asset id
      "url": "https://ambientcg.com/view?id=WoodFloor064",   # informational
      "license": "CC0",                       # informational
      "dir": "textures_src/parquet",          # optional; base folder for relative "files" + auto-discovery.
                                              #   Relative paths resolve against M/assets/ (then M/). Absolute ok.
      "files": {                              # explicit channel -> file (relative to "dir" if given, else M/assets/)
        "albedo":       "WoodFloor064_2K-JPG_Color.jpg",   # aliases: color, diffuse, diff, basecolor, base_color
        "normal_gl":    "WoodFloor064_2K-JPG_NormalGL.jpg",# alias: normal.  OpenGL (+Y) normal
        "normal_dx":    "..._NormalDX.jpg",                # DirectX (-Y) normal; green is flipped on load
        "roughness":    "..._Roughness.jpg",               # alias: rough
        "ao":           "..._AmbientOcclusion.jpg",        # alias: ambientocclusion, occlusion
        "metal":        "..._Metalness.jpg",               # aliases: metalness, metallic
        "arm":          "..._arm_2k.jpg",                  # Poly Haven packed R=AO G=rough B=metal (alias: orm);
                                                           #   individual ao/roughness/metal files override it
        "displacement": "..._Displacement.jpg"             # aliases: disp, height; only used to derive a normal
      },                                                   #   when no normal file is given
      "crop": [x0, y0, x1, y1],               # optional crop box, source pixels (or 0..1 fractions);
                                              #   default: centred square crop when the source is not square
      "rotate": 0,                            # optional 0/90/180/270 (counter-clockwise), after the crop
      "albedo_target_linear": [r, g, b],      # optional: rescale linear albedo so its mean equals this; null = keep.
                                              #   Default per set (DEFAULT_SETS[set]["download_albedo_target_linear"]):
                                              #   plaster & metal are normalised to the placeholder means so that
                                              #   baseColorFactor tints behave the same whatever the source.
      "roughness_scale": 1.0,                 # optional: rough = clip(rough*scale + offset)
      "roughness_offset": 0.0,
      "roughness_default": 0.35,              # optional: constant when no roughness/arm file (default: set value)
      "metal_default": 0,                     # optional: constant when no metal/arm file (default: set value)
      "normal_strength": 1.0,                 # optional: scales the normal's XY before renormalising
      "displacement_mm": 2.0,                 # optional: full black->white range of the displacement map (mm)
      "seamless": "check"                     # "check" (default: measure + warn), "blend" (offset-blend the wrap
                                              #   seams of every channel), "off"
    }
  }
}
Auto-discovery: channels missing from "files" are looked up in "dir" by filename pattern (case-insensitive):
  ambientCG  *_Color.* *_NormalGL.* *_NormalDX.* *_Roughness.* *_AmbientOcclusion.* *_Metalness.* *_Displacement.*
  Poly Haven *_diff_*  *_nor_gl_*  *_nor_dx_*  *_rough_*  *_ao_*  *_metal_*  *_arm_*  *_disp_*
Missing channels are synthesised: AO = 1, metal = set default (0, metal set 1), roughness = set default,
normal = from displacement if present else flat. Formats: anything PIL reads (jpg, png incl. 16-bit, tif); not EXR.

texture_map.json: regenerated on every run. Only its per-set "overrides" objects are read back and deep-merged over
DEFAULT_SETS (e.g. {"sets": {"parquet": {"overrides": {"placeholder": {"pattern": "chevron"}}}}}); everything else
in that file is output.
"""
import argparse
import datetime
import io
import json
import math
import os
import sys
import time
import zlib

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.dirname(HERE)
M_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, "..", ".."))
ASSETS_DIR = os.path.join(M_DIR, "assets")
OUT_DIR = os.path.join(ASSETS_DIR, "textures")
DOWNLOADS_JSON = os.path.join(ASSETS_DIR, "texture_downloads.json")
MAP_JSON = os.path.join(ASSETS_DIR, "texture_map.json")
PREVIEW_DIR = os.path.join(M_DIR, "blender", "renders", "dev", "textures")

SQ2 = math.sqrt(2.0)
DEFAULT_SEED = 20260927
SET_ORDER = ["parquet", "marble", "plaster", "metal"]

# ---------------------------------------------------------------------------------------------------------------
# Set table. Colours are sRGB 0..255 unless the key ends in _lin. Lengths in mm unless the key says _m / _px.
# ---------------------------------------------------------------------------------------------------------------
DEFAULT_SETS = {
    "parquet": {
        "res": 2048, "tile_m": 2.0, "metal": 0.0, "roughness": 0.35,
        "jpeg": {"albedo": 88, "normal": 92, "orm": 88},
        "download_albedo_target_linear": None,
        "download_guards": {"roughness_mean_min": "slots_min", "albedo_mean_min_linear": None},
        "placeholder": {
            # Oak parquet. "herringbone" (batons rompus, square ends) or "chevron" (point de Hongrie, 45 deg ends).
            # Both are exactly periodic in the 2 m tile: plank length L = tile/(rows_per_tile*sqrt2) = 0.471 m,
            # width = L/plank_ratio = 78.6 mm. Zig-zag spine runs along texture U ("u") or V ("v").
            "pattern": "herringbone", "spine": "u",
            "rows_per_tile": 3, "plank_ratio": 6,           # herringbone: 3 rows x 18 = 108 planks / tile
            "chevron_cols": 6, "chevron_planks_per_col": 18, "chevron_angle_deg": 45.0,
            "oak_light": [184, 140, 94], "oak_dark": [128, 91, 58], "oak_red": [150, 100, 66],
            "red_frac": 0.06, "tone_sd": 0.055, "quartersawn_frac": 0.35,
            "ring_mm": [1.8, 5.5], "ring_contrast": 0.26, "ring_contrast_qs": 0.12, "streak_contrast": 0.05,
            "broad_streak_contrast": 0.16, "figure_contrast": 0.10, "pore_contrast": 0.16, "fleck_contrast": 0.08, "wear_contrast": 0.05,
            "gap_mm": 0.45, "gap_rgb": [52, 36, 24], "bevel_mm": 1.1, "bevel_depth_mm": 0.45,
            "bevel_dirt": 0.16, "plank_height_sd_mm": 0.08, "cup_mm": 0.06,
            "rough_base": 0.34, "rough_plank_sd": 0.03, "rough_wear": 0.04,
        },
    },
    "marble": {
        "res": 2048, "tile_m": 2.0, "metal": 0.0, "roughness": 0.22,
        "jpeg": {"albedo": 88, "normal": 92, "orm": 88},
        "download_albedo_target_linear": None,
        "download_guards": {"roughness_mean_min": "slots_min", "albedo_mean_min_linear": None},
        "placeholder": {
            # White Carrara-like: warm-white ground, soft grey veils (anisotropic fbm along the main veins) and
            # vein layers of two kinds, all exactly periodic in the tile:
            #  "sine":  classic turbulence marble, phase = 2pi*(k . uv) + sum_i A_i*fbm_i(uv), integer k; amplitudes
            #           fall with frequency so the phase never folds (no closed loops); vein where phase wraps 0.
            #  "cells": crack network = edges of a periodic Worley diagram on domain-warped coordinates.
            # core_px / halo_px are vein half-widths in pixels at the set resolution.
            "base": [236, 234, 229], "vein": [104, 110, 120], "cloud_rgb": [194, 197, 202],
            "cloud": 0.18, "grain": 0.010,
            "veins": [
                {"type": "sine", "k": [2, 1], "turb": [[1.0, 1, 3], [0.30, 3, 10], [0.05, 10, 60]],
                 "core_px": 2.4, "halo_px": 28, "core": 0.52, "halo": 0.26, "width_var": 0.6,
                 "mask": [-1.0, 0.8], "feather": 0.6},
                {"type": "cells", "cells": 4, "warp_px": 110, "warp_f": [1, 6], "fine_px": 3.0,
                 "fine_f": [20, 120], "core_px": 1.2, "halo_px": 9, "core": 0.36, "halo": 0.12,
                 "width_var": 0.5, "mask": [-0.4, 1.2], "feather": 0.5},
                {"type": "cells", "cells": 9, "warp_px": 45, "warp_f": [2, 12], "fine_px": 2.0,
                 "fine_f": [30, 200], "core_px": 0.7, "halo_px": 3.0, "core": 0.22, "halo": 0.05,
                 "width_var": 0.4, "mask": [0.1, 1.5], "feather": 0.3},
            ],
            "rough_base": 0.21, "rough_vein": 0.04, "rough_var": 0.025, "undulation_mm": 0.25,
        },
    },
    "plaster": {
        "res": 1024, "tile_m": 3.0, "metal": 0.0, "roughness": 0.65,
        "jpeg": {"albedo": 88, "normal": 92, "orm": 88},
        "download_albedo_target_linear": "placeholder_mean",
        "download_guards": {"roughness_mean_min": "slots_min", "albedo_mean_min_linear": "slots_max_capped",
                            "albedo_cap": 0.9},
        "placeholder": {
            # Near-white lime plaster; wall / ceiling / trim tints come from baseColorFactor.
            "base": [245, 243, 239], "mottle": 0.028, "mottle_fine": 0.008, "tint": 0.010, "grain": 0.006,
            "trowel_layers": 4, "trowel_mm": 0.30, "grain_mm": 0.025, "undulation_mm": 0.6,
            "rough_base": 0.65, "rough_var": 0.05,
        },
    },
    "metal": {
        "res": 1024, "tile_m": 0.5, "metal": 1.0, "roughness": 0.32,
        "jpeg": {"albedo": 88, "normal": 92, "orm": 88},
        "download_albedo_target_linear": "placeholder_mean",
        "download_guards": {"roughness_mean_min": "slots_min", "albedo_mean_min_linear": "slots_max_capped",
                            "albedo_cap": 0.9},
        "placeholder": {
            # Near-neutral light metal (F0 ~0.9 linear); gilt/brass/window tints come from baseColorFactor.
            # Burnished: soft hammered undulation (periodic Worley dimples) + fine brushing streaks along U.
            "base_lin": 0.90, "albedo_var": 0.025, "tarnish": 0.05,
            "hammer_cells": 16, "hammer_mm": 0.06, "brush_mm": 0.0035, "brush_coarse_mm": 0.006,
            "rough_base": 0.30, "rough_brush": 0.05, "rough_var": 0.045,
        },
    },
}

# Contract section 5 slot table: slot -> (set, target base colour linear, roughness, metalness, tile_m)
SLOTS = {
    "parquet":         ("parquet", [0.36, 0.22, 0.12], 0.35, 0.0, 2.0),
    "marble_white":    ("marble",  [0.88, 0.86, 0.82], 0.18, 0.0, 2.0),
    "marble_dark":     ("marble",  [0.10, 0.09, 0.085], 0.20, 0.0, 2.0),
    "marble_stair":    ("marble",  [0.80, 0.76, 0.68], 0.25, 0.0, 2.0),
    "plaster_wall":    ("plaster", [0.86, 0.82, 0.72], 0.60, 0.0, 3.0),
    "plaster_ceiling": ("plaster", [0.93, 0.91, 0.87], 0.65, 0.0, 3.0),
    "painted_trim":    ("plaster", [0.90, 0.88, 0.82], 0.45, 0.0, 1.0),
    "gilt":            ("metal",   [1.00, 0.78, 0.34], 0.28, 1.0, 0.5),
    "brass":           ("metal",   [0.90, 0.70, 0.40], 0.35, 1.0, 0.5),
    "window_frame":    ("metal",   [0.22, 0.18, 0.14], 0.50, 0.6, 1.0),
}

CHANNEL_ALIASES = {
    "albedo": "albedo", "color": "albedo", "colour": "albedo", "diffuse": "albedo", "diff": "albedo",
    "basecolor": "albedo", "base_color": "albedo",
    "normal": "normal_gl", "normal_gl": "normal_gl", "normalgl": "normal_gl", "nor_gl": "normal_gl",
    "normal_dx": "normal_dx", "normaldx": "normal_dx", "nor_dx": "normal_dx",
    "roughness": "roughness", "rough": "roughness",
    "ao": "ao", "ambientocclusion": "ao", "ambient_occlusion": "ao", "occlusion": "ao",
    "metal": "metal", "metalness": "metal", "metallic": "metal",
    "arm": "arm", "orm": "arm",
    "displacement": "displacement", "disp": "displacement", "height": "displacement",
}
# auto-discovery patterns (lower-case substrings), checked in order
DISCOVERY = [
    ("normal_gl", ["_normalgl.", "_normalgl_", "_nor_gl_", "_nor_gl."]),
    ("normal_dx", ["_normaldx.", "_normaldx_", "_nor_dx_", "_nor_dx."]),
    ("albedo", ["_color.", "_color_", "_diff_", "_diff.", "_diffuse", "_albedo", "_basecolor", "_col_"]),
    ("roughness", ["_roughness.", "_roughness_", "_rough_", "_rough."]),
    ("ao", ["_ambientocclusion.", "_ambientocclusion_", "_ao_", "_ao."]),
    ("metal", ["_metalness.", "_metalness_", "_metal_", "_metal.", "_metallic"]),
    ("arm", ["_arm_", "_arm."]),
    ("displacement", ["_displacement.", "_displacement_", "_disp_", "_disp."]),
]
IMG_EXT = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp", ".tga")


# ===============================================================================================================
# small numeric helpers (all periodic)
# ===============================================================================================================
def srgb_to_lin(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(x):
    x = np.clip(np.asarray(x, dtype=np.float64), 0.0, 1.0)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1.0 / 2.4) - 0.055)


def rgb_lin(rgb255):
    return srgb_to_lin(np.asarray(rgb255, dtype=np.float64) / 255.0)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def spectral_noise(n, rng, beta=2.0, f_lo=1.0, f_hi=None, aniso=1.0, angle_deg=0.0):
    """Periodic zero-mean, unit-std noise (n x n) by FFT filtering of white noise.
    Amplitude ~ f^(-beta/2) (power ~ f^-beta) between f_lo and f_hi (cycles per tile).
    aniso > 1 elongates features along angle_deg (image coords: 0 = along +x/columns, 90 = along rows/down)."""
    fy = np.fft.fftfreq(n) * n
    fx = np.fft.rfftfreq(n) * n
    FX, FY = np.meshgrid(fx, fy)
    a = math.radians(angle_deg)
    fu = FX * math.cos(a) + FY * math.sin(a)
    fv = -FX * math.sin(a) + FY * math.cos(a)
    f = np.sqrt((fu * aniso) ** 2 + fv ** 2)
    f[0, 0] = 1.0
    amp = f ** (-beta / 2.0)
    amp *= 1.0 - np.exp(-((f / max(f_lo, 1e-6)) ** 4))
    if f_hi:
        amp *= np.exp(-((f / f_hi) ** 2))
    amp[0, 0] = 0.0
    spec = np.fft.rfft2(rng.standard_normal((n, n)))
    out = np.fft.irfft2(spec * amp, s=(n, n))
    out -= out.mean()
    out /= out.std() + 1e-12
    return out.astype(np.float32)


def blur_wrap(img, sigma_px):
    """Periodic gaussian blur via FFT (2-D or H x W x C)."""
    if sigma_px <= 0:
        return img
    h, w = img.shape[:2]
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    g = np.exp(-2.0 * (math.pi * sigma_px) ** 2 * (fx ** 2 + fy ** 2))
    if img.ndim == 2:
        return np.fft.irfft2(np.fft.rfft2(img) * g, s=(h, w)).astype(np.float32)
    return np.stack([np.fft.irfft2(np.fft.rfft2(img[..., c]) * g, s=(h, w)) for c in range(img.shape[2])],
                    -1).astype(np.float32)


def sample_wrap(field, x, y):
    """Bilinear sample of a periodic 2-D field at float pixel coords (x = column, y = row), wrap-around."""
    h, w = field.shape
    x0f = np.floor(x)
    y0f = np.floor(y)
    tx = (x - x0f).astype(np.float32)
    ty = (y - y0f).astype(np.float32)
    x0 = np.mod(x0f.astype(np.int64), w)
    y0 = np.mod(y0f.astype(np.int64), h)
    x1 = (x0 + 1) % w
    y1 = (y0 + 1) % h
    a = field[y0, x0]
    b = field[y0, x1]
    c = field[y1, x0]
    d = field[y1, x1]
    return (a + (b - a) * tx) * (1.0 - ty) + (c + (d - c) * tx) * ty


def worley_f1(n, cells, rng, jitter=0.85):
    """Periodic Worley F1 distance (in cell units) on an n x n grid with cells x cells jittered feature points."""
    cs = n / cells
    pts = rng.random((cells, cells, 2)) * jitter + (1.0 - jitter) * 0.5
    c = (np.arange(n, dtype=np.float64) + 0.5) / cs
    CX, CY = np.meshgrid(c, c)
    ci = np.floor(CX).astype(np.int64)
    cj = np.floor(CY).astype(np.int64)
    best = np.full((n, n), 1e9)
    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            ni = ci + di
            nj = cj + dj
            p = pts[np.mod(nj, cells), np.mod(ni, cells)]
            d2 = (CX - (ni + p[..., 0])) ** 2 + (CY - (nj + p[..., 1])) ** 2
            best = np.minimum(best, d2)
    return np.sqrt(best).astype(np.float32)


def height_to_normal(h_mm, px_mm, strength=1.0):
    """OpenGL tangent normal from a periodic height field (mm). Row 0 = top (+V)."""
    dx = (np.roll(h_mm, -1, 1) - np.roll(h_mm, 1, 1)) / (2.0 * px_mm)
    dr = (np.roll(h_mm, -1, 0) - np.roll(h_mm, 1, 0)) / (2.0 * px_mm)
    n = np.stack([-dx * strength, dr * strength, np.ones_like(dx)], -1).astype(np.float32)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n


def seam_score(img):
    """Wrap-edge discontinuity / interior neighbour difference (~1.0 = seamless; > ~1.6 = visible seam)."""
    a = np.asarray(img, dtype=np.float32)
    if a.ndim == 3:
        a = a.mean(-1)
    inner_r = np.abs(np.diff(a, axis=0)).mean()
    inner_c = np.abs(np.diff(a, axis=1)).mean()
    edge_r = np.abs(a[0] - a[-1]).mean()
    edge_c = np.abs(a[:, 0] - a[:, -1]).mean()
    return float(max(edge_r / (inner_r + 1e-6), edge_c / (inner_c + 1e-6)))


def offset_blend(arr, band_frac=0.18):
    """Make an image wrap seamlessly: blend with its half-offset copy near the borders."""
    h, w = arr.shape[:2]
    rolled = np.roll(np.roll(arr, h // 2, 0), w // 2, 1)
    dy = np.minimum(np.arange(h), np.arange(h)[::-1]) / (band_frac * h)
    dx = np.minimum(np.arange(w), np.arange(w)[::-1]) / (band_frac * w)
    wgt = np.minimum(np.clip(dy, 0, 1)[:, None], np.clip(dx, 0, 1)[None, :])
    wgt = smoothstep(0.0, 1.0, wgt).astype(np.float32)
    if arr.ndim == 3:
        wgt = wgt[..., None]
    return arr * wgt + rolled * (1.0 - wgt)


def stable_rng(set_name, seed, salt=""):
    return np.random.default_rng((zlib.crc32((set_name + ":" + salt).encode()) ^ int(seed)) & 0xFFFFFFFF)


# ===============================================================================================================
# placeholder generators. Each returns dict(albedo_lin HxWx3, height_mm HxW, rough HxW, ao HxW, metal float)
# ===============================================================================================================
def _parquet_layout(n, T, p):
    """Per-pixel plank id, plank-local coords (along s, across w, metres), distance to plank edge (m)."""
    c = (np.arange(n, dtype=np.float64) + 0.5) * T / n
    X, Y = np.meshgrid(c, c)                       # X: columns (U), Y: rows (down)
    pattern = p["pattern"]
    spine = p.get("spine", "u")
    if pattern == "herringbone":
        k = int(p["rows_per_tile"])
        ratio = int(p["plank_ratio"])
        L = T / (k * SQ2)
        W = L / ratio
        m = k * ratio
        U = (X - Y) / SQ2
        V = (X + Y) / SQ2
        i0 = np.floor((U + V) / (2 * W)).astype(np.int64)
        j0 = np.floor((U - V) / (2 * L)).astype(np.int64)
        pid = np.full((n, n), -1, np.int64)
        s = np.zeros((n, n))
        w = np.zeros((n, n))
        for di in range(-5, 2):
            for dj in range(-2, 3):
                ii = i0 + di
                jj = j0 + dj
                ru = U - (ii * W + jj * L)
                rv = V - (ii * W - jj * L)
                free = pid < 0
                mH = free & (ru >= 0) & (ru < L) & (rv >= 0) & (rv < W)
                mV = free & ~mH & (ru >= 0) & (ru < W) & (rv >= W) & (rv < W + L)
                base = ((np.mod(ii, m) * k + np.mod(jj, k)) * 2)
                pid[mH] = base[mH]
                s[mH] = ru[mH]
                w[mH] = rv[mH]
                pid[mV] = base[mV] + 1
                s[mV] = rv[mV] - W
                w[mV] = ru[mV]
        NP = m * k * 2
        d_edge = np.minimum(np.minimum(s, L - s), np.minimum(w, W - w))
        Lp, Wp = L, W
    elif pattern == "chevron":
        ncol = int(p["chevron_cols"])
        if ncol % 2:
            ncol += 1
        nper = int(p["chevron_planks_per_col"])
        th = math.radians(p["chevron_angle_deg"])
        C = T / ncol
        P = T / nper
        Wp = P * math.cos(th)
        Lp = C / math.cos(th)
        col = np.floor(X / C).astype(np.int64)
        xl = X - col * C
        sign = np.where(np.mod(col, 2) == 0, 1.0, -1.0)
        yy = Y - sign * math.tan(th) * xl
        pi = np.floor(yy / P).astype(np.int64)
        t = yy - pi * P
        w = t * math.cos(th)
        s = xl / math.cos(th) + sign * t * math.sin(th)
        pid = np.mod(col, ncol) * nper + np.mod(pi, nper)
        NP = ncol * nper
        d_edge = np.minimum(np.minimum(w, Wp - w), np.minimum(xl, C - xl))
    else:
        raise ValueError("unknown parquet pattern %r" % pattern)
    if spine_swapped(pattern, spine):
        pid, s, w, d_edge = pid.T.copy(), s.T.copy(), w.T.copy(), d_edge.T.copy()
    return pid, s, w, d_edge, NP, Lp, Wp


def spine_swapped(pattern, spine):
    return (pattern == "herringbone" and spine == "v") or (pattern == "chevron" and spine == "u")


def gen_parquet(res, tile_m, p, rng):
    n = res
    px_mm = tile_m * 1000.0 / n
    pid, s_m, w_m, d_m, NP, Lp, Wp = _parquet_layout(n, tile_m, p)
    uncovered = int((pid < 0).sum())
    pid = np.maximum(pid, 0)
    s = (s_m * 1000.0).astype(np.float32)          # mm along the plank
    w = (w_m * 1000.0).astype(np.float32)          # mm across the plank
    d = (d_m * 1000.0).astype(np.float32)          # mm to the nearest plank edge
    Lmm, Wmm = Lp * 1000.0, Wp * 1000.0

    # ---- per-plank random parameters
    tone = np.clip(rng.normal(1.0, p["tone_sd"], NP), 0.78, 1.25)
    mixt = rng.random(NP)                             # light <-> dark oak
    red = rng.random(NP) < p["red_frac"]
    qs = rng.random(NP) < p["quartersawn_frac"]
    ring = rng.uniform(p["ring_mm"][0], p["ring_mm"][1], NP)
    curv = np.where(qs, 0.0, rng.uniform(0.08, 0.35, NP))
    s0 = rng.uniform(0.25, 0.75, NP) * Lmm
    w0 = rng.uniform(-40.0, 40.0, NP)
    grad = rng.normal(0.0, 0.035, NP)                 # tone drift along the plank
    offs = rng.uniform(0, 512, (NP, 6)).astype(np.float32)
    r_off = rng.normal(0.0, p["rough_plank_sd"], NP)
    h_off = rng.normal(0.0, p["plank_height_sd_mm"], NP)

    light = rgb_lin(p["oak_light"])
    dark = rgb_lin(p["oak_dark"])
    redc = rgb_lin(p["oak_red"])
    t = mixt[:, None] ** 1.3
    pc = light[None, :] * (1 - t) + dark[None, :] * t
    pc = np.where(red[:, None], pc * 0.45 + redc[None, :] * 0.55, pc)
    pc = pc * tone[:, None]
    plank_col = pc.astype(np.float32)[pid]                              # HxWx3

    nrng = np.random.default_rng(rng.integers(1 << 31))
    noiseA = spectral_noise(512, nrng, beta=2.2, f_lo=2, f_hi=48)       # smooth wobble
    noiseB = spectral_noise(512, nrng, beta=0.9, f_lo=8, f_hi=200)      # fine streaks / pores
    noiseC = spectral_noise(512, nrng, beta=1.6, f_lo=6, f_hi=90)       # flecks

    o = offs[pid]
    # growth-ring figure: iso-lines of g (cathedral parabolas for flat-sawn, straight for quarter-sawn);
    # ring spacing is made irregular by a 1-D noise of g itself.
    wob = sample_wrap(noiseA, s * 0.006 + o[..., 0], w * 0.03 + o[..., 1])
    g = (w - w0[pid]) + curv[pid] * (s - s0[pid]) ** 2 / Lmm + 6.0 * wob
    phi = g / ring[pid] + 3.0 * sample_wrap(noiseA, g * 0.03 + o[..., 2], o[..., 3] + s * 0.004)
    # figure: groups of rings form lighter / darker zones (growth years), varying along the board as well
    zone = sample_wrap(noiseA, g * 0.012 + o[..., 5], o[..., 0] + s * 0.006)
    r = np.mod(phi, 1.0)
    ring_id = np.floor(phi)
    ring_h = np.mod(np.sin(ring_id * 12.9898 + pid * 78.233) * 43758.5453, 1.0)   # per-ring strength
    band = smoothstep(0.45, 0.62, r) * (1.0 - smoothstep(0.86, 1.0, r))       # dark latewood band
    band = band * (0.25 + 1.3 * ring_h ** 2)
    early = np.exp(-((r - 0.08) / 0.07) ** 2) + np.exp(-((r - 1.08) / 0.07) ** 2)  # earlywood pore zone
    streak = sample_wrap(noiseB, s * 0.035 + o[..., 2], w * 0.9 + o[..., 3])
    broad = sample_wrap(noiseA, s * 0.004 + o[..., 4], w * 0.25 + o[..., 5])
    pores = smoothstep(0.9, 2.2, sample_wrap(noiseB, s * 0.22 + o[..., 4], w * 1.4 + o[..., 5])) * (0.35 + early)
    pores = np.clip(pores, 0.0, 1.0)
    fleck = smoothstep(1.0, 2.2, sample_wrap(noiseC, s * 0.09 + o[..., 1], w * 0.30 + o[..., 4])) * qs[pid]
    along = grad[pid] * (s / Lmm - 0.5) * 2.0
    rc = np.where(qs[pid], p["ring_contrast_qs"], p["ring_contrast"]).astype(np.float32)

    wear = spectral_noise(n, nrng, beta=3.0, f_lo=1, f_hi=10)
    lum = (1.0 - rc * band * (0.35 + 0.65 * smoothstep(-1.2, 1.2, zone + 0.5 * streak))
           - p["pore_contrast"] * pores
           + p["streak_contrast"] * streak * 0.5
           + p["broad_streak_contrast"] * broad * 0.5
           + p["figure_contrast"] * zone * 0.5
           + p["fleck_contrast"] * fleck
           + along + p["wear_contrast"] * wear)
    alb = plank_col * lum[..., None]

    # seams: anti-aliased gap + dirt in the bevel
    half_gap = 0.5 * p["gap_mm"]
    gap_cov = np.clip((half_gap - (d - 0.5 * px_mm)) / px_mm, 0.0, 1.0)
    bevel_band = 1.0 - smoothstep(0.0, p["bevel_mm"] * 1.4, d)
    alb = alb * (1.0 - p["bevel_dirt"] * bevel_band)[..., None]
    gapc = rgb_lin(p["gap_rgb"]).astype(np.float32)
    alb = alb * (1.0 - gap_cov[..., None]) + gapc[None, None, :] * gap_cov[..., None]

    # height (mm): per-plank offset + slight cupping + micro bevel + gap + grain relief
    wn = np.clip(w / Wmm, 0.0, 1.0)
    cup = p["cup_mm"] * ((2.0 * wn - 1.0) ** 2)
    bevel = -p["bevel_depth_mm"] * np.clip(1.0 - d / p["bevel_mm"], 0.0, 1.0) ** 1.4
    h = h_off[pid] + cup + bevel - 1.2 * gap_cov - 0.012 * band - 0.02 * pores + 0.004 * streak
    h = blur_wrap(h.astype(np.float32), 0.45)

    rough = (p["rough_base"] + r_off[pid] + p["rough_wear"] * wear + 0.07 * pores + 0.02 * band
             - 0.04 * fleck + 0.12 * bevel_band + 0.35 * gap_cov)
    ao = 1.0 - 0.5 * gap_cov - 0.10 * bevel_band - 0.03 * pores
    info = {"plank_len_mm": round(Lmm, 1), "plank_w_mm": round(Wmm, 1), "planks_per_tile": int(NP),
            "uncovered_px": uncovered}
    return dict(albedo_lin=alb.astype(np.float32), height_mm=h, rough=rough.astype(np.float32),
                ao=ao.astype(np.float32), metal=0.0, info=info)


def _wrap_pi(x):
    return (x + np.pi) % (2.0 * np.pi) - np.pi


def worley_edges(cx, cy, cells, pts):
    """Periodic Worley on arbitrary coords (cell units): returns approx. distance to the nearest cell edge
    (cell units) = (F2^2 - F1^2) / (2 |p2 - p1|)."""
    ci = np.floor(cx).astype(np.int64)
    cj = np.floor(cy).astype(np.int64)
    shp = cx.shape
    f1 = np.full(shp, 1e9)
    f2 = np.full(shp, 1e9)
    p1x = np.zeros(shp)
    p1y = np.zeros(shp)
    p2x = np.zeros(shp)
    p2y = np.zeros(shp)
    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            ni = ci + di
            nj = cj + dj
            q = pts[np.mod(nj, cells), np.mod(ni, cells)]
            qx = ni + q[..., 0]
            qy = nj + q[..., 1]
            d2 = (cx - qx) ** 2 + (cy - qy) ** 2
            is1 = d2 < f1
            is2 = (~is1) & (d2 < f2)
            f2 = np.where(is1, f1, np.where(is2, d2, f2))
            p2x = np.where(is1, p1x, np.where(is2, qx, p2x))
            p2y = np.where(is1, p1y, np.where(is2, qy, p2y))
            f1 = np.where(is1, d2, f1)
            p1x = np.where(is1, qx, p1x)
            p1y = np.where(is1, qy, p1y)
    sep = np.sqrt((p2x - p1x) ** 2 + (p2y - p1y) ** 2) + 1e-9
    return ((f2 - f1) / (2.0 * sep)).astype(np.float32)


def _wrap_pi(x):
    return (x + np.pi) % (2.0 * np.pi) - np.pi


def gen_marble(res, tile_m, p, rng):
    n = res
    c = (np.arange(n, dtype=np.float32) + 0.5) / n
    U, V = np.meshgrid(c, c)                         # tile fractions: U = columns, V = rows (down)
    D = np.zeros((n, n), np.float32)
    Dcore = np.zeros((n, n), np.float32)
    smoke = spectral_noise(n, rng, beta=2.2, f_lo=3, f_hi=60)
    vein_angle = 0.0
    for li, lay in enumerate(p["veins"]):
        if lay.get("type", "sine") == "sine":
            kx, ky = lay["k"]
            phase = 2.0 * np.pi * (kx * U + ky * V)
            for amp, flo, fhi in lay["turb"]:
                phase = phase + amp * spectral_noise(n, rng, beta=2.0, f_lo=flo, f_hi=fhi)
            gx = _wrap_pi(np.roll(phase, -1, 1) - np.roll(phase, 1, 1)) * 0.5
            gy = _wrap_pi(np.roll(phase, -1, 0) - np.roll(phase, 1, 0)) * 0.5
            g = np.hypot(gx, gy)
            dist = np.abs(_wrap_pi(phase)) / (g + 0.25 * np.median(g))
            if li == 0:
                vein_angle = math.degrees(math.atan2(kx, -ky))
        else:
            cells = int(lay["cells"])
            pts = rng.random((cells, cells, 2)) * 0.8 + 0.1
            wx = (spectral_noise(n, rng, beta=3.0, f_lo=lay["warp_f"][0], f_hi=lay["warp_f"][1]) * lay["warp_px"]
                  + spectral_noise(n, rng, beta=1.5, f_lo=lay["fine_f"][0], f_hi=lay["fine_f"][1]) * lay["fine_px"])
            wy = (spectral_noise(n, rng, beta=3.0, f_lo=lay["warp_f"][0], f_hi=lay["warp_f"][1]) * lay["warp_px"]
                  + spectral_noise(n, rng, beta=1.5, f_lo=lay["fine_f"][0], f_hi=lay["fine_f"][1]) * lay["fine_px"])
            cs = n / float(cells)
            dist = worley_edges((U * n + wx) / cs, (V * n + wy) / cs, cells, pts) * cs
        wmod = np.exp(lay["width_var"] * spectral_noise(n, rng, beta=3.0, f_lo=1, f_hi=10))
        core = np.exp(-(dist / (lay["core_px"] * wmod)) ** 2)
        halo = np.exp(-dist / (lay["halo_px"] * wmod))
        halo = halo * (1.0 - lay["feather"] + lay["feather"] * smoothstep(-1.2, 1.2, smoke))
        mlo, mhi = lay["mask"]
        mask = smoothstep(mlo, mhi, spectral_noise(n, rng, beta=3.0, f_lo=1, f_hi=6))
        contrib = np.clip(mask * (lay["core"] * core + lay["halo"] * halo), 0, 1)
        D = 1.0 - (1.0 - D) * (1.0 - contrib)
        Dcore = np.maximum(Dcore, mask * core)
    D = np.clip(D, 0.0, 0.85).astype(np.float32)
    cloud = spectral_noise(n, rng, beta=2.6, f_lo=1.5, f_hi=50, aniso=2.5, angle_deg=vein_angle)
    cl = p["cloud"] * smoothstep(-0.2, 2.4, cloud)
    grain = spectral_noise(n, rng, beta=0.3, f_lo=150, f_hi=700)
    base = rgb_lin(p["base"]).astype(np.float32)
    cloudc = rgb_lin(p["cloud_rgb"]).astype(np.float32)
    vein = rgb_lin(p["vein"]).astype(np.float32)
    col = base[None, None, :] * (1 - cl[..., None]) + cloudc[None, None, :] * cl[..., None]
    col = col * (1.0 + p["grain"] * grain)[..., None]
    col = col * (1.0 - D[..., None]) + vein[None, None, :] * D[..., None]

    smudge = spectral_noise(n, rng, beta=2.8, f_lo=1, f_hi=24)
    rough = p["rough_base"] + p["rough_vein"] * D + p["rough_var"] * smudge + 0.006 * grain
    und = spectral_noise(n, rng, beta=3.0, f_lo=2, f_hi=12)
    h = p["undulation_mm"] * und - 0.004 * Dcore
    ao = np.ones((n, n), np.float32)
    return dict(albedo_lin=col.astype(np.float32), height_mm=h.astype(np.float32),
                rough=rough.astype(np.float32), ao=ao, metal=0.0, info={"vein_angle_deg": round(vein_angle, 1)})


def gen_plaster(res, tile_m, p, rng):
    n = res
    mott = spectral_noise(n, rng, beta=2.6, f_lo=1.5, f_hi=40)
    mott2 = spectral_noise(n, rng, beta=1.8, f_lo=10, f_hi=160)
    tint = spectral_noise(n, rng, beta=3.0, f_lo=1, f_hi=10)
    grain = spectral_noise(n, rng, beta=0.4, f_lo=120, f_hi=500)
    trowel = np.zeros((n, n), np.float32)
    for _ in range(int(p["trowel_layers"])):
        ang = float(rng.uniform(0, 180))
        layer = spectral_noise(n, rng, beta=2.2, f_lo=8, f_hi=70, aniso=4.0, angle_deg=ang)
        mask = smoothstep(-0.2, 1.0, spectral_noise(n, rng, beta=3.0, f_lo=1, f_hi=8))
        trowel += layer * mask
    trowel /= trowel.std() + 1e-6
    und = spectral_noise(n, rng, beta=3.2, f_lo=1, f_hi=10)
    lum = 1.0 + p["mottle"] * mott + p["mottle_fine"] * mott2 + 0.006 * trowel + p["grain"] * grain
    base = rgb_lin(p["base"]).astype(np.float32)
    warmv = np.array([1.0, 0.2, -1.0], np.float32)
    col = base[None, None, :] * lum[..., None] * (1.0 + p["tint"] * tint[..., None] * warmv[None, None, :])
    h = p["trowel_mm"] * trowel + p["grain_mm"] * grain + p["undulation_mm"] * und
    rough = p["rough_base"] + p["rough_var"] * (0.6 * mott2 - 0.5 * np.clip(trowel, -2, 2) * 0.5) + 0.02 * grain
    ao = 1.0 - 0.02 * smoothstep(0.5, 2.5, -grain)
    return dict(albedo_lin=col.astype(np.float32), height_mm=h.astype(np.float32),
                rough=rough.astype(np.float32), ao=ao.astype(np.float32), metal=0.0, info={})


def gen_metal(res, tile_m, p, rng):
    n = res
    brush = spectral_noise(n, rng, beta=0.8, f_lo=40, f_hi=480, aniso=40.0, angle_deg=0.0)
    brush2 = spectral_noise(n, rng, beta=1.6, f_lo=6, f_hi=120, aniso=14.0, angle_deg=0.0)
    f1 = worley_f1(n, int(p["hammer_cells"]), rng)
    dimple = blur_wrap(f1 ** 2, 2.5)
    dimple = (dimple - dimple.mean()) / (dimple.std() + 1e-6)
    blot = spectral_noise(n, rng, beta=3.0, f_lo=1, f_hi=10)
    tarn = smoothstep(0.6, 2.2, blot)
    lum = 1.0 + p["albedo_var"] * (0.5 * brush2 + 0.3 * brush) - p["tarnish"] * tarn
    col = np.repeat((p["base_lin"] * lum)[..., None], 3, -1)
    h = p["hammer_mm"] * dimple + p["brush_mm"] * brush + p["brush_coarse_mm"] * brush2
    rough = (p["rough_base"] + p["rough_brush"] * (0.6 * brush + 0.4 * brush2) + p["rough_var"] * blot * 0.6
             + 0.03 * tarn)
    ao = 1.0 - 0.03 * smoothstep(0.5, 2.0, dimple)
    return dict(albedo_lin=col.astype(np.float32), height_mm=h.astype(np.float32),
                rough=rough.astype(np.float32), ao=ao.astype(np.float32), metal=1.0, info={})


GENERATORS = {"parquet": gen_parquet, "marble": gen_marble, "plaster": gen_plaster, "metal": gen_metal}


# ===============================================================================================================
# download path
# ===============================================================================================================
def _resolve(path, base_dirs):
    if not path:
        return None
    if os.path.isabs(path):
        return path if os.path.isfile(path) else None
    for b in base_dirs:
        cand = os.path.normpath(os.path.join(b, path))
        if os.path.isfile(cand):
            return cand
    return None


def _discover(folder):
    found = {}
    if not folder or not os.path.isdir(folder):
        return found
    names = sorted(f for f in os.listdir(folder) if f.lower().endswith(IMG_EXT))
    for fname in names:
        low = fname.lower()
        for ch, pats in DISCOVERY:
            if any(pt in low for pt in pats):
                if ch not in found:
                    found[ch] = os.path.join(folder, fname)
                break
    return found


def _load_float(path):
    """-> float32 array in 0..1, shape HxW or HxWx3."""
    im = Image.open(path)
    if im.mode in ("I;16", "I;16B", "I;16L", "I"):
        a = np.asarray(im, dtype=np.float32)
        a = a / (65535.0 if a.max() > 255 else 255.0)
        return np.clip(a, 0, 1)
    if im.mode in ("F",):
        return np.clip(np.asarray(im, dtype=np.float32), 0, 1)
    if im.mode in ("L", "LA"):
        return np.asarray(im.convert("L"), dtype=np.float32) / 255.0
    return np.asarray(im.convert("RGB"), dtype=np.float32) / 255.0


def _gray(a):
    return a if a.ndim == 2 else a[..., :3].mean(-1)


def _crop_square_rotate(a, entry):
    """Explicit crop box -> square (square_mode stack|crop|none) -> rotate. Returns (array, notes)."""
    notes = []
    h, w = a.shape[:2]
    crop = entry.get("crop")
    if crop:
        x0, y0, x1, y1 = crop
        if max(abs(v) for v in crop) <= 1.0:
            x0, x1 = int(round(x0 * w)), int(round(x1 * w))
            y0, y1 = int(round(y0 * h)), int(round(y1 * h))
        a = a[int(y0):int(y1), int(x0):int(x1)]
        notes.append("crop box %s" % (list(crop),))
        h, w = a.shape[:2]
    if h != w:
        mode = str(entry.get("square_mode") or "crop").lower()
        short, long_ = min(h, w), max(h, w)
        if mode == "stack":
            reps = int(math.ceil(long_ / float(short)))
            if h < w:
                a = np.concatenate([a] * reps, 0)[:w]
            else:
                a = np.concatenate([a] * reps, 1)[:, :h]
            notes.append("stacked x%d along the short axis%s" % (reps, "" if long_ % short == 0 else
                                                                  " (non-integer aspect: wrap seam likely)"))
        else:
            oy, ox = (h - short) // 2, (w - short) // 2
            a = a[oy:oy + short, ox:ox + short]
            notes.append("centre-cropped %dx%d -> %d%s" % (w, h, short, "" if mode == "crop" else
                                                           " (square_mode %r but source not square)" % mode))
    rot = int(entry.get("rotate", 0) or 0) % 360
    if rot:
        a = np.rot90(a, rot // 90).copy()
        notes.append("rotated %d" % rot)
    return a, notes


def _resize(a, res):
    if a.shape[0] == res and a.shape[1] == res:
        return a.astype(np.float32)
    chans = [a] if a.ndim == 2 else [a[..., c] for c in range(a.shape[2])]
    out = [np.asarray(Image.fromarray(c.astype(np.float32), mode="F").resize((res, res), Image.LANCZOS),
                      dtype=np.float32) for c in chans]
    return out[0] if a.ndim == 2 else np.stack(out, -1)


def soft_clip(x, knee=0.9):
    """Identity below knee, smooth tanh shoulder up to 1.0 above it."""
    k = float(knee)
    return np.where(x < k, x, k + (1.0 - k) * np.tanh((x - k) / (1.0 - k))).astype(np.float32)


def guard_targets(set_name, cfg):
    """(roughness_mean_min, albedo_mean_min_linear or None) from the contract slot table (glTF factors <= 1)."""
    g = cfg.get("download_guards")
    if not g:
        return None, None
    slots = [v for v in SLOTS.values() if v[0] == set_name]
    rmin = g.get("roughness_mean_min")
    if rmin == "slots_min":
        rmin = min(s[2] for s in slots) if slots else None
    amin = g.get("albedo_mean_min_linear")
    if amin == "slots_max_capped":
        cap = float(g.get("albedo_cap", 0.9))
        amin = [min(cap, max(s[1][c] for s in slots)) for c in range(3)] if slots else None
    return rmin, amin


def build_from_download(set_name, entry, cfg, placeholder_means):
    """Returns (maps dict like the generators + 'normal' + 'metal_map', provenance dict) or (None, reason).
    cfg must already carry the entry's tile_m/out_res (see effective_cfg)."""
    res = int(cfg["res"])
    base_dirs = [ASSETS_DIR, M_DIR]
    d = entry.get("dir")
    folder = None
    if d:
        folder = d if os.path.isabs(d) else next((os.path.join(b, d) for b in base_dirs
                                                  if os.path.isdir(os.path.join(b, d))), None)
    if folder:
        base_dirs = [folder] + base_dirs
    files = {}
    explicit_null = set()
    for k, v in (entry.get("files") or {}).items():
        ch = CHANNEL_ALIASES.get(k.lower().replace("-", "_"))
        if ch is None:
            print("  [%s] WARNING unknown channel key %r ignored" % (set_name, k))
            continue
        if v in (None, ""):
            explicit_null.add(ch)                 # null = synthesise, no auto-discovery
            continue
        path = _resolve(v, base_dirs)
        if path is None:
            print("  [%s] WARNING %s file not found: %s" % (set_name, ch, v))
            continue
        files[ch] = path
    for ch, path in _discover(folder).items():
        if ch not in explicit_null:
            files.setdefault(ch, path)
    if "albedo" not in files:
        return None, "no albedo file found"
    prov = {"channels": {}, "notes": []}
    loaded = {}
    for ch, path in sorted(files.items()):
        try:
            a, notes = _crop_square_rotate(_load_float(path), entry)
            if ch == "albedo":
                prov["notes"] += notes
            loaded[ch] = _resize(a, res)
            prov["channels"][ch] = os.path.relpath(path, M_DIR).replace("\\", "/")
        except Exception as ex:  # noqa: BLE001 - report and fall back per channel
            print("  [%s] WARNING could not read %s (%s): %s" % (set_name, ch, path, ex))
    if "albedo" not in loaded:
        return None, "albedo unreadable"
    guards_on = entry.get("guards", True) is not False
    r_min, a_min = guard_targets(set_name, cfg) if guards_on else (None, None)

    # ---- albedo
    alb = loaded["albedo"]
    if alb.ndim == 2:
        alb = np.repeat(alb[..., None], 3, -1)
    alb_lin = srgb_to_lin(alb[..., :3]).astype(np.float32)
    mean0 = alb_lin.reshape(-1, 3).mean(0)
    prov["albedo_source_mean_linear"] = [round(float(v), 4) for v in mean0]
    mode = entry.get("albedo_mode")
    target = entry.get("albedo_target_linear")
    if target is None and not mode:
        target = cfg.get("download_albedo_target_linear")
        if target == "placeholder_mean":
            target = placeholder_means.get(set_name)
    if target is not None:
        alb_lin = alb_lin * (np.asarray(target, np.float32) / np.maximum(mean0, 1e-4))
        prov["albedo"] = "rescaled per channel to linear mean %s" % [round(float(v), 3) for v in target]
    elif str(mode).lower() == "neutralize":
        lum = float(entry.get("neutral_luminance", 0.9))
        alb_lin = alb_lin / np.maximum(mean0, 1e-4) * lum
        prov["albedo"] = "neutralized to linear mean %.3f (grey)" % lum
    else:
        prov["albedo"] = "as_is"
    alb_lin = soft_clip(alb_lin, 0.92)
    if a_min is not None:
        m = alb_lin.reshape(-1, 3).mean(0)
        s = float(max(a_min[c] / max(m[c], 1e-4) for c in range(3)))
        if s > 1.02:
            alb_lin = soft_clip(alb_lin * s, 0.92)
            msg = "albedo x%.2f (mean %s -> %s) so baseColorFactor<=1 reaches the slot table" % (
                s, [round(float(v), 3) for v in m], [round(float(v), 3) for v in alb_lin.reshape(-1, 3).mean(0)])
            prov.setdefault("guards_applied", []).append(msg)
            print("  [%s] GUARD %s" % (set_name, msg))

    # ---- AO / roughness / metal (individual files override the packed ARM file)
    arm = loaded.get("arm")
    ao = rough = metal = None
    if arm is not None and arm.ndim == 3:
        ao, rough, metal = arm[..., 0], arm[..., 1], arm[..., 2]
    if "ao" in loaded:
        ao = _gray(loaded["ao"])
    if "roughness" in loaded:
        rough = _gray(loaded["roughness"])
    if "metal" in loaded:
        metal = _gray(loaded["metal"])
    synth = []
    rdef = float(entry.get("roughness_default", cfg["roughness"]))
    mdef = float(entry.get("metal_default", cfg["metal"]))
    if ao is None:
        ao = np.ones((res, res), np.float32)
        synth.append("ao=1")
    if rough is None:
        rough = np.full((res, res), rdef, np.float32)
        synth.append("roughness=%.2f" % rdef)
    if metal is None:
        metal = np.full((res, res), mdef, np.float32)
        synth.append("metal=%g" % mdef)
    prov["roughness_source_mean"] = round(float(rough.mean()), 4)
    rough = np.clip(rough * float(entry.get("roughness_scale", 1.0)) + float(entry.get("roughness_offset", 0.0)),
                    0.02, 1.0)
    prov["roughness_after_scale_mean"] = round(float(rough.mean()), 4)
    if r_min is not None and rough.mean() < r_min - 0.005:
        off = float(r_min - rough.mean())
        rough = np.clip(rough + off, 0.02, 1.0)
        msg = "roughness mean %.3f -> %.3f (+%.3f): below the glossiest slot target %.2f of this set" % (
            prov["roughness_after_scale_mean"], float(rough.mean()), off, r_min)
        prov.setdefault("guards_applied", []).append(msg)
        print("  [%s] GUARD %s" % (set_name, msg))

    # ---- normal
    if "normal_gl" in loaded or "normal_dx" in loaded:
        nm = loaded.get("normal_gl", loaded.get("normal_dx"))
        if nm.ndim == 2:
            nm = np.repeat(nm[..., None], 3, -1)
        normal = nm[..., :3] * 2.0 - 1.0
        if "normal_gl" not in loaded:
            normal[..., 1] *= -1.0
            synth.append("normal DX->GL")
    elif "displacement" in loaded:
        disp = _gray(loaded["displacement"]) * float(entry.get("displacement_mm", 2.0))
        normal = height_to_normal(disp, cfg["tile_m"] * 1000.0 / res)
        synth.append("normal from displacement")
    else:
        normal = np.zeros((res, res, 3), np.float32)
        normal[..., 2] = 1.0
        synth.append("normal=flat")
    normal = normal.astype(np.float32)
    normal[..., :2] *= float(entry.get("normal_strength", 1.0))
    normal[..., 2] = np.maximum(normal[..., 2], 1e-3)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)

    maps = dict(albedo_lin=alb_lin.astype(np.float32), rough=rough.astype(np.float32), ao=ao.astype(np.float32),
                metal_map=metal.astype(np.float32), normal=normal, info={})
    smode = str(entry.get("seamless", "check")).lower()
    prov["seam_score_source"] = round(seam_score(lin_to_srgb(alb_lin)), 3)
    if smode == "blend":
        for key in ("albedo_lin", "rough", "ao", "metal_map", "normal"):
            maps[key] = offset_blend(maps[key])
        maps["normal"] /= np.linalg.norm(maps["normal"], axis=-1, keepdims=True)
        prov["seamless"] = "offset-blend applied"
    elif smode == "check" and prov["seam_score_source"] > 1.6:
        print("  [%s] WARNING source albedo seam score %.2f (> 1.6): tiling seam likely; \"seamless\": \"blend\" "
              "in the downloads entry would hide it" % (set_name, prov["seam_score_source"]))
    prov["synthesised"] = synth
    for k in ("source", "asset", "asset_id", "url", "page", "license", "downloaded", "real_size_m"):
        if k in entry:
            prov[k] = entry[k]
    return maps, prov


def effective_cfg(cfg, entry):
    """Set config with a download entry's tile_m / out_res applied."""
    c = dict(cfg)
    if entry.get("tile_m"):
        c["tile_m"] = float(entry["tile_m"])
    if entry.get("out_res"):
        c["res"] = int(entry["out_res"])
    return c


# ===============================================================================================================
# encoding / writing
# ===============================================================================================================
def to_u8(a):
    return np.clip(np.round(np.asarray(a, dtype=np.float32) * 255.0), 0, 255).astype(np.uint8)


def encode_jpeg(arr_u8, quality, subsampling):
    buf = io.BytesIO()
    Image.fromarray(arr_u8).save(buf, format="JPEG", quality=int(quality), subsampling=subsampling,
                                 optimize=True, progressive=False)
    return buf.getvalue()


def write_if_changed(path, data):
    """Atomic write; skips identical bytes. Returns True if written."""
    if os.path.isfile(path):
        with open(path, "rb") as f:
            if f.read() == data:
                return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    for attempt in range(10):
        try:
            os.replace(tmp, path)
            return True
        except PermissionError:
            time.sleep(0.3 * (attempt + 1))
    os.replace(tmp, path)
    return True


def pack_outputs(maps, cfg):
    """-> (albedo_u8, normal_u8, orm_u8)."""
    res = cfg["res"]
    alb = to_u8(lin_to_srgb(maps["albedo_lin"]))
    if "normal" in maps:
        nrm = maps["normal"]
    else:
        nrm = height_to_normal(maps["height_mm"], cfg["tile_m"] * 1000.0 / res)
    nrm_u8 = to_u8(nrm * 0.5 + 0.5)
    metal = maps.get("metal_map")
    if metal is None:
        metal = np.full((res, res), float(maps.get("metal", cfg["metal"])), np.float32)
    orm = np.stack([np.clip(maps["ao"], 0, 1), np.clip(maps["rough"], 0.02, 1), np.clip(metal, 0, 1)], -1)
    return alb, nrm_u8, to_u8(orm)


def stats_for(alb_u8, nrm_u8, orm_u8):
    lin = srgb_to_lin(alb_u8.astype(np.float32) / 255.0)
    lum = (0.2126 * alb_u8[..., 0] + 0.7152 * alb_u8[..., 1] + 0.0722 * alb_u8[..., 2])
    nz = nrm_u8[..., 2].astype(np.float32) / 255.0 * 2 - 1
    o = orm_u8.astype(np.float32) / 255.0
    return {
        "albedo_mean_linear": [round(float(v), 4) for v in lin.reshape(-1, 3).mean(0)],
        "albedo_mean_srgb8": [int(round(float(v))) for v in alb_u8.reshape(-1, 3).mean(0)],
        "albedo_lum_srgb8_p1_p99": [int(np.percentile(lum, 1)), int(np.percentile(lum, 99))],
        "albedo_min_max_srgb8": [int(alb_u8.min()), int(alb_u8.max())],
        "normal_mean_z": round(float(nz.mean()), 4),
        "normal_min_z": round(float(nz.min()), 4),
        "ao_mean": round(float(o[..., 0].mean()), 4),
        "roughness_mean": round(float(o[..., 1].mean()), 4),
        "roughness_p5_p95": [round(float(np.percentile(o[..., 1], 5)), 3),
                             round(float(np.percentile(o[..., 1], 95)), 3)],
        "metal_mean": round(float(o[..., 2].mean()), 4),
        "seam_score": {"albedo": round(seam_score(alb_u8), 3), "normal": round(seam_score(nrm_u8), 3),
                       "orm": round(seam_score(orm_u8), 3)},
    }


# ===============================================================================================================
# previews (2x2 tiles) for visual QA
# ===============================================================================================================
def _down(a, maxdim):
    im = Image.fromarray(a)
    if max(im.size) > maxdim:
        im = im.resize((maxdim, maxdim), Image.LANCZOS)
    return np.asarray(im)


def shade(alb_u8, nrm_u8, orm_u8, light=(-0.55, 0.55, 0.45), exposure=1.5):
    """Tiny PBR-ish shader (view straight down, one raking light) to eyeball the normal/roughness maps."""
    alb = srgb_to_lin(alb_u8.astype(np.float32) / 255.0)
    n = nrm_u8.astype(np.float32) / 255.0 * 2 - 1
    n /= np.linalg.norm(n, axis=-1, keepdims=True) + 1e-6
    o = orm_u8.astype(np.float32) / 255.0
    ao, rough, metal = o[..., 0], np.maximum(o[..., 1], 0.04), o[..., 2]
    L = np.asarray(light, np.float32)
    L /= np.linalg.norm(L)
    V = np.array([0.0, 0.0, 1.0], np.float32)
    H = (L + V) / np.linalg.norm(L + V)
    ndl = np.clip((n * L).sum(-1), 0, 1)
    ndh = np.clip((n * H).sum(-1), 0, 1)
    a2 = (rough ** 2) ** 2
    dd = ndh ** 2 * (a2 - 1) + 1
    D = a2 / (math.pi * dd * dd)
    F0 = 0.04 * (1 - metal[..., None]) + alb * metal[..., None]
    spec = F0 * (D * 0.25)[..., None]
    diff = alb * (1 - metal[..., None]) / math.pi
    col = (diff + spec) * (ndl * 3.2)[..., None] + (0.18 * alb * (1 - 0.7 * metal[..., None]) + 0.05 * F0) * ao[..., None]
    col = col * exposure
    col = col / (1.0 + col)                  # Reinhard
    return to_u8(lin_to_srgb(col * 1.6))


def write_previews(set_name, alb, nrm, orm, preview_dir, tag=""):
    os.makedirs(preview_dir, exist_ok=True)
    set_name = set_name + ("_" + tag if tag else "")
    t = lambda a: np.tile(a, (2, 2, 1))  # noqa: E731
    out = {}
    tiled = _down(t(alb), 2048)
    p = os.path.join(preview_dir, "%s_tiled.jpg" % set_name)
    Image.fromarray(tiled).save(p, quality=90)
    out["tiled"] = p
    lit_full = shade(alb, nrm, orm)
    p = os.path.join(preview_dir, "%s_lit_tiled.jpg" % set_name)
    Image.fromarray(_down(t(lit_full), 2048)).save(p, quality=90)
    out["lit_tiled"] = p
    maps = np.concatenate([_down(t(nrm), 1024), _down(t(orm), 1024)], 1)
    p = os.path.join(preview_dir, "%s_maps_tiled.jpg" % set_name)
    Image.fromarray(maps).save(p, quality=90)
    out["maps_tiled"] = p
    # full-resolution crop centred on the wrap corner (the 4 tile copies meet in the middle of this crop)
    res = alb.shape[0]
    c = min(512, res // 2)
    big_a = t(alb)[res - c:res + c, res - c:res + c]
    big_l = t(lit_full)[res - c:res + c, res - c:res + c]
    p = os.path.join(preview_dir, "%s_seam_crop.jpg" % set_name)
    Image.fromarray(np.concatenate([big_a, big_l], 1)).save(p, quality=92)
    out["seam_crop"] = p
    return out


# ===============================================================================================================
# config / json
# ===============================================================================================================
def deep_merge(base, over):
    out = dict(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_json(path):
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as ex:  # noqa: BLE001
        print("WARNING could not parse %s: %s" % (path, ex))
        return None


def download_entries(dl):
    if not isinstance(dl, dict):
        return {}
    sets = dl.get("sets") if isinstance(dl.get("sets"), dict) else dl
    return {k: v for k, v in sets.items() if k in DEFAULT_SETS and isinstance(v, dict)}


def slot_suggestions(set_stats, set_tiles):
    out = {}
    for slot, (tset, base, rgh, met, tile) in SLOTS.items():
        st = set_stats.get(tset)
        if not st:
            continue
        tile = round(tile * float(set_tiles.get(tset, DEFAULT_SETS[tset]["tile_m"])) / DEFAULT_SETS[tset]["tile_m"], 4)
        mean = st["albedo_mean_linear"]
        raw = [b / max(m, 1e-4) for b, m in zip(base, mean)]
        fac = [round(min(1.0, v), 3) for v in raw]
        rf_raw = rgh / max(st["roughness_mean"], 1e-4)
        out[slot] = {
            "set": tset, "tile_m": tile,
            "target_base_linear": base, "target_roughness": rgh, "target_metallic": met,
            "baseColorFactor": fac + [1.0],
            "baseColorFactor_clipped": any(v > 1.0 for v in raw),
            "roughnessFactor": round(min(1.0, rf_raw), 3),
            "roughness_result_mean": round(min(1.0, rf_raw) * st["roughness_mean"], 3),
            "base_result_mean_linear": [round(f * m, 3) for f, m in zip(fac, mean)],
            "metallicFactor": met,
        }
    return out


# ===============================================================================================================
# main
# ===============================================================================================================
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--sets", default=",".join(SET_ORDER))
    ap.add_argument("--placeholder", action="store_true")
    ap.add_argument("--no-preview", action="store_true")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--downloads", default=DOWNLOADS_JSON)
    ap.add_argument("--out-dir", default=OUT_DIR)
    ap.add_argument("--map-json", default=MAP_JSON)
    ap.add_argument("--preview-dir", default=PREVIEW_DIR)
    ap.add_argument("--preview-tag", default="", help="inserted into preview file names: <set>_<tag>_tiled.jpg")
    ap.add_argument("--budget-mb", type=float, default=12.0)
    args = ap.parse_args(argv)

    wanted = [s.strip() for s in args.sets.split(",") if s.strip()]
    for s in wanted:
        if s not in DEFAULT_SETS:
            ap.error("unknown set %r (known: %s)" % (s, ", ".join(SET_ORDER)))

    prev_map = load_json(args.map_json) or {}
    prev_sets = prev_map.get("sets", {}) if isinstance(prev_map.get("sets"), dict) else {}
    dl_entries = {} if args.placeholder else download_entries(load_json(args.downloads))

    t_all = time.time()
    set_out = {}
    set_stats = {}
    placeholder_means = {}
    for set_name in SET_ORDER:
        overrides = (prev_sets.get(set_name) or {}).get("overrides") or {}
        cfg = deep_merge(DEFAULT_SETS[set_name], overrides)
        files = {ch: os.path.join(args.out_dir, "v2_%s_%s.jpg" % (set_name, ch)) for ch in ("albedo", "normal", "orm")}
        if set_name not in wanted:
            # keep the previous record for sets not rebuilt this run
            if set_name in prev_sets:
                set_out[set_name] = prev_sets[set_name]
                if prev_sets[set_name].get("stats"):
                    set_stats[set_name] = prev_sets[set_name]["stats"]
            continue
        t0 = time.time()
        entry = dl_entries.get(set_name)
        maps, prov, source = None, None, "placeholder"
        base_cfg = cfg
        if entry is not None and entry.get("enabled", True):
            cfg = effective_cfg(base_cfg, entry)
            res = int(cfg["res"])
            # the placeholder mean is the normalisation target for plaster/metal downloads
            if (cfg.get("download_albedo_target_linear") == "placeholder_mean" and not entry.get("albedo_mode")
                    and entry.get("albedo_target_linear") is None):
                prev_stats = (prev_sets.get(set_name) or {}).get("placeholder_albedo_mean_linear")
                if prev_stats:
                    placeholder_means[set_name] = prev_stats
                else:
                    pm = GENERATORS[set_name](int(base_cfg["res"]), base_cfg["tile_m"], base_cfg["placeholder"],
                                              stable_rng(set_name, args.seed))
                    placeholder_means[set_name] = [float(v) for v in pm["albedo_lin"].reshape(-1, 3).mean(0)]
            maps, prov = build_from_download(set_name, entry, cfg, placeholder_means)
            if maps is None:
                print("  [%s] download entry unusable (%s) -> placeholder" % (set_name, prov))
                prov = {"download_rejected": prov}
                cfg = base_cfg
            else:
                source = "download:%s" % entry.get("asset_id", entry.get("asset", entry.get("source", "unnamed")))
        res = int(cfg["res"])
        if maps is None:
            maps = GENERATORS[set_name](res, cfg["tile_m"], cfg["placeholder"], stable_rng(set_name, args.seed))
            prov = dict(prov or {}, generator="gen_%s" % set_name, seed=args.seed, info=maps.get("info", {}))
        alb, nrm, orm = pack_outputs(maps, cfg)
        q = cfg["jpeg"]
        blobs = {"albedo": encode_jpeg(alb, q["albedo"], 2),
                 "normal": encode_jpeg(nrm, q["normal"], 0),
                 "orm": encode_jpeg(orm, q["orm"], 0)}
        written = {ch: write_if_changed(files[ch], blobs[ch]) for ch in blobs}
        st = stats_for(alb, nrm, orm)
        set_stats[set_name] = st
        rec = {
            "res": res, "tile_m": cfg["tile_m"], "res_placeholder": base_cfg["res"],
            "tile_m_placeholder": base_cfg["tile_m"],
            "metal_default": cfg["metal"], "roughness_default": cfg["roughness"],
            "files": {ch: os.path.relpath(files[ch], ASSETS_DIR).replace("\\", "/") for ch in files},
            "blender_image_names": {ch: os.path.basename(files[ch]) for ch in files},
            "colorspace": {"albedo": "sRGB", "normal": "Non-Color", "orm": "Non-Color"},
            "jpeg_quality": q,
            "placeholder": cfg["placeholder"],
            "download_albedo_target_linear": cfg.get("download_albedo_target_linear"),
            "overrides": overrides,
            "last_run": {"source": source, "provenance": prov,
                         "bytes": {ch: len(blobs[ch]) for ch in blobs}, "rewritten": written,
                         "seconds": round(time.time() - t0, 1)},
            "stats": st,
        }
        if source == "placeholder":
            rec["placeholder_albedo_mean_linear"] = st["albedo_mean_linear"]
        elif (prev_sets.get(set_name) or {}).get("placeholder_albedo_mean_linear"):
            rec["placeholder_albedo_mean_linear"] = prev_sets[set_name]["placeholder_albedo_mean_linear"]
        elif set_name in placeholder_means:
            rec["placeholder_albedo_mean_linear"] = [round(v, 4) for v in placeholder_means[set_name]]
        if not args.no_preview:
            rec["last_run"]["previews"] = {k: os.path.relpath(v, M_DIR).replace("\\", "/")
                                           for k, v in write_previews(set_name, alb, nrm, orm, args.preview_dir,
                                                                      args.preview_tag).items()}
        set_out[set_name] = rec
        print("  [%s] %s  %dpx  tile %.2f m  %.1fs  albedo %s srgb  rough %.3f  seams a/n/o %.2f/%.2f/%.2f"
              % (set_name, source, res, cfg["tile_m"], time.time() - t0, st["albedo_mean_srgb8"],
                 st["roughness_mean"], st["seam_score"]["albedo"], st["seam_score"]["normal"],
                 st["seam_score"]["orm"]))

    # ---- size report
    total = 0
    print("\nSize report (%s):" % os.path.relpath(args.out_dir, M_DIR))
    print("  %-8s %-26s %10s %10s %10s %10s" % ("set", "source", "albedo", "normal", "orm", "set total"))
    for set_name in SET_ORDER:
        sizes = []
        for ch in ("albedo", "normal", "orm"):
            fp = os.path.join(args.out_dir, "v2_%s_%s.jpg" % (set_name, ch))
            sizes.append(os.path.getsize(fp) if os.path.isfile(fp) else 0)
        total += sum(sizes)
        src = (set_out.get(set_name) or {}).get("last_run", {}).get("source", "-")
        print("  %-8s %-26s %9.0fK %9.0fK %9.0fK %9.2fM" % (set_name, src[:26], sizes[0] / 1024, sizes[1] / 1024,
                                                           sizes[2] / 1024, sum(sizes) / 1048576))
    print("  %-8s %-26s %43.2fM  (target <= %.1f MB) %s" % ("TOTAL", "", total / 1048576, args.budget_mb,
                                                               "OK" if total <= args.budget_mb * 1048576
                                                               else "OVER BUDGET"))

    doc = {
        "_doc": ("Owned by blender/scripts/tools/pack_textures.py (regenerated each run; only sets.<set>.overrides "
                 "is read back and deep-merged over the script defaults). Texture sets per V2_CONTRACT.md s5. "
                 "Paths in 'files' are relative to M/assets/. albedo = sRGB; normal = OpenGL (+Y up), Non-Color; "
                 "orm = R AO, G roughness, B metalness, Non-Color. UV = world metres / tile_m. 'slots' gives "
                 "suggested glTF factors so that factor x texture-mean hits the contract table (factors clipped "
                 "to <= 1 per glTF spec). Parquet herringbone spine runs along texture U."),
        "generated_by": "blender/scripts/tools/pack_textures.py",
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "seed": args.seed,
        "downloads_json": os.path.relpath(args.downloads, M_DIR).replace("\\", "/"),
        "downloads_used": bool(dl_entries),
        "budget_mb": args.budget_mb,
        "total_bytes": total,
        "sets": set_out,
        "slots": slot_suggestions(set_stats, {k: v.get("tile_m") for k, v in set_out.items() if v}),
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.map_json)), exist_ok=True)
    with open(args.map_json + ".tmp", "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)
    os.replace(args.map_json + ".tmp", args.map_json)
    print("\nwrote %s  (%.1fs total)" % (os.path.relpath(args.map_json, M_DIR), time.time() - t_all))
    return 0


if __name__ == "__main__":
    sys.exit(main())
