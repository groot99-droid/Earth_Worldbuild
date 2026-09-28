"""render_framings.py - render the standard check framings (framings.json) from any museum .blend.

Two modes in one file:

A) Inside Blender (headless). Renders framings; NEVER saves the .blend; restores every scene
   setting it touched and removes its temporary camera, so it is also safe to import/call from
   another script that later saves.

   "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" -b <file.blend> --python-exit-code 1 ^
       --python render_framings.py -- --framings all|name1,name2 --out <dir>
       [--res 1280 720] [--samples 64] [--engine BLENDER_EEVEE|CYCLES] [--prefix str]
       [--framings-file <path>] [--fov-source lens|fov] [--percent 100]
       [--device CPU|GPU] [--skip-existing] [--dry-run] [--list]

   * Camera: a temporary camera "_TMP-render_framings_cam" is created, placed at framing.pos and
     aimed with look_at(pos -> target, up = +Z) (no roll), lens = framing.lens_mm on a 36 mm
     sensor with HORIZONTAL sensor fit (so the horizontal FOV is 2*atan(18/lens) at any aspect).
     --fov-source fov uses framing.fov_deg as the VERTICAL fov instead (for matching three.js
     screenshots 1:1; note framings.json v1 fov_deg values do not match lens_mm at 16:9).
   * Colour management (view transform AgX, look, exposure) is left exactly as in the file.
   * Output: <out>/<prefix><name>.png (8-bit RGB PNG). A line "RENDER_FRAMINGS_DONE {json}" is
     printed at the end; the process exits non-zero on any failure (with --python-exit-code 1 it
     also does so on an uncaught exception).

   Import use (inside Blender):
       sys.path.insert(0, r"...\\blender\\scripts\\tools"); import render_framings as RF
       RF.render_framings(["gallery_a_north"], out_dir, res=(960, 540), samples=32)

B) Desktop Python with PIL (no bpy): build a labelled contact sheet.

   <_RAG\\.venv\\Scripts\\python.exe> render_framings.py --contact-sheet <dir>
       [--pattern "baseline_*.png"] [--sheet-out <dir>/_contact_sheet.jpg] [--cols 3]
       [--thumb 640] [--title "text"] [--order name1,name2,...]
"""
import sys
import os
import json
import math
import time
import glob as _glob

try:
    import bpy  # noqa: F401
    import mathutils
    IN_BLENDER = True
except ImportError:  # desktop python (contact-sheet mode)
    bpy = None
    mathutils = None
    IN_BLENDER = False

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.dirname(TOOLS_DIR)
DEFAULT_FRAMINGS = os.path.join(SCRIPTS_DIR, "framings.json")
TMP_CAM_NAME = "_TMP-render_framings_cam"
SENSOR_WIDTH_MM = 36.0
# Canonical framing order (framings.json order); used for contact sheets.
CANONICAL_ORDER = ["rotunda_wide", "rotunda_dome", "through_door", "spine1_west", "gallery_a_north",
                   "gallery_a_corner", "gallery_a_art", "stairs", "gallery_f"]


# --------------------------------------------------------------------------------------------
# framings
# --------------------------------------------------------------------------------------------
def load_framings(path=None):
    """Return (framings_dict, meta_dict). framings_dict: name -> {pos, target, lens_mm, fov_deg, ...}."""
    path = path or DEFAULT_FRAMINGS
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    fr = data.get("framings", data)
    if not isinstance(fr, dict) or not fr:
        raise ValueError("no framings found in %s" % path)
    for name, v in fr.items():
        for key in ("pos", "target"):
            if key not in v or len(v[key]) != 3:
                raise ValueError("framing %r lacks a 3-vector %r" % (name, key))
        if "lens_mm" not in v and "fov_deg" not in v:
            raise ValueError("framing %r needs lens_mm or fov_deg" % name)
    meta = {k: v for k, v in data.items() if k != "framings"} if "framings" in data else {}
    return fr, meta


def select_framings(framings, spec):
    """spec: 'all' | 'a,b,c' | list. Returns ordered list of names; raises on unknown names."""
    if spec is None or (isinstance(spec, str) and spec.strip().lower() in ("", "all", "*")):
        return list(framings.keys())
    names = [s.strip() for s in (spec.split(",") if isinstance(spec, str) else spec) if s.strip()]
    unknown = [n for n in names if n not in framings]
    if unknown:
        raise KeyError("unknown framing(s) %s; available: %s" % (unknown, ", ".join(framings)))
    return names


