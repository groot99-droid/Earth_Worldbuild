import bpy, bmesh
art_imgs = set()
for o in bpy.data.objects:
    if o.name.startswith('ART-'):
        for s in o.material_slots:
            for n in s.material.node_tree.nodes:
                if n.type == 'TEX_IMAGE' and n.image: art_imgs.add(n.image)
sz = sorted((max(i.size), i.name) for i in art_imgs)
print("ARTIMG", len(art_imgs), "max", sz[-5:], "over900", sum(1 for s,_ in sz if s > 900))
# from_mesh append test
m1 = bpy.data.meshes.new('a'); m1.from_pydata([(0,0,0),(1,0,0),(0,1,0)],[],[(0,1,2)])
bm = bmesh.new(); bm.from_mesh(m1); bm.from_mesh(m1); print("FROMMESH verts", len(bm.verts), "faces", len(bm.faces))
img = sorted(art_imgs, key=lambda i: -max(i.size))[0]
print("before", img.name, tuple(img.size), img.is_dirty)
img.scale(100, 80); print("after scale", tuple(img.size), img.is_dirty)
import numpy as np
buf = np.empty(100*80*4, np.float32); img.pixels.foreach_get(buf); img.pixels.foreach_set(buf); print("after foreach_set dirty", img.is_dirty)
