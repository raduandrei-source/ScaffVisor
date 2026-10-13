"""Bill of materials + weight."""
from collections import OrderedDict


def _add(lines, key, cat, code, desc, qty, unit, est=False):
    if qty <= 0:
        return
    k = (cat, code, desc)
    if k in lines:
        lines[k]["qty"] += qty
    else:
        lines[k] = dict(cat=cat, code=code, desc=desc, qty=qty, unit_kg=unit, est=est)


def compute_bom(plan, preset, deck_grade="visually_sorted_S10", toeboards=True):
    R = preset.rules
    c = preset.c
    L = OrderedDict()
    if not plan.stations:
        return dict(lines=[], total_kg=0.0, est_kg=0.0, area=0.0, kg_m2=0.0, counts={})
    from .layout import bay_deck_levels
    st = plan.stations
    ns = len(st)
    fh = int(round(preset.frame_h * 1000))
    m, est = preset.frame(fh)
    code = next(t["id"] for t in c["frame"]["steel_light_74"] if t["h_mm"] == fh)
    _add(L, 0, "Frames", code, preset.label("frame", "Frame %.2f x %.2f m" % (preset.frame_h, preset.width)), sum(s.lifts for s in st), m, est)
    for s in st:
        if s.comp > 0:
            ch = int(round(s.comp * 1000))
            m, est = preset.frame(ch)
            code = next(t["id"] for t in c["frame"]["steel_light_74"] if t["h_mm"] == ch)
            _add(L, 0, "Frames", code, "Compensation frame " + (("%.1f" % s.comp) if abs(round(s.comp, 1) - s.comp) < 1e-9 else ("%.2f" % s.comp)) + " m", 1, m, est)

    deck_grade = preset.pick_grade(deck_grade)
    deckcode = {t["l_mm"]: t["id"] for t in c["timber_deck_w320"][deck_grade]}
    acccode = {t["l_mm"]: t["id"] for t in c["access_deck_with_ladder_w640"] if t["surface"] == preset.access_surface}
    railcode = {t["l_mm"]: t["id"] for t in c["guard_rail"]}
    toecode = {t["l_mm"]: t["id"] for t in c["toeboard_timber_h150"]}
    nrail = 2 + (2 if plan.gap > R["inner_rail_gap_m"] else 0)
    for b in plan.bays:
        l = b.length_mm
        for d in bay_deck_levels(plan, b):
            if (b.id, d) in plan.access:
                m, est = preset.access_deck(l)
                _add(L, 1, "Decks", acccode.get(l, "access-%d" % l), preset.label("access", "Access deck with ladder+hatch") + " %.2f m" % (l / 1000), 1, m, est)
            else:
                m, est = preset.deck(l, deck_grade)
                _add(L, 1, "Decks", deckcode.get(l, "deck-%d" % l), preset.label("deck", "Timber deck W32") + " %.2f m" % (l / 1000), preset.decks_per_bay, m, est)
            m, est = preset.guard_rail(l)
            _add(L, 2, "Protection", railcode.get(l, "guard-rail-%d" % l), "Guard rail %.2f m" % (l / 1000), nrail, m, est)
            if toeboards:
                m, est = preset.toeboard(l)
                _add(L, 2, "Protection", toecode.get(l, "toeboard-%d" % l), "Timber toeboard 15 cm %.2f m" % (l / 1000), 1, m, est)
    for (bid, d) in plan.braces:
        l = plan.bays[bid].length_mm
        ll, m, est = preset.brace(l, fh)
        code = {t["bay_mm"]: t["id"] for t in c["vertical_brace"]}.get(l, "brace-%d" % l)
        _add(L, 3, "Bracing", code, "Vertical diagonal brace, %.2f m bay" % (l / 1000), 1, m, est)
    ne = len(plan.end_rails)
    er = c["double_end_guard_rail_74"]
    _add(L, 2, "Protection", er["id"], preset.label("end_rail", "End guard rail, double, 0.74 m"), ne, er["mass"], er.get("estimated", False))
    if toeboards:
        et = c["end_toeboard_74"]
        _add(L, 2, "Protection", et["id"], preset.label("end_toeboard", "End toeboard 0.74 m"), ne, et["mass"], et.get("estimated", False))
    sup = c["top_level"]["steel_guard_rail_support_h1000_w740"]
    _add(L, 2, "Protection", sup["id"], preset.label("support", "Top-level guard rail support h=1.0 m"), ns, sup["mass"], sup.get("estimated", False))
    jacks = {t["h_mm"]: t for t in c["base_plate_threaded"]}
    for info in plan.leg_info.values():
        t = jacks[info["jack_mm"]]
        _add(L, 4, "Base", t["id"], "Threaded base jack %.1f m" % (t["h_mm"] / 1000), 1, t["mass"])
    na = len(plan.anchors)
    t80 = c["ties"]["scaffold_tie_80"]
    nc, eb = c["ties"]["normal_coupler"], c["ties"]["eyebolt_120"]
    _add(L, 5, "Ties", t80["id"], preset.label("tie", "Wall tie 0.8 m"), na, t80["mass"], t80.get("estimated", False))
    _add(L, 5, "Ties", nc["id"], preset.label("coupler", "Normal couplers (tie)"), 2 * na, nc["mass"], nc.get("estimated", False))
    _add(L, 5, "Ties", eb["id"], preset.label("eyebolt", "Eyebolt"), na, eb["mass"], eb.get("estimated", False))

    lines = []
    for (cat, code, desc), d in sorted(L.items(), key=lambda kv: (kv[0][0], kv[0][2])):
        d["total_kg"] = d["qty"] * d["unit_kg"]
        lines.append(d)
    total = sum(d["total_kg"] for d in lines)
    est = sum(d["total_kg"] for d in lines if d["est"])
    V = plan.vertical
    area = 0.0
    for b in plan.bays:
        a, cc = st[b.i], st[b.j]
        area += b.length_mm / 1000.0 * (V["top_z"] + 1.0 - 0.25 * (a.g_in + a.g_out + cc.g_in + cc.g_out))
    counts = dict(frames=sum(s.lifts + (1 if s.comp > 0 else 0) for s in st), stations=ns, bays=len(plan.bays),
                  anchors=na, braces=len(plan.braces), legs=len(plan.legs), lifts=V["n"])
    return dict(lines=lines, total_kg=total, est_kg=est, area=area,
                kg_m2=(total / area if area > 0 else 0.0), counts=counts)


def merge_boms(boms):
    """Combine several BOMs (one per wall chain) into one."""
    L = {}
    counts = {}
    area = 0.0
    for b in boms:
        for d in b["lines"]:
            k = (d["cat"], d["code"], d["desc"])
            if k in L:
                L[k]["qty"] += d["qty"]
                L[k]["total_kg"] += d["total_kg"]
            else:
                L[k] = dict(d)
        for k, v in b["counts"].items():
            counts[k] = counts.get(k, 0) + v
        area += b["area"]
    lines = sorted(L.values(), key=lambda d: (d["cat"], d["desc"]))
    total = sum(d["total_kg"] for d in lines)
    est = sum(d["total_kg"] for d in lines if d["est"])
    return dict(lines=lines, total_kg=total, est_kg=est, area=area,
                kg_m2=(total / area if area > 0 else 0.0), counts=counts)
