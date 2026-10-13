"""Indicative rules: braces, access, ties, ends. Not a substitute for a stability calculation.

Levels: d = 0 is the top working deck, d = 1 the deck 2 m below it, and so on.
A bay has decks at levels 0 .. min(lifts_i, lifts_j) - 1.
"""
import math
from .layout import leg_clearance_report, station_levels, bay_deck_levels, bay_lift_levels

CLADDING = ("NONE", "NET", "TARP")


def apply_rules(plan, preset, cladding="NONE", access_every_m=None, brace_every=None):
    R = preset.rules
    V = plan.vertical
    if not plan.stations:
        return plan
    st = plan.stations
    brace_every = brace_every or R["brace_every_n_bays"]
    access_every_m = access_every_m or R["access_every_m"]
    W = R["wind_factor"].get(cladding, 1.0)

    by_run = {}
    for b in plan.bays:
        by_run.setdefault(b.run, []).append(b)

    # --- braces: both ends + every N bays, only on bays >= 1500 mm; zigzag handled in geometry
    plan.braces = set()
    for run, bl in by_run.items():
        nb = len(bl)
        want = set(range(0, nb, brace_every)) | {0, nb - 1}
        for idx in want:
            order = sorted(range(nb), key=lambda q: abs(q - idx))
            for q in order:
                if bl[q].length_mm >= 1500:
                    for d in bay_lift_levels(plan, bl[q]):
                        plan.braces.add((bl[q].id, d))
                    break
    # --- access (deck with ladder+hatch): 2.5/3.0 m bays, one per ~access_every_m per level
    plan.access = set()
    acc_len = list(preset.access_lengths())
    cand = [b for b in plan.bays if b.length_mm in acc_len]
    cnt = max(1, int(math.ceil(plan.wall_length / access_every_m)))
    if not cand:
        plan.warnings.append("No 2.5/3.0 m bay available: no room for an access deck with ladder/hatch.")
    else:
        nlev = max(len(station_levels(plan, s)) for s in st)
        for d in range(nlev):
            lev = [b for b in cand if d in bay_deck_levels(plan, b)]
            if not lev:
                continue
            for j in range(cnt):
                pos = ((j + 0.5) / cnt + (0.5 / cnt) * (d % 2)) % 1.0
                plan.access.add((lev[min(int(pos * len(lev)), len(lev) - 1)].id, d))
    # --- open ends + step ends
    ends = set()
    for r in plan.runs:
        if r["ring"]:
            continue
        sts = [s for s in st if s.run == r["index"]]
        picks = []
        if r["start"] == "open":
            picks.append(sts[0])
        if r["end"] == "open" or r["end_kind"] == "convex":
            picks.append(sts[-1])
        for s in picks:
            for d in station_levels(plan, s):
                ends.add((s.id, d))
    for b in plan.bays:
        a, c = st[b.i], st[b.j]
        la, lc = station_levels(plan, a), station_levels(plan, c)
        for d in la - lc:
            ends.add((a.id, d))
        for d in lc - la:
            ends.add((c.id, d))
    plan.end_rails = sorted(ends)
    # --- ties
    plan.anchors = []
    plan.params["anchor_levels"] = []
    tops = [V["top_z"] + 1.0 - 0.5 * (s.g_in + s.g_out) for s in st]
    if max(tops) > 4.0:
        levels = [d for d in range(1, V["n"], 2)] or [0]
        area = 0.0
        for b in plan.bays:
            a, c = st[b.i], st[b.j]
            area += b.length_mm / 1000.0 * (V["top_z"] + 1.0 - 0.25 * (a.g_in + a.g_out + c.g_in + c.g_out))
        total = max(int(math.ceil(area * W / R["anchor_area_m2"])), len(levels) * 2)
        per = int(math.ceil(total / len(levels)))
        for li, d in enumerate(levels):
            el = [s for s in st if s.lifts > d]
            if not el:
                continue
            m = min(per, len(el))
            used = set()
            for j in range(m):
                idx = int((j + 0.25 + 0.5 * (li % 2)) * len(el) / m) % len(el)
                while idx in used:
                    idx = (idx + 1) % len(el)
                used.add(idx)
                plan.anchors.append((el[idx].id, d))
        plan.params["anchor_levels"] = levels
        if cladding != "NONE":
            plan.warnings.append("Ties increased by factor %.1f for %s (heuristic, check wind loading)." % (W, cladding))
    else:
        plan.warnings.append("Structure height %.1f m <= 4 m: no ties generated; check the height/width ratio." % max(tops))

    # --- checks
    bad = leg_clearance_report(plan, R["min_leg_clearance_m"])
    if bad:
        plan.warnings.append("%d leg pairs too close (<%d cm) at corners." % (len(bad), int(R["min_leg_clearance_m"] * 100)))
    nx = sum(1 for b in plan.bays if b.extra)
    if nx:
        plan.warnings.append("%d short bays (0.74/1.10 m) used for fitting." % nx)
    return plan
