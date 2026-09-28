import bpy, math, os
D = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else r"C:\Users\utopi\OneDrive\Desktop\Earth _WorldBuilding\_Museum\blender\_dev\core"
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'
sc.view_settings.view_transform = 'Standard'
sc.eevee.taa_render_samples = 8
sc.render.resolution_x = sc.render.resolution_y = 16
w = bpy.data.worlds.new("W"); sc.world = w
w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.0
me = bpy.data.meshes.new("p"); me.from_pydata([(-5,-5,0),(5,-5,0),(5,5,0),(-5,5,0)],[],[(0,1,2,3)])
ob = bpy.data.objects.new("p", me); sc.collection.objects.link(ob)
mat = bpy.data.materials.new("m")
try: mat.use_nodes = True
except Exception: pass
b = mat.node_tree.nodes.get('Principled BSDF')
b.inputs['Base Color'].default_value = (1,1,1,1); b.inputs['Roughness'].default_value = 1.0
b.inputs['Specular IOR Level'].default_value = 0.0
me.materials.append(mat)
cd = bpy.data.cameras.new("c"); cd.type='ORTHO'; cd.ortho_scale = 0.5
cam = bpy.data.objects.new("c", cd); cam.location=(0,0,5); sc.collection.objects.link(cam); sc.camera = cam
sc.render.image_settings.file_format = 'OPEN_EXR'
def shot(tag):
    fp = os.path.join(D, f"units_{tag}.exr"); sc.render.filepath = fp
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(fp); px = list(img.pixels[:4*16*16])
    v = sum(px[0::4])/(16*16); print("UNITS", tag, round(v,4)); bpy.data.images.remove(img)
ld = bpy.data.lights.new("s", 'SUN'); ld.energy = 1.0; ld.angle = 0.0
lo = bpy.data.objects.new("s", ld); sc.collection.objects.link(lo)
shot("sun1")
bpy.data.objects.remove(lo)
ld2 = bpy.data.lights.new("pt", 'POINT'); ld2.energy = 4*math.pi; ld2.shadow_soft_size = 0.0
lo2 = bpy.data.objects.new("pt", ld2); lo2.location=(0,0,1); sc.collection.objects.link(lo2)
shot("point4pi_at1m")
ld3 = bpy.data.lights.new("ar", 'AREA'); ld3.energy = math.pi; ld3.size = 0.2
bpy.data.objects.remove(lo2)
lo3 = bpy.data.objects.new("ar", ld3); lo3.location=(0,0,1); sc.collection.objects.link(lo3)
shot("area_pi_at1m")
