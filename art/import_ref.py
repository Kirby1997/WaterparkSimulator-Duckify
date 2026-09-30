import bpy, json, sys, os
from mathutils import Matrix, Vector
HERE=os.path.dirname(os.path.abspath(__file__))
REF=os.path.join(HERE,'..','ref')
# Unity (x,y,z) -> Blender (-x,-z,y)
C=Matrix(((-1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)))
def v(p): return Vector((-p[0],-p[2],p[1]))
def load(tag, arm=None, collection=None):
    d=json.load(open(os.path.join(REF,tag+'.json')))
    names=[d['transforms'][b]['name'] for b in d['bone_ids']]
    if arm is None:
        ad=bpy.data.armatures.new(tag+'_rig'); arm=bpy.data.objects.new(tag+'_rig',ad)
        bpy.context.scene.collection.objects.link(arm)
        bpy.context.view_layer.objects.active=arm
        bpy.ops.object.mode_set(mode='EDIT')
        worlds={}
        for n,bp in zip(names,d['bind']):
            M=Matrix(bp).inverted()
            worlds[n]=C@M@C.inverted()
        parent={}
        T=d['transforms']
        for b in d['bone_ids']:
            pid=str(T[b]['parent']); parent[T[b]['name']]=T[pid]['name'] if pid in T else None
        for n in names:
            eb=ad.edit_bones.new(n)
            W=worlds[n]; head=W.to_translation()
            kids=[k for k in names if parent.get(k)==n]
            if kids:
                tail=sum((worlds[k].to_translation() for k in kids),Vector())/len(kids)
                if (tail-head).length<0.005: tail=head+Vector((0,0,0.03))
            else:
                tail=head+(W.to_3x3()@Vector((0,0,1))).normalized()*0.04
            eb.head=head; eb.tail=tail
        for n in names:
            if parent.get(n) in ad.edit_bones: ad.edit_bones[n].parent=ad.edit_bones[parent[n]]
        bpy.ops.object.mode_set(mode='OBJECT')
    me=bpy.data.meshes.new(tag)
    verts=[v(p) for p in d['verts']]
    tris=[t[::-1] for sub in d['tris'] for t in sub]  # reflection flips winding
    me.from_pydata(verts,[],tris); me.update()
    if d.get('uv'):
        uvl=me.uv_layers.new(name='UV0')
        for poly in me.polygons:
            for li in poly.loop_indices:
                vi=me.loops[li].vertex_index; uvl.data[li].uv=d['uv'][vi][:2]
    ob=bpy.data.objects.new(tag,me); bpy.context.scene.collection.objects.link(ob)
    groups=[ob.vertex_groups.new(name=n) for n in names]
    for vi,(ws,ix) in enumerate(zip(d['weights'] or [],d['bidx'] or [])):
        for w,i in zip(ws,ix):
            if w>0: groups[i].add([vi],w,'ADD')
    ob.parent=arm; mod=ob.modifiers.new('Armature','ARMATURE'); mod.object=arm
    return arm,ob
if __name__=='__main__':
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    bpy.ops.wm.read_factory_settings(use_empty=True)
    armm,bm=load('body_m')
    load('duckhelmet_m',armm)
    armf,bf=load('body_f'); armf.location.x=-0.8
    load('duckhelmet_f',armf)
    arm3,b3=load('mascot_body_m'); arm3.location.x=0.8; load('mascot_head_m',arm3)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE,'ref_bodies.blend'))
    for o in bpy.data.objects:
        if o.type=='MESH': print(o.name, len(o.data.vertices), [round(x,3) for x in o.dimensions])
