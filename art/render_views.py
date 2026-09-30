import bpy, sys, os, math
from mathutils import Vector
argv=sys.argv[sys.argv.index('--')+1:]
out=argv[0]; engine=argv[1] if len(argv)>1 else 'WORKBENCH'
sc=bpy.context.scene
sc.render.engine='BLENDER_WORKBENCH' if engine=='WORKBENCH' else 'BLENDER_EEVEE'
sc.render.resolution_x=1600; sc.render.resolution_y=900
if engine=='WORKBENCH':
    sc.display.shading.light='STUDIO'; sc.display.shading.color_type='MATERIAL' if any(o.active_material for o in sc.objects if o.type=='MESH') else 'OBJECT'
    sc.display.shading.show_cavity=True
meshes=[o for o in sc.objects if o.type=='MESH' and not o.hide_render and o.name!='Floor']
lo=Vector((1e9,)*3); hi=Vector((-1e9,)*3)
dg=bpy.context.evaluated_depsgraph_get()
for o in meshes:
    for c in o.bound_box:
        w=o.matrix_world@Vector(c); lo=Vector(map(min,lo,w)); hi=Vector(map(max,hi,w))
ctr=(lo+hi)/2; size=max(hi.x-lo.x, (hi.z-lo.z)*16/9)*1.1
cam=bpy.data.objects.get('RenderCam') or bpy.data.objects.new('RenderCam',bpy.data.cameras.new('RenderCam'))
if cam.name not in sc.collection.objects: sc.collection.objects.link(cam)
cam.data.type='ORTHO'; cam.data.ortho_scale=size; sc.camera=cam
views={'front':(0,-1,0),'side':(1,0,0),'three':(0.7,-1,0.25)}
for name,d in (views.items() if len(argv)<3 else [(k,views[k]) for k in argv[2].split(',')]):
    dv=Vector(d).normalized(); cam.location=ctr+dv*10
    cam.rotation_euler=(-dv).to_track_quat('-Z','Y').to_euler()
    if name=='three': cam.data.type='PERSP'; cam.data.lens=50; cam.location=ctr+dv*size*1.9
    else: cam.data.type='ORTHO'
    sc.render.filepath=out+'_'+name+'.png'; bpy.ops.render.render(write_still=True)
