# SPDX-License-Identifier: GPL-3.0-or-later
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
    modular = preset.kind == "modular"
    if modular:
        _modular_members(L, plan, preset)
    else:
        m, est = preset.frame(fh)
        code = next(t["id"] for t in c["frame"]["steel_light_74"] if t["h_mm"] == fh)
        _add(L, 0, "Frames", code, preset.label("frame", "Frame %.2f x %.2f m" % (preset.frame_h, preset.width)), sum(s.lifts for s in st), m, est)
    for s in ([] if modular else st):
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
                if preset.access_extra_decks:
                    m, est = preset.deck(l, deck_grade)
                    _add(L, 1, "Decks", deckcode.get(l, "deck-%d" % l), preset.label("deck", "Timber deck W32") + " %.2f m" % (l / 1000), preset.access_extra_decks, m, est)
            else:
                m, est = preset.deck(l, deck_grade)
                _add(L, 1, "Decks", deckcode.get(l, "deck-%d" % l), preset.label("deck", "Timber deck W32") + " %.2f m" % (l / 1000), preset.decks_per_bay, m, est)
            m, est = preset.guard_rail(l)
            _add(L, 2, "Protection", railcode.get(l, "guard-rail-%d" % l), preset.label("guard_rail", "Guard rail") + " %.2f m" % (l / 1000), nrail, m, est)
            if toeboards:
                m, est = preset.toeboard(l)
                _add(L, 2, "Protection", toecode.get(l, "toeboard-%d" % l), preset.label("toeboard", "Timber toeboard 15 cm") + " %.2f m" % (l / 1000), 1, m, est)
    for (bid, d) in plan.braces:
        l = plan.bays[bid].length_mm
        ll, m, est = preset.brace(l, fh)
        code = {t["bay_mm"]: t["id"] for t in c["vertical_brace"]}.get(l, "brace-%d" % l)
        _add(L, 3, "Bracing", code, preset.label("brace", "Vertical diagonal brace") + ", %.2f m bay" % (l / 1000), R.get("brace_faces", 1), m, est)
    ne = len(plan.end_rails)
    er = c["double_end_guard_rail_74"]
    _add(L, 2, "Protection", er["id"], preset.label("end_rail", "End guard rail, double, 0.74 m"), ne, er["mass"], er.get("estimated", False))
    if toeboards:
        et = c["end_toeboard_74"]
        _add(L, 2, "Protection", et["id"], preset.label("end_toeboard", "End toeboard 0.74 m"), ne, et["mass"], et.get("estimated", False))
    if not modular:   # modular standards run on 1 m above the top deck instead (counted with the standards)
        sup = c["top_level"]["steel_guard_rail_support_h1000_w740"]
        _add(L, 2, "Protection", sup["id"], preset.label("support", "Top-level guard rail support h=1.0 m"), ns, sup["mass"], sup.get("estimated", False))
    jacks = {t["h_mm"]: t for t in c["base_plate_threaded"]}
    for info in plan.leg_info.values():
        t = jacks[info["jack_mm"]]
        _add(L, 4, "Base", t["id"], "Threaded base jack %.1f m" % (t["h_mm"] / 1000), 1, t["mass"], t.get("estimated", False))
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


def standard_set(h_m, lengths_mm):
    """Standards (longest first) whose total reaches h_m. -> list of lengths in mm."""
    ls = sorted(lengths_mm)
    need = int(round(h_m * 1000))
    out = []
    while need > 0:
        fit = [x for x in ls if x >= need]
        x = fit[0] if fit else ls[-1]
        out.append(x)
        need -= x
    return out


def _modular_members(L, plan, preset):
    """Standards, base collars, transoms and the ledgers that carry each lift (modular systems)."""
    from .layout import bay_deck_levels, station_levels
    c = preset.c
    st = plan.stations
    hh = preset.frame_h
    top = preset.rules.get("top_post_m", 1.0)
    # standards per leg: from the top of the jack (compensation part included) to 1 m above the top deck
    owner = {}
    for s in st:
        for pt in (s.inner, s.outer):
            owner.setdefault((round(pt[0] * 1000), round(pt[1] * 1000)), s)
    stds = {t["l_mm"]: t for t in c["standard"]}
    for k, info in plan.leg_info.items():
        s = owner.get(k)
        if s is None:
            continue
        h = s.comp + s.lifts * hh + top
        for x in standard_set(h, stds.keys()):
            t = stds[x]
            _add(L, 0, "Standards", t["id"], preset.label("standard", "Standard") + " %.2f m" % (x / 1000), 1, t["mass"], t.get("estimated", False))
    bc = c.get("base_collar")
    if bc:
        _add(L, 0, "Standards", bc["id"], preset.label("base_collar", "Base collar"), len(plan.leg_info), bc["mass"], bc.get("estimated", False))
    tr = c["transom"]
    ntr = sum(1 + len(station_levels(plan, s)) for s in st)     # base level + every deck level
    _add(L, 0, "Ledgers", tr["id"], preset.label("transom", "Transom") + " %.2f m" % (tr["l_mm"] / 1000), ntr, tr["mass"], tr.get("estimated", False))
    led = {t["l_mm"]: t["id"] for t in c["ledger"]}
    for b in plan.bays:
        n = 2 * (1 + len(bay_deck_levels(plan, b)))              # inner + outer, base level + every deck level
        m, est = preset.ledger(b.length_mm)
        _add(L, 0, "Ledgers", led.get(b.length_mm, "ledger-%d" % b.length_mm), preset.label("ledger", "Ledger") + " %.2f m" % (b.length_mm / 1000), n, m, est)


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
