
import bpy, math

WALL_T = 0.4

def get_or_make_collection(name, parent=None):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(coll)
    return coll

def link_only(obj, coll):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)

def box(name, cx, cy, cz, sx, sy, sz, coll):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, cz))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    link_only(obj, coll)
    return obj

def wall_run(name_prefix, axis, const_pos, run_from, run_to, z0, height, coll, doors=None):
    doors = sorted(doors or [], key=lambda d: d[0])
    segments = []
    cursor = run_from
    for dc, dw, dh in doors:
        d_from, d_to = dc - dw / 2, dc + dw / 2
        if d_from > cursor:
            segments.append((cursor, d_from, 0, height))
        segments.append((d_from, d_to, dh, height))
        cursor = d_to
    if cursor < run_to:
        segments.append((cursor, run_to, 0, height))
    objs = []
    for i, (sf, st, zlo, zhi) in enumerate(segments):
        length = st - sf
        if length <= 0.02:
            continue
        seg_h = zhi - zlo
        mid = (sf + st) / 2
        z_center = z0 + zlo + seg_h / 2
        if axis == 'x':
            o = box(f"{name_prefix}_{i}", mid, const_pos, z_center, length, WALL_T, seg_h, coll)
        else:
            o = box(f"{name_prefix}_{i}", const_pos, mid, z_center, WALL_T, length, seg_h, coll)
        objs.append(o)
    return objs

def slab(name, cx, cy, cz, sx, sy, coll, thickness=0.2):
    return box(name, cx, cy, cz, sx, sy, thickness, coll)

def room_shell(room_id, cx, cy, z0, size_x, size_y, height, coll, doors_by_wall=None, skip_walls=None):
    doors_by_wall = doors_by_wall or {}
    skip_walls = set(skip_walls or [])
    x0, x1 = cx - size_x / 2, cx + size_x / 2
    y0, y1 = cy - size_y / 2, cy + size_y / 2
    slab(f"GEO-{room_id}_floor", cx, cy, z0, size_x, size_y, coll)
    slab(f"GEO-{room_id}_ceiling", cx, cy, z0 + height, size_x, size_y, coll)
    if 'north' not in skip_walls:
        n_doors = [(cx + off, w, h) for off, w, h in doors_by_wall.get('north', [])]
        wall_run(f"GEO-{room_id}_wallN", 'x', y1, x0, x1, z0, height, coll, n_doors)
    if 'south' not in skip_walls:
        s_doors = [(cx + off, w, h) for off, w, h in doors_by_wall.get('south', [])]
        wall_run(f"GEO-{room_id}_wallS", 'x', y0, x0, x1, z0, height, coll, s_doors)
    if 'east' not in skip_walls:
        e_doors = [(cy + off, w, h) for off, w, h in doors_by_wall.get('east', [])]
        wall_run(f"GEO-{room_id}_wallE", 'y', x1, y0, y1, z0, height, coll, e_doors)
    if 'west' not in skip_walls:
        w_doors = [(cy + off, w, h) for off, w, h in doors_by_wall.get('west', [])]
        wall_run(f"GEO-{room_id}_wallW", 'y', x0, y0, y1, z0, height, coll, w_doors)

def rotunda_shell(cx, cy, z0, outer_r, height, coll, doors):
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=outer_r, depth=height, location=(cx, cy, z0 + height / 2))
    outer = bpy.context.active_object
    outer.name = "GEO-rotunda_outer"
    link_only(outer, coll)
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=outer_r - WALL_T, depth=height + 0.4, location=(cx, cy, z0 + height / 2))
    inner = bpy.context.active_object
    inner.name = "GEO-rotunda_inner_cutter"
    mod = outer.modifiers.new('Hollow', type='BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.object = inner
    mod.solver = 'EXACT'
    bpy.context.view_layer.objects.active = outer
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(inner, do_unlink=True)
    dir_vec = {'east': (1, 0), 'west': (-1, 0), 'north': (0, 1), 'south': (0, -1)}
    for i, d in enumerate(doors):
        dx, dy = dir_vec[d['side']]
        w, h = d['width'], d['height']
        ccx, ccy = cx + dx * outer_r, cy + dy * outer_r
        sx, sy = (WALL_T * 4, w) if d['side'] in ('east', 'west') else (w, WALL_T * 4)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(ccx, ccy, z0 + h / 2))
        cutter = bpy.context.active_object
        cutter.name = f"GEO-rotunda_door_cutter_{i}"
        cutter.scale = (sx, sy, h)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        mod = outer.modifiers.new(f'DoorCut{i}', type='BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.object = cutter
        mod.solver = 'EXACT'
        bpy.context.view_layer.objects.active = outer
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(cutter, do_unlink=True)
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=outer_r, depth=0.2, location=(cx, cy, z0))
    floor = bpy.context.active_object
    floor.name = "GEO-rotunda_floor"
    link_only(floor, coll)
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=outer_r, depth=0.2, location=(cx, cy, z0 + height))
    ceil_ = bpy.context.active_object
    ceil_.name = "GEO-rotunda_ceiling"
    link_only(ceil_, coll)
    return outer

