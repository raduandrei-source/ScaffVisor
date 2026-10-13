"""Fitting a scaffold to a wall path: bays, height, corners. Pure Python.

Conventions (metres, world XY):
 - the path = the wall (footprint). The scaffold stands on the 'outside' (right-hand side).
 - each station = one frame; it has an inner leg and an outer leg (outer = inner + n*leg_span).
 - n = outward normal; the frame local Y axis = n, X = (n.y, -n.x).
"""
import math
from dataclasses import dataclass, field

UNIT = 10  # mm


# ---------------------------------------------------------------- vector 2D
def _sub(a, b): return (a[0] - b[0], a[1] - b[1])
def _add(a, b): return (a[0] + b[0], a[1] + b[1])
def _mul(a, k): return (a[0] * k, a[1] * k)
def _dot(a, b): return a[0] * b[0] + a[1] * b[1]
def _cross(a, b): return a[0] * b[1] - a[1] * b[0]
def _len(a): return math.hypot(a[0], a[1])
def _unit(a):
    l = _len(a)
    return (a[0] / l, a[1] / l) if l > 1e-12 else (1.0, 0.0)


# ---------------------------------------------------------------- bays
def choose_total(s_ref_mm, std, extra, mode="NEAREST", lo=None, hi=None, forbid=None,
                 extra_penalty_m=0.30):
    """Choose the total length T (mm) and its composition in bays.
    mode: COVER (T>=ref), UNDER (T<=ref), NEAREST. lo/hi = hard limits (mm).
    forbid(T)->bool excludes totals. Returns (T, [bays]) or (None, []).
    """
    bays = [(b, False) for b in std] + [(b, True) for b in extra]
    umax = int(max(s_ref_mm, 0) / UNIT) + int(max(std) / UNIT) * 2 + 10
    if hi is not None:
        umax = min(umax, int(hi / UNIT) + 1)
    INF = (10 ** 9, 10 ** 9)
    best = [INF] * (umax + 1)       # (n_extra, n_bays)
    prev = [None] * (umax + 1)
    best[0] = (0, 0)
    for u in range(1, umax + 1):
        for b, ex in bays:
            bu = int(round(b / UNIT))
            if bu <= u and best[u - bu] != INF:
                c = (best[u - bu][0] + (1 if ex else 0), best[u - bu][1] + 1)
                if c < best[u]:
                    best[u] = c
                    prev[u] = (bu, b)
    cand = None
    for u in range(1, umax + 1):
        if best[u] == INF:
            continue
        T = u * UNIT
        if lo is not None and T < lo - 0.5:
            continue
        if hi is not None and T > hi + 0.5:
            continue
        dev = (T - s_ref_mm) / 1000.0
        if mode == "COVER" and dev < -1e-6:
            continue
        if mode == "UNDER" and dev > 1e-6:
            continue
        if forbid and forbid(T):
            continue
        score = abs(dev) + extra_penalty_m * best[u][0] + 0.15 * best[u][1]
        if cand is None or score < cand[0]:
            cand = (score, u)
    if cand is None:
        return None, []
    u = cand[1]
    out = []
    while u > 0:
        bu, b = prev[u]
        out.append(b)
        u -= bu
    out.sort(reverse=True)         # largest bays first
    return cand[1] * UNIT, out


def arrange_bays(bays):
    """Bay ordering hook (currently: keep the descending order)."""
    return bays


# ---------------------------------------------------------------- height
def jack_limits(preset):
    r = preset.rules
    emin = r["jack_ext_min_m"]
    emax = preset.jack_emax()
    return emin, emax


