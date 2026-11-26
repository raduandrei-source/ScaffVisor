"""Build ScaffVisor presets from the sourced research data (web_frames.json).
Usage: python -I build_presets.py <web_frames.json> <presets dir>
Every number comes from the extracted, sourced tables; placeholders are flagged in rules_verified / notes."""
import copy
import json
import math
import os
import sys

SRC, OUT = sys.argv[1], sys.argv[2]
D = json.load(open(SRC, encoding="utf-8"))


def sysd(name_part):
    for s in D:
        if name_part in s["system"]:
            return s
    raise KeyError(name_part)


def comp(s, cid, l=None, cat=None):
    """Component by id (and length when ids repeat)."""
    hits = [c for c in s["components"] if c.get("id") == cid and (cat is None or c["category"] == cat)
            and (l is None or (c.get("dims_mm") or {}).get("l") == l)]
    if len(hits) != 1:
        raise KeyError((s["system"], cid, l, len(hits)))
    return hits[0]


def m(s, cid, l=None):
    return comp(s, cid, l)["mass_kg"]


def by_len(s, ids_lens, key="l_mm", extra=None):
    out = []
    for cid, L in ids_lens:
        e = {"id": cid if not isinstance(cid, tuple) else cid[1], key: L,
             "mass": m(s, cid[0] if isinstance(cid, tuple) else cid, L if isinstance(cid, tuple) else None)}
        if extra:
            e.update(extra)
        out.append(e)
    return out


def table(s, cat, prefix, key="l_mm", dim="l", only=None):
    """All components of a category whose id or desc starts with prefix, keyed by length."""
    out = []
    for c in s["components"]:
        if c["category"] != cat:
            continue
        if not (str(c.get("id", "")).startswith(prefix) or c.get("desc", "").startswith(prefix)):
            continue
        L = (c.get("dims_mm") or {}).get(dim)
        if L is None or (only and L not in only):
            continue
        out.append({"id": c["id"], key: L, "mass": c["mass_kg"]})
    out.sort(key=lambda e: e[key])
    if not out:
        raise KeyError((s["system"], cat, prefix))
    return out


def braces(s, rows):
    """rows: (id, bay_mm, l_mm or None, length_for_id or None). Missing lengths computed from the bay geometry."""
    out = []
    for cid, bay, l, lid in rows:
        c = comp(s, cid, lid)
        e = {"id": cid, "bay_mm": bay, "h_mm": 2000, "l_mm": l if l else int(round(math.hypot(bay, 2000))), "mass": c["mass_kg"]}
        if not l:
            e["l_note"] = "length not in the source; computed from bay x 2.00 m"
        out.append(e)
    return out


def jacks(s, rows):
    out = []
    for cid, h, ext in rows:
        e = {"id": cid, "h_mm": h, "mass": m(s, cid, None if h is None else None)}
        if ext:
            e["ext_max_mm"] = ext
        out.append(e)
    return out


BASE_RULES = {
    "anchor_area_m2": 22,
    "max_free_height_above_anchor_m": 4.0,
    "max_wall_gap_m": 0.3,
    "inner_rail_gap_m": 0.3,
    "jack_ext_min_m": 0.1,
    "jack_ext_max_ratio": 0.68,
    "brace_every_n_bays": 5,
    "access_every_m": 40,
    "wind_factor": {"NONE": 1.0, "NET": 1.5, "TARP": 2.0},
    "joint_deg": 25,
    "min_leg_clearance_m": 0.07,
    "brace_est_mass_per_m": 2.5,
    "brace_est_extra_mm": 0,
    "toeboard_est_kg_per_m": 2.0,
}


def rules(over=None, verified=None, note=""):
    r = copy.deepcopy(BASE_RULES)
    r.update(over or {})
    v = {"anchor_area_m2": False, "max_wall_gap_m": False, "jack_ext_min_m": False}
    v.update(verified or {})
    v["note"] = note
    r["rules_verified"] = v
    r["note"] = "Indicative rules. Not a substitute for a stability calculation or the manufacturer's instructions."
    return r


def preset(pid, name, status, note, sources, approvals, changes, system, components, rules_, kg_range, to_measure, examples=None, sanity_desc=None):
    for t in components["frame"]["steel_light_74"]:
        t.setdefault("verified", False)
    return {
        "_meta": {"id": pid, "name": name, "status": status, "note": note, "units": {"length": "mm", "mass": "kg"},
                  "sources": sources, "approvals": approvals, "changes": changes},
        "system": system,
        "components": components,
        "sanity_check": {"description": sanity_desc or "No catalog example found for this system yet.",
                         "examples": examples or [], "kg_per_m2_range": kg_range if examples else None},
        "to_measure_on_site": to_measure,
        "rules": rules_,
    }


def sysblock(width, bays, extra, comp_frames, decks_per_bay, usable, access_surface, grade_labels, labels, connection,
             width_class, load_class_text, access_extra=0, tube=48.3):
    return {
        "width_mm": width, "leg_axis_mm": width,
        "leg_axis_note": "nominal system width = distance between leg axes (same grid as the decks and bays)",
        "frame_height_mm": 2000, "tube_od_mm": tube,
        "bay_lengths_mm": bays, "extra_bay_lengths_mm": extra,
        "deck_module_width_mm": 320, "decks_per_bay": decks_per_bay, "usable_deck_width_mm": usable,
        "width_class": width_class, "max_load_class": 3, "max_load_kn_m2": 2.0, "load_classes_note": load_class_text,
        "star_pin_spacing_mm": 0, "connection": connection, "diagonals_outside": True, "bay_height_mm": 2000,
        "compensation_frames_mm": comp_frames, "access_surface": access_surface, "access_extra_decks": access_extra,
        "deck_grade_labels": grade_labels, "labels": labels,
    }


TO_MEASURE = ["frame, deck, diagonal and jack weights on real parts",
              "real deck width and number of decks per bay",
              "jack travel and the minimum length that must stay inside the frame",
              "tie length used for the real wall gap"]
