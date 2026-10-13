"""Build / rebuild the scaffold geometry from a root Empty."""
import json
import math
import bpy
from mathutils import Matrix, Vector

from .core import preset as P
from .core.layout import build_plan
from .core.rules import apply_rules
from .core.bom import compute_bom, merge_boms
from .core.layout import bay_deck_levels
from . import geometry as G

_GROUND = {}   # cache: key -> (BVH tree, z max)

_BUSY = False
LIVE_LIMIT = 4000          # above this many objects live rebuild is skipped


def clear_ground_cache():
    _GROUND.clear()


def _ground_tree(obj, max_slope_deg):
    import numpy as np
    from mathutils.bvhtree import BVHTree
    key = (obj.name, obj.data.name, len(obj.data.vertices), len(obj.data.polygons),
           tuple(round(v, 4) for row in obj.matrix_world for v in row), round(max_slope_deg, 1))
    if key in _GROUND:
        return _GROUND[key]
    for k in [k for k in _GROUND if k[0] == obj.name]:
        del _GROUND[k]
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    try:
        me.calc_loop_triangles()
        n = len(me.vertices)
        co = np.empty(n * 3, dtype=np.float32)
        me.vertices.foreach_get("co", co)
        co = co.reshape(n, 3).astype(np.float64)
        mw = np.array(obj.matrix_world)
        co = co @ mw[:3, :3].T + mw[:3, 3]
        nt = len(me.loop_triangles)
        idx = np.empty(nt * 3, dtype=np.int32)
        me.loop_triangles.foreach_get("vertices", idx)
        idx = idx.reshape(nt, 3)
        a, b, c = co[idx[:, 0]], co[idx[:, 1]], co[idx[:, 2]]
        nrm = np.cross(b - a, c - a)
        ln = np.linalg.norm(nrm, axis=1)
        nz = np.abs(nrm[:, 2]) / np.maximum(ln, 1e-12)
        keep = nz >= math.cos(math.radians(max_slope_deg))
        idx = idx[keep]
        if len(idx) == 0:
            raise ValueError("The ground mesh has no faces flatter than %.0f degrees." % max_slope_deg)
        tree = BVHTree.FromPolygons([tuple(v) for v in co.tolist()], idx.tolist())
        zmax = float(co[:, 2].max())
    finally:
        ev.to_mesh_clear()
    _GROUND[key] = (tree, zmax)
    return _GROUND[key]


def make_ground_fn(s, z_ref):
    """Callable (x, y) -> z of the terrain, or None. z_ref = base level of the faces/path."""
    obj = s.ground_obj
    if obj is None:
        return None
    tree, zmax = _ground_tree(obj, s.ground_max_slope)
    down = Vector((0.0, 0.0, -1.0))
    start = z_ref + s.ground_search_up

    def g(x, y):
        h = tree.ray_cast(Vector((x, y, start)), down)
        if h[0] is None:
            h = tree.ray_cast(Vector((x, y, zmax + 1.0)), down)
        return None if h[0] is None else h[0].z
    return g


def find_root(obj):
    while obj is not None:
        if "sv_fp" in obj.keys():
            return obj
        obj = obj.parent
    return None


def reset_flags(*_a):
    global _BUSY
    _BUSY = False


def _basis(origin, n, z=0.0):
    nx, ny = n
    return Matrix(((ny, nx, 0, origin[0]), (-nx, ny, 0, origin[1]), (0, 0, 1, z), (0, 0, 0, 1)))


def _mat3(p0, p1, hint):
    x = Vector(p1) - Vector(p0)
    L = x.length
    x.normalize()
    y = Vector(hint) - x * Vector(hint).dot(x)
    if y.length < 1e-6:
        y = Vector((0, 0, 1)) - x * x.z
    y.normalize()
    z = x.cross(y)
    return Matrix(((x.x, y.x, z.x, p0[0]), (x.y, y.y, z.y, p0[1]), (x.z, y.z, z.z, p0[2]), (0, 0, 0, 1))), L


def _materials():
    out = []
    for name, col in G.MATS.items():
        mat = bpy.data.materials.get("SV_" + name)
        if mat is None:
            mat = bpy.data.materials.new("SV_" + name)
            mat.diffuse_color = (*col, 1.0)
            mat.use_nodes = True
            bsdf = mat.node_tree.nodes.get("Principled BSDF")
            if bsdf:
                bsdf.inputs["Base Color"].default_value = (*col, 1.0)
                bsdf.inputs["Roughness"].default_value = 0.6
        out.append(mat)
    return out


def estimate_objects(plan):
    if not plan.stations:
        return 0
    n = plan.vertical["n"]
    return len(plan.stations) * (n + 2) + len(plan.bays) * (n * 2 + 1) + len(plan.braces) + len(plan.legs)