def look_at_matrix(pos, target, up=(0.0, 0.0, 1.0)):
    """4x4 world matrix for a Blender camera at pos looking at target (camera looks down its -Z,
    local +Y is 'up'). Roll-free with respect to world +Z; handles straight-up/down views."""
    p = mathutils.Vector(pos)
    fwd = mathutils.Vector(target) - p
    if fwd.length < 1e-9:
        raise ValueError("pos and target coincide: %s" % (tuple(pos),))
    fwd.normalize()
    upv = mathutils.Vector(up).normalized()
    right = fwd.cross(upv)
    if right.length < 1e-6:  # looking straight along +-Z: pick world +Y as the image-up hint
        right = fwd.cross(mathutils.Vector((0.0, 1.0, 0.0)))
    right.normalize()
    cam_up = right.cross(fwd).normalized()
    m = mathutils.Matrix.Identity(4)
    for i in range(3):
        m[i][0] = right[i]
        m[i][1] = cam_up[i]
        m[i][2] = -fwd[i]
        m[i][3] = p[i]
    return m


def lens_to_vfov_deg(lens_mm, aspect=16.0 / 9.0, sensor_w=SENSOR_WIDTH_MM):
    """Vertical FOV (deg) of a horizontal-fit sensor_w camera at the given aspect (three.js fov)."""
    return math.degrees(2.0 * math.atan((sensor_w / aspect) / 2.0 / lens_mm))


# --------------------------------------------------------------------------------------------
# Blender side
# --------------------------------------------------------------------------------------------
def _set_engine(scene, engine):
    aliases = {"EEVEE": ["BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"],
               "BLENDER_EEVEE": ["BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"],
               "BLENDER_EEVEE_NEXT": ["BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"],
               "CYCLES": ["CYCLES"], "WORKBENCH": ["BLENDER_WORKBENCH"],
               "BLENDER_WORKBENCH": ["BLENDER_WORKBENCH"]}
    last = None
    for cand in aliases.get(engine.upper(), [engine]):
        try:
            scene.render.engine = cand
            return cand
        except (TypeError, ValueError) as ex:
            last = ex
    raise ValueError("cannot set render engine %r: %s" % (engine, last))


def _set_samples(scene, engine, samples):
    if samples is None:
        return
    if engine.startswith("BLENDER_EEVEE"):
        scene.eevee.taa_render_samples = int(samples)
    elif engine == "CYCLES":
        scene.cycles.samples = int(samples)


def _setup_cycles_device(scene, device):
    if device is None or device.upper() == "CPU":
        scene.cycles.device = "CPU"
        return "CPU"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for backend in ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL"):
            try:
                prefs.compute_device_type = backend
            except TypeError:
                continue
            prefs.get_devices()
            gpus = [d for d in prefs.devices if d.type != "CPU"]
            if gpus:
                for d in prefs.devices:
                    d.use = d.type != "CPU"
                scene.cycles.device = "GPU"
                return "GPU:" + backend
    except Exception as ex:  # pragma: no cover
        print("render_framings: GPU setup failed (%s); using CPU" % ex)
    scene.cycles.device = "CPU"
    return "CPU"


class _SceneState:
    """Snapshot/restore of every scene setting render_framings touches."""

    def __init__(self, scene):
        r = scene.render
        im = r.image_settings
        self.scene = scene
        self.vals = dict(
            camera=scene.camera, engine=r.engine, res_x=r.resolution_x, res_y=r.resolution_y,
            pct=r.resolution_percentage, filepath=r.filepath, use_file_extension=r.use_file_extension,
            fmt=im.file_format, cmode=im.color_mode, cdepth=im.color_depth,
            compression=getattr(im, "compression", None),
            eevee_samples=scene.eevee.taa_render_samples if hasattr(scene, "eevee") else None,
            cycles_samples=scene.cycles.samples if hasattr(scene, "cycles") else None,
            cycles_device=scene.cycles.device if hasattr(scene, "cycles") else None,
            view=(scene.view_settings.view_transform, scene.view_settings.look,
                  scene.view_settings.exposure, scene.view_settings.gamma),
        )

    def restore(self):
        s, v, r = self.scene, self.vals, self.scene.render
        im = r.image_settings
        try:
            r.engine = v["engine"]
        except Exception:
            pass
        r.resolution_x, r.resolution_y, r.resolution_percentage = v["res_x"], v["res_y"], v["pct"]
        r.filepath, r.use_file_extension = v["filepath"], v["use_file_extension"]
        for attr, key in (("file_format", "fmt"), ("color_mode", "cmode"), ("color_depth", "cdepth"),
                          ("compression", "compression")):
            if v[key] is not None:
                try:
                    setattr(im, attr, v[key])
                except Exception:
                    pass
        if v["eevee_samples"] is not None:
            s.eevee.taa_render_samples = v["eevee_samples"]
        if v["cycles_samples"] is not None:
            s.cycles.samples = v["cycles_samples"]
        if v["cycles_device"] is not None:
            try:
                s.cycles.device = v["cycles_device"]
            except Exception:
                pass
        vt, look, exp, gam = v["view"]
        vs = s.view_settings
        if (vs.view_transform, vs.look, vs.exposure, vs.gamma) != (vt, look, exp, gam):
            vs.view_transform, vs.look, vs.exposure, vs.gamma = vt, look, exp, gam
        cam = v["camera"]
        try:
            s.camera = cam if (cam is None or cam.name in bpy.data.objects) else None
        except ReferenceError:
            s.camera = None