P = {}

# ---------------------------------------------------------------- Layher Blitz 100 steel
s = sysd("Blitz 100 Stahl")
PL = "Layher Blitz price list 04/2019 (leiternprofi24.de, 'Layher DE_Blitz_Preisliste.pdf'); weights are 'ca.' guideline values"
AUV = "Layher Blitz Fassadengeruest AuV 11.2013, Art.-Nr. 8102.030 (leiternprofi24.de): jacks p.11, diagonals p.12, tie grids p.19"
grades = {
    "steel_U_LW": table(s, "deck", "3883."),
    "steel_U_T4": table(s, "deck", "3812.") + table(s, "deck", "3802."),
    "alu_U_perforated": table(s, "deck", "3803."),
}
for g in grades.values():
    g.sort(key=lambda e: e["l_mm"])
acc = ([dict(e, surface="aluminium") for e in table(s, "access_deck", "3852.")] +
       [dict(e, surface="plywood") for e in table(s, "access_deck", "3838.")])
P["layher_blitz100_steel"] = preset(
    "layher_blitz100_steel", "Layher Blitz 100 (steel, 109 cm)", "draft",
    "Wide variant of Blitz 70: same decks, rails, diagonals and toeboards, 1.09 m frames with three 0.32 m decks. "
    "'verified' = false until weighed on real parts.",
    [PL + ": frames p.11/13, decks p.15, access p.17, rails p.19, toeboards/diagonals p.21, ties p.27, top level p.29", AUV],
    ["DIBt Z-8.1-840 (Layher Blitz Geruest 100 Stahl), cited in the price list p.6; approval text not read"],
    ["Access deck 0.61 m + one 0.32 m deck in the access bay (AuV p.11: 3 x 0.32 or 0.61 + 0.32).",
     "Eye bolt 4009.121: the price list weight is for a pack of 10 (sold only in VE 10); 0.18 kg per bolt, estimated.",
     "Normal coupler weight is not in the extract of the price list; 1.0 kg estimated (Plettac value).",
     "Tie 1754.069 (0.69 m) as in the Blitz 70 preset; the right length depends on the wall gap."],
    sysblock(1090, [1570, 2070, 2570, 3070], [730, 1090], [660, 1000, 1500], 3, 960, "aluminium",
             {"steel_U_LW": "Steel U-LW 0.32 m", "steel_U_T4": "Steel U-T4 0.32 m", "alu_U_perforated": "Aluminium U, perforated 0.32 m"},
             {"frame": "Blitz frame LW steel 2.00 x 1.09 m", "deck": "Deck U 0.32 m", "access": "Access deck with ladder and hatch 0.61 m",
              "end_rail": "Double end guard rail 1.09 m", "end_toeboard": "End toeboard 1.09 m", "support": "Guard rail support 1.0 m, 1.09 m",
              "tie": "Scaffold tie 0.69 m", "coupler": "Couplers (tie)", "eyebolt": "Ring bolt M12 120 mm"},
             "U-decks hook onto the frame crossbars", "W09 (EN 12811-1), deduced from 3 x 0.32 m",
             "up to LK6 depending on deck type and bay (price list p.6)", access_extra=1),
    {"frame": {"steel_light_74": [{"id": c["id"], "h_mm": c["dims_mm"]["h"], "mass": c["mass_kg"]}
                                  for c in s["components"] if c["category"] == "frame" and c["id"] in ("1780.066", "1780.100", "1780.150", "1780.200")]},
     "timber_deck_w320": grades,
     "access_deck_with_ladder_w640": acc,
     "vertical_brace": braces(s, [("1736.157", 1570, 2250, None), ("1736.207", 2070, 2800, None), ("1736.257", 2570, 3200, None), ("1736.307", 3070, 3600, None)]),
     "guard_rail": table(s, "guard_rail", "Geländer, Stahl"),
     "double_end_guard_rail_74": {"id": "1728.122", "mass": m(s, "1728.122"), "note": "Doppelstirngelaender 1.09 m SW22"},
     "toeboard_timber_h150": table(s, "toeboard", "Bordbrett (Längsseite)"),
     "end_toeboard_74": {"id": "1757.109", "mass": m(s, "1757.109")},
     "top_level": {"steel_guard_rail_support_h1000_w740": {"id": "1719.109", "mass": m(s, "1719.109"), "note": "Blitz Gelaenderstuetze 1.09 m, steel"}},
     "base_plate_threaded": [{"id": "4001.060", "h_mm": 600, "mass": m(s, "4001.060"), "ext_max_mm": 410},
                             {"id": "4002.080", "h_mm": 800, "mass": m(s, "4002.080"), "ext_max_mm": 550}],
     "ties": {"scaffold_tie_80": {"id": "1754.069", "l_mm": 690, "mass": m(s, "1754.069")},
              "normal_coupler": {"id": "coupler", "mass": 1.0, "estimated": True, "note": "not in the price list extract; Plettac value"},
              "eyebolt_120": {"id": "4009.121", "mass": 0.18, "estimated": True, "note": "price list: 1.8 kg per pack of 10"}},
     "tubes": {"steel_48_3x3_2_per_m": 3.76, "note": "generic value"}},
    rules({"brace_every_n_bays": 5, "max_wall_gap_m": 0.3},
          {"brace_every_n_bays": True},
          "From the Layher AuV 11.2013: one diagonal serves at most 5 bays (p.12); jack travel 41 cm (jack 60) and 55 cm (jack 80, price list); "
          "tie grids 8 m staggered / 4 m / 2 m depending on cladding (p.19). The area rule (22 m2 per tie) and the wall gap are placeholders."),
    [9.0, 18.0], TO_MEASURE)

