"""Validate ONE ScaffVisor preset file against the engine (same checks as tests/test_core.py).
Usage: python validate_preset.py <path/to/preset.json>   (run from anywhere; engine = C:/Users/radu_/Documents/GitHub/ScaffVisor)"""
import sys, os, json
ROOT = r"C:\Users\radu_\Documents\GitHub\ScaffVisor"
sys.path.insert(0, ROOT)
from core import preset as _P
from core.layout import build_plan, jack_limits
from core.rules import apply_rules
from core.bom import compute_bom
path = sys.argv[1]
pr = _P.load_preset(path)
tag = pr.id
ok = 0
def check(c, msg):
    global ok
    if not c:
        print("FAIL:", msg); sys.exit(1)
    ok += 1
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
        check(len(Bm["lines"]) == len(set((d["cat"], d["code"], d["desc"]) for d in Bm["lines"])), tag + " unique lines")
        check(5.0 < Bm["kg_m2"] < 30.0, "%s kg/m2 %.1f" % (tag, Bm["kg_m2"]))
Pp = build_plan([(0, 0), (30, 0)], False, pr, 0, ground=lambda x, y: 0.1 * x, base_z=0.0, top_z=9.0, phase_tol=0.5)
apply_rules(Pp, pr)
out = [v["ext"] for v in Pp.leg_info.values() if not (emin_ - 1e-6 <= v["ext"] <= emax_ + 1e-6)]
check(not out or any("jack range exceeded" in w for w in Pp.warnings), "%s slope out of range without warning" % tag)
check(len(out) <= 0.5 * len(Pp.leg_info), "%s too many legs out of jack range (%d of %d)" % (tag, len(out), len(Pp.leg_info)))
# reference wall: 30 m x 3 lifts, flat
P = build_plan([(0, 0), (30, 0)], False, pr, 6.0, gap=0.15, allow_short=False)
apply_rules(P, pr)
B = compute_bom(P, pr, deck_grade=pr.default_grade())
print("%s: OK %d checks | 30 m x 3 lifts: %.0f kg, %.1f kg/m2, estimated %.0f kg" % (tag, ok, B["total_kg"], B["kg_m2"], B["est_kg"]))
for d in B["lines"]:
    print("  %-10s %-14s %-48s %4d x %6.2f%s" % (d["cat"], d["code"], d["desc"][:48], d["qty"], d["unit_kg"], " *" if d["est"] else ""))