def chain_params(s, chain, ground_on):
    """-> (top_z or None, height) for build_plan."""
    face = bool(chain.get("height")) and s.use_face_height
    if face:
        top = chain.get("z_top")
        if top is None:
            top = chain["z0"] + chain["height"]
        return top + s.height_offset, s.height
    if ground_on:
        return None, s.height                     # slider = height above the lowest ground
    return chain["z0"] + s.height, s.height       # flat ground at the base of the path


def compute(root):
    s = root.scaffvisor
    fp = json.loads(root["sv_fp"])
    preset = P.load_preset(s.preset)
    plans = []
    ground_on = s.ground_obj is not None
    for chain in fp["chains"]:
        top_z, height = chain_params(s, chain, ground_on)
        gfn = make_ground_fn(s, chain["z0"]) if ground_on else None
        plan = build_plan([tuple(p) for p in chain["points"]], chain["closed"], preset, height,
                          gap=s.gap, fit_mode=s.fit_mode, allow_short=s.allow_short, flip=s.flip,
                          right_out=chain.get("right_out"), ground=gfn, base_z=chain["z0"], top_z=top_z,
                          e_pref=s.jack_pref, phase_tol=s.top_tol, pad=s.ground_pad, low_decks=s.low_decks)
        if plan.stations and "top_z" not in plan.vertical:
            raise RuntimeError("Mixed add-on versions are loaded. Disable the add-on, restart Blender, then enable it again.")
        apply_rules(plan, preset, cladding=s.cladding)
        plans.append((plan, chain["z0"], compute_bom(plan, preset, deck_grade=preset.pick_grade(s.deck_grade), toeboards=s.toeboards)))
    return fp, preset, plans


def rebuild_safe(root, context=None, live=False):
    global _BUSY
    if _BUSY:
        return False
    _BUSY = True
    try:
        ok = rebuild(root, live=live)
        if "sv_error" in root.keys():
            del root["sv_error"]
        return ok
    except Exception as e:
        # Keep the message on the scaffold so the panel can show it with the way out (Rebuild),
        # instead of a traceback in the console only.
        root["sv_error"] = str(e) or e.__class__.__name__
        raise
    finally:
        _BUSY = False