# ---------------------------------------------------------------- Layher Blitz 70 aluminium (frames swapped into the Blitz 70 steel preset)
s = sysd("Blitz 70 Aluminium")
base = json.load(open(os.path.join(OUT, "layher_blitz70_steel.json"), encoding="utf-8"))
p = copy.deepcopy(base)
p["_meta"].update(id="layher_blitz70_alu", name="Layher Blitz 70 (aluminium, 73 cm)", status="draft")
p["_meta"]["approvals"] = ["DIBt Z-8.1-844 (Blitz 70 Alu), cited in the price list p.6; approval text not read"]
p["_meta"]["changes"] = p["_meta"]["changes"] + [
    "Aluminium frames 1714.066/.101/.150/.200 (price list p.11/13) replace the steel frames; all other parts are shared with Blitz 70 steel.",
    "Top-level guard rail support: aluminium 1769.073 (2.7 kg).",
    "Which decks the approval admits with the aluminium frames is set in Z-8.1-844 (not read)."]
p["components"]["frame"]["steel_light_74"] = [
    {"id": c["id"], "h_mm": c["dims_mm"]["h"], "mass": c["mass_kg"], "verified": False}
    for c in s["components"] if c["category"] == "frame"]
p["components"]["top_level"]["steel_guard_rail_support_h1000_w740"] = {"id": "1769.073", "mass": m(s, "1769.073"), "note": "aluminium, without tube connector"}
p["system"]["labels"]["frame"] = "Blitz frame aluminium 2.00 x 0.73 m"
p["sanity_check"] = {"description": "No catalog example found for this system yet.", "examples": [], "kg_per_m2_range": None}
P["layher_blitz70_alu"] = p

# ---------------------------------------------------------------- plettac SL 100 steel
s = sysd("SL 100 Stahl")
SLP = "Altrad plettac SL 70/100 price list (ramirent.ee, Plettac_SL70.100.pdf) pp.3-17, 24-26; weights are guideline values (doc p.2)"
lens = [740, 1100, 1500, 2000, 2500, 3000]
P["plettac_sl100_steel"] = preset(
    "plettac_sl100_steel", "Plettac SL 100 (steel, 110 cm)", "draft",
    "Wide variant of SL 70: 1.10 m frames with three 0.32 m decks; decks, rails, diagonals and toeboards shared with SL 70. "
    "'verified' = false until weighed on real parts.",
    [SLP],
    ["DIBt Z-8.1-171 (plettac SL 100 Stahl), cited p.3/p.5; Geruestgruppe 4-6 (DIN 4420) depending on deck and bay"],
    ["Access bay: B64 access deck + one B32 deck (inferred from the widths, not stated).",
     "Tie rules, jack travel and wall gap are not in the price list: the SL 70 values are used as placeholders."],
    sysblock(1100, [1500, 2000, 2500, 3000], [740, 1100], [500, 1000, 1500], 3, 980, "aluminium",
             {"steel_perforated": "Steel deck SL B32", "timber": "Timber deck SL B32", "aluminium": "Aluminium deck SL B32"},
             {"frame": "Steel frame SL 2.00 x 1.10 m", "deck": "Deck SL B32", "access": "Access deck B64 with ladder",
              "end_rail": "Double end guard rail SL 100", "end_toeboard": "End toeboard SL 100", "support": "Guard rail support SL 100, 1.0 x 1.10 m",
              "tie": "Scaffold tie 0.8 m", "coupler": "Normal couplers SW22 (tie)", "eyebolt": "Ring bolt M12 120 mm"},
             "decks on the frame transom (SL system)", "W09 (EN 12811-1), usable width 980 mm (p.4)",
             "Geruestgruppe 4-6 (DIN 4420) depending on deck and bay (p.3)", access_extra=1),
    {"frame": {"steel_light_74": [{"id": c["id"], "h_mm": c["dims_mm"]["h"], "mass": c["mass_kg"]}
                                  for c in s["components"] if c["category"] == "frame"]},
     "timber_deck_w320": {"steel_perforated": table(s, "deck", "5FSLN47"), "timber": table(s, "deck", "5FSLN04"),
                          "aluminium": table(s, "deck", "5FSLN13", only=lens)},
     "access_deck_with_ladder_w640": [dict(e, surface="aluminium") for e in table(s, "access_deck", "5FSLN5000", only=[2500, 3000])] +
                                     [dict(e, surface="plywood") for e in table(s, "access_deck", "5FSLN5700")],
     "vertical_brace": braces(s, [("5FSNN60003", 1500, 2550, None), ("5FSNN60002", 2000, 2880, None), ("5FSNN60001", 2500, 3260, None), ("5FSNN60000", 3000, 3660, None)]),
     "diagonal_fixing_bracket": {"id": "5FSNN61000", "mass": m(s, "5FSNN61000")},
     "guard_rail": table(s, "guard_rail", "5FSNN05", only=lens),
     "double_end_guard_rail_74": {"id": "5FSL112000", "mass": m(s, "5FSL112000")},
     "single_end_guard_rail_74": {"id": "5FSL109000", "mass": m(s, "5FSL109000")},
     "toeboard_timber_h150": table(s, "toeboard", "5FSNN14", only=lens),
     "end_toeboard_74": {"id": "5FSL115000", "mass": m(s, "5FSL115000")},
     "top_level": {"steel_guard_rail_support_h1000_w740": {"id": "5FSL120000", "mass": m(s, "5FSL120000")},
                   "end_guard_rail_frame_h1000_w740": {"id": "5FSL119000", "mass": m(s, "5FSL119000")}},
     "base_plate_threaded": [{"id": "5FSOG59006", "h_mm": 400, "mass": m(s, "5FSOG59006")},
                             {"id": "5FSOG59007", "h_mm": 600, "mass": m(s, "5FSOG59007")},
                             {"id": "5FSOG59008", "h_mm": 800, "mass": m(s, "5FSOG59008")}],
     "ties": {"scaffold_tie_80": {"id": "5FSNN24005", "l_mm": 800, "mass": m(s, "5FSNN24005")},
              "normal_coupler": {"id": "5FKUP10010", "mass": m(s, "5FKUP10010")},
              "eyebolt_120": {"id": "5FDIV00107", "mass": m(s, "5FDIV00107")}},
     "tubes": {"steel_48_3x3_2_per_m": 3.76, "note": "generic value"}},
    rules({"max_wall_gap_m": 0.2, "jack_ext_max_ratio": 0.75, "brace_est_mass_per_m": 3.0},
          {"jack_ext_max_ratio": False},
          "Placeholders copied from the Plettac SL 70 preset; the SL 100 price list gives no tie, jack or wall-gap rules."),
    [10.0, 18.0], TO_MEASURE)

