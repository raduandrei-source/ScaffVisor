"""Opening picture of the guide, from a real project (the Deleni test file). Nothing is saved.

    blender -b --factory-startup "<project>.blend" --python tools/render_hero.py -- <output.png> [hide=name1,name2]

Workbench, scan texture, outlines, scaffold parts in the catalog pinks, transparent background.
"""
import sys

import bpy

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = args[0]
hide = set()
for a in args[1:]:
    if a.startswith("hide="):
        hide |= set(x for x in a[5:].split(",") if x)
sc = bpy.context.scene
root = bpy.data.objects.get("ScaffVisor")
parts = set(root.children_recursive) if root else set()


def rgba(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return (c[0], c[1], c[2], 1.0)


PINK = {"structure": "#D9409F", "deck": "#FBA0E3", "rail": "#FF6EC7", "small": "#C8358C"}
for o in parts:
    n = o.name.lower()
    k = ("deck" if n.startswith(("deck", "access deck")) else "rail" if "guard rail" in n
         else "small" if n.startswith(("brace", "tie", "base jack")) else "structure")
    if o.type == "MESH":
        m = bpy.data.materials.new("hero " + k)
        m.diffuse_color = rgba(PINK[k])
        if len(o.data.materials) == 0:
            o.data.materials.append(None)
        for sl in o.material_slots:
            sl.link = "OBJECT"
            sl.material = m
for o in sc.objects:
    if o.name in hide or (o.parent and o.parent.name in hide):
        o.hide_render = True
    if o.name.startswith("Side arrow"):
        o.hide_render = True
# camera framed on the scaffold (a little ground around it), from the direction given by view=x,y,z
from mathutils import Vector
view = Vector((1.0, 1.3, 0.75))
for a in args[1:]:
    if a.startswith("view="):
        view = Vector(tuple(float(v) for v in a[5:].split(",")))
bpy.context.view_layer.update()
pts = [o.matrix_world @ Vector(c) for o in parts if o.type == "MESH" and not o.hide_render for c in o.bound_box]
mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
ctr = (mn + mx) / 2
d = view.normalized()
cd = bpy.data.cameras.new("Guide")
cd.type = "ORTHO"
cam = bpy.data.objects.new("Guide camera", cd)
sc.collection.objects.link(cam)
cam.location = ctr + d * 200
cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
cd.clip_end = 1000
sc.camera = cam
bpy.context.view_layer.update()
mw = cam.matrix_world
r, u = mw.col[0].xyz.normalized(), mw.col[1].xyz.normalized()
box = [Vector((x, y, z)) for x in (mn.x, mx.x) for y in (mn.y, mx.y) for z in (mn.z, mx.z)]
us = [(p - ctr).dot(r) for p in box]
vs = [(p - ctr).dot(u) for p in box]
RX, RY = 1600, 900
cd.ortho_scale = max(max(us) - min(us), (max(vs) - min(vs)) * RX / RY) * 1.18
cd.shift_x = ((max(us) + min(us)) / 2) / cd.ortho_scale
cd.shift_y = ((max(vs) + min(vs)) / 2) / cd.ortho_scale

sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading
sh.light = "STUDIO"
sh.color_type = "TEXTURE"
sh.show_object_outline = True
sh.object_outline_color = (0.12, 0.05, 0.10)
sh.show_cavity = True
sh.cavity_type = "WORLD"
sc.display.render_aa = "8"
sc.render.film_transparent = True
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1600, 900, 100
sc.render.image_settings.file_format = "WEBP" if out.lower().endswith(".webp") else "PNG"
if out.lower().endswith(".webp"):
    sc.render.image_settings.quality = 86
sc.render.image_settings.color_mode = "RGBA"
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print("HERO", out, "camera", sc.camera.name if sc.camera else None)
