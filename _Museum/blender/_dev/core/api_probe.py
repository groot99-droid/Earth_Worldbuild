import bpy
sc = bpy.context.scene
e = sc.eevee
print("EEVEE_PROPS", [p.identifier for p in e.bl_rna.properties if not p.identifier.startswith('bl_')])
try:
    print("RTOPT", [p.identifier for p in e.ray_tracing_options.bl_rna.properties])
except Exception as ex: print("no rt options", ex)
me = bpy.data.meshes.new("t")
print("MESH has set_sharp_from_angle", hasattr(me, 'set_sharp_from_angle'), "shade_smooth", hasattr(me,'shade_smooth'))
m = bpy.data.materials.new("probe_mat")
print("MAT node_tree after new:", m.node_tree is not None, "use_nodes", m.use_nodes)
if m.node_tree: print([n.type for n in m.node_tree.nodes])
print("MAT props", [p for p in ('surface_render_method','blend_method','use_transparent_shadow','use_backface_culling','use_backface_culling_shadow','use_transparency_overlap','use_raytrace_refraction','shadow_method') if hasattr(m,p)])
p = None
if m.node_tree:
    for n in m.node_tree.nodes:
        if n.type=='BSDF_PRINCIPLED': p=n
if p: print("PRINC inputs", [i.name for i in p.inputs])
L = bpy.data.lights.new("l",'POINT')
print("LIGHT props", [x.identifier for x in L.bl_rna.properties if x.identifier in ('use_shadow','shadow_soft_size','radius','use_custom_distance','cutoff_distance','use_soft_falloff','exposure','normalize','shadow_jitter')])
o = bpy.data.objects.new("o", me)
print("OBJ vis", [x for x in ('visible_shadow','visible_camera','hide_render') if hasattr(o,x)])
print("CAM", [x.identifier for x in bpy.data.cameras.new('c').bl_rna.properties if 'sensor' in x.identifier or 'angle' in x.identifier])
print("RENDER", sc.render.engine, sc.render.film_transparent, sc.render.filter_size, sc.view_settings.view_transform)
import bmesh
print("BMESH has from_mesh join doc:", bmesh.types.BMesh.from_mesh.__doc__[:300])