def solve_column(ztop, g_hi, g_lo, preset, e_pref=0.30, pad=0.0):
    """One frame column. ztop = absolute level of the top deck, g_hi/g_lo = ground under the higher/lower leg.
    n lifts of 2 m + compensation frame c at the bottom + jacks e_hi/e_lo, with
    e_hi + c + 2n = ztop - (g_hi + pad). Returns dict(n, c, e_hi, e_lo, ok, low)."""
    emin, emax = jack_limits(preset)
    hh = preset.frame_h
    r = ztop - (g_hi + pad)
    n = int(math.floor((r - emin) / hh + 1e-9))
    low = False
    if n < 1:
        n, low = 1, True
    rem = r - n * hh
    best = None
    for c in [0.0] + list(preset.comp_frames):
        e_hi = rem - c
        e_lo = e_hi + (g_hi - g_lo)
        if e_hi < emin - 1e-9 or e_lo > emax + 1e-9:
            continue
        cost = (1.0 if c > 0 else 0.0) + abs(0.5 * (e_hi + e_lo) - e_pref)
        if best is None or cost < best[0]:
            best = (cost, c, e_hi, e_lo)
    ok = best is not None
    if not ok:
        feas = [c for c in [0.0] + list(preset.comp_frames) if rem - c >= emin - 1e-9]
        c = max(feas) if feas else 0.0
        e_hi = rem - c
        best = (99.0, c, e_hi, e_hi + (g_hi - g_lo))
    return dict(n=n, c=best[1], e_hi=best[2], e_lo=best[3], ok=ok and not low, low=low, cost=best[0])


def solve_height(h_deck_m, preset):
    """Flat ground: choose n, c and the jack extension so that ext + c + 2n = h (top working deck height)."""
    emin, emax = jack_limits(preset)
    warns = []
    h = h_deck_m
    if h < preset.frame_h + emin - 1e-9:
        warns.append("Height below the minimum (%.2f m); minimum used." % (preset.frame_h + emin))
        h = preset.frame_h + emin
    col = solve_column(h, 0.0, 0.0, preset)
    jack = preset.jack_for(col["e_hi"])
    return dict(n=col["n"], comp=col["c"], ext=col["e_hi"], jack_mm=jack["h_mm"] if jack else None,
                h_deck=col["e_hi"] + col["c"] + col["n"] * preset.frame_h, warnings=warns)


# ---------------------------------------------------------------- plan
@dataclass
class Station:
    id: int
    run: int
    k: int
    inner: tuple
    outer: tuple
    n: tuple
    lifts: int = 1          # number of 2 m lifts in this column
    comp: float = 0.0       # compensation frame height at the bottom
    z_bot: float = 0.0      # absolute bottom of the first full 2 m frame
    g_in: float = 0.0       # ground level under the inner / outer leg
    g_out: float = 0.0


@dataclass
class Bay:
    id: int
    run: int
    i: int          # start station id
    j: int          # end station id
    length_mm: int
    extra: bool


@dataclass
class Plan:
    preset_id: str
    stations: list = field(default_factory=list)
    bays: list = field(default_factory=list)
    runs: list = field(default_factory=list)       # informational dicts
    vertical: dict = field(default_factory=dict)
    corners: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    wall_length: float = 0.0
    closed: bool = False
    gap: float = 0.0
    params: dict = field(default_factory=dict)
    points: list = field(default_factory=list)
    right_out: bool = True
    # filled in by rules.py:
    braces: set = field(default_factory=set)       # (bay_id, level d); d=0 is the top deck, d grows downward
    access: set = field(default_factory=set)       # (bay_id, level d)
    anchors: list = field(default_factory=list)    # (station_id, level d)
    end_rails: list = field(default_factory=list)  # (station_id, level d)
    legs: dict = field(default_factory=dict)       # rounded key -> (x,y)
    leg_info: dict = field(default_factory=dict)   # rounded key -> dict(pt, ext, jack_mm, z_jack, g)


def _clean(points, closed):
    out = []
    for p in points:
        if not out or _len(_sub(p, out[-1])) > 1e-3:
            out.append((float(p[0]), float(p[1])))
    if closed and len(out) > 1 and _len(_sub(out[0], out[-1])) <= 1e-3:
        out.pop()
    return out


