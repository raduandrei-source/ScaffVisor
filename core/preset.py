"""Preset JSON loading + mass/size lookups (mm in JSON, m in the plan)."""
import json
import os

PRESET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "presets")


# Numbers of the systems shipped in 0.5.0 (files saved then store these numbers).
_LEGACY_NUMBERS = {"layher_blitz70_steel": 0, "plettac_sl70": 1}
_FAMILY = {}


def enum_number(pid):
    """Fixed number for the System list: Blender saves this number in the .blend file."""
    if pid in _LEGACY_NUMBERS:
        return _LEGACY_NUMBERS[pid]
    import zlib
    return 1000 + zlib.crc32(pid.encode("utf-8")) % 1000000


def family(path):
    return _FAMILY.get(path, "")


def list_presets(directory=None):
    """(id, name, path) of every preset, grouped by family (kind, then family text, then name)."""
    out = []
    d = directory or PRESET_DIR
    if not os.path.isdir(d):
        return out
    for fn in sorted(os.listdir(d)):
        if fn.endswith(".json"):
            try:
                path = os.path.join(d, fn)
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                meta = data["_meta"]
                kind = data.get("system", {}).get("kind", "frame")
                fam = meta.get("family", "")
                _FAMILY[path] = fam
                out.append(((0 if kind == "frame" else 1), fam, meta.get("name", fn[:-5]), fn[:-5], path))
            except Exception:
                continue
    out.sort()
    return [(pid, name, path) for _k, _f, name, pid, path in out]


def load_preset(preset_id, directory=None):
    d = directory or PRESET_DIR
    path = preset_id if preset_id.endswith(".json") else os.path.join(d, preset_id + ".json")
    with open(path, encoding="utf-8") as f:
        return Preset(json.load(f))


def _lookup(table, x, key, val):
    """Exact value if present, otherwise linear interpolation/extrapolation. -> (value, estimated)"""
    for t in table:
        if abs(t[key] - x) < 1:
            return t[val], bool(t.get("estimated", False))
    pts = sorted((t[key], t[val]) for t in table)
    if len(pts) == 1:
        return pts[0][1] * x / pts[0][0], True
    lo = [p for p in pts if p[0] < x]
    hi = [p for p in pts if p[0] > x]
    if lo and hi:
        a, b = lo[-1], hi[0]
    elif hi:
        a, b = hi[0], hi[1]
    else:
        a, b = lo[-2], lo[-1]
    return a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0]), True


class Preset:
    def __init__(self, data):
        self.data = data
        m, s, c, r = data["_meta"], data["system"], data["components"], data["rules"]
        self.id, self.name = m["id"], m["name"]
        self.width = s["width_mm"] / 1000.0
        self.tube_r = s["tube_od_mm"] / 2000.0
        # distance between the leg axes: the nominal system width (axis to axis) when the preset gives it
        self.leg_span = s["leg_axis_mm"] / 1000.0 if s.get("leg_axis_mm") else self.width - 2 * self.tube_r
        self.frame_h = s["frame_height_mm"] / 1000.0
        self.bays_std = list(s["bay_lengths_mm"])
        self.bays_extra = list(s["extra_bay_lengths_mm"])
        self.comp_frames = [x / 1000.0 for x in s["compensation_frames_mm"]]
        self.deck_w = s["deck_module_width_mm"] / 1000.0
        self.decks_per_bay = s["decks_per_bay"]
        self.usable_w = s["usable_deck_width_mm"] / 1000.0
        self.pin_spacing = s["star_pin_spacing_mm"] / 1000.0
        self.rules = r
        self.c = c
        self.labels = s.get("labels", {})
        self.grade_labels = s.get("deck_grade_labels", {})
        self.access_surface = s.get("access_surface", "plywood")
        # standard decks laid beside the access deck (e.g. 1 x 0.32 next to a 0.61 hatch deck in a 1.09 m frame)
        self.access_extra_decks = int(s.get("access_extra_decks", 0))
        # "frame" (frame facade scaffold) or "modular" (standards + ledgers + transoms: ringlock, cuplock, kwikstage ...)
        self.kind = s.get("kind", "frame")
        self.node_spacing = s.get("node_spacing_mm", 0) / 1000.0

    def label(self, key, default):
        """Text used in the bill of materials; presets can override the Plettac defaults."""
        return self.labels.get(key, default)

    def grade_label(self, grade):
        return self.grade_labels.get(grade, grade.replace("_", " ").title())

    def default_grade(self):
        g = self.deck_grades()
        return g[0] if g else ""

    def pick_grade(self, grade):
        """The requested deck grade if this system has it, otherwise its first one."""
        return grade if grade in self.deck_grades() else self.default_grade()

    # --- frames
    def frame(self, h_mm):
        v, est = _lookup(self.c["frame"]["steel_light_74"], h_mm, "h_mm", "mass")
        return v, est

    # --- decks
    def deck(self, l_mm, grade="visually_sorted_S10"):
        tab = self.c["timber_deck_w320"][grade]
        return _lookup(tab, l_mm, "l_mm", "mass")

    def deck_grades(self):
        return [k for k in self.c["timber_deck_w320"] if isinstance(self.c["timber_deck_w320"][k], list)]

    def access_deck(self, l_mm):
        tab = [t for t in self.c["access_deck_with_ladder_w640"] if t["surface"] == self.access_surface]
        return _lookup(tab, l_mm, "l_mm", "mass")

    def access_lengths(self):
        return sorted({t["l_mm"] for t in self.c["access_deck_with_ladder_w640"]})

    # --- braces (catalog only for h=2000; others estimated geometrically)
    def brace(self, bay_mm, h_mm=2000):
        for t in self.c["vertical_brace"]:
            if t["bay_mm"] == bay_mm and t["h_mm"] == h_mm:
                return t["l_mm"], t["mass"], False
        import math
        r = self.rules
        l = math.hypot(bay_mm, h_mm) + r["brace_est_extra_mm"]
        return l, l / 1000.0 * r["brace_est_mass_per_m"], True

    def ledger(self, l_mm):
        return _lookup(self.c["ledger"], l_mm, "l_mm", "mass")

    def guard_rail(self, l_mm):
        return _lookup(self.c["guard_rail"], l_mm, "l_mm", "mass")

    def toeboard(self, l_mm):
        for t in self.c["toeboard_timber_h150"]:
            if t["l_mm"] == l_mm:
                return t["mass"], False
        return l_mm / 1000.0 * self.rules["toeboard_est_kg_per_m"], True

    def jack_max_ext(self, t):
        """Largest allowed visible extension of a jack: its own limit if the catalog gives one, else ratio x length."""
        if "ext_max_mm" in t:
            return t["ext_max_mm"] / 1000.0
        return self.rules["jack_ext_max_ratio"] * t["h_mm"] / 1000.0

    def jack_emax(self):
        return max(self.jack_max_ext(t) for t in self.c["base_plate_threaded"])

    def jack_for(self, ext_m):
        """Shortest threaded jack that allows this visible extension."""
        for t in sorted(self.c["base_plate_threaded"], key=lambda t: t["h_mm"]):
            if ext_m <= self.jack_max_ext(t) + 1e-9:
                return t
        return None
