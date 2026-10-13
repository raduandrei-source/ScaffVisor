import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.preset import load_preset
from core.layout import build_plan, solve_height, leg_clearance_report, choose_total
from core.rules import apply_rules
from core.bom import compute_bom

p = load_preset("plettac_sl70")
ok = 0
def check(c, msg):
    global ok
    assert c, msg
    ok += 1

# 1. inaltime: orice H din [2.1, 30] se obtine exact, jack in limite
for i in range(21, 301):
    h = i / 10.0
    s = solve_height(h, p)
    check(abs(s["h_deck"] - h) < 1e-6, "h %s" % h)
    check(0.10 - 1e-9 <= s["ext"] <= 0.60 + 1e-9, "ext %s" % h)
    check(s["jack_mm"] is not None and s["ext"] <= 0.75 * s["jack_mm"] / 1000 + 1e-9, "jack %s" % h)

# 2. potrivire travei
for L in range(1600, 20000, 137):
    T, bl = choose_total(L, p.bays_std, p.bays_extra, "COVER")
    check(T >= L and T - L < 600 and sum(bl) == T, "cover %d" % L)
    T, bl = choose_total(L, p.bays_std, p.bays_extra, "UNDER")
    check(T <= L and L - T < 600 and sum(bl) == T, "under %d" % L)

# 3. catalog example: 123 m, 3 lifturi, travei 3 m
P = build_plan([(0, 0), (123, 0)], False, p, 6.3, gap=0.15, allow_short=False)
apply_rules(P, p)
B = compute_bom(P, p)
c = B["counts"]
check((c["frames"], c["stations"], c["braces"], c["legs"]) == (126, 42, 27, 84), "counts %s" % c)
target = 9831 + 679 + 212
check(abs(B["total_kg"] - target) / target < 0.05, "mass %.0f vs %d" % (B["total_kg"], target))
print("catalog: %.0f kg vs %d (%.1f%%)" % (B["total_kg"], target, 100 * (B["total_kg"] / target - 1)))

# 4. dreptunghi inchis, ambele sensuri de parcurgere, fara coliziuni de picioare
for pts in ([(0, 0), (12.3, 0), (12.3, 8.2), (0, 8.2)], [(0, 0), (0, 8.2), (12.3, 8.2), (12.3, 0)]):
    P = build_plan(pts, True, p, 6.0)
    apply_rules(P, p)
    check(not leg_clearance_report(P), "collision rectangle")
    check(len(P.runs) == 4 and all(r["end_kind"] == "convex" for r in P.runs), "convex corners")
    # schela e in exterior: toate piciorele la distanta >= gap de perete
    xs = [s.inner for s in P.stations]
    for (x, y) in xs:
        inside = 0 < x < 12.3 and 0 < y < 8.2
        check(not inside, "leg inside the wall")

# 5. forma L (colt concav) si U
Lsh = [(0, 0), (10, 0), (10, 5), (5, 5), (5, 10), (0, 10)]
P = build_plan(Lsh, True, p, 6.0)
apply_rules(P, p)
kinds = sorted(c["kind"] for c in P.corners)
check(kinds == ["concave"] + ["convex"] * 5, "L corners %s" % kinds)
check(not leg_clearance_report(P), "collision L: %s" % leg_clearance_report(P)[:2])
# nicio statie inauntrul poligonului (pereti)
def inside(pt, poly):
    x, y = pt; c = False
    for i in range(len(poly)):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c
check(not any(inside(s.inner, Lsh) for s in P.stations), "leg inside building (L)")
check(not any(inside(s.outer, Lsh) for s in P.stations), "outer leg inside building (L)")

# 6. cerc poligonal: inel inchis fara colturi
circ = [(10 * math.cos(a * 2 * math.pi / 32), 10 * math.sin(a * 2 * math.pi / 32)) for a in range(32)]
P = build_plan(circ, True, p, 6.0)
check(len(P.runs) == 1 and P.runs[0]["ring"], "inel")
check(not leg_clearance_report(P), "collision circle")

# 7. greutatea creste cu inaltimea, ancore exista peste 4 m
m = []
for h in (3.0, 6.0, 9.0, 12.0):
    P = build_plan([(0, 0), (30, 0)], False, p, h); apply_rules(P, p); b = compute_bom(P, p); m.append(b["total_kg"])
check(m == sorted(m), "monotonic")