# ---------------------------------------------------------------- plettac SL 70 aluminium
s = sysd("SL 70 Aluminium")
base = json.load(open(os.path.join(OUT, "plettac_sl70.json"), encoding="utf-8"))
p = copy.deepcopy(base)
p["_meta"].update(id="plettac_sl70_alu", name="Plettac SL 70 (aluminium, 74 cm)", status="draft")
p["_meta"]["sources"] = p["_meta"]["sources"] + [SLP + " (aluminium frames p.6)"]
p["_meta"]["approvals"] = ["DIBt Z-8.1-29.1 (SL 70 aluminium), cited p.3/p.5; Geruestgruppe 3 (2 kN/m2)"]
p["_meta"]["changes"] = p["_meta"]["changes"] + [
    "Aluminium frames 5FSL7020xx (H50/100/150/200) replace the steel frames; everything else is the SL 70 steel preset.",
    "Which decks the approval admits with the aluminium frames is set in Z-8.1-29.1 (not read)."]
p["components"]["frame"]["steel_light_74"] = [
    {"id": c["id"], "h_mm": c["dims_mm"]["h"], "mass": c["mass_kg"], "verified": False}
    for c in s["components"] if c["category"] == "frame" and c["id"].startswith("5FSL7020")]
p["system"].setdefault("labels", {})["frame"] = "Aluminium frame SL B74, 2.00 m"
p["sanity_check"] = {"description": "No catalog example for the aluminium variant yet (the steel examples do not apply).",
                     "examples": [], "kg_per_m2_range": None}
P["plettac_sl70_alu"] = p

# ---------------------------------------------------------------- Huennebeck BOSTA 70
s = sysd("BOSTA 70")
BS = "Huennebeck BOSTA 70 Aufbau- und Verwendungsanleitung (AuV) 2005 (verband-wohneigentum.de, Bosta_70.pdf) pp.3-12, 19-20, 44-55"
L5 = [1250, 1500, 2000, 2500, 3000]
P["hunnebeck_bosta70_steel"] = preset(
    "hunnebeck_bosta70_steel", "Hünnebeck BOSTA 70 (steel, 74 cm)", "draft",
    "Values from the BOSTA 70 assembly instructions (AuV). 'verified' = false until weighed on real parts.",
    [BS],
    ["DIBt Z-8.1-54.2 (p.3); load class 3 EN 12811 / Geruestgruppe 3 DIN 4420"],
    ["Diagonal lengths are not printed; l_mm is computed from bay x 2.00 m.",
     "Toeboards are timber 11 cm (BOSTA), not 15 cm.",
     "Tie couplers and eye bolts are not in the AuV parts list: 1.0 kg and 0.2 kg estimated (Plettac values).",
     "Jack 70 travels up to 50 cm, but the standard configuration (Regelausfuehrung) allows 26.5 cm; beyond that a separate proof is needed."],
    sysblock(740, [1500, 2000, 2500, 3000], [1250], [660, 1000, 1500], 2, 640, "plywood",
             {"steel": "Steel deck x/32", "aluminium": "Aluminium deck x/32", "box_steel": "Hollow-box deck x/32", "timber": "Solid timber plank x/32"},
             {"frame": "B-vertical frame 200/70", "deck": "Deck x/32", "access": "Alu ladder deck x/70 with ladder",
              "end_rail": "Double guard rail 70/cross", "end_toeboard": "Toeboard cross/70", "support": "B-guard rail post N/70",
              "tie": "Scaffold tie 0.75 m", "coupler": "Couplers (tie)", "eyebolt": "Ring bolt M12", "toeboard": "Timber toeboard 11 cm",
              "guard_rail": "Guard rail"},
             "decks on the frame transom", "W06 (EN 12811-1), system width 0.74 m",
             "LK3 for the frame system (p.3)"),
    {"frame": {"steel_light_74": [{"id": c["id"], "h_mm": c["dims_mm"]["h"], "mass": c["mass_kg"]}
                                  for c in s["components"] if c["category"] == "frame" and c["desc"].startswith("B-Vertikalrahmen")]},
     "timber_deck_w320": {"steel": table(s, "deck", "Stahlboden x/32", only=L5), "aluminium": table(s, "deck", "Aluboden x/32", only=L5),
                          "box_steel": table(s, "deck", "Hohlkastenbelag", only=L5), "timber": table(s, "deck", "Vollholzbohle", only=L5)},
     "access_deck_with_ladder_w640": [dict(e, surface="plywood") for e in table(s, "access_deck", "Alu-Leitergangstafel x/70 mit Leiter")],
     "vertical_brace": braces(s, [("410 736", 1500, None, None), ("410 758", 2000, None, None), ("110 020", 2500, None, None), ("110 167", 3000, None, None)]),
     "guard_rail": table(s, "guard_rail", "Schutzgeländer", only=L5),
     "double_end_guard_rail_74": {"id": "534 419", "mass": m(s, "534 419")},
     "single_end_guard_rail_74": {"id": "024 733", "mass": m(s, "024 733")},
     "toeboard_timber_h150": table(s, "toeboard", "Bordbrett (timber", only=L5),
     "end_toeboard_74": {"id": "454 854", "mass": m(s, "454 854")},
     "top_level": {"steel_guard_rail_support_h1000_w740": {"id": "452 980", "mass": m(s, "452 980")}},
     "base_plate_threaded": [{"id": "144 131", "h_mm": 500, "mass": m(s, "144 131"), "ext_max_mm": 265},
                             {"id": "054 630", "h_mm": 700, "mass": m(s, "054 630"), "ext_max_mm": 500,
                              "note": "range 6.5-50 cm; the standard configuration allows 26.5 cm"}],
     "ties": {"scaffold_tie_80": {"id": "078 940", "l_mm": 750, "mass": m(s, "078 940")},
              "normal_coupler": {"id": "coupler", "mass": 1.0, "estimated": True},
              "eyebolt_120": {"id": "eyebolt", "mass": 0.2, "estimated": True}},
     "tubes": {"steel_48_3x3_2_per_m": 3.76, "note": "generic value"}},
    rules({"jack_ext_min_m": 0.065, "max_wall_gap_m": 0.3, "inner_rail_gap_m": 0.3, "brace_est_mass_per_m": 2.6},
          {"jack_ext_min_m": True, "brace_every_n_bays": True, "inner_rail_gap_m": True},
          "From the AuV: jack range from 6.5 cm, 26.5 cm in the standard configuration (p.6/17); one diagonal per five bays (p.19); "
          "inner side protection when the gap exceeds 30 cm (p.4); tie grids 8 m or 4 m staggered by variant (pp.44-55). "
          "The area rule (22 m2 per tie) is a placeholder."),
    [9.0, 16.0], TO_MEASURE)