def build_plan(points, closed, preset, height, gap=0.15, fit_mode="COVER",
               allow_short=True, flip=False, joint_deg=None, right_out=None, ground=None, base_z=0.0, top_z=None,
               e_pref=0.30, phase_tol=0.0, pad=0.0, low_decks=True, **extra_params):
    P = Plan(preset_id=preset.id, closed=closed, gap=gap)
    P.params = dict(height=height, gap=gap, fit_mode=fit_mode, allow_short=allow_short, flip=flip, low_decks=low_decks)
    pts = _clean(points, closed)
    nmin = 3 if closed else 2
    if len(pts) < nmin:
        P.warnings.append("Path too short / degenerate.")
        return P
    R = preset.rules
    jdeg = R["joint_deg"] if joint_deg is None else joint_deg
    W = preset.leg_span
    g = gap + preset.tube_r                       # inner leg axis distance from the wall
    if gap > R["max_wall_gap_m"] + 1e-9:
        P.warnings.append("Wall offset %.0f cm > %.0f cm (indicative limit)." % (gap * 100, R["max_wall_gap_m"] * 100))


    P.points = pts
    nv = len(pts)
    segs = []
    for i in range(nv if closed else nv - 1):
        a, b = pts[i], pts[(i + 1) % nv]
        segs.append((a, b))
    area = 0.0
    if closed:
        area = 0.5 * sum(_cross(pts[i], pts[(i + 1) % nv]) for i in range(nv))
    if right_out is None:
        right_out = (area > 0) if closed else True
    if flip:
        right_out = not right_out
    P.right_out = right_out
    sgn = 1.0 if right_out else -1.0
    D, N, L = [], [], []
    for a, b in segs:
        d = _unit(_sub(b, a))
        D.append(d)
        N.append((d[1], -d[0]) if right_out else (-d[1], d[0]))
        L.append(_len(_sub(b, a)))
    P.wall_length = sum(L)
    ns = len(segs)

    # --- kind of each vertex
    def vertex_info(vi):
        """vertex vi between segment (vi-1) and vi. -> (kind, phi)"""
        ia, ib = (vi - 1) % ns, vi % ns
        cr = _cross(D[ia], D[ib])
        dt = _dot(D[ia], D[ib])
        phi = abs(math.atan2(cr, dt))
        if phi <= math.radians(jdeg):
            return "joint", phi
        convex = cr * sgn > 0
        return ("convex" if convex else "concave"), min(phi, math.radians(150))

    vrange = range(nv) if closed else range(1, nv - 1)
    info = {vi: vertex_info(vi) for vi in vrange}
    corner_vs = [vi for vi in vrange if info[vi][0] != "joint"]
    for vi in corner_vs:
        k, phi = info[vi]
        P.corners.append(dict(v=vi, kind=k, deg=math.degrees(phi)))
        if abs(math.degrees(phi) - 90) > 25:
            P.warnings.append("Corner at %.0f° (vertex %d): approximate geometry, check manually." % (math.degrees(phi), vi))

    def corner_ext(vi):
        """(xa_ext, xb) for a corner: A = the segment before, B = the one after."""
        kind, phi = info[vi]
        ia, ib = (vi - 1) % ns, vi % ns
        t = math.tan(phi / 2)
        if kind == "convex":
            xa = (g + W) * t
            q = _add(_mul(D[ia], xa), _mul(N[ia], g))
        else:
            xa = -g * t
            q = _add(_mul(D[ia], xa), _mul(N[ia], g + W))
        return xa, _dot(q, D[ib])

    # --- runs: lists of consecutive segments
    runs = []
    if not corner_vs:
        runs.append(dict(segs=list(range(ns)), v0=None, v1=None, ring=closed))
    elif closed:
        for ci, vi in enumerate(corner_vs):
            vj = corner_vs[(ci + 1) % len(corner_vs)]
            s = []
            k = vi % ns
            while True:
                s.append(k)
                k = (k + 1) % ns
                if k == vj % ns:
                    break
                if len(s) > ns:
                    break
            runs.append(dict(segs=s, v0=vi, v1=vj, ring=False))
    else:
        bounds = [0] + corner_vs + [nv - 1]
        for a, b in zip(bounds[:-1], bounds[1:]):
            runs.append(dict(segs=list(range(a, b)), v0=(a if a in corner_vs else None),
                             v1=(b if b in corner_vs else None), ring=False))

    allowed_extra = preset.bays_extra if allow_short else []
    sid = 0
    bid = 0
    for ri, run in enumerate(runs):
        sl = run["segs"]
        first, last = sl[0], sl[-1]
        # start
        if run["v0"] is None:
            xb = 0.0
            start_type = "open"
        else:
            _, xb = corner_ext(run["v0"])
            start_type = "corner"
        # end
        if run["v1"] is None:
            xa = 0.0
            end_type = "open"
            end_kind = None
        else:
            xa, _ = corner_ext(run["v1"])
            end_type = "corner"
            end_kind = info[run["v1"]][0]
        # inner polyline (inner leg axis)
        a0 = segs[first][0]
        pl = [_add(_add(a0, _mul(D[first], xb)), _mul(N[first], g))]
        for q in range(len(sl) - 1):
            i0, i1 = sl[q], sl[q + 1]
            v = segs[i1][0]
            m = _add(N[i0], N[i1])
            den = 1 + _dot(N[i0], N[i1])
            pl.append(_add(v, _mul(m, g / max(den, 1e-6))))
        endv = segs[last][1]
        pl.append(_add(_add(endv, _mul(D[last], xa)), _mul(N[last], g)))
        if run["ring"]:
            # closed polygon: mitred vertices everywhere
            pl = []
            for vi in range(nv):
                ia, ib = (vi - 1) % ns, vi % ns
                m = _add(N[ia], N[ib])
                den = 1 + _dot(N[ia], N[ib])
                pl.append(_add(pts[vi], _mul(m, g / max(den, 1e-6))))
            pl.append(pl[0])
        seglen = [_len(_sub(pl[q + 1], pl[q])) for q in range(len(pl) - 1)]
        S = sum(seglen)
        # directions/normals along the polyline
        if run["ring"]:
            pn = [N[q % ns] for q in range(len(pl) - 1)]
        else:
            pn = [N[s] for s in sl]
        pd = [_unit(_sub(pl[q + 1], pl[q])) for q in range(len(pl) - 1)]

        # --- choosing the total length
        ref = S * 1000.0
        lo = hi = None
        mode = fit_mode
        forbid = None
        if run["ring"]:
            mode = "NEAREST"
        else:
            if end_type == "corner":
                if end_kind == "convex":
                    mode = "COVER"
                    clr = R["min_leg_clearance_m"] * 1000.0
                    smin = ref
                    forbid = (lambda T, smin=smin, clr=clr: 0.5 < (T - smin) < clr)
                else:
                    mode = "UNDER"
        T, bl = choose_total(ref, preset.bays_std, allowed_extra, mode, lo, hi, forbid)
        if T is None:
            T, bl = choose_total(ref, preset.bays_std, allowed_extra, "NEAREST", None, None, None)
            P.warnings.append("Run %d: corner/end constraint could not be satisfied; please check." % (ri + 1))
        if not bl:
            P.warnings.append("Run %d too short for bays." % (ri + 1))
            continue
        # bay order: keep the descending sort
        bl = arrange_bays(bl)
        scale = 1.0
        if run["ring"]:
            scale = S / (T / 1000.0)
            dev = abs(scale - 1)
            P.warnings.append("Closed ring: perimeter %.2f m, bays %.2f m (difference %.1f%%)." % (S, T / 1000.0, dev * 100))
            if dev > 0.10:
                P.warnings.append("Large mismatch closing the ring; adjust manually.")

        def point_at(s):
            if s <= 0:
                return pl[0], pd[0], pn[0], 1.0
            acc = 0.0
            for q, ll in enumerate(seglen):
                if s <= acc + ll + 1e-9 or q == len(seglen) - 1:
                    t = s - acc
                    p = _add(pl[q], _mul(pd[q], t))
                    nn = pn[q]
                    # near an interior vertex -> bisector
                    if q > 0 and t < 0.10:
                        nn = _unit(_add(pn[q - 1], pn[q]))
                    elif q < len(seglen) - 1 and (ll - t) < 0.10:
                        nn = _unit(_add(pn[q], pn[q + 1]))
                    return p, pd[q], nn, max(0.5, _dot(nn, pn[q]))
                acc += ll
            return pl[-1], pd[-1], pn[-1], 1.0

        s_acc = 0.0
        cum = [0.0]
        for b in bl:
            s_acc += b / 1000.0 * scale
            cum.append(s_acc)
        first_id = sid
        nstat = len(bl) + (0 if run["ring"] else 1)
        for kk in range(nstat):
            p, dd, nn, cosf = point_at(cum[kk])
            outer = _add(p, _mul(nn, W / cosf))
            st = Station(sid, ri, kk, p, outer, nn)
            P.stations.append(st)
            sid += 1
        for kk, b in enumerate(bl):
            i = first_id + kk
            j = first_id + kk + 1
            if run["ring"] and kk == len(bl) - 1:
                j = first_id
            P.bays.append(Bay(bid, ri, i, j, int(b), b in preset.bays_extra and b not in preset.bays_std))
            bid += 1
        P.runs.append(dict(index=ri, start=start_type, end=end_type, end_kind=end_kind, ring=run["ring"],
                           total_mm=T, n_bays=len(bl), first_station=first_id, n_stations=nstat,
                           slack_mm=int(round(T - ref)) if not run["ring"] else 0))

    # unique legs
    for st in P.stations:
        for pt in (st.inner, st.outer):
            P.legs.setdefault((round(pt[0] * 1000), round(pt[1] * 1000)), pt)
    if P.stations:
        _solve_vertical(P, preset, ground, base_z, top_z, height, e_pref, phase_tol, pad)
    return P


