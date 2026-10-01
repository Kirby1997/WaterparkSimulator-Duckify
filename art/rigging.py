"""Blender: skin a duck's parts to the game skeleton."""
import bmesh
import bpy
from mathutils import Vector

ARM = {"clavicle", "upperarm", "lowerarm", "hand", "thumb", "index", "middle", "ring", "pinky"}
LEG = {"thigh", "calf", "foot", "ball", "butt"}
# Families that leave a torso vertex. Clavicles stay: they only shrug, and the shoulders follow them.
LIMB = (ARM - {"clavicle"}) | (LEG - {"butt"})


def family(bone):
    return bone.split("_")[0]


def weights_of(ob, v):
    names = ob.vertex_groups
    return {names[g.group].name: g.weight for g in v.groups if g.weight > 1e-4}


def set_weights(ob, v, weights):
    for g in list(v.groups):
        ob.vertex_groups[g.group].remove([v.index])
    total = sum(weights.values())
    for name, w in weights.items():
        ob.vertex_groups[name].add([v.index], w / total, "REPLACE")


def transfer(ob, source):
    """Copy a source mesh's weights onto a duck part (nearest face, interpolated) and return them,
    one dict per vertex. The part's own groups are emptied first, so nothing is left from before."""
    for g in list(ob.vertex_groups):
        ob.vertex_groups.remove(g)
    for g in source.vertex_groups:
        ob.vertex_groups.new(name=g.name)
    mod = ob.modifiers.new("weights", "DATA_TRANSFER")
    mod.object = source
    mod.use_vert_data = True
    mod.data_types_verts = {"VGROUP_WEIGHTS"}
    mod.vert_mapping = "POLYINTERP_NEAREST"
    mod.layers_vgroup_select_src = "ALL"
    mod.layers_vgroup_select_dst = "NAME"
    bpy.context.view_layer.objects.active = ob
    with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob], selected_editable_objects=[ob]):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return [weights_of(ob, v) for v in ob.data.vertices]