def rebuild(root, live=False):
    s = root.scaffvisor
    fp, preset, plans = compute(root)
    if live and sum(estimate_objects(p) for p, _, _ in plans) > LIVE_LIMIT:
        root["sv_stale"] = 1
        return False
    root["sv_stale"] = 0
    cname = "ScaffVisor_" + root.name
    coll = bpy.data.collections.get(cname)
    if coll is None:
        coll = bpy.data.collections.new(cname)
        host = root.users_collection[0] if root.users_collection else bpy.context.scene.collection
        host.children.link(coll)
    if root.name not in coll.objects:
        coll.objects.link(root)
        for c in list(root.users_collection):
            if c is not coll:
                c.objects.unlink(root)
    for o in list(coll.objects):
        if o is not root and o.get("sv_part"):
            bpy.data.objects.remove(o, do_unlink=True)
    pref = "SV.%s." % root.name
    for me in list(bpy.data.meshes):
        if me.name.startswith(pref) and me.users == 0:
            bpy.data.meshes.remove(me)

    mats = _materials()
    cache = {}

    def mesh(key, builder):
        if key not in cache:
            cache[key] = builder().to_bpy(bpy, pref + str(key), mats)
        return cache[key]

    def put(name, me, matrix):
        o = bpy.data.objects.new(name, me)
        o["sv_part"] = 1
        coll.objects.link(o)
        o.parent = root
        o.matrix_parent_inverse = Matrix.Identity(4)
        o.matrix_basis = matrix
        return o

    warnings = []
    multi = len(plans) > 1
    for ci, (plan, z0, _bom) in enumerate(plans):
        tag = ("Chain %d: " % (ci + 1)) if multi else ""
        warnings += [tag + w for w in plan.warnings]
        if not plan.stations:
            continue
        V = plan.vertical
        ztop = V["top_z"]
        st = plan.stations
        hh = preset.frame_h

        for info in plan.leg_info.values():
            e = max(info["ext"], 0.02)
            jm = mesh(("jack", round(e, 2)), lambda e=e: G.jack(e, 0))
            put("Base jack", jm, _basis(info["pt"], (0.0, 1.0), info["z_jack"]))
        fm = mesh("frame2", lambda: G.frame(preset, hh))
        cms = {}
        for s_ in st:
            if s_.comp > 0:
                cm = mesh(("frameC", round(s_.comp, 2)), lambda c=s_.comp: G.frame(preset, c))
                put("Comp frame", cm, _basis(s_.inner, s_.n, s_.z_bot - s_.comp))
            for d in range(s_.lifts):
                put("Frame", fm, _basis(s_.inner, s_.n, ztop - hh * (d + 1)))
        inner_rails = plan.gap > preset.rules["inner_rail_gap_m"]
        for b in plan.bays:
            a, c = st[b.i], st[b.j]
            mid = ((a.inner[0] + c.inner[0]) / 2, (a.inner[1] + c.inner[1]) / 2)
            nv = (a.n[0] + c.n[0], a.n[1] + c.n[1])
            nl = math.hypot(*nv) or 1.0
            nv = (nv[0] / nl, nv[1] / nl)
            for d in bay_deck_levels(plan, b):
                z = ztop - hh * d
                if (b.id, d) in plan.access:
                    put("Access deck", mesh(("acc", b.length_mm), lambda l=b.length_mm: G.access_deck(preset, l)), _basis(mid, nv, z))
                else:
                    put("Deck", mesh(("deck", b.length_mm), lambda l=b.length_mm: G.deck(preset, l)), _basis(mid, nv, z))
                if s.show_rails:
                    put("Guard rail", mesh(("rail", b.length_mm, inner_rails, s.toeboards), lambda l=b.length_mm, i=inner_rails, tb=s.toeboards: G.rails(preset, l, i, tb)), _basis(mid, nv, z))
        if s.show_rails:
            em = mesh(("endrail", s.toeboards), lambda: G.end_rail(preset, s.toeboards))
            for sid, d in plan.end_rails:
                put("End guard rail", em, _basis(st[sid].inner, st[sid].n, ztop - hh * d))
            sm = mesh("support", lambda: G.support(preset))
            for s_ in st:
                put("Top post", sm, _basis(s_.inner, s_.n, ztop))
        if s.show_braces:
            bm = mesh("brace", G.brace_unit)
            for (bid, d) in sorted(plan.braces):
                b = plan.bays[bid]
                a, c = st[b.i], st[b.j]
                if (d + bid) % 2:
                    a, c = c, a
                off = 0.03
                p0 = (a.outer[0] + a.n[0] * off, a.outer[1] + a.n[1] * off, ztop - hh * (d + 1) + 0.1)
                p1 = (c.outer[0] + c.n[0] * off, c.outer[1] + c.n[1] * off, ztop - hh * d - 0.1)
                mtx, L = _mat3(p0, p1, (a.n[0], a.n[1], 0.0))
                put("Brace", bm, mtx @ Matrix.Diagonal((L, 1, 1, 1)))
        if s.show_anchors:
            tl = plan.gap + 0.30
            tm = mesh(("tie", round(tl, 2)), lambda tl=tl: G.tie(tl))
            for sid, d in plan.anchors:
                put("Tie", tm, _basis(st[sid].inner, st[sid].n, ztop - hh * d - 0.1))
        if s.show_arrows:
            pts = plan.points
            nseg = len(pts) if plan.closed else len(pts) - 1
            for i in range(nseg):
                a, b = pts[i], pts[(i + 1) % len(pts)]
                d = (b[0] - a[0], b[1] - a[1])
                L = math.hypot(*d)
                if L < 1e-6:
                    continue
                d = (d[0] / L, d[1] / L)
                nrm = (d[1], -d[0]) if plan.right_out else (-d[1], d[0])
                e = bpy.data.objects.new("Side arrow", None)
                e["sv_part"] = 1
                e.empty_display_type = "SINGLE_ARROW"
                e.empty_display_size = 1.0
                coll.objects.link(e)
                e.parent = root
                e.matrix_parent_inverse = Matrix.Identity(4)
                e.location = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, plan.vertical["ground_min"] + 1.0)
                e.rotation_euler = Vector((nrm[0], nrm[1], 0.0)).to_track_quat("Z", "Y").to_euler()

    bom = merge_boms([b for _, _, b in plans])
    plan_info = [dict(wall_length=p.wall_length, h_deck=p.vertical.get("h_deck", 0), n=p.vertical.get("n", 0),
                      nmin=p.vertical.get("nmin", 0), comp=p.vertical.get("comp", 0), comp_columns=p.vertical.get("comp_columns", 0),
                      ext=p.vertical.get("ext", 0), ext_min=p.vertical.get("ext_min", 0), jack_mm=p.vertical.get("jack_mm"),
                      top_z=p.vertical.get("top_z", 0), ground_min=p.vertical.get("ground_min", 0),
                      ground_max=p.vertical.get("ground_max", 0), flat=p.vertical.get("flat", True),
                      closed=p.closed, corners=p.corners, runs=p.runs,
                      face_height=bool(ch.get("height") and s.use_face_height))
                 for (p, _, _), ch in zip(plans, fp["chains"])]
    if fp.get("notes"):
        warnings = list(fp["notes"]) + warnings
    root["sv_result"] = json.dumps(dict(
        warnings=warnings, counts=bom["counts"], total_kg=bom["total_kg"], est_kg=bom["est_kg"],
        kg_m2=bom["kg_m2"], area=bom["area"], wall_length=sum(i["wall_length"] for i in plan_info),
        chains=plan_info, preset=preset.name, width=preset.width,
        empty=not any(p.stations for p, _, _ in plans)))
    root["sv_bom"] = json.dumps(bom["lines"])
    root["sv_what"] = fp.get("what", "")       # read by the panel (draw() must not parse the whole path)
    return True