def build_stairs(name, x0, y, z0, step_w, step_depth, step_height, count, coll):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x0, y, z0 + step_height / 2))
    step = bpy.context.active_object
    step.name = f"GEO-{name}_step"
    step.scale = (step_depth, step_w, step_height)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    arr = step.modifiers.new('Array', type='ARRAY')
    arr.count = count
    arr.use_relative_offset = False
    arr.use_constant_offset = True
    arr.constant_offset_displace = (step_depth, 0, step_height)
    link_only(step, coll)
    return step

print("museum_lib defined")


def wall_segments_for_room(cx, cy, sx, sy, sides):
    segs = []
    for side in sides:
        if side == 'north':
            segs.append(dict(axis='x', const=cy + sy / 2, lo=cx - sx / 2, hi=cx + sx / 2, normal=(0, -1, 0)))
        elif side == 'south':
            segs.append(dict(axis='x', const=cy - sy / 2, lo=cx - sx / 2, hi=cx + sx / 2, normal=(0, 1, 0)))
        elif side == 'east':
            segs.append(dict(axis='y', const=cx + sx / 2, lo=cy - sy / 2, hi=cy + sy / 2, normal=(-1, 0, 0)))
        elif side == 'west':
            segs.append(dict(axis='y', const=cx - sx / 2, lo=cy - sy / 2, hi=cy + sy / 2, normal=(1, 0, 0)))
    return segs

