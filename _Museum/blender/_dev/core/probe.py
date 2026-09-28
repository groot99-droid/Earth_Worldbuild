import bpy
sc = bpy.context.scene
print("SCENES", [s.name for s in bpy.data.scenes], "cam", sc.camera and sc.camera.name, "res", sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage, "engine", sc.render.engine)
def walk(c, d=0):
    print("  "*d + "COLL", c.name, len(c.objects), [ch.name for ch in c.children])
    for ch in c.children: walk(ch, d+1)
walk(sc.collection)
for vl in sc.view_layers:
    print("VL", vl.name)
    def w2(lc, d=0):
        print("  "*d, lc.name, "exclude", lc.exclude, "hide", lc.hide_viewport)
        for ch in lc.children: w2(ch, d+1)
    w2(vl.layer_collection)
print("IMAGES", len(bpy.data.images), [ (i.name, tuple(i.size), i.filepath[:60]) for i in list(bpy.data.images)[:5]])
print("MATS", len(bpy.data.materials), sorted(m.name for m in bpy.data.materials if not m.name.startswith('MAT-ART'))[:40])
print("WORLD", sc.world.name if sc.world else None, sc.world.use_nodes if sc.world else None)
if sc.world and sc.world.node_tree:
    for n in sc.world.node_tree.nodes: print("  WN", n.type, n.name)
print("EEVEE", sc.eevee.taa_render_samples, getattr(sc.eevee,'use_raytracing',None))
for o in bpy.data.objects:
    if o.type=='LIGHT': print("LIGHT", o.name, o.data.type, o.data.energy, tuple(o.data.color), getattr(o.data,'shadow_soft_size',None))
print("VIEW", sc.view_settings.view_transform, sc.view_settings.look, sc.view_settings.exposure, sc.display_settings.display_device)
print("MESH COUNT", len(bpy.data.meshes))
o = bpy.data.objects['GEO-rotunda_outer']
print("rot outer verts", len(o.data.vertices), len(o.data.polygons))
m = bpy.data.materials['MAT-wall_plaster_cream']
print("mat nodes", [n.type for n in m.node_tree.nodes], m.use_backface_culling, getattr(m,'surface_render_method',None), getattr(m,'blend_method',None))
print(bpy.app.version_string)
