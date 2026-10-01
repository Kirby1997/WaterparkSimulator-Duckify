"""Blender: rebuilds a game mesh and its armature from art/ref/<tag>.json."""
import json
import os

import bpy
from mathutils import Matrix, Vector

# Unity (x, y, z) -> Blender (-x, -z, y). A reflection, so triangle winding is reversed.
C = Matrix(((-1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))


def to_blender(p):
    return Vector((-p[0], -p[2], p[1]))


def load_json(ref_dir, tag):
    with open(os.path.join(ref_dir, tag + ".json")) as f:
        return json.load(f)


def load(ref_dir, tag):
    """Returns (armature object, mesh object, json dict). The mesh carries one vertex group per bone."""
    d = load_json(ref_dir, tag)
    names, parents = d["bones"], d["parents"]
    ad = bpy.data.armatures.new(tag + "_rig")
    arm = bpy.data.objects.new(tag + "_rig", ad)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    worlds = {n: C @ Matrix(bp).inverted() @ C.inverted() for n, bp in zip(names, d["bind"])}
    for n in names:
        eb = ad.edit_bones.new(n)
        head = worlds[n].to_translation()
        kids = [k for k in names if parents.get(k) == n]
        if kids:
            tail = sum((worlds[k].to_translation() for k in kids), Vector()) / len(kids)
            if (tail - head).length < 0.005:
                tail = head + Vector((0, 0, 0.03))
        else:
            tail = head + (worlds[n].to_3x3() @ Vector((0, 0, 1))).normalized() * 0.04
        eb.head, eb.tail = head, tail
    for n in names:
        p = parents.get(n)
        if p and p in ad.edit_bones:
            ad.edit_bones[n].parent = ad.edit_bones[p]
    bpy.ops.object.mode_set(mode="OBJECT")

    me = bpy.data.meshes.new(tag)
    tris = [t[::-1] for sub in d["tris"] for t in sub]
    me.from_pydata([to_blender(p) for p in d["verts"]], [], tris)
    me.update()
    ob = bpy.data.objects.new(tag, me)
    bpy.context.scene.collection.objects.link(ob)
    groups = [ob.vertex_groups.new(name=n) for n in names]
    for vi, (ws, ix) in enumerate(zip(d["weights"], d["bidx"])):
        for w, i in zip(ws, ix):
            if w > 0:
                groups[i].add([vi], w, "ADD")
    ob.parent = arm
    ob.modifiers.new("Armature", "ARMATURE").object = arm
    return arm, ob, d