def make_art_frame(name, position, normal, frame_w, image_path, coll, min_ar=0.4, max_ar=2.5):
    import mathutils
    img = bpy.data.images.load(image_path, check_existing=True)
    iw, ih = img.size[0], img.size[1]
    ar = (ih / iw) if iw else 1.0
    ar = max(min(ar, max_ar), min_ar)
    height = frame_w * ar

    bpy.ops.mesh.primitive_plane_add(size=1)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (frame_w, height, 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    nvec = mathutils.Vector(normal).normalized()
    z_axis = mathutils.Vector((0, 0, 1))
    x_axis = z_axis.cross(nvec)
    if x_axis.length < 1e-6:
        x_axis = mathutils.Vector((1, 0, 0))
    x_axis.normalize()
    y_axis = nvec.cross(x_axis).normalized()
    rot_mat = mathutils.Matrix((x_axis, y_axis, nvec)).transposed().to_4x4()
    obj.matrix_world = rot_mat
    obj.location = position

    mat = bpy.data.materials.new(f"MAT-{name}")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes['Principled BSDF']
    tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image = img
    mat.node_tree.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.5
    bsdf.inputs['Metallic'].default_value = 0.0
    obj.data.materials.append(mat)
    link_only(obj, coll)
    return obj, height

def build_gallery_exhibits(gallery_id, cx, cy, z0, sx, sy, sides, artists, images_root, coll,
                            frame_w_max=1.3, frame_w_min=0.5, inset=1.0, eye_z=1.7, wall_clear=0.25):
    segs = wall_segments_for_room(cx, cy, sx, sy, sides)
    works = [(a, w) for a in artists for w in a['works']]
    n = len(works)
    if n == 0:
        return
    usable = [(s['hi'] - s['lo']) - 2 * inset for s in segs]
    total_usable = sum(usable)
    counts = [max(1, round(n * u / total_usable)) for u in usable]
    diff = n - sum(counts)
    order = sorted(range(len(segs)), key=lambda i: -usable[i])
    i = 0
    while diff != 0:
        seg_i = order[i % len(order)]
        if diff > 0:
            counts[seg_i] += 1
            diff -= 1
        elif counts[seg_i] > 1:
            counts[seg_i] -= 1
            diff += 1
        i += 1

    pitches = [usable[i] / counts[i] for i in range(len(segs))]
    frame_w = max(frame_w_min, min(frame_w_max, min(pitches) * 0.75))

    placed = 0
    wi = 0
    for si, seg in enumerate(segs):
        c = counts[si]
        pitch = pitches[si]
        for k in range(c):
            if wi >= n:
                break
            a, w = works[wi]
            wi += 1
            pos_in_seg = seg['lo'] + inset + pitch / 2 + k * pitch
            if seg['axis'] == 'x':
                wx, wy = pos_in_seg, seg['const']
            else:
                wx, wy = seg['const'], pos_in_seg
            px = wx + seg['normal'][0] * wall_clear
            py = wy + seg['normal'][1] * wall_clear
            pz = z0 + eye_z
            img_path = os.path.join(images_root, w['image'].replace('/', os.sep))
            name = f"ART-{a['slug']}__{w['id']}"
            if not os.path.exists(img_path):
                print("MISSING IMAGE:", img_path)
                continue
            make_art_frame(name, (px, py, pz), seg['normal'], frame_w, img_path, coll)
            placed += 1
    print(f"{gallery_id}: placed {placed}/{n} works across {len(segs)} walls, "
          f"pitches={[round(p, 2) for p in pitches]} frame_w={frame_w:.2f}m")


def add_moldings(room_id, cx, cy, sx, sy, sides, z0, height, coll, doors_by_side=None,
                  base_h=0.18, rail_h=0.12, protrude=0.05):
    """Gold baseboard + picture-rail trim along a rectangular room's solid walls.
    doors_by_side: {side: [(offset_from_center, width), ...]} for sides that have
    door gaps of their own (rooms whose door lives on a neighbor's wall need
    nothing here)."""
    doors_by_side = doors_by_side or {}
    x0, x1 = cx - sx / 2, cx + sx / 2
    y0, y1 = cy - sy / 2, cy + sy / 2
    # (axis, const, lo, hi, inward_sign)
    specs = {
        'north': ('x', y1, x0, x1, -1),
        'south': ('x', y0, x0, x1, 1),
        'east': ('y', x1, y0, y1, -1),
        'west': ('y', x0, y0, y1, 1),
    }
    inward_dist = WALL_T / 2 + protrude / 2
    for side in sides:
        axis, const, lo, hi, sign = specs[side]
        cpos = const + sign * inward_dist
        raw_doors = doors_by_side.get(side, [])
        base_doors = [(d[0], d[1], base_h) for d in raw_doors]
        wall_run(f"GEO-{room_id}_baseboard_{side}", axis, cpos, lo, hi, z0, base_h, coll, doors=base_doors)
        rail_z0 = z0 + height - 0.75
        wall_run(f"GEO-{room_id}_picturerail_{side}", axis, cpos, lo, hi, rail_z0, rail_h, coll)


def add_door_frame(name, axis, const_pos, door_center, door_w, door_h, z0, coll, jamb_w=0.08, protrude=0.04):
    """A thin gold frame (two jambs + a lintel trim) around a rectangular door
    opening cut into a wall_run-style wall."""
    inward = WALL_T / 2 + protrude / 2
    cpos = const_pos  # caller passes the already-signed inward position
    if axis == 'x':
        box(f"{name}_jambL", door_center - door_w / 2 - jamb_w / 2, cpos, z0 + door_h / 2,
            jamb_w, protrude, door_h + jamb_w, coll)
        box(f"{name}_jambR", door_center + door_w / 2 + jamb_w / 2, cpos, z0 + door_h / 2,
            jamb_w, protrude, door_h + jamb_w, coll)
        box(f"{name}_lintel", door_center, cpos, z0 + door_h + jamb_w / 2,
            door_w + jamb_w * 2, protrude, jamb_w, coll)
    else:
        box(f"{name}_jambL", cpos, door_center - door_w / 2 - jamb_w / 2, z0 + door_h / 2,
            protrude, jamb_w, door_h + jamb_w, coll)
        box(f"{name}_jambR", cpos, door_center + door_w / 2 + jamb_w / 2, z0 + door_h / 2,
            protrude, jamb_w, door_h + jamb_w, coll)
        box(f"{name}_lintel", cpos, door_center, z0 + door_h + jamb_w / 2,
            protrude, door_w + jamb_w * 2, jamb_w, coll)

print("moldings + door-frame helpers added")


def rotunda_ring(name, cx, cy, z0, outer_r, height, coll, doors):
    """A thin decorative ring (baseboard or picture-rail) around the rotunda,
    with the same east/west door cuts as the main wall."""
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=outer_r, depth=height, location=(cx, cy, z0 + height / 2))
    ring = bpy.context.active_object
    ring.name = f"{name}_outer"
    link_only(ring, coll)
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=outer_r - 0.06, depth=height + 0.4, location=(cx, cy, z0 + height / 2))
    inner = bpy.context.active_object
    inner.name = f"{name}_inner_cutter"
    mod = ring.modifiers.new('Hollow', type='BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.object = inner
    mod.solver = 'EXACT'
    bpy.context.view_layer.objects.active = ring
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(inner, do_unlink=True)
    dir_vec = {'east': (1, 0), 'west': (-1, 0), 'north': (0, 1), 'south': (0, -1)}
    for i, d in enumerate(doors):
        dx, dy = dir_vec[d['side']]
        w = d['width']
        ccx, ccy = cx + dx * outer_r, cy + dy * outer_r
        sx, sy = (0.5, w) if d['side'] in ('east', 'west') else (w, 0.5)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(ccx, ccy, z0 + height / 2))
        cutter = bpy.context.active_object
        cutter.name = f"{name}_door_cutter_{i}"
        cutter.scale = (sx, sy, height + 0.4)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        mod = ring.modifiers.new(f'DoorCut{i}', type='BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.object = cutter
        mod.solver = 'EXACT'
        bpy.context.view_layer.objects.active = ring
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(cutter, do_unlink=True)
    return ring
