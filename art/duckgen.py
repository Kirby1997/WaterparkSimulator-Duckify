"""Procedural humanoid duck built on the game's guest skeleton."""
import bpy, bmesh, math, os, sys
from mathutils import Vector, Matrix, Quaternion
sc=lambda: bpy.context.scene
FWD=Vector((0,-1,0)); UP=Vector((0,0,1)); X=Vector((1,0,0))

def srgb(h):
    c=[int(h[i:i+2],16)/255 for i in (0,2,4)]
    return tuple(((x+0.055)/1.055)**2.4 if x>0.04045 else x/12.92 for x in c)
def mat(name,hexc,rough=0.6):
    m=bpy.data.materials.get(name)
    if m: return m
    m=bpy.data.materials.new(name); m.use_nodes=True
    b=m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value=(*srgb(hexc),1); b.inputs['Roughness'].default_value=rough
    m.diffuse_color=(*srgb(hexc),1); return m

class Part:
    """collects primitives into one bmesh, then fuses them with a voxel remesh"""
    def __init__(s,name): s.name=name; s.bm=bmesh.new()
    def _add(s,bm2,M):
        bm2.transform(M); me=bpy.data.meshes.new('tmp'); bm2.to_mesh(me); s.bm.from_mesh(me); bpy.data.meshes.remove(me); bm2.free()
    def ell(s,c,r,rot=Quaternion()):
        bm=bmesh.new(); bmesh.ops.create_uvsphere(bm,u_segments=32,v_segments=20,radius=1)
        s._add(bm,Matrix.Translation(c)@rot.to_matrix().to_4x4()@Matrix.Diagonal((*r,1))); return s
    def cap(s,a,b,r1,r2=None,flat=1.0,twist=0.0):
        r2=r1 if r2 is None else r2; a,b=Vector(a),Vector(b); d=b-a; L=d.length
        q=UP.rotation_difference(d.normalized())@Quaternion(UP,twist)
        bm=bmesh.new(); bmesh.ops.create_cone(bm,cap_ends=True,segments=24,radius1=r1,radius2=r2,depth=L)
        s._add(bm,Matrix.Translation((a+b)/2)@q.to_matrix().to_4x4()@Matrix.Diagonal((1,flat,1,1)))
        s.ell(a,(r1,r1*flat,r1),q); s.ell(b,(r2,r2*flat,r2),q); return s
    def feather(s,a,b,r1,r2,normal,flat=0.35):
        a,b=Vector(a),Vector(b); z=(b-a).normalized(); y=(normal-normal.dot(z)*z).normalized(); x=y.cross(z)
        R=Matrix((x,y,z)).transposed().to_quaternion()
        L=(b-a).length
        bm=bmesh.new(); bmesh.ops.create_cone(bm,cap_ends=True,segments=24,radius1=r1,radius2=r2,depth=L)
        s._add(bm,Matrix.Translation((a+b)/2)@R.to_matrix().to_4x4()@Matrix.Diagonal((1,flat,1,1)))
        s.ell(a,(r1,r1*flat,r1),R); s.ell(b,(r2,r2*flat,r2),R); return s
    def build(s,material,voxel=0.012,smooth=6,ratio=None,target=None):
        me=bpy.data.meshes.new(s.name); s.bm.to_mesh(me); s.bm.free()
        ob=bpy.data.objects.new(s.name,me); sc().collection.objects.link(ob)
        r=ob.modifiers.new('fuse','REMESH'); r.mode='VOXEL'; r.voxel_size=voxel
        if smooth: sm=ob.modifiers.new('sm','SMOOTH'); sm.iterations=smooth; sm.factor=0.6
        if target:
            dg=bpy.context.evaluated_depsgraph_get(); n=len(ob.evaluated_get(dg).data.polygons)
            ratio=min(1.0,target/max(n,1))
        if ratio and ratio<1: dc=ob.modifiers.new('dec','DECIMATE'); dc.ratio=ratio
        dg=bpy.context.evaluated_depsgraph_get()
        me2=bpy.data.meshes.new_from_object(ob.evaluated_get(dg)); old=ob.data; ob.modifiers.clear(); ob.data=me2; bpy.data.meshes.remove(old)
        me2.materials.append(material)
        for p in me2.polygons: p.use_smooth=True
        return ob

