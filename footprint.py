"""Extract the wall path(s) from selected faces (Edit Mode), a curve, or mesh edges.

Result: {"chains": [{"points": [(x,y)..], "closed": bool, "z0": float, "z_top": float|None, "height": float|None,
                     "right_out": bool|None}], "source": str, "what": str, "notes": [str]}
 - from faces: the scaffold stands on the side the face normal points to; height = face height.
 - from a curve / edges: side is automatic (flip with the toggle); height comes from the slider.
"""
import math
import bpy
import bmesh


class FootprintError(Exception):
    pass


# ------------------------------------------------------------------ helpers
def _rdp(pts, tol):
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy)
    best, bi = -1.0, 0
    for i in range(1, len(pts) - 1):
        p = pts[i]
        d = (abs(dy * p[0] - dx * p[1] + b[0] * a[1] - b[1] * a[0]) / L) if L > 1e-12 else math.hypot(p[0] - a[0], p[1] - a[1])
        if d > best:
            best, bi = d, i
    if best <= tol:
        return [a, b]
    return _rdp(pts[:bi + 1], tol)[:-1] + _rdp(pts[bi:], tol)


def simplify(pts, closed, tol):
    if tol <= 0 or len(pts) < 4:
        return pts
    if not closed:
        return _rdp(pts, tol)
    far = max(range(len(pts)), key=lambda i: math.hypot(pts[i][0] - pts[0][0], pts[i][1] - pts[0][1]))
    a = _rdp(pts[:far + 1], tol)
    b = _rdp(pts[far:] + [pts[0]], tol)
    return a[:-1] + b[:-1]


def _chain_edges(verts, edges):
    """verts: [(x,y,z)], edges: [(i,j)] -> (order, closed). Longest connected component."""
    adj = {}
    for i, j in edges:
        adj.setdefault(i, []).append(j)
        adj.setdefault(j, []).append(i)
    if not adj:
        raise FootprintError("No edges found in the selection.")
    seen, comps = set(), []
    for s in adj:
        if s in seen:
            continue
        stack, comp = [s], []
        seen.add(s)
        while stack:
            u = stack.pop()
            comp.append(u)
            for w in adj[u]:
                if w not in seen:
                    seen.add(w)
                    stack.append(w)
        comps.append(comp)

    def clen(c):
        return sum(math.dist(verts[i], verts[j]) for i, j in edges if i in c and j in c)
    comp = set(max(comps, key=clen))
    if any(len(adj[u]) > 2 for u in comp):
        raise FootprintError("The path branches (a vertex with more than 2 edges). Select a single loop or chain.")
    ends = [u for u in comp if len(adj[u]) == 1]
    closed = not ends
    start = ends[0] if ends else next(iter(comp))
    order, prev, cur = [start], None, start
    while True:
        nxt = [w for w in adj[cur] if w != prev]
        if not nxt:
            break
        nx = nxt[0]
        if nx == start:
            break
        order.append(nx)
        prev, cur = cur, nx
        if len(order) > len(comp):
            break
    return order, closed


def _key(p):
    return (round(p[0] * 500), round(p[1] * 500))


def _drop_collinear(pts, closed, deg=0.5):
    """Remove vertices where the path turns by less than `deg` degrees."""
    n = len(pts)
    if n < 3:
        return pts
    out = []
    rng = range(n) if closed else range(1, n - 1)
    keep = set(range(n))
    for i in rng:
        a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
        v1 = (b[0] - a[0], b[1] - a[1])
        v2 = (c[0] - b[0], c[1] - b[1])
        l1, l2 = math.hypot(*v1), math.hypot(*v2)
        if l1 < 1e-9 or l2 < 1e-9:
            continue
        ang = abs(math.atan2(v1[0] * v2[1] - v1[1] * v2[0], v1[0] * v2[0] + v1[1] * v2[1]))
        if ang < math.radians(deg):
            keep.discard(i)
    return [pts[i] for i in range(n) if i in keep]


