"""Headless Blender test (run with a bpy-enabled Python)."""
import sys, math, json, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import bpy, bmesh
import scaffvisor as sp
sp.register(); sp.register()   # double registration must be safe
from scaffvisor import build

def add_box(name, x0, y0, w, d, h):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in [(x0,y0,0),(x0+w,y0,0),(x0+w,y0+d,0),(x0,y0+d,0),(x0,y0,h),(x0+w,y0,h),(x0+w,y0+d,h),(x0,y0+d,h)]]
    for idx in [(0,1,2,3),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:
        bm.faces.new([vs[i] for i in idx])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob); return ob

def select_side_faces(ob):
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(ob.data)
    for f in bm.faces:
        f.select = abs(f.normal.z) < 0.5
    bm.select_flush_mode()
    bmesh.update_edit_mesh(ob.data)

# 1) two separate buildings with different heights, selected faces
a = add_box("A", 0, 0, 12.3, 8.2, 8.0)
b = add_box("B", 30, 0, 10.0, 6.0, 5.0)
for o in (a, b):
    pass
bm_obj = bpy.data.objects.new("dummy", None)
# join A and B into one mesh
bpy.ops.object.select_all(action="DESELECT")
a.select_set(True); b.select_set(True); bpy.context.view_layer.objects.active = a
bpy.ops.object.join()
select_side_faces(a)
r = bpy.ops.scaffvisor.create()
root = bpy.context.active_object
res = json.loads(root["sv_result"])
print("create:", r, "chains:", len(res["chains"]), [round(c["h_deck"], 2) for c in res["chains"]], res["warnings"])
assert len(res["chains"]) == 2
hs = sorted(round(c["h_deck"], 2) for c in res["chains"])
assert hs == [5.0, 8.0], hs
# check actual geometry heights (matrix_basis since parent is identity)
tops = sorted({round(max((o.matrix_basis @ v.co).z for v in o.data.vertices), 2) for o in root.children if o.name.startswith("Top post")})
print("top post tops:", tops)
# scaffold is outside the buildings: no leg inside either box
def inside(p):
    return (0 < p[0] < 12.3 and 0 < p[1] < 8.2) or (30 < p[0] < 40 and 0 < p[1] < 6.0)
bad = [o for o in root.children if o.name.startswith("Base jack") and inside(o.location)]
print("legs inside buildings:", len(bad)); assert not bad
# 2) numeric offset moves legs
root.scaffvisor.gap = 0.5
xs = [o.location.x for o in root.children if o.name.startswith("Base jack") and o.location.y < 0]
print("gap 0.5 -> nearest leg row y:", round(max(o.location.y for o in root.children if o.name.startswith("Base jack") and o.location.y < 0), 3))
# 3) flip puts scaffold inside
root.scaffvisor.gap = 0.15
root.scaffvisor.flip = True
inn = [o for o in root.children if o.name.startswith("Base jack") and inside(o.location)]
print("flipped, legs inside:", len(inn)); assert inn
root.scaffvisor.flip = False
# 4) use_face_height off -> slider
root.scaffvisor.use_face_height = False
root.scaffvisor.height = 4.2
res = json.loads(root["sv_result"]); print("slider heights:", [round(c["h_deck"], 2) for c in res["chains"]])
assert all(abs(c["h_deck"] - 4.2) < 1e-3 for c in res["chains"])
# 5) side arrows exist
print("arrows:", sum(1 for o in root.children if o.name.startswith("Side arrow")))
# 6) curve circle (path mode)
bpy.ops.object.mode_set(mode="OBJECT") if bpy.context.object and bpy.context.object.mode != "OBJECT" else None
bpy.ops.curve.primitive_bezier_circle_add(radius=10)
bpy.ops.scaffvisor.create()
r2 = bpy.context.active_object
print("circle:", json.loads(r2["sv_result"])["counts"])
# 7) export + save/reload
bpy.ops.scaffvisor.export_bom()
bpy.ops.wm.save_as_mainfile(filepath="/tmp/scaffvisor_test.blend")
bpy.ops.wm.open_mainfile(filepath="/tmp/scaffvisor_test.blend")
print("after reload:", [o.name for o in bpy.data.objects if "sv_fp" in o.keys()], build._BUSY)
sp.unregister(); sp.unregister()
print("OK")