# 8. sloped ground (analytic): along-wall slope, cross slope, steps
from core.layout import jack_limits
emin, emax = jack_limits(p)
for name, gf, top in (("along 10deg", lambda x, y: 0.176 * x, 14.0), ("cross 15%", lambda x, y: 0.15 * y, 8.0),
                      ("bumpy", lambda x, y: 0.6 * math.sin(x / 3.0), 9.0)):
    P = build_plan([(0, 0), (30, 0)], False, p, 0, ground=gf, base_z=0.0, top_z=top, phase_tol=0.5)
    apply_rules(P, p)
    check(P.stations, name)
    check(not any("cross-slope" in w for w in P.warnings), name + " " + str(P.warnings))
    for s in P.stations:
        check(abs(s.z_bot + 2 * s.lifts - P.vertical["top_z"]) < 1e-9, name + " lattice")
    for k, v in P.leg_info.items():
        check(emin - 1e-6 <= v["ext"] <= emax + 1e-6, "%s jack ext %.3f" % (name, v["ext"]))
        check(abs(v["z_jack"] - v["ext"] - v["g"]) < 1e-9, name + " jack top")
    # all bays have decks at level 0 and at the same absolute heights
    check(all(min(P.stations[b.i].lifts, P.stations[b.j].lifts) >= 1 for b in P.bays), name + " bay levels")
    B = compute_bom(P, p)
    print("%s: lifts %d-%d, comp columns %d, shift %.2f, kg %.0f" % (name, P.vertical["nmin"], P.vertical["n"], P.vertical["comp_columns"], P.vertical["phase_shift"], B["total_kg"]))
# phase tolerance never increases compensation frames
P0 = build_plan([(0, 0), (30, 0)], False, p, 0, ground=lambda x, y: 0.0, base_z=0.0, top_z=3.0)
P1 = build_plan([(0, 0), (30, 0)], False, p, 0, ground=lambda x, y: 0.0, base_z=0.0, top_z=3.0, phase_tol=0.5)
check(P1.vertical["comp_columns"] <= P0.vertical["comp_columns"], "phase tol")
print("flat top 3.0: comp columns %d -> %d with 0.5 m tolerance (shift %.2f)" % (P0.vertical["comp_columns"], P1.vertical["comp_columns"], P1.vertical["phase_shift"]))
# step ends get end rails
P = build_plan([(0, 0), (30, 0)], False, p, 0, ground=lambda x, y: 0.0 if x < 15 else 2.0, base_z=0.0, top_z=8.0)
apply_rules(P, p)
check(P.vertical["nmin"] != P.vertical["n"] and len(P.end_rails) > 0, "step")

# ---- every preset in presets/ loads and produces a consistent plan + bill of materials
from core import preset as _P
import glob as _g
for path in sorted(_g.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "presets", "*.json"))):
    pr = _P.load_preset(path)
    tag = pr.id
    check(pr.deck_grades() and pr.pick_grade("no-such-grade") == pr.default_grade(), tag + " grades")
    emin_, emax_ = jack_limits(pr)
    check(0 < emin_ < emax_ <= 1.2, "%s jack limits %.2f-%.2f" % (tag, emin_, emax_))
    check(all(pr.jack_for(e) is not None for e in (emin_, 0.3, emax_ - 1e-6)), tag + " jack_for")
    check(pr.jack_for(emax_ + 0.01) is None, tag + " jack above limit")
    for Lw in (7.9, 30.0, 45.7):
        Pp = build_plan([(0, 0), (Lw, 0)], False, pr, 6.3, gap=0.15, fit_mode="COVER")
        apply_rules(Pp, pr)
        tot = sum(b.length_mm for b in Pp.bays) / 1000.0
        check(Lw - 1e-6 <= tot <= Lw + max(pr.bays_std) / 1000.0, "%s cover %.1f -> %.2f" % (tag, Lw, tot))
        check(all(b.length_mm in pr.bays_std or b.length_mm in pr.bays_extra for b in Pp.bays), tag + " bay lengths")
        for gr in pr.deck_grades():
            Bm = compute_bom(Pp, pr, deck_grade=gr)
            check(Bm["total_kg"] > 0 and all(d["unit_kg"] > 0 and d["qty"] > 0 for d in Bm["lines"]), "%s bom %s" % (tag, gr))
            codes = [d["code"] for d in Bm["lines"]]
            check(len(codes) == len(set((d["cat"], d["code"], d["desc"]) for d in Bm["lines"])), tag + " unique lines")
            check(5.0 < Bm["kg_m2"] < 30.0, "%s kg/m2 %.1f" % (tag, Bm["kg_m2"]))
        check(Bm["est_kg"] <= Bm["total_kg"], tag + " estimated share")
    # one-lift-per-2m lattice on a slope with this system's compensation frames
    Pp = build_plan([(0, 0), (30, 0)], False, pr, 0, ground=lambda x, y: 0.1 * x, base_z=0.0, top_z=9.0, phase_tol=0.5)
    apply_rules(Pp, pr)
    # A system whose frame set leaves gaps in the jack range may miss some columns; then the plan must say so.
    out = [v["ext"] for v in Pp.leg_info.values() if not (emin_ - 1e-6 <= v["ext"] <= emax_ + 1e-6)]
    check(not out or any("jack range exceeded" in w for w in Pp.warnings), "%s slope jack ext out of range without a warning" % tag)
    check(len(out) <= 0.5 * len(Pp.leg_info), "%s too many legs out of jack range (%d of %d)" % (tag, len(out), len(Pp.leg_info)))
    Bm = compute_bom(Pp, pr, deck_grade=pr.default_grade())
    print("%s: slope 30 m -> %d frames, %.0f kg, %d jacks, est %.0f kg" % (tag, Bm["counts"]["frames"], Bm["total_kg"], len(Pp.leg_info), Bm["est_kg"]))
print("OK %d checks" % ok)
