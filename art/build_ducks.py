"""Builds, checks and exports every duck. Run from DuckMod/ after art/extract_reference.py:

"/mnt/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" --background --factory-startup \
    --python art/build_ducks.py -- --ref art/ref --out art/out --previews art/previews --icon thunderstore/icon.png
"""
import argparse
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import duckgen  # noqa: E402
import duckmesh_io  # noqa: E402
import ref_import  # noqa: E402
import render_views  # noqa: E402
import rigging  # noqa: E402

STYLES = ["classic", "mallard", "rubber"]
SEXES = {"m": "male", "f": "female"}
BUDGET = {"body": 7000, "wings": 2000}
# Rough poses for the review renders. Local X bends most limbs; a wrong sign bends backwards,
# which still shows tearing, the thing the render is for.
POSES = {
    "walk": {"thigh_l": (-0.5, 0, 0), "thigh_r": (0.4, 0, 0), "calf_r": (0.6, 0, 0),
             "upperarm_l": (0.4, 0, 0), "upperarm_r": (-0.4, 0, 0), "head": (0, 0, 0.4), "spine_03": (0, 0, 0.15)},
    "sit": {"thigh_l": (-1.5, 0, 0), "thigh_r": (-1.5, 0, 0), "calf_l": (1.5, 0, 0), "calf_r": (1.5, 0, 0),
            "lowerarm_l": (0, 0, 0.8), "lowerarm_r": (0, 0, -0.8)},
}


def srgb_bytes(hexc):
    return tuple(int(hexc[i:i + 2], 16) for i in (0, 2, 4)) + (255,)


def collect(parts, bone_order):
    """Flatten Blender parts into .duckmesh arrays in Unity space, one submesh per material."""
    subs, positions, normals, vweights = {}, [], [], []
    for ob in parts:
        me = ob.data
        me.calc_loop_triangles()
        base = len(positions)
        mw = ob.matrix_world
        nw = mw.to_3x3().inverted().transposed()
        names = [g.name for g in ob.vertex_groups]
        for v in me.vertices:
            p = mw @ v.co
            n = (nw @ v.normal).normalized()
            positions.append((-p.x, p.z, -p.y))
            normals.append((-n.x, n.z, -n.y))
            vweights.append({names[g.group]: g.weight for g in v.groups if g.weight > 1e-4})
        for t in me.loop_triangles:
            m = me.materials[t.material_index]
            sub = subs.setdefault(m.name, [srgb_bytes(m["hex"]), float(m["smoothness"]), []])
            a, b, c = t.vertices
            sub[2].extend((base + a, base + c, base + b))
    used = [b for b in bone_order if any(b in w for w in vweights)]
    index = {b: i for i, b in enumerate(used)}
    bone_idx, weights = [], []
    for vi, w in enumerate(vweights):
        top = sorted(w.items(), key=lambda kv: -kv[1])[:4]
        total = sum(x for _, x in top)
        if total <= 0:
            raise RuntimeError(f"vertex {vi} has no weights")
        bone_idx.append(tuple([index[n] for n, _ in top] + [0] * (4 - len(top))))
        weights.append(tuple([x / total for _, x in top] + [0.0] * (4 - len(top))))
    return dict(bones=used, positions=positions, normals=normals, bone_idx=bone_idx, weights=weights,
                submeshes=[(s[0], s[1], s[2]) for s in subs.values()])


def remap_bind(mesh, bind_from, bind_to):
    """Move vertices from one mesh's bind space to another's, blended by weight (linear blend skinning)."""
    mats = {n: Matrix(bind_to[n]).inverted() @ Matrix(bind_from[n]) for n in mesh["bones"]}
    for i, (p, n) in enumerate(zip(mesh["positions"], mesh["normals"])):
        acc, accn = Vector(), Vector()
        for bi, w in zip(mesh["bone_idx"][i], mesh["weights"][i]):
            if w > 0:
                m = mats[mesh["bones"][bi]]
                acc += w * (m @ Vector(p))
                accn += w * (m.to_3x3() @ Vector(n))
        mesh["positions"][i] = tuple(acc)
        mesh["normals"][i] = tuple(accn.normalized())


def check(mesh, part, skeleton, label):
    tris = sum(len(s[2]) for s in mesh["submeshes"]) // 3
    assert tris <= BUDGET[part], f"{label}: {tris} triangles, over the {BUDGET[part]} budget"
    assert set(mesh["bones"]) <= set(skeleton), f"{label}: unknown bones {set(mesh['bones']) - set(skeleton)}"
    assert all(abs(sum(w) - 1) < 0.01 for w in mesh["weights"]), f"{label}: weights not normalised"
    return tris


def pose_render(arm, parts, prefix):
    for ob in parts:
        if not any(m.type == "ARMATURE" for m in ob.modifiers):
            ob.modifiers.new("Armature", "ARMATURE").object = arm
    for pose, rot in POSES.items():
        for pb in arm.pose.bones:
            pb.rotation_mode = "XYZ"
            pb.rotation_euler = rot.get(pb.name, (0, 0, 0))
        bpy.context.view_layer.update()
        render_views.render(f"{prefix}_{pose}", views=("three",))
    for pb in arm.pose.bones:
        pb.rotation_euler = (0, 0, 0)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--previews", required=True)
    ap.add_argument("--icon")
    args = ap.parse_args(argv)
    # Blender resolves relative render paths against the .blend file, and there is none here.
    args.previews = os.path.abspath(args.previews)
    if args.icon:
        args.icon = os.path.abspath(args.icon)
    os.makedirs(args.out, exist_ok=True)
    os.makedirs(args.previews, exist_ok=True)

    for code, sex in SEXES.items():
        bpy.ops.wm.read_factory_settings(use_empty=True)
        render_views.setup_scene()
        arm, human, body_ref = ref_import.load(args.ref, f"body_{code}")
        arms_ref = ref_import.load_json(args.ref, f"arms_{code}")
        human.hide_render = True
        bind_body = dict(zip(body_ref["bones"], body_ref["bind"]))
        bind_arms = dict(zip(arms_ref["bones"], arms_ref["bind"]))
        lineup = []
        for i, style in enumerate(STYLES):
            parts, meta = duckgen.build_duck(style, arm)
            rigging.rig(parts, human, meta)
            body = collect(parts, body_ref["bones"])
            label = f"{style}_{sex}_body"
            tris = check(body, "body", body_ref["bones"], label)
            duckmesh_io.write(os.path.join(args.out, label + ".duckmesh"), **body)

            wing_parts = rigging.cut_wings(parts)
            wings = collect(wing_parts, arms_ref["bones"])
            remap_bind(wings, bind_body, bind_arms)
            wlabel = f"{style}_{sex}_wings"
            wtris = check(wings, "wings", arms_ref["bones"], wlabel)
            duckmesh_io.write(os.path.join(args.out, wlabel + ".duckmesh"), **wings)
            print(f"EXPORTED {label}: {tris} tris, {len(body['bones'])} bones; {wlabel}: {wtris} tris")

            pose_render(arm, parts, os.path.join(args.previews, f"{style}_{sex}"))
            for ob in wing_parts:
                bpy.data.objects.remove(ob)
            if args.icon and style == "classic" and code == "m":
                render_views.render_icon(args.icon, meta["head_center"])
            for ob in parts:
                ob.hide_render = True
            lineup.append((parts, (i - 1) * 1.4))
        for parts, dx in lineup:
            for ob in parts:
                ob.hide_render = False
                ob.location.x += dx
        render_views.render(os.path.join(args.previews, f"lineup_{sex}"), views=("front", "three"))


main()
