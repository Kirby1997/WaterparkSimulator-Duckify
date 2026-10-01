"""Copies the game's guest skeletons into art/ref/*.json for the Blender build.

art/ref/ is git-ignored: it holds game data. Run from DuckMod/:
    uv run --with UnityPy==1.25.3 python art/extract_reference.py \
        --game "/mnt/e/SteamLibrary/steamapps/common/WaterPark Simulator"
"""
import argparse
import json
import os

import UnityPy
from UnityPy.helpers.MeshHelper import MeshHandler

# tag -> (asset file, mesh name, mesh whose skinned renderer supplies the bones).
# The female first-person mesh has no renderer of its own: the game swaps it into the male renderer,
# so its bone indices refer to that renderer's bone list.
WANT = {
    "body_m": ("resources.assets", "CC_Body_Male_LOD0", "CC_Body_Male_LOD0"),
    "body_f": ("resources.assets", "CC_Body_Female_LOD0", "CC_Body_Female_LOD0"),
    "arms_m": ("sharedassets1.assets", "First_Person_Male", "First_Person_Male"),
    "arms_f": ("sharedassets1.assets", "First_Person_Female", "First_Person_Male"),
}


def find_renderer(env, mesh_name):
    for o in env.objects:
        if o.type.name != "SkinnedMeshRenderer":
            continue
        smr = o.read()
        if smr.m_Mesh.file_id != 0 or smr.m_Mesh.path_id == 0:
            continue
        mesh = smr.m_Mesh.read()
        if mesh.m_Name == mesh_name:
            return smr, mesh
    raise SystemExit(f"No skinned renderer uses {mesh_name}; the game may have renamed it.")


def find_mesh(env, mesh_name):
    for o in env.objects:
        if o.type.name == "Mesh":
            mesh = o.read()
            if mesh.m_Name == mesh_name:
                return mesh
    raise SystemExit(f"No mesh named {mesh_name}; the game may have renamed it.")


def export(env, mesh_name, bones_from):
    smr, bone_mesh = find_renderer(env, bones_from)
    mesh = bone_mesh if mesh_name == bones_from else find_mesh(env, mesh_name)
    h = MeshHandler(mesh)
    h.process()
    if len(mesh.m_BindPose) != len(smr.m_Bones):
        raise SystemExit(f"{mesh.m_Name} has {len(mesh.m_BindPose)} bind poses but the renderer "
                         f"has {len(smr.m_Bones)} bones.")
    transforms = [b.read() for b in smr.m_Bones]
    names = [t.m_GameObject.read().m_Name for t in transforms]
    by_id = {b.path_id: n for b, n in zip(smr.m_Bones, names)}
    parents = {n: by_id.get(t.m_Father.path_id) for n, t in zip(names, transforms)}
    bind = [[[m.e00, m.e01, m.e02, m.e03], [m.e10, m.e11, m.e12, m.e13],
             [m.e20, m.e21, m.e22, m.e23], [m.e30, m.e31, m.e32, m.e33]] for m in mesh.m_BindPose]
    all_tris = h.get_triangles()
    tris = [all_tris[i] for i in range(len(mesh.m_SubMeshes))]
    return dict(name=mesh.m_Name, verts=h.m_Vertices, normals=h.m_Normals, tris=tris,
                weights=h.m_BoneWeights, bidx=h.m_BoneIndices, bones=names, bind=bind, parents=parents)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", required=True, help="Waterpark Simulator install folder")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "ref"))
    args = ap.parse_args()
    data_dir = os.path.join(args.game, "WaterparkSimulator_Data")
    os.makedirs(args.out, exist_ok=True)
    envs = {}
    for tag, (asset, mesh_name, bones_from) in WANT.items():
        if asset not in envs:
            envs[asset] = UnityPy.load(os.path.join(data_dir, asset))
        env = envs[asset]
        d = export(env, mesh_name, bones_from)
        with open(os.path.join(args.out, tag + ".json"), "w") as f:
            json.dump(d, f)
        print(f"{tag}: {d['name']}, {len(d['verts'])} vertices, {len(d['bones'])} bones")


if __name__ == "__main__":
    main()
