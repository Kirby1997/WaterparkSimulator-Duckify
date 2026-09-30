import bpy, sys, os, math, bmesh
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import import_ref, duckgen
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
arm,body=import_ref.load('body_m'); body.hide_render=True
stats={}
for i,st in enumerate(['classic','mallard','rubber']):
    parts=duckgen.build_duck(st,arm)
    stats[st]=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in parts)
    for p in parts: p.location.x+=(i-1)*1.15
print('TRIS',stats)
w=bpy.data.worlds.new('W'); sc.world=w; w.use_nodes=True; bg=w.node_tree.nodes['Background']; bg.inputs['Color'].default_value=(0.55,0.75,0.82,1); bg.inputs['Strength'].default_value=1.0
sun=bpy.data.objects.new('Sun',bpy.data.lights.new('Sun','SUN')); sun.data.energy=3.0; sun.data.angle=0.2; sun.rotation_euler=(math.radians(45),0,math.radians(-30)); sc.collection.objects.link(sun)
fl=bpy.data.meshes.new('floor'); bm=bmesh.new(); bmesh.ops.create_grid(bm,x_segments=1,y_segments=1,size=8); bm.to_mesh(fl)
fo=bpy.data.objects.new('Floor',fl); sc.collection.objects.link(fo); fl.materials.append(duckgen.mat('floor','cfe8ee',0.9))
sc.view_settings.view_transform='Standard'
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE,'duck_concepts.blend'))