def get_temp_camera(scene):
    """Create (or reuse) the temporary render camera, linked to the scene's master collection."""
    obj = bpy.data.objects.get(TMP_CAM_NAME)
    if obj is None or obj.type != "CAMERA":
        cam = bpy.data.cameras.new(TMP_CAM_NAME)
        obj = bpy.data.objects.new(TMP_CAM_NAME, cam)
    if obj.name not in scene.collection.objects:
        scene.collection.objects.link(obj)
    obj.hide_render = False
    obj.hide_viewport = False
    return obj


def remove_temp_camera():
    obj = bpy.data.objects.get(TMP_CAM_NAME)
    if obj is not None:
        cam = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if cam is not None and cam.users == 0:
            bpy.data.cameras.remove(cam)


def place_camera(cam_obj, framing, fov_source="lens", clip=(0.05, 1000.0)):
    """Place/aim cam_obj for a framing dict. Returns a description dict."""
    cam_obj.matrix_world = look_at_matrix(framing["pos"], framing["target"])
    c = cam_obj.data
    c.type = "PERSP"
    c.shift_x = c.shift_y = 0.0
    c.clip_start, c.clip_end = clip
    c.dof.use_dof = False
    c.sensor_width = SENSOR_WIDTH_MM
    if fov_source == "fov" and framing.get("fov_deg"):
        c.sensor_fit = "VERTICAL"
        c.sensor_height = SENSOR_WIDTH_MM * 9.0 / 16.0
        c.angle_y = math.radians(float(framing["fov_deg"]))
    else:
        c.sensor_fit = "HORIZONTAL"
        c.lens = float(framing.get("lens_mm") or 0) or \
            (SENSOR_WIDTH_MM * 9.0 / 16.0) / 2.0 / math.tan(math.radians(framing["fov_deg"]) / 2.0)
    return dict(lens=round(c.lens, 3), sensor_fit=c.sensor_fit,
                hfov=round(math.degrees(c.angle_x), 2), loc=[round(x, 3) for x in cam_obj.matrix_world.translation])