# ---------------------------------------------------------------- Scafom-rux FRAMESCAFF
s = sysd("FRAMESCAFF")
FS = "Scafom-rux FRAMESCAFF instructions for assembly and use (geruest-welt.de, FramecsaffAVA(4).pdf) pp.2, 8, 10-12, 29-36"
rails = table(s, "guard_rail", "E04FS00")
for e in rails:
    if e["l_mm"] == 2070:
        e.update(mass=4.2, estimated=True, mass_printed=1.2,
                 note="source prints 1.2 kg (checked on the page image), clearly a misprint; 4.2 kg interpolated from 1.57 and 2.57 m")
P["scafom_rux_framescaff"] = preset(
    "scafom_rux_framescaff", "Scafom-rux Framescaff (steel, 73 cm)", "draft",
    "Values from the Framescaff assembly instructions, appendix of parts. 'verified' = false until weighed on real parts.",
    [FS],
    ["DIBt Z-8.1-924; EN 12810/12811, load class 3 (p.2)"],
    ["Diagonal lengths are not printed; l_mm is computed from bay x 2.00 m. No catalog diagonal for the 1.57 m bay: estimated (2.35 kg/m from the 2.07-3.07 m diagonals).",
     "Guard rail 2.07 m: printed 1.2 kg, replaced by 4.2 kg interpolated and flagged as estimated.",
     "Jack travel is not stated as a limit (only loads by spindle length, p.8): ratio 0.68 of the jack length as a placeholder.",
     "Normal coupler and eye bolt not in the parts list: 1.0 kg and 0.2 kg estimated."],
    sysblock(732, [1570, 2070, 2570, 3070], [730, 1090], [660, 1000, 1500], 2, 640, "plywood",
             {"steel_U": "Steel plank 0.32 m", "steel_U_019": "Steel plank 0.19 m"},
             {"frame": "Framescaff frame 2.00 x 0.732 m", "deck": "Steel plank 0.32 m", "access": "Aluminium/plywood ladder frame deck 0.61 m",
              "end_rail": "Double end guard rail 0.732 m", "end_toeboard": "End toeboard 0.732 m", "support": "Guard rail post with transom 1.00 x 0.732 m",
              "tie": "Wall tie 1.0 m", "coupler": "Couplers (tie)", "eyebolt": "Ring bolt M12"},
             "U-profile decks on the frame transom", "W06 (EN 12811-1)", "LK3 (p.2)"),
    {"frame": {"steel_light_74": [{"id": cid, "h_mm": h, "mass": m(s, cid)} for cid, h in
                                  (("E04FS0005", 660), ("E04FS0003", 1000), ("E04FS0002", 1500), ("E04FS0001", 2000))]},
     "timber_deck_w320": {"steel_U": [e for e in table(s, "deck", "E04RS0") if e["id"] not in ("E04RS0608", "E04RS0609", "E04RS0611", "E04RS0612", "E04RS0613", "E04RS0614")]},
     "access_deck_with_ladder_w640": [dict(e, surface="plywood") for e in table(s, "access_deck", "E04RS04")],
     "vertical_brace": braces(s, [("E04FS0036", 2070, None, None), ("E04FS0038", 2570, None, None), ("E04FS0040", 3070, None, None)]),
     "guard_rail": rails,
     "double_end_guard_rail_74": {"id": "E04FS0023", "mass": m(s, "E04FS0023")},
     "single_end_guard_rail_74": {"id": "E04FS0021", "mass": m(s, "E04FS0021")},
     "toeboard_timber_h150": table(s, "toeboard", "E04FS00"),
     "end_toeboard_74": {"id": "E04FS0034", "mass": m(s, "E04FS0034")},
     "top_level": {"steel_guard_rail_support_h1000_w740": {"id": "E04FS0025", "mass": m(s, "E04FS0025")},
                   "end_guard_rail_frame_h1000_w740": {"id": "E04FS0027", "mass": m(s, "E04FS0027")}},
     "base_plate_threaded": [{"id": "E02RS0011", "h_mm": 400, "mass": m(s, "E02RS0011")},
                             {"id": "E02RS0005", "h_mm": 600, "mass": m(s, "E02RS0005")},
                             {"id": "E02RS0002", "h_mm": 780, "mass": m(s, "E02RS0002")}],
     "ties": {"scaffold_tie_80": {"id": "E04AA0095", "l_mm": 1000, "mass": m(s, "E04AA0095")},
              "normal_coupler": {"id": "coupler", "mass": 1.0, "estimated": True},
              "eyebolt_120": {"id": "eyebolt", "mass": 0.2, "estimated": True}},
     "tubes": {"steel_48_3x3_2_per_m": 3.76, "note": "generic value"}},
    rules({"brace_est_mass_per_m": 2.35, "jack_ext_max_ratio": 0.68},
          {"brace_every_n_bays": True},
          "From the instructions: vertical braces in at least every 5th bay on every lift (p.12); ties near the frame top on both standards, "
          "grids 8 m (4 m on the outer standards), 4 m, 4 m staggered or 2 m, V-ties at both ends (pp.10-12). Area rule, wall gap and jack ratio are placeholders."),
    [9.0, 16.0], TO_MEASURE)

