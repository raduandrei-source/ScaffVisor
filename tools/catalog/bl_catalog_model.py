"""One catalog model: blender -b --factory-startup -P bl_catalog_model.py  (env SVROOT, PRESET, BLEND_OUT, IMG_OUT)
Builds a 2-bay, 2-lift scaffold with ScaffVisor on a test facade, colours the parts in the catalog pinks,
renders an isometric view (Workbench, outlines, transparent background) and saves the .blend."""
import os, sys, json, math
import bpy, bmesh
from mathutils import Vector

sys.path.insert(0, os.environ["SVROOT"])
import scaffvisor as sp
sp.register()
from scaffvisor.core.preset import load_preset

pid = os.environ["PRESET"]
pr = load_preset(pid)
bay = min(pr.bays_std, key=lambda b: abs(b - 2500)) / 1000.0
L = 2 * bay
H = pr.frame_h
h_deck = 2 * H + 0.30

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)

# test facade: a plain box, scaffold on its front face (normal -Y)
me = bpy.data.meshes.new("Facade")
bm = bmesh.new()
d, hb = 3.0, h_deck + 1.6
vs = [bm.verts.new(p) for p in [(0, 0, 0), (L, 0, 0), (L, d, 0), (0, d, 0), (0, 0, hb), (L, 0, hb), (L, d, hb), (0, d, hb)]]
for idx in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]:
    bm.faces.new([vs[i] for i in idx])
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(me)
bm.free()
wall = bpy.data.objects.new("Facade", me)
bpy.context.scene.collection.objects.link(wall)
bpy.context.view_layer.objects.active = wall
wall.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
bm = bmesh.from_edit_mesh(me)
for f in bm.faces:
    f.select = f.normal.y < -0.9
bmesh.update_edit_mesh(me)
bpy.ops.scaffvisor.create()
root = bpy.context.active_object
s = root.scaffvisor
s.live_update = False
s.preset = pid
s.use_face_height = False
s.height = h_deck
s.gap = 0.15
s.show_arrows = False
s.allow_short = False
s.live_update = True
s.height = h_deck  # rebuild
if bpy.context.object and bpy.context.object.mode != "OBJECT":
    bpy.ops.object.mode_set(mode="OBJECT")
res = json.loads(root["sv_result"])

PINK = {"structure": "#D9409F", "deck": "#FBA0E3", "access": "#FF6EC7", "rail": "#FF6EC7", "small": "#C8358C", "wall": "#F1EEEA"}


def rgba(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return (c[0], c[1], c[2], 1.0)


mats = {}
for k, hx in PINK.items():
    m = bpy.data.materials.new("SV catalog " + k)
    m.diffuse_color = rgba(hx)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = rgba(hx)
        bsdf.inputs["Roughness"].default_value = 0.6
    mats[k] = m


def kind_of(name):
    n = name.lower()
    if n.startswith("access deck"):
        return "access"
    if n.startswith("deck"):
        return "deck"
    if "guard rail" in n:
        return "rail"
    if n.startswith(("brace", "tie", "base jack")):
        return "small"
    return "structure"


def paint(o, k):
    o.color = rgba(PINK[k])
    if o.type == "MESH":
        if len(o.data.materials) == 0:
            o.data.materials.append(None)
        for sl in o.material_slots:
            sl.link = "OBJECT"
            sl.material = mats[k]


for o in root.children_recursive if hasattr(root, "children_recursive") else root.children:
    if o.type == "MESH":
        paint(o, kind_of(o.name))
paint(wall, "wall")
wall.hide_render = True   # pieces only in the catalog render (the facade stays in the .blend)

# camera: isometric from the street side
sc = bpy.context.scene
bpy.context.view_layer.update()
parts = [o for o in (root.children_recursive if hasattr(root, "children_recursive") else root.children) if o.type == "MESH"]
pts = [o.matrix_world @ Vector(c) for o in parts for c in o.bound_box]
print("BBOX", len(parts), min(p.x for p in pts), max(p.x for p in pts), min(p.y for p in pts), max(p.y for p in pts), min(p.z for p in pts), max(p.z for p in pts))
mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
ctr = (mn + mx) / 2
cam_d = bpy.data.cameras.new("Iso")
cam_d.type = "ORTHO"
cam = bpy.data.objects.new("Iso camera", cam_d)
sc.collection.objects.link(cam)
dirv = Vector((-1.0, -1.25, 0.95)).normalized()
cam.location = ctr + dirv * 40
cam.rotation_euler = (-dirv).to_track_quat("-Z", "Y").to_euler()
sc.camera = cam
RX, RY = 1100, 864
sc.render.resolution_x, sc.render.resolution_y = RX, RY
bpy.context.view_layer.update()
mw = cam.matrix_world
r, u = mw.col[0].xyz.normalized(), mw.col[1].xyz.normalized()
box = [Vector((x, y, z)) for x in (mn.x, mx.x) for y in (mn.y, mx.y) for z in (mn.z, mx.z)]
us = [(p - ctr).dot(r) for p in box]
vs_ = [(p - ctr).dot(u) for p in box]
du, dv = max(us) - min(us), max(vs_) - min(vs_)
cam_d.ortho_scale = max(du, dv * RX / RY) * 1.06
cam_d.shift_x = ((max(us) + min(us)) / 2) / cam_d.ortho_scale
cam_d.shift_y = ((max(vs_) + min(vs_)) / 2) / cam_d.ortho_scale

sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading
sh.light = "FLAT"
sh.color_type = "OBJECT"
sh.show_object_outline = True
sh.object_outline_color = (0.12, 0.05, 0.10)
sh.show_cavity = True
sh.cavity_type = "BOTH"
sc.render.film_transparent = True
sc.display.render_aa = "8"
sc.render.image_settings.file_format = "WEBP"
sc.render.image_settings.color_mode = "RGBA"
sc.render.image_settings.quality = 88
sc.render.filepath = os.path.join(os.environ["IMG_OUT"], pid + "_iso.webp")
bpy.ops.render.render(write_still=True)

# viewport shading for whoever opens the .blend
for scr in bpy.data.screens:
    for area in scr.areas:
        if area.type == "VIEW_3D":
            for spc in area.spaces:
                if spc.type == "VIEW_3D":
                    spc.shading.type = "SOLID"
                    spc.shading.color_type = "OBJECT"
sc["scaffvisor_catalog"] = json.dumps(dict(preset=pid, name=pr.name, bay=bay, lifts=2, h_deck=h_deck, sources=pr.data["_meta"].get("sources", [])))
os.makedirs(os.environ["BLEND_OUT"], exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.environ["BLEND_OUT"], pid + ".blend"), compress=True)
print("MODEL", pid, "kg", round(res.get("total_kg", 0)), "parts", len(root.children), "warnings", res.get("warnings"))
sp.unregister()