def render_framings(names=None, out_dir=None, res=(1280, 720), samples=64, engine="BLENDER_EEVEE",
                    prefix="", framings_file=None, fov_source="lens", percent=100, device=None,
                    skip_existing=False, dry_run=False, scene=None):
    """Render framings to <out_dir>/<prefix><name>.png. Never saves the .blend; restores scene state
    and deletes the temporary camera afterwards (also on error). Returns a list of result dicts."""
    scene = scene or bpy.context.scene
    framings, _meta = load_framings(framings_file)
    names = select_framings(framings, names)
    out_dir = os.path.abspath(out_dir or os.path.join(os.getcwd(), "renders"))
    os.makedirs(out_dir, exist_ok=True)
    state = _SceneState(scene)
    results = []
    try:
        eng = _set_engine(scene, engine)
        dev = _setup_cycles_device(scene, device) if eng == "CYCLES" else None
        _set_samples(scene, eng, samples)
        r = scene.render
        r.resolution_x, r.resolution_y = int(res[0]), int(res[1])
        r.resolution_percentage = int(percent)
        im = r.image_settings
        im.file_format = "PNG"
        im.color_mode = "RGB"
        im.color_depth = "8"
        try:
            im.compression = 15
        except Exception:
            pass
        r.use_file_extension = False
        cam = get_temp_camera(scene)
        scene.camera = cam
        vs = scene.view_settings
        print("render_framings: blend=%s engine=%s%s samples=%s res=%dx%d@%d%% view=%s look=%s exp=%.2f"
              % (bpy.data.filepath, eng, (" device=%s" % dev) if dev else "", samples, res[0], res[1],
                 percent, vs.view_transform, vs.look, vs.exposure))
        for name in names:
            fr = framings[name]
            out_png = os.path.join(out_dir, "%s%s.png" % (prefix, name))
            info = place_camera(cam, fr, fov_source=fov_source)
            rec = dict(name=name, path=out_png, **info)
            if skip_existing and os.path.exists(out_png):
                rec["status"] = "skipped"
                results.append(rec)
                print("SKIPPED", name, out_png)
                continue
            if dry_run:
                rec["status"] = "dry_run"
                results.append(rec)
                print("DRYRUN", name, json.dumps(info))
                continue
            t0 = time.time()
            r.filepath = out_png
            bpy.ops.render.render(write_still=True, scene=scene.name)
            ok = os.path.exists(out_png) and os.path.getsize(out_png) > 0
            rec.update(status="ok" if ok else "missing_output", seconds=round(time.time() - t0, 1))
            results.append(rec)
            print("RENDERED" if ok else "RENDER_FAILED", name, out_png, "%.1fs" % rec["seconds"], flush=True)
    finally:
        state.restore()
        remove_temp_camera()
    return results


def _parse_blender_args(argv):
    import argparse
    ap = argparse.ArgumentParser(prog="render_framings.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--framings", default="all", help="all | comma-separated framing names")
    ap.add_argument("--out", default=None, help="output directory")
    ap.add_argument("--res", nargs=2, type=int, default=[1280, 720], metavar=("W", "H"))
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--engine", default="BLENDER_EEVEE")
    ap.add_argument("--prefix", default="")
    ap.add_argument("--framings-file", default=None)
    ap.add_argument("--fov-source", choices=["lens", "fov"], default="lens")
    ap.add_argument("--percent", type=int, default=100)
    ap.add_argument("--device", default=None, help="Cycles only: CPU (default) or GPU")
    ap.add_argument("--skip-existing", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="place the camera and report, no render")
    ap.add_argument("--list", action="store_true", help="list framings and exit")
    return ap.parse_args(argv)


def blender_main(argv):
    a = _parse_blender_args(argv)
    if a.list:
        fr, _ = load_framings(a.framings_file)
        for n, v in fr.items():
            print("FRAMING", n, v.get("pos"), "->", v.get("target"), "lens", v.get("lens_mm"),
                  "vfov16:9=%.1f" % lens_to_vfov_deg(v["lens_mm"]) if v.get("lens_mm") else "")
        return 0
    if not a.out:
        print("render_framings: --out is required")
        return 2
    t0 = time.time()
    try:
        res = render_framings(a.framings, a.out, res=tuple(a.res), samples=a.samples, engine=a.engine,
                              prefix=a.prefix, framings_file=a.framings_file, fov_source=a.fov_source,
                              percent=a.percent, device=a.device, skip_existing=a.skip_existing,
                              dry_run=a.dry_run)
    except Exception as ex:
        import traceback
        traceback.print_exc()
        print("RENDER_FRAMINGS_FAILED", repr(ex))
        return 1
    bad = [r for r in res if r["status"] not in ("ok", "skipped", "dry_run")]
    print("RENDER_FRAMINGS_DONE " + json.dumps(dict(
        n=len(res), failed=[r["name"] for r in bad], seconds=round(time.time() - t0, 1),
        files=[r["path"] for r in res])))
    return 1 if bad else 0