def bone_pts(arm):
    return {b.name:(arm.matrix_world@b.head_local, arm.matrix_world@b.tail_local) for b in arm.data.bones}

STYLES={
 'classic':dict(body='f6f3ec',bill='f5a01e',feet='f5a01e',chub=1.0,head=1.0,neck=0.0,tuft=True),
 'mallard':dict(body='8f7a63',chest='6b4a3a',bill='e3c23c',feet='f08a24',hood='1d6a3c',ring='f4f1ea',chub=0.92,head=0.92,neck=0.015),
 'rubber': dict(body='ffd21f',bill='ff7a1a',feet='ff7a1a',chub=1.25,head=1.2,neck=-0.04,shiny=True),
}

def build_duck(style,arm,budget=None):
    S=STYLES[style]; P=bone_pts(arm); H=lambda n:P[n][0]; T=lambda n:P[n][1]
    rough=0.3 if S.get('shiny') else 0.65
    M={k:mat(f'{style}_{k}',v,rough) for k,v in S.items() if isinstance(v,str)}
    ch=S['chub']; hs=S['head']
    pelvis,sp2,sp4,neck,head=H('pelvis'),H('spine_02'),H('spine_04'),H('neck_01'),H('head')
    out=[]
    body=Part(style+'_body')
    # pear torso: bottom bulb around hips, top toward chest
    body.ell(pelvis+UP*0.04+FWD*0.03,(0.25*ch,0.22*ch,0.26*ch))
    body.ell(sp4-UP*0.02+FWD*0.03,(0.2*ch,0.18*ch,0.2*ch))
    body.ell((pelvis+sp4)/2+FWD*0.05,(0.23*ch,0.21*ch,0.3*ch))
    # tail feathers
    tq=Quaternion(X,math.radians(-35))
    body.ell(pelvis-FWD*0.2*ch+UP*0.1,(0.13*ch,0.1,0.05),tq)
    # neck + head
    hc=head+UP*(0.09+S['neck'])+FWD*0.02
    body.cap(sp4+UP*0.1,hc,0.11*ch,0.1*hs)
    hr=Vector((0.165,0.17,0.17))*hs
    body.ell(hc,hr)
    if S.get('tuft'):
        top=hc+UP*hr.z*0.92
        for a in (-25,0,25):
            q=Quaternion(FWD,math.radians(a))
            p1=top+q@(UP*0.05)-FWD*0.01; p2=p1+q@(UP*0.04)+FWD*0.035
            body.feather(top-UP*0.03,p1,0.03,0.022,X,0.55); body.feather(p1,p2,0.022,0.008,X,0.55)
    # thighs: feather puffs so the body reads as one
    for s in 'lr':
        th,ca=H('thigh_'+s),H('calf_'+s)
        body.cap(th,th.lerp(ca,0.55),0.1*ch,0.075*ch)
    # wings: arms with feather fingers
    for s in 'lr':
        cl,ua,la,hd=H('clavicle_'+s),H('upperarm_'+s),H('lowerarm_'+s),H('hand_'+s)
        body.cap(ua.lerp(cl,0.3),la,0.085*ch,0.065*ch)
        body.cap(la,hd,0.065*ch,0.05*ch)
        spread=(H('index_01_'+s)-H('pinky_01_'+s)).normalized()
        fdir=(T('middle_03_'+s)-hd).normalized()
        nrm=fdir.cross(spread).normalized()
        # wing tip: broad paddle + three long primaries that follow the finger bones
        tipc=hd+fdir*0.1
        body.feather(la.lerp(hd,0.5),tipc,0.065*ch,0.06,nrm,0.42)
        for f,w in (('index',1.0),('middle',1.12),('pinky',0.9)):
            a,b=H(f'{f}_01_{s}'),T(f'{f}_03_{s}')
            d=(b-a).normalized()
            body.feather(hd.lerp(a,0.5),a+d*0.17*w,0.042,0.02,nrm,0.36)
        tb=T('thumb_03_'+s); ta=H('thumb_01_'+s)
        body.feather(ta,ta+(tb-ta).normalized()*0.1,0.03,0.015,nrm,0.4)
    if not style=='mallard' or True:
        out.append(body.build(M['body'],target=1900))
    if 'chest' in S:
        c=Part(style+'_chest'); c.ell(sp4+FWD*(0.11*ch)-UP*0.02,(0.16*ch,0.1*ch,0.14*ch)); out.append(c.build(M['chest'],target=160))
    if 'hood' in S:
        h=Part(style+'_hood'); h.ell(hc+UP*0.004,hr*1.035); h.cap(hc,hc.lerp(sp4,0.4),0.108*hs,0.104*hs); out.append(h.build(M['hood'],target=260))
        r=Part(style+'_ring'); nr=0.1*hs+ (0.11*ch-0.1*hs)*0.45; r.cap(hc.lerp(sp4,0.42),hc.lerp(sp4,0.48),nr+0.012,nr+0.014); out.append(r.build(M['ring'],voxel=0.008,target=70))
    # bill: wide, flat, rounded
    bill=Part(style+'_bill')
    bc=hc+FWD*hr.y*0.92-UP*hr.z*0.15
    bill.ell(bc+FWD*0.05,(0.085*hs,0.1*hs,0.035*hs),Quaternion(X,math.radians(-8)))
    bill.ell(bc+FWD*0.035-UP*0.035*hs,(0.07*hs,0.085*hs,0.025*hs),Quaternion(X,math.radians(5)))
    out.append(bill.build(M['bill'],voxel=0.006,smooth=4,target=180))
    # legs + webbed feet
    feet=Part(style+'_feet')
    for s in 'lr':
        th,ca,ft,bl=H('thigh_'+s),H('calf_'+s),H('foot_'+s),H('ball_'+s)
        feet.cap(th.lerp(ca,0.5),ca,0.05,0.042); feet.cap(ca,ft,0.042,0.034)
        heel=Vector((ft.x,ft.y+0.02,0.03))
        fdir=(Vector((bl.x,bl.y,0))-Vector((ft.x,ft.y,0))).normalized()
        side=Vector((fdir.y,-fdir.x,0))
        feet.ell(heel+fdir*0.06,(0.07,0.07,0.028),fdir.to_track_quat('Y','Z'))
        for a in (-0.55,0,0.55):
            dirv=(fdir*math.cos(a)+side*math.sin(a)).normalized()
            feet.cap(heel+fdir*0.05,heel+fdir*0.05+dirv*0.17,0.03,0.022,flat=1.0)
        # web between toes
        tipc=heel+fdir*0.18
        feet.ell(tipc,(0.1,0.06,0.016),fdir.to_track_quat('Y','Z'))
    out.append(feet.build(M['feet'],voxel=0.008,smooth=4,target=520))
    # eyes
    ew=mat('eye_white','ffffff',0.15); eb=mat('eye_black','0f1216',0.1)
    for sx in (-1,1):
        side=X*sx
        ep=hc+side*hr.x*0.5+FWD*hr.y*0.72+UP*hr.z*0.3
        e=Part(style+'_eyeW'); e.ell(ep,(0.055*hs,0.035*hs,0.065*hs),Quaternion(UP,math.radians(20*sx)))
        out.append(e.build(ew,voxel=0.004,smooth=2,target=48))
        pp=ep+FWD*0.03*hs+side*0.004+UP*0.006
        p=Part(style+'_pupil'); p.ell(pp,(0.026*hs,0.012*hs,0.032*hs),Quaternion(UP,math.radians(20*sx)))
        out.append(p.build(eb,voxel=0.003,smooth=1,target=28))
    return out