# ---------------------------------------------------------------- Altrad Mostostal Plus 70 / 100
s = sysd("Mostostal Plus")
MP = "ALTRAD-Mostostal (Siedlce) 'Frame scaffoldings' catalogue, Mostostal Plus (amm.siedlce.pl, frame-scaffolodings.pdf) pp.3-19"
plus_common = {
    "timber_deck_w320": {"steel_perforated": table(s, "deck", "e4913"), "steel_eco": table(s, "deck", "e4916"),
                         "timber": table(s, "deck", "e4990")},
    "access_deck_with_ladder_w640": [dict(e, surface="plywood") for e in table(s, "access_deck", "e49232")],
    "vertical_brace": braces(s, [("e284715", 1570, 2400, None), ("e284720", 2070, 2800, None), ("e284725", 2570, 3200, None), ("e284730", 3070, 3600, None)]),
    "guard_rail": table(s, "guard_rail", "e2836"),
    "toeboard_timber_h150": table(s, "toeboard", "e2868"),
    "base_plate_threaded": [{"id": "e511204", "h_mm": 400, "mass": m(s, "e511204"), "ext_max_mm": 200},
                            {"id": "e511206", "h_mm": 600, "mass": m(s, "e511206"), "ext_max_mm": 400},
                            {"id": "e511208", "h_mm": 800, "mass": m(s, "e511208"), "ext_max_mm": 600}],
    "ties": {"scaffold_tie_80": {"id": "e286606", "l_mm": 600, "mass": m(s, "e286606")},
             "normal_coupler": {"id": "e581119", "mass": m(s, "e581119")},
             "eyebolt_120": {"id": "e511023", "mass": m(s, "e511023")}},
    "tubes": {"steel_48_3x3_2_per_m": 3.76, "note": "generic value"},
}
plus_rules = rules({"jack_ext_min_m": 0.1},
                   {"jack_ext_max": True},
                   "From the catalogue: jack 0.40 -> 20 cm, 0.60 -> 40 cm, 0.80 -> 60 cm, at least 15 cm of the threaded tube inside the frame (p.6). "
                   "No tie grid, brace or wall-gap rule published: area rule, braces every 5 bays and wall gap are placeholders.")
plus_changes = ["Diagonals for bay x 2.00 m listed by length only (2.40/2.80/3.20/3.60 m); assigned to the 1.57/2.07/2.57/3.07 m bays in order.",
                "Front railing used as the double end guard rail (3.7 kg, as Plettac's double end rail).",
                "No 0.73 m long toeboard in the catalogue: estimated for 0.73 m bays."]
for pid, name, width, frames, comps, decks, endr, endt, sup, acc_extra, wc in (
        ("altrad_mostostal_plus70", "Altrad Mostostal Plus 70 (steel, 73 cm)", 730,
         ("e281606", "e281610", "e281615", "e281620"), [660, 1000, 1500], 2, "e283907", "e286807", "e202091", 0, "W06"),
        ("altrad_mostostal_plus100", "Altrad Mostostal Plus 100 (steel, 109 cm)", 1090,
         ("e281206", "e281210", "e281220"), [660, 1000], 3, "e283910", "e286810", "e202092", 1, "W09")):
    c = copy.deepcopy(plus_common)
    c["frame"] = {"steel_light_74": [{"id": cid, "h_mm": comp(s, cid)["dims_mm"]["h"], "mass": m(s, cid)} for cid in frames]}
    c["double_end_guard_rail_74"] = {"id": endr, "mass": m(s, endr), "note": "front railing"}
    c["end_toeboard_74"] = {"id": endt, "mass": m(s, endt)}
    c["top_level"] = {"steel_guard_rail_support_h1000_w740": {"id": sup, "mass": m(s, sup)}}
    P[pid] = preset(
        pid, name, "draft",
        "Blitz-type frame scaffold made in Poland (also sold in Romania). 'verified' = false until weighed on real parts.",
        [MP],
        ["Safety certificate B/02/014/08 (ITBM Warsaw), height up to 34 m (p.3); decks 2-6 kN/m2 per PN-EN 12811-1"],
        plus_changes + (["Access bay: 0.61 m access deck + one 0.32 m deck; no 1.50 m frame for the 1.09 m width."] if acc_extra else []),
        sysblock(width, [1570, 2070, 2570, 3070], [730, 1090], comps, decks, 320 * decks, "plywood",
                 {"steel_perforated": "Steel plank 0.32 m (perforated)", "steel_eco": "ECO plank 0.32 m", "timber": "Wooden plank 0.32 m"},
                 {"frame": "Steel frame 2.00 x %.2f m" % (width / 1000.0), "deck": "Plank 0.32 m", "access": "Aluminium-plywood access deck with ladder 0.61 m",
                  "end_rail": "Front railing %.2f m" % (width / 1000.0), "end_toeboard": "Transverse toe board %.2f m" % (width / 1000.0),
                  "support": "Steel railing post 1.00 x %.2f m" % (width / 1000.0), "tie": "Anchor coupling with hook 0.60 m",
                  "coupler": "Normal coupling (tie)", "eyebolt": "Anchor eye bolt 0.23 m"},
                 "U-decks on the frame transom (Blitz type)", wc + " (EN 12811-1), deduced from the deck widths",
                 "2-6 kN/m2 by deck and length (p.3)", access_extra=acc_extra),
        c, copy.deepcopy(plus_rules), [9.0, 18.0], TO_MEASURE)

