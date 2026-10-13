"""Simple low-poly meshes for scaffold parts. The builder is pure Python; to_bpy() creates the Mesh."""
import math

MATS = {  # name: (r,g,b)
    "Steel": (0.55, 0.57, 0.60),
    "Timber": (0.62, 0.45, 0.25),
    "Plywood": (0.72, 0.58, 0.36),
    "Hatch": (0.85, 0.75, 0.50),
    "Brace": (0.45, 0.50, 0.55),
    "Tie": (0.80, 0.25, 0.15),
}
MAT_ORDER = list(MATS)


class MB:
    def __init__(self):
        self.v, self.f, self.m = [], [], []

    def quad(self, a, b, c, d, mat):
        self.f.append((a, b, c, d))
        self.m.append(MAT_ORDER.index(mat))

    def box(self, x0, x1, y0, y1, z0, z1, mat="Steel"):
        i = len(self.v)
        for x in (x0, x1):
            for y in (y0, y1):
                for z in (z0, z1):
                    self.v.append((x, y, z))
        # indices: (x,y,z) -> i + 4*ix + 2*iy + iz
        q = lambda a, b, c, d: self.quad(i + a, i + b, i + c, i + d, mat)
        q(0, 1, 3, 2); q(4, 6, 7, 5); q(0, 4, 5, 1); q(2, 3, 7, 6); q(0, 2, 6, 4); q(1, 5, 7, 3)

    def cyl(self, p0, p1, r, seg=8, mat="Steel"):
        d = [p1[i] - p0[i] for i in range(3)]
        L = math.sqrt(sum(c * c for c in d))
        if L < 1e-9:
            return
        d = [c / L for c in d]
        a = (1, 0, 0) if abs(d[0]) < 0.9 else (0, 1, 0)
        u = [d[1] * a[2] - d[2] * a[1], d[2] * a[0] - d[0] * a[2], d[0] * a[1] - d[1] * a[0]]
        ul = math.sqrt(sum(c * c for c in u))
        u = [c / ul for c in u]
        w = [d[1] * u[2] - d[2] * u[1], d[2] * u[0] - d[0] * u[2], d[0] * u[1] - d[1] * u[0]]
        i = len(self.v)
        for end in (p0, p1):
            for s in range(seg):
                t = 2 * math.pi * s / seg
                self.v.append(tuple(end[k] + r * (math.cos(t) * u[k] + math.sin(t) * w[k]) for k in range(3)))
        for s in range(seg):
            s2 = (s + 1) % seg
            self.quad(i + s, i + s2, i + seg + s2, i + seg + s, mat)

    def to_bpy(self, bpy, name, mats):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        for m in mats:
            me.materials.append(m)
        me.update()
        for p, mi in zip(me.polygons, self.m):
            p.material_index = mi
        return me


R_TUBE = 0.02415


def frame(preset, h, pins=True):
    """Frame: inner leg at y=0, outer leg at y=W; X = along the facade."""
    W = preset.leg_span
    b = MB()
    for y in (0.0, W):
        b.cyl((0, y, 0), (0, y, h), R_TUBE, 8)
    # a single transom below deck level (no mid/low cross members: free circulation)
    b.cyl((0, 0, h - 0.06), (0, W, h - 0.06), 0.0165, 6)
    if pins:
        c = W / 2
        for dy in (-0.295, -0.035, 0.035, 0.295):
            b.cyl((0, c + dy, h - 0.06), (0, c + dy, h - 0.002), 0.009, 5)
    return b


def deck(preset, l_mm):
    l = l_mm / 1000.0 - 0.02
    W, dw = preset.leg_span, preset.deck_w
    b = MB()
    for s in (-1, 1):
        yc = W / 2 + s * (dw / 2 + 0.005)
        b.box(-l / 2, l / 2, yc - dw / 2, yc + dw / 2, -0.045, 0.0, "Timber")
        for x in (-l / 2, l / 2 - 0.05):   # end fittings flush with the deck (no trip edge)
            b.box(x, x + 0.05, yc - dw / 2, yc + dw / 2, -0.05, 0.0, "Steel")
    return b


def access_deck(preset, l_mm):
    l = l_mm / 1000.0 - 0.02
    W = preset.leg_span
    b = MB()
    b.box(-l / 2, l / 2, W / 2 - 0.32, W / 2 + 0.32, -0.045, 0.0, "Plywood")
    hx = min(0.6, l * 0.22)
    b.box(-hx / 2, hx / 2, W / 2 - 0.26, W / 2 + 0.26, -0.045, 0.0006, "Hatch")   # hatch flush with the deck
    # ladder (side stiles) below the deck
    for s in (-1, 1):
        b.cyl((-hx / 2, W / 2 + s * 0.2, -1.9), (-hx / 2, W / 2 + s * 0.2, -0.045), 0.015, 5)
    return b


def rails(preset, l_mm, inner=False, toeboard=True):
    l = l_mm / 1000.0
    W = preset.leg_span
    b = MB()
    ys = [W + 0.03] + ([-0.03] if inner else [])
    for y in ys:
        for z in (0.5, 1.0):
            b.cyl((-l / 2, y, z), (l / 2, y, z), 0.0165, 6)
        if toeboard:
            b.box(-l / 2, l / 2, y - 0.01, y + 0.01, 0.0, 0.15, "Timber")
    return b


def end_rail(preset, toeboard=True):
    W = preset.leg_span
    b = MB()
    for z in (0.5, 1.0):
        b.cyl((0, 0, z), (0, W, z), 0.0165, 6)
    if toeboard:
        b.box(-0.01, 0.01, 0, W, 0.0, 0.15, "Timber")
    return b


def support(preset):
    W = preset.leg_span
    b = MB()
    for y in (0.0, W):   # posts only; no cross members across the walkway
        b.cyl((0, y, 0), (0, y, 1.0), R_TUBE * 0.8, 6)
    return b


def brace_unit():
    b = MB()
    b.cyl((0, 0, 0), (1, 0, 0), 0.0125, 5, "Brace")
    return b


def jack(ext, jack_len):
    b = MB()
    e = max(ext, 0.02)
    b.cyl((0, 0, -e), (0, 0, 0.0), 0.017, 6)
    b.box(-0.075, 0.075, -0.075, 0.075, -e - 0.006, -e, "Steel")
    return b


def tie(length):
    b = MB()
    b.cyl((0, 0, 0), (0, -length, 0), 0.012, 5, "Tie")
    return b
