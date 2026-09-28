"""Headless scene inventory: blender -b museum.blend --python dump_inventory.py -- <out.json>
Writes every object's name, collection, type, world AABB (Blender Z-up), materials,
vert/face counts, modifiers and custom props, plus lights/cameras. Read-only."""
import bpy, json, sys, mathutils
out = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'inventory.json'
dg = bpy.context.evaluated_depsgraph_get()
objs = []
for o in bpy.data.objects:
    corners = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
    lo = [round(min(c[i] for c in corners), 4) for i in range(3)]
    hi = [round(max(c[i] for c in corners), 4) for i in range(3)]
    e = dict(name=o.name, type=o.type, collections=[c.name for c in o.users_collection],
             aabb_min=lo, aabb_max=hi, location=[round(v, 4) for v in o.location],
             rotation=[round(v, 4) for v in o.rotation_euler], scale=[round(v, 4) for v in o.scale],
             modifiers=[m.type for m in o.modifiers],
             props={k: (o[k] if isinstance(o[k], (int, float, str)) else str(o[k])) for k in o.keys() if not k.startswith('_')})
    if o.type == 'MESH':
        ev = o.evaluated_get(dg); me = ev.to_mesh()
        e.update(verts=len(me.vertices), faces=len(me.polygons), uv_layers=[u.name for u in o.data.uv_layers],
                 materials=[s.material.name if s.material else None for s in o.material_slots])
        ev.to_mesh_clear()
    elif o.type == 'LIGHT':
        L = o.data
        e.update(light_type=L.type, energy=L.energy, color=list(L.color),
                 size=getattr(L, 'size', None), size_y=getattr(L, 'size_y', None), shape=getattr(L, 'shape', None))
    objs.append(e)
scene = bpy.context.scene
meta = dict(blender=bpy.app.version_string, engine=scene.render.engine,
            view_transform=scene.view_settings.view_transform, look=scene.view_settings.look,
            exposure=scene.view_settings.exposure,
            world=(scene.world.name if scene.world else None),
            texts=[t.name for t in bpy.data.texts],
            cameras=[dict(name=o.name, loc=list(o.location), rot=list(o.rotation_euler), lens=o.data.lens) for o in bpy.data.objects if o.type == 'CAMERA'])
json.dump(dict(meta=meta, objects=objs), open(out, 'w', encoding='utf-8'), indent=1)
print('INVENTORY_WRITTEN', out, len(objs))
