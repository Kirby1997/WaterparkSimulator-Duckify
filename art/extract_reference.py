import UnityPy,json
from UnityPy.helpers.MeshHelper import MeshHandler
D="/mnt/e/SteamLibrary/steamapps/common/WaterPark Simulator/WaterparkSimulator_Data/"
env=UnityPy.load(D+"resources.assets")
objs={o.path_id:o for o in env.objects}
want={49585:"body_m",49810:"body_f",49441:"duckhelmet_m",49318:"duckhelmet_f",49566:"mascot_head_m",49751:"mascot_body_m"}
def tr(pid):
    t=objs[pid].read()
    return t
for sid,tag in want.items():
    s=objs[sid].read()
    mesh=s.m_Mesh.read()
    h=MeshHandler(mesh); h.process()
    bones=[]
    ids=[b.path_id for b in s.m_Bones]
    # collect full hierarchy from root upward
    allt={}
    def add(pid):
        if pid in allt or pid==0: return
        t=objs[pid].read()
        allt[pid]=t
        add(t.m_Father.path_id)
    for b in ids: add(b)
    tf={}
    for pid,t in allt.items():
        tf[pid]=dict(name=t.m_GameObject.read().m_Name,parent=t.m_Father.path_id if t.m_Father.path_id in allt else 0,
            p=list(t.m_LocalPosition.__dict__.values()) if hasattr(t.m_LocalPosition,'__dict__') else None,
            r=[t.m_LocalRotation.x,t.m_LocalRotation.y,t.m_LocalRotation.z,t.m_LocalRotation.w],
            s=[t.m_LocalScale.x,t.m_LocalScale.y,t.m_LocalScale.z])
        tf[pid]['p']=[t.m_LocalPosition.x,t.m_LocalPosition.y,t.m_LocalPosition.z]
    bind=[]
    for m in mesh.m_BindPose:
        bind.append([[m.e00,m.e01,m.e02,m.e03],[m.e10,m.e11,m.e12,m.e13],[m.e20,m.e21,m.e22,m.e23],[m.e30,m.e31,m.e32,m.e33]])
    subs=[]
    for i in range(len(mesh.m_SubMeshes)):
        subs.append(h.get_triangles()[i] if callable(getattr(h,'get_triangles',None)) else None)
    out=dict(name=mesh.m_Name,verts=h.m_Vertices,normals=h.m_Normals,uv=h.m_UV0,
        weights=h.m_BoneWeights, bidx=h.m_BoneIndices,
        bone_ids=[str(b) for b in ids],transforms={str(k):v for k,v in tf.items()},bind=bind,
        tris=subs, mats=[m.read().m_Name for m in s.m_Materials])
    json.dump(out,open(f'ref/{tag}.json','w'))
    print(tag,mesh.m_Name,len(h.m_Vertices or []),'subs',len(subs),'bones',len(ids),'hier',len(tf),out['mats'])