# ---------------------------------------------------------------- SLV-GROUP RAM 2 / SLV 70
s = sysd("RAM 2 / SLV 70")
SL = "SLV-GROUP product catalogue 'System RAM 2 / SLV 70' (machineryline.fi, slv-70-ktl-en.pdf) pp.4-18, values read from the page images"
P["slv_ram2_slv70"] = preset(
    "slv_ram2_slv70", "SLV RAM 2 / SLV 70 (steel, 74 cm)", "draft",
    "Plettac SL 70 type frame scaffold made in Poland. 'verified' = false until weighed on real parts.",
    [SL],
    ["Safety certificates from ITBM Warsaw and SP Sweden (p.4), numbers not given"],
    ["Jack travel, tie rules and wall gap are not published: Plettac SL 70 values used as placeholders.",
     "The kit table (p.18) differs slightly from the catalogue for the end guard rail (4.00 vs 5.30 kg) and the 0.5 m jack (3.00 vs 3.35 kg); catalogue values used."],
    sysblock(740, [1500, 2000, 2500, 3000], [740, 1100], [500, 1000, 1500], 2, 650, "plywood",
             {"steel": "Steel platform 0.32 m", "timber": "Wooden platform 0.32 m"},
             {"frame": "Steel vertical frame 2.00 x 0.74 m", "deck": "Platform 0.32 m", "access": "Aluplywood access with ladder 0.64 m",
              "end_rail": "Side guard rail 0.74 m (double)", "end_toeboard": "Side wooden toe board 0.74 m", "support": "Frame type L steel 1.00 x 0.74 m",
              "tie": "Anchor 0.6 m", "coupler": "Normal coupler (tie)", "eyebolt": "Eye bolt 0.23 m"},
             "star pins on the frame transom (Plettac type)", "W06 (EN 12811-1)", "not stated"),
    {"frame": {"steel_light_74": [{"id": c["id"], "h_mm": c["dims_mm"]["h"], "mass": c["mass_kg"]}
                                  for c in s["components"] if c["category"] == "frame" and c["id"].startswith("SLV-70-01-01-0") and c["id"][-1] in "1234"]},
     "timber_deck_w320": {"steel": table(s, "deck", "SLV-70-02-01"), "timber": table(s, "deck", "SLV-70-02-04")},
     "access_deck_with_ladder_w640": [dict(e, surface="plywood") for e in table(s, "access_deck", "SLV-70-02-05")] +
                                     [dict(e, surface="aluminium") for e in table(s, "access_deck", "SLV-70-02-06")],
     "vertical_brace": braces(s, [("SLV-70-04-01-04", 1500, 2560, None), ("SLV-70-04-01-03", 2000, 2880, None), ("SLV-70-04-01-02", 2500, 3260, None), ("SLV-70-04-01-01", 3000, 3660, None)]),
     "guard_rail": table(s, "guard_rail", "SLV-70-03-01"),
     "double_end_guard_rail_74": {"id": "SLV-70-03-03-01", "mass": m(s, "SLV-70-03-03-01")},
     "toeboard_timber_h150": table(s, "toeboard", "SLV-70-07-01"),
     "end_toeboard_74": {"id": "SLV-70-07-02-01", "mass": m(s, "SLV-70-07-02-01")},
     "top_level": {"steel_guard_rail_support_h1000_w740": {"id": "SLV-70-06-01-01", "mass": m(s, "SLV-70-06-01-01")},
                   "end_guard_rail_frame_h1000_w740": {"id": "SLV-70-01-01-05", "mass": m(s, "SLV-70-01-01-05")}},
     "base_plate_threaded": [{"id": "SLV-UNI-07-01-01", "h_mm": 400, "mass": m(s, "SLV-UNI-07-01-01")},
                             {"id": "SLV-UNI-07-03-01", "h_mm": 600, "mass": m(s, "SLV-UNI-07-03-01")},
                             {"id": "SLV-UNI-07-04-01", "h_mm": 800, "mass": m(s, "SLV-UNI-07-04-01")}],
     "ties": {"scaffold_tie_80": {"id": "SLV-UNI-01-01-07", "l_mm": 600, "mass": m(s, "SLV-UNI-01-01-07")},
              "normal_coupler": {"id": "SLV-UNI-02-01-01", "mass": m(s, "SLV-UNI-02-01-01")},
              "eyebolt_120": {"id": "SLV-UNI-19-01-05", "mass": m(s, "SLV-UNI-19-01-05")}},
     "tubes": {"steel_48_3x3_2_per_m": 3.76, "note": "generic value"}},
    rules({"max_wall_gap_m": 0.2, "jack_ext_max_ratio": 0.75, "brace_est_mass_per_m": 3.0},
          {}, "Placeholders copied from the Plettac SL 70 preset; the SLV catalogue gives only the height limits (24 m standard, 64 m by calculation, p.4). Engine check: 120 m x 3 lifts gives 9.6 t vs 10.46 t in the catalogue kit (-8%); the kit content is not itemised."),
    [9.5, 11.5], TO_MEASURE,
    examples=[{"area_m2": 199.2, "mass_kg": 2090.36, "size": "24.00 x 8.30 m"},
              {"area_m2": 498.0, "mass_kg": 5065.78, "size": "60.00 x 8.30 m"},
              {"area_m2": 996.0, "mass_kg": 10460.88, "size": "120.00 x 8.30 m"}],
    sanity_desc="Catalogue kits (p.18): 3.0 m steel platforms, 3.0 m guard rails and diagonals, 0.4 m anchors, 0.5 m jacks; about 10.5 kg/m2")

# ---------------------------------------------------------------- Altrad assco quadro 70
s = sysd("assco quadro 70")
AQ = "Altrad plettac assco 'assco quadro 70' Aufbau- und Verwendungsanleitung 08/2020 (rolle-gerueste.de, 13_assco_quadro_70_auv_2020_08.pdf) PDF pp.3, 5, 11-12, 38-44, 83-93"