# --------------------------------------------------------------------------------------------
# Desktop side: contact sheet (PIL)
# --------------------------------------------------------------------------------------------
def _font(size, bold=False):
    from PIL import ImageFont
    cands = (["segoeuib.ttf", "arialbd.ttf"] if bold else []) + ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"]
    for c in cands:
        for d in ("", os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")):
            try:
                return ImageFont.truetype(os.path.join(d, c) if d else c, size)
            except OSError:
                continue
    return ImageFont.load_default()


def contact_sheet(src_dir, pattern="*.png", out_path=None, cols=3, thumb_w=640, title=None,
                  order=None, framings_file=None, strip_prefix=None):
    """Build a labelled grid JPG from PNGs in src_dir. Label = framing name (+ lens/desc from framings.json)."""
    from PIL import Image, ImageDraw
    files = sorted(_glob.glob(os.path.join(src_dir, pattern)))
    files = [f for f in files if not os.path.basename(f).startswith("_")]
    if not files:
        raise FileNotFoundError("no images match %s in %s" % (pattern, src_dir))
    pre = strip_prefix
    if pre is None:
        stem = pattern.split("*")[0] if "*" in pattern else ""
        pre = stem
    def key_name(f):
        n = os.path.splitext(os.path.basename(f))[0]
        return n[len(pre):] if pre and n.startswith(pre) else n
    order = order or CANONICAL_ORDER
    rank = {n: i for i, n in enumerate(order)}
    files.sort(key=lambda f: (rank.get(key_name(f), 999), key_name(f)))
    try:
        framings, _ = load_framings(framings_file)
    except Exception:
        framings = {}
    ims = [Image.open(f).convert("RGB") for f in files]
    w0, h0 = ims[0].size
    th_w = thumb_w
    th_h = int(round(th_w * h0 / float(w0)))
    lab_h = 44
    pad = 10
    head = 56 if title else 0
    rows = int(math.ceil(len(ims) / float(cols)))
    W = cols * th_w + (cols + 1) * pad
    H = head + rows * (th_h + lab_h) + (rows + 1) * pad
    sheet = Image.new("RGB", (W, H), (22, 20, 18))
    dr = ImageDraw.Draw(sheet)
    f_title, f_lab, f_small = _font(26, True), _font(19, True), _font(14)
    if title:
        dr.text((pad + 2, 14), title, fill=(236, 226, 205), font=f_title)
    for i, (f, im) in enumerate(zip(files, ims)):
        r_, c_ = divmod(i, cols)
        x = pad + c_ * (th_w + pad)
        y = head + pad + r_ * (th_h + lab_h + pad)
        sheet.paste(im.resize((th_w, th_h), Image.LANCZOS), (x, y))
        n = key_name(f)
        fr = framings.get(n, {})
        dr.text((x + 2, y + th_h + 3), "%d. %s" % (i + 1, n), fill=(240, 214, 150), font=f_lab)
        sub = []
        if fr.get("lens_mm"):
            sub.append("%smm" % fr["lens_mm"])
        if "slice" in fr:
            sub.append("slice" if fr["slice"] else "phase 3")
        if fr.get("desc"):
            sub.append(fr["desc"])
        s = "  |  ".join(sub)
        if dr.textlength(s, font=f_small) > th_w - 4:
            while s and dr.textlength(s + "...", font=f_small) > th_w - 4:
                s = s[:-1]
            s = s.rstrip() + "..."
        dr.text((x + 2, y + th_h + 25), s, fill=(170, 162, 150), font=f_small)
    out_path = out_path or os.path.join(src_dir, "_contact_sheet.jpg")
    sheet.save(out_path, quality=90, optimize=True)
    return out_path, len(ims), sheet.size


def desktop_main(argv):
    import argparse
    ap = argparse.ArgumentParser(prog="render_framings.py (desktop)")
    ap.add_argument("--contact-sheet", required=True, metavar="DIR")
    ap.add_argument("--pattern", default="*.png")
    ap.add_argument("--sheet-out", default=None)
    ap.add_argument("--cols", type=int, default=3)
    ap.add_argument("--thumb", type=int, default=640)
    ap.add_argument("--title", default=None)
    ap.add_argument("--order", default=None)
    ap.add_argument("--framings-file", default=None)
    a = ap.parse_args(argv)
    out, n, size = contact_sheet(a.contact_sheet, a.pattern, a.sheet_out, a.cols, a.thumb, a.title,
                                 a.order.split(",") if a.order else None, a.framings_file)
    print("CONTACT_SHEET", out, n, "images", "%dx%d" % size)
    return 0


def _argv_after_dashes():
    if "--" in sys.argv:
        return sys.argv[sys.argv.index("--") + 1:]
    return [] if IN_BLENDER else sys.argv[1:]


if __name__ == "__main__":
    if IN_BLENDER:
        rc = blender_main(_argv_after_dashes())
        if rc:
            sys.exit(rc)
    else:
        sys.exit(desktop_main(_argv_after_dashes()))