def torso_of(human):
    """A copy of the human body without its arms and legs, so the nearest surface to any point of a
    fat duck belly is the human's torso, never the arm hanging beside it or the thigh below it."""
    names = [g.name for g in human.vertex_groups]
    bm = bmesh.new()
    bm.from_mesh(human.data)
    deform = bm.verts.layers.deform.active

    def limb(v):
        return sum(w for gi, w in v[deform].items() if family(names[gi]) in LIMB)

    bmesh.ops.delete(bm, geom=[v for v in bm.verts if limb(v) >= 0.5], context="VERTS")
    me = bpy.data.meshes.new(human.name + "_torso")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(me.name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.matrix_world = human.matrix_world.copy()
    ob.hide_render = True
    for n in names:
        ob.vertex_groups.new(name=n)
    return ob


def only(w, drop):
    """Weights without the given bone families, renormalised (empty if nothing is left)."""
    w = {n: x for n, x in w.items() if family(n) not in drop}
    total = sum(w.values())
    return {n: x / total for n, x in w.items()} if total > 0 else {}


def blend(a, wa, b, wb):
    out = {}
    for w, f in ((a, wa), (b, wb)):
        for n, x in w.items():
            out[n] = out.get(n, 0.0) + x * f
    return out


def membership(p, limbs, kind, band):
    """1 inside the duck's own arm or thigh capsules, fading to 0 a band's width outside them."""
    best = 0.0
    for k, a, b, r1, r2 in limbs:
        if k != kind:
            continue
        ab = b - a
        t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
        d = (p - (a + ab * t)).length - (r1 + (r2 - r1) * t)
        best = max(best, 1.0 if d <= 0 else max(0.0, 1.0 - d / band))
    return best * best * (3 - 2 * best)


def rig(parts, human, meta, band=0.05):
    """Weights for every part.
    Head parts (bill, eyes) follow only the head, and so does the duck's head ball.
    The legs-and-feet part takes the human's leg weights and never follows the arms.
    Everything else follows the human's arms or thighs only inside the duck's own arm and thigh
    shapes (meta["limbs"]), blending over `band` metres into the torso's weights."""
    bone_names = [g.name for g in human.vertex_groups]
    torso = torso_of(human)
    hc, hr = meta["head_center"], meta["head_radius"] * 1.08
    limbs = meta["limbs"]
    for ob in parts:
        if ob.get("rig") == "head":
            for n in bone_names:
                if n not in ob.vertex_groups:
                    ob.vertex_groups.new(name=n)
            ob.vertex_groups["head"].add(list(range(len(ob.data.vertices))), 1.0, "REPLACE")
            continue
        mw = ob.matrix_world
        if ob.get("rig") == "legs":
            full = transfer(ob, human)
            final = [only(w, ARM) or w for w in full]
        else:
            body = transfer(ob, torso)
            full = transfer(ob, human)
            final = []
            on_arm = ob.data.attributes.new("arm", "FLOAT", "POINT")  # read by cut_wings
            for v, wf, wt in zip(ob.data.vertices, full, body):
                p = mw @ v.co
                wt = only(wt, LIMB) or {"pelvis_wt": 1.0}
                arm, leg = membership(p, limbs, "arm", band), membership(p, limbs, "leg", band)
                on_arm.data[v.index].value = arm
                if arm >= leg and arm > 0:
                    w = blend(only(wf, LEG) or wt, arm, wt, 1 - arm)
                elif leg > 0:
                    w = blend(only(wf, ARM) or wt, leg, wt, 1 - leg)
                else:
                    w = wt
                final.append(w)
        for v, w in zip(ob.data.vertices, final):
            d = mw @ v.co - hc
            if (d.x / hr.x) ** 2 + (d.y / hr.y) ** 2 + (d.z / hr.z) ** 2 <= 1.0:
                w = {"head": 1.0}
            set_weights(ob, v, w)
    bpy.data.objects.remove(torso)
    for ob in parts:
        clean(ob)


def clean(ob, limit=4):
    """Stop hands pulling on legs (they hang beside the thighs in the A-pose) and vice versa,
    then keep the 4 strongest weights per vertex and normalise them."""
    for v in ob.data.vertices:
        w = weights_of(ob, v)
        if not w:
            raise RuntimeError(f"{ob.name}: vertex {v.index} got no weights")
        arm = sum(x for n, x in w.items() if family(n) in ARM)
        leg = sum(x for n, x in w.items() if family(n) in LEG)
        if arm >= 0.3 and leg > 0:
            w = {n: x for n, x in w.items() if family(n) not in LEG}
        elif leg >= 0.3 and arm > 0:
            w = {n: x for n, x in w.items() if family(n) not in ARM}
        w = dict(sorted(w.items(), key=lambda kv: -kv[1])[:limit])
        set_weights(ob, v, w)


def cut_wings(parts):
    """The arm section of the body part, holes filled at the shoulder: faces that are mostly
    arm-weighted and lie on the duck's own arm (so no belly or neck the arm touches comes along)."""
    body = next(p for p in parts if p.get("part") == "body")
    names = [g.name for g in body.vertex_groups]
    bm = bmesh.new()
    bm.from_mesh(body.data)
    deform = bm.verts.layers.deform.active
    on_arm = bm.verts.layers.float.get("arm")
    keep = {v for v in bm.verts
            if sum(w for gi, w in v[deform].items() if family(names[gi]) in ARM) >= 0.5 and v[on_arm] >= 0.9}
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if not all(v in keep for v in f.verts)], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
    me = bpy.data.meshes.new(body.name + "_wings")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(body.data.materials[0])
    ob = bpy.data.objects.new(me.name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.matrix_world = body.matrix_world.copy()
    for n in names:
        ob.vertex_groups.new(name=n)
    for p in me.polygons:
        p.use_smooth = True
        p.material_index = 0
    return [ob]