def qtab(cat, cid, only=None):
    out = [{"id": "%s/%d" % (c["id"], c["dims_mm"]["l"]), "l_mm": c["dims_mm"]["l"], "mass": c["mass_kg"]}
           for c in s["components"] if c["category"] == cat and c["id"] == cid and (c.get("dims_mm") or {}).get("l")
           and (only is None or c["dims_mm"]["l"] in only)]
    return sorted(out, key=lambda e: e["l_mm"])


def qid(cid, desc_start):
    hits = [c for c in s["components"] if c["id"] == cid and c["desc"].startswith(desc_start)]
    assert len(hits) == 1, (cid, desc_start, len(hits))
    return hits[0]


qbr = []
for c in s["components"]:
    if c["id"] == "A-18/19":
        bay = int(round(float(c["desc"].split()[1].replace(",", ".")) * 1000))
        qbr.append({"id": "A-18/19/%d" % bay, "bay_mm": bay, "h_mm": 2000, "l_mm": int(round(math.hypot(bay, 2000))),
                    "mass": c["mass_kg"], "l_note": "length computed from bay x 2.00 m"})
P["altrad_assco_quadro70"] = preset(
    "altrad_assco_quadro70", "Altrad assco quadro 70 (steel, 73 cm)", "draft",
    "Values from the assembly instructions (AuV 08/2020), parts annex. The source gives sheet numbers of the approval annex, not article numbers; "
    "codes here are 'sheet/length'. 'verified' = false until weighed on real parts.",
    [AQ],
    ["DIBt Z-8.1-190 (PDF p.3/5); height class H2 to EN 12811-1"],
    ["Codes are annex sheet numbers + length (no article numbers in the source).",
     "Normal coupler: Ankerkupplung A-152 (0.8 kg). Eye bolt not listed: 0.2 kg estimated.",
     "Jacks: 35.5 cm travel in the first unclad standard variant, 20 cm in the other main variants; 0.40 m jack limited to 20 cm."],
    sysblock(730, [1570, 2070, 2570, 3070], [730, 1090], [660, 1000, 1500], 2, 640, "plywood",
             {"steel": "Steel deck 32", "timber": "Timber deck"},
             {"frame": "Vertical frame 2.00 x 0.73 m (t = 2.7 mm)", "deck": "Deck 0.32 m", "access": "Alu frame deck with hatch and ladder 0.61 m",
              "end_rail": "End double guard rail 0.73 m", "end_toeboard": "End toeboard 0.73 m", "support": "Guard rail support 0.73 m",
              "tie": "Scaffold tie 0.8 m", "coupler": "Anchor coupler (tie)", "eyebolt": "Ring bolt M12"},
             "decks on the frame transom", "W06 (EN 12811-1)", "see deck table AuV 1.6"),
    {"frame": {"steel_light_74": [{"id": c["id"], "h_mm": c["dims_mm"]["h"], "mass": c["mass_kg"]}
                                  for c in s["components"] if c["category"] == "frame" and c["id"].startswith("A-1/")]},
     "timber_deck_w320": {"steel": qtab("deck", "A-23/24"), "timber": qtab("deck", "A-28")},
     "access_deck_with_ladder_w640": [dict(e, surface="plywood") for e in qtab("access_deck", "A-98")] +
                                     [dict(e, surface="aluminium") for e in qtab("access_deck", "A-108/109")],
     "vertical_brace": sorted(qbr, key=lambda e: e["bay_mm"]),
     "guard_rail": qtab("guard_rail", "A-40"),
     "double_end_guard_rail_74": {"id": "A-54/D73", "mass": qid("A-54", "Stirnseiten-Doppelgeländer 73")["mass_kg"]},
     "single_end_guard_rail_74": {"id": "A-54/E73", "mass": qid("A-54", "Stirnseitengeländer 73")["mass_kg"]},
     "toeboard_timber_h150": qtab("toeboard", "A-58"),
     "end_toeboard_74": {"id": "A-60/730", "mass": comp(s, "A-60", 730)["mass_kg"]},
     "top_level": {"steel_guard_rail_support_h1000_w740": {"id": "A-48", "mass": m(s, "A-48")},
                   "end_guard_rail_frame_h1000_w740": {"id": "A-56", "mass": m(s, "A-56")}},
     "base_plate_threaded": [{"id": "A-13/400", "h_mm": 400, "mass": comp(s, "A-13", 400)["mass_kg"], "ext_max_mm": 200},
                             {"id": "A-13/600", "h_mm": 600, "mass": comp(s, "A-13", 600)["mass_kg"], "ext_max_mm": 355},
                             {"id": "A-13/800", "h_mm": 800, "mass": comp(s, "A-13", 800)["mass_kg"], "ext_max_mm": 355}],
     "ties": {"scaffold_tie_80": {"id": "A-39/800", "l_mm": 800, "mass": comp(s, "A-39", 800)["mass_kg"]},
              "normal_coupler": {"id": "A-152", "mass": qid("A-152", "Ankerkupplung")["mass_kg"]},
              "eyebolt_120": {"id": "eyebolt", "mass": 0.2, "estimated": True}},
     "tubes": {"steel_48_3x3_2_per_m": 3.76, "note": "generic value"}},
    rules({"max_wall_gap_m": 0.3, "brace_est_mass_per_m": 2.5},
          {"max_wall_gap_m": True, "brace_every_n_bays": True},
          "From the AuV: clear gap deck-facade max. 30 cm (PDF p.11-12); unclad: tie grid 8 m staggered, V-tie once per 5 bays in each tie level "
          "(twice at the top); nets: 4 m grid; tarpaulin: 2 m grid (PDF pp.38-44); jack 35.5 cm (GV) / 20 cm (other variants). "
          "The area rule (22 m2 per tie) is a placeholder for the 8 m staggered grid."),
    [9.0, 16.0], TO_MEASURE)

for pid, p in P.items():
    with open(os.path.join(OUT, pid + ".json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(p, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("wrote", pid)