# ------------------------------------------------------------------ faces
def _chains_from_faces(obj, notes):
    mw = obj.matrix_world
    nm = mw.to_3x3().inverted_safe().transposed()
    bm = bmesh.from_edit_mesh(obj.data)
    segs = []   # (a2d, b2d, zmin, zmax)
    skipped = 0
    for f in bm.faces:
        if not f.select:
            continue
        wv = [mw @ v.co for v in f.verts]
        n = (nm @ f.normal)
        n.normalize()
        if abs(n.z) > 0.7 or math.hypot(n.x, n.y) < 1e-6:
            skipped += 1
            continue
        zmin, zmax = min(v.z for v in wv), max(v.z for v in wv)
        edges = []
        for e in f.edges:
            a, b = mw @ e.verts[0].co, mw @ e.verts[1].co
            edges.append((a, b))
        low = [(a, b) for a, b in edges if max(a.z, b.z) <= zmin + 0.05]
        if not low:
            low = [min(edges, key=lambda ab: ab[0].z + ab[1].z)]
        for a, b in low:
            d = (b.x - a.x, b.y - a.y)
            if math.hypot(*d) < 1e-4:
                continue
            right = (d[1], -d[0])
            if right[0] * n.x + right[1] * n.y < 0:
                a, b = b, a
            segs.append(((a.x, a.y), (b.x, b.y), zmin, zmax))
    if skipped:
        notes.append("%d horizontal face(s) ignored (only wall faces are used)." % skipped)
    if not segs:
        raise FootprintError("No usable wall faces selected. Select vertical faces in Edit Mode.")
    by_start = {}
    ends = set()
    for i, (a, b, z0, z1) in enumerate(segs):
        by_start.setdefault(_key(a), []).append(i)
        ends.add(_key(b))
    used = set()
    chains = []

    def follow(i):
        path = [i]
        used.add(i)
        while True:
            nxt = [j for j in by_start.get(_key(segs[path[-1]][1]), []) if j not in used]
            if not nxt:
                break
            j = nxt[0]
            if j == path[0]:
                break
            used.add(j)
            path.append(j)
        return path

    order = [i for i in range(len(segs)) if _key(segs[i][0]) not in ends] + list(range(len(segs)))
    for i in order:
        if i in used:
            continue
        path = follow(i)
        closed = _key(segs[path[-1]][1]) == _key(segs[path[0]][0]) and len(path) >= 3
        pts = [segs[j][0] for j in path]
        if not closed:
            pts.append(segs[path[-1]][1])
        pts = _drop_collinear(pts, closed)
        z0 = min(segs[j][2] for j in path)
        z_top = max(segs[j][3] for j in path)
        hs = [segs[j][3] - segs[j][2] for j in path]
        h = max(hs)
        if max(hs) - min(hs) > 0.1 and len(path) > 1:
            notes.append("Faces in one chain differ in height (%.1f-%.1f m): the tallest (%.1f m) is used for the whole chain." % (min(hs), max(hs), h))
        if len(pts) < (3 if closed else 2):
            continue
        chains.append(dict(points=pts, closed=closed, z0=z0, z_top=z_top, height=h, right_out=True))
    if not chains:
        raise FootprintError("Could not build a path from the selected faces.")
    return chains


# ------------------------------------------------------------------ main
def extract_footprint(context, tol=0.03):
    obj = context.active_object
    if obj is None:
        raise FootprintError("Select a curve or mesh that marks the wall (or select wall faces in Edit Mode).")
    notes = []
    mw = obj.matrix_world
    if obj.type == "MESH" and obj.mode == "EDIT":
        obj.update_from_editmode()
        bm = bmesh.from_edit_mesh(obj.data)
        if any(f.select for f in bm.faces):
            chains = _chains_from_faces(obj, notes)
            return dict(chains=chains, source=obj.name, what="selected faces", notes=notes)
    tmp = None
    if obj.type == "CURVE":
        dg = context.evaluated_depsgraph_get()
        tmp = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
        me = tmp
        use_sel = False
        what = "curve"
    elif obj.type == "MESH":
        me = obj.data
        use_sel = obj.mode == "EDIT" and any(e.select for e in me.edges)
        what = "selected edges" if use_sel else "base ring"
    else:
        raise FootprintError("The active object must be a curve or a mesh.")
    try:
        wv = [tuple(mw @ v.co) for v in me.vertices]
        if not wv:
            raise FootprintError("The object has no vertices.")
        if obj.type == "CURVE" or use_sel:
            edges = [tuple(e.vertices) for e in me.edges if (not use_sel or e.select)]
        else:
            zmin = min(p[2] for p in wv)
            low = {i for i, p in enumerate(wv) if p[2] <= zmin + 0.02}
            edges = [tuple(e.vertices) for e in me.edges if e.vertices[0] in low and e.vertices[1] in low]
        order, closed = _chain_edges(wv, edges)
        pts3 = [wv[i] for i in order]
        z0 = min(p[2] for p in pts3)
        pts = simplify([(p[0], p[1]) for p in pts3], closed, tol)
        if len(pts) < (3 if closed else 2):
            raise FootprintError("Degenerate path after simplification.")
        return dict(chains=[dict(points=pts, closed=closed, z0=z0, z_top=None, height=None, right_out=None)],
                    source=obj.name, what=what, notes=notes)
    finally:
        if tmp is not None:
            bpy.data.meshes.remove(tmp)
