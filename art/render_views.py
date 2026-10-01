"""Blender: preview renders of whatever meshes are visible in the scene."""
import math

import bpy
from mathutils import Vector

VIEWS = {"front": (0, -1, 0), "side": (1, 0, 0), "three": (0.7, -1, 0.25)}


def setup_scene():
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.view_settings.view_transform = "Standard"
    w = bpy.data.worlds.new("W")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.55, 0.75, 0.82, 1)
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sun.data.energy = 3.0
    # No cast shadows: on low-poly smooth-shaded meshes they draw false dark facets (the shadow
    # terminator), which look like damage. The previews are for reading shape and tearing.
    sun.data.use_shadow = False
    sun.rotation_euler = (math.radians(45), 0, math.radians(-30))
    sc.collection.objects.link(sun)


def _bounds():
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in bpy.context.scene.objects:
        if o.type != "MESH" or o.hide_render:
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo, hi = Vector(map(min, lo, w)), Vector(map(max, hi, w))
    return lo, hi


def _camera():
    sc = bpy.context.scene
    cam = bpy.data.objects.get("RenderCam") or bpy.data.objects.new("RenderCam", bpy.data.cameras.new("RenderCam"))
    if cam.name not in sc.collection.objects:
        sc.collection.objects.link(cam)
    sc.camera = cam
    return cam


def render(prefix, views=("front", "three"), size=(1600, 900)):
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = size
    bpy.context.view_layer.update()  # objects moved since the last update report stale matrix_world
    lo, hi = _bounds()
    ctr = (lo + hi) / 2
    span = max(hi.x - lo.x, (hi.z - lo.z) * size[0] / size[1]) * 1.1
    cam = _camera()
    for name in views:
        dv = Vector(VIEWS[name]).normalized()
        if name == "three":
            cam.data.type, cam.data.lens = "PERSP", 50
            cam.location = ctr + dv * span * 1.9
        else:
            cam.data.type, cam.data.ortho_scale = "ORTHO", span
            cam.location = ctr + dv * 10
        cam.rotation_euler = (-dv).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = f"{prefix}_{name}.png"
        bpy.ops.render.render(write_still=True)


def render_icon(path, center, size=0.62):
    """256×256 front view of a duck's head for the Thunderstore icon."""
    sc = bpy.context.scene
    sc.render.resolution_x = sc.render.resolution_y = 256
    cam = _camera()
    cam.data.type, cam.data.ortho_scale = "ORTHO", size
    cam.location = center + Vector((0, -10, 0.02))
    cam.rotation_euler = Vector((0, 1, 0)).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