def _solve_vertical(P, preset, ground, base_z, top_z, height, e_pref, phase_tol, pad):
    """Heights per column: follow the ground with jacks + compensation frames + extra lifts."""
    emin, emax = jack_limits(preset)
    hh = preset.frame_h
    misses = 0
    last = base_z
    cache = {}

    def g_at(pt):
        nonlocal misses, last
        key = (round(pt[0] * 1000), round(pt[1] * 1000))
        if key in cache:
            return cache[key]
        v = ground(pt[0], pt[1]) if ground else base_z
        if v is None:
            misses += 1
            v = last
        last = v
        cache[key] = v
        return v

    for st in P.stations:
        st.g_in, st.g_out = g_at(st.inner), g_at(st.outer)
    gmin = min(min(s.g_in, s.g_out) for s in P.stations)
    gmax = max(max(s.g_in, s.g_out) for s in P.stations)
    if top_z is None:
        top_z = (gmin if ground else base_z) + height
    # groups of stations that share a leg (one jack under two frames)
    parent = list(range(len(P.stations)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    owner = {}
    for st in P.stations:
        for pt in (st.inner, st.outer):
            k = (round(pt[0] * 1000), round(pt[1] * 1000))
            if k in owner:
                parent[find(st.id)] = find(owner[k])
            else:
                owner[k] = st.id
    groups = {}
    for st in P.stations:
        groups.setdefault(find(st.id), []).append(st)

    def solve_all(zt):
        sols, cost = {}, 0.0
        for gid, sts in groups.items():
            gs = [v for s in sts for v in (s.g_in, s.g_out)]
            col = solve_column(zt, max(gs), min(gs), preset, e_pref, pad)
            sols[gid] = col
            cost += col["cost"] * len(sts)
        return sols, cost

    best = None
    steps = int(round(phase_tol / 0.05)) if phase_tol > 0 else 0
    for i in range(steps + 1):
        zt = top_z - 0.05 * i
        sols, cost = solve_all(zt)
        cost += 0.001 * i
        if best is None or cost < best[0] - 1e-9:
            best = (cost, zt, sols)
    _, ztop, sols = best
    bad_cross = low = 0
    for gid, sts in groups.items():
        col = sols[gid]
        for st in sts:
            st.lifts, st.comp = col["n"], col["c"]
            st.z_bot = ztop - col["n"] * hh
        bad_cross += (0 if col["ok"] or col["low"] else len(sts))
        low += len(sts) if col["low"] else 0
    for st in P.stations:
        for pt, g in ((st.inner, st.g_in), (st.outer, st.g_out)):
            k = (round(pt[0] * 1000), round(pt[1] * 1000))
            zj = st.z_bot - st.comp
            e = zj - (g + pad)
            jack = preset.jack_for(max(e, emin)) or max(preset.c["base_plate_threaded"], key=lambda t: t["h_mm"])
            P.leg_info[k] = dict(pt=pt, ext=e, jack_mm=jack["h_mm"], z_jack=zj, g=g)
    lifts = [s.lifts for s in P.stations]
    comps = [s.comp for s in P.stations]
    exts = [v["ext"] for v in P.leg_info.values()]
    top_lifts = max(lifts)
    jmax = max(v["jack_mm"] for v in P.leg_info.values())
    P.vertical = dict(top_z=ztop, n=top_lifts, nmin=min(lifts), comp=max(comps), ext=max(exts), ext_min=min(exts),
                      jack_mm=jmax, h_deck=ztop - gmin, ground_min=gmin, ground_max=gmax,
                      comp_columns=sum(1 for c in comps if c > 0), flat=(gmax - gmin) < 0.02,
                      phase_shift=top_z - ztop)
    if misses:
        P.warnings.append("Ground not found under %d leg position(s); the previous height was reused." % misses)
    if low:
        P.warnings.append("%d column(s): top deck less than %.2f m above the ground; frames sink below the ground." % (low, hh + emin))
    if bad_cross:
        P.warnings.append("%d column(s): cross-slope or jack range exceeded (jack extension up to %.2f m allowed)." % (bad_cross, emax))
    if P.vertical["nmin"] != P.vertical["n"]:
        P.warnings.append("Stepped scaffold: %d to %d lifts; step ends get end guard rails." % (P.vertical["nmin"], P.vertical["n"]))
    if P.vertical["comp_columns"]:
        P.warnings.append("%d column(s) use a compensation frame at the base (no deck)." % P.vertical["comp_columns"])
    if P.vertical["phase_shift"] > 1e-6:
        P.warnings.append("Top deck lowered by %.2f m to reduce compensation frames." % P.vertical["phase_shift"])


def leg_clearance_report(plan, min_d=0.07):
    """Leg pairs from different stations that do not coincide (<2 mm) yet are closer than min_d.
    Returns a list [(dist, pt1, pt2)]."""
    items = []
    for st in plan.stations:
        items.append((st.id, st.inner))
        items.append((st.id, st.outer))
    cell = max(min_d, 0.1)
    grid = {}
    for idx, (sid_, p) in enumerate(items):
        grid.setdefault((int(math.floor(p[0] / cell)), int(math.floor(p[1] / cell))), []).append(idx)
    bad = []
    for idx, (sid_, p) in enumerate(items):
        cx, cy = int(math.floor(p[0] / cell)), int(math.floor(p[1] / cell))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in grid.get((cx + dx, cy + dy), []):
                    if j <= idx:
                        continue
                    if items[j][0] == sid_:
                        continue
                    dd = _len(_sub(p, items[j][1]))
                    if 0.002 < dd < min_d:
                        bad.append((dd, p, items[j][1]))
    return bad


# ---------------------------------------------------------------- deck levels
def station_levels(plan, st):
    """Deck levels a column can carry. d = 0 is the top deck, d grows downward in 2 m steps.
    Levels 0..lifts-1 sit on the frame heads; if the column has a compensation frame (and low decks are
    allowed), one more level sits on top of the compensation frame."""
    lv = set(range(st.lifts))
    if plan.params.get("low_decks", True) and st.comp > 0:
        lv.add(st.lifts)
    return lv


def bay_deck_levels(plan, b):
    """Levels at which bay b has decks (both end columns can carry them)."""
    return sorted(station_levels(plan, plan.stations[b.i]) & station_levels(plan, plan.stations[b.j]))


def bay_lift_levels(plan, b):
    """Levels with a full 2 m lift in both columns (these can take diagonal braces)."""
    return range(min(plan.stations[b.i].lifts, plan.stations[b.j].lifts))
