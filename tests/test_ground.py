"""Headless Blender test: scaffold on sloping photogrammetry-like terrain that also contains a ruin."""
import sys, math, json, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import bpy, bmesh
import scaffvisor as sp
sp.register()
from scaffvisor import build

def gz(x, y):   # analytic ground: 12% slope along x + 8% along y + bumps
    return 0.12 * x + 0.08 * y + 0.25 * math.sin(x / 2.0) * math.cos(y / 2.5)

# terrain grid + ruin walls (in the SAME mesh) -------------------------------
bm = bmesh.new()
N = 60
grid = [[bm.verts.new((i - 10, j - 10, gz(i - 10, j - 10))) for j in range(N)] for i in range(N)]
for i in range(N - 1):
    for j in range(N - 1):
        bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
# ruin: walls 12 x 8 m with a gap-free top, placed on the ground (vertical faces + a top face)
x0, y0, w, d, h = 5.0, 5.0, 12.0, 8.0, 6.0
base = [(x0, y0), (x0 + w, y0), (x0 + w, y0 + d), (x0, y0 + d)]
zlow = min(gz(*p) for p in base)
bot = [bm.verts.new((px, py, zlow - 0.5)) for px, py in base]
top = [bm.verts.new((px, py, zlow + h)) for px, py in base]
for k in range(4):
    bm.faces.new((bot[k], bot[(k + 1) % 4], top[(k + 1) % 4], top[k]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
me = bpy.data.meshes.new("scan"); bm.to_mesh(me); bm.free()
scan = bpy.data.objects.new("scan", me); bpy.context.scene.collection.objects.link(scan)

# the box the user draws: faces of the ruin (bottom at lowest ground)
bm = bmesh.new()
bv = [bm.verts.new((px, py, zlow)) for px, py in base]
tv = [bm.verts.new((px, py, zlow + h)) for px, py in base]
for k in range(4):
    bm.faces.new((bv[k], bv[(k + 1) % 4], tv[(k + 1) % 4], tv[k]))
bm.faces.new(bv[::-1]); bm.faces.new(tv)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
mb = bpy.data.meshes.new("box"); bm.to_mesh(mb); bm.free()
box = bpy.data.objects.new("box", mb); bpy.context.scene.collection.objects.link(box)
bpy.context.view_layer.objects.active = box; box.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
bmx = bmesh.from_edit_mesh(box.data)
for f in bmx.faces:
    if abs(f.normal.z) < 0.5: f.select_set(True)
bmx.select_flush_mode(); bmesh.update_edit_mesh(box.data)
bpy.context.scene.scaffvisor_ground = scan
bpy.ops.scaffvisor.create()
root = bpy.context.active_object
assert root.scaffvisor.ground_obj == scan, "scene ground not applied"
res0 = json.loads(root["sv_result"]); print("with scene ground:", [(round(c["h_deck"],2), c["n"]) for c in res0["chains"]])

root.scaffvisor.ground_obj = None
res_flat = json.loads(root['sv_result']); print('flat:', [(round(c['h_deck'],2), c['n']) for c in res_flat['chains']])
root.scaffvisor.ground_obj = scan
res = json.loads(root["sv_result"]); c = res["chains"][0]
print("ground: z %.2f..%.2f lifts %d-%d comp cols %d jack ext %.2f..%.2f top_z %.2f" % (c["ground_min"], c["ground_max"], c["nmin"], c["n"], c["comp_columns"], c["ext_min"], c["ext"], c["top_z"]))
print("warnings:", res["warnings"])
assert c["ground_max"] - c["ground_min"] > 2.0
assert abs(c["top_z"] - (zlow + h)) < 1e-4, (c["top_z"], zlow + h)    # face top prevails
# verify against the analytic ground: every jack sits on the ground
bad = 0; worst = 0.0
for o in root.children:
    if o.name.startswith("Base jack"):
        x, y, z = o.matrix_basis.translation
        # jack mesh spans z-ext..z; its bottom plate is at the lowest vertex
        zb = min((o.matrix_basis @ v.co).z for v in o.data.vertices)
        err = abs(zb - gz(x, y)); worst = max(worst, err)
        if err > 0.08: bad += 1     # terrain grid is 1 m, bumps -> interpolation error allowed
print("jacks:", sum(1 for o in root.children if o.name.startswith("Base jack")), "off-ground >8cm:", bad, "worst %.3f" % worst)
assert bad == 0
# all decks at consistent absolute levels (multiples of 2 m below the top)
zs = sorted({round(c["top_z"] - (o.matrix_basis.translation.z), 3) for o in root.children if o.name.startswith("Deck")})
print("deck depths below top:", zs); assert all(abs(v / 2 - round(v / 2)) < 1e-3 for v in zs)
# slope filter matters: ruin walls excluded; tight filter should fail or change
root.scaffvisor.ground_max_slope = 20.0
print("slope 20 deg ->", json.loads(root["sv_result"])["warnings"][:2])
root.scaffvisor.ground_max_slope = 60.0
root.scaffvisor.top_tol = 0.5
c2 = json.loads(root["sv_result"])["chains"][0]; print("top tol 0.5 -> comp cols", c2["comp_columns"], "top_z", round(c2["top_z"], 2))
root.scaffvisor.top_tol = 0.0
bpy.ops.scaffvisor.refresh_ground()
bpy.ops.wm.save_as_mainfile(filepath="/tmp/sv_ground.blend")
print("OK")
