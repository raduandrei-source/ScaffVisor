"""ScaffVisor sidebar.

Layout rules (see the UI principles in the project skill):
- one sidebar tab; the panel has no header of its own (the tab already says "ScaffVisor");
- before a scaffold exists: only the three inputs and one primary action;
- with a scaffold: a status strip (name, weight, notes, options), then one row of section tabs
  (Layout / Ground / Parts / Result), at most one collapsible level inside a tab;
- property split everywhere (labels right-aligned on the left, values on the right, no decorators);
- feedback is drawn dimmed under the value column, next to the control it belongs to;
- notes are never hidden: their count sits in the status strip and links to Result;
  the alert colour is kept for real failures (build error, out of date).
draw() only reads state. It never writes ID data and never parses the whole path.
"""
import json
import bpy
from . import build, _reg

SPLIT = 0.4                 # same label/value ratio Blender uses for property split
MAX_NOTES = 8


# ── small layout helpers ─────────────────────────────────────────────────────

def _result(root):
    try:
        return json.loads(root["sv_result"]) if "sv_result" in root.keys() else {}
    except Exception:
        return {}


def _kg(x):
    return "{:,.0f}".format(x).replace(",", " ")


def _wrap(text, context, indent=0):
    """Split text into lines that fit the current region width."""
    width = 300
    try:
        width = context.region.width
    except Exception:
        pass
    scale = 1.0
    try:
        scale = context.preferences.view.ui_scale
    except Exception:
        pass
    n = max(18, int(width / (6.2 * scale)) - 6 - indent)
    out, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > n:
            out.append(line)
            line = word
        else:
            line = (line + " " + word) if line else word
    if line:
        out.append(line)
    return out or [""]


def _kv(layout, key, value, icon="NONE", dim=False):
    """A read-only row aligned like a property: key right-aligned on the left, value on the right."""
    sp = layout.split(factor=SPLIT)
    k = sp.row()
    k.alignment = "RIGHT"
    k.label(text=key)
    v = sp.row()
    v.active = not dim
    v.label(text=value, icon=icon)
    return v


def _note(layout, text, icon="NONE"):
    """Dimmed feedback under the value column."""
    sp = layout.split(factor=SPLIT)
    sp.label(text="")
    r = sp.row()
    r.active = False
    r.label(text=text, icon=icon)


def _range(a, b, fmt):
    return (fmt % a) if abs(a - b) < 1e-6 else ((fmt % a) + "–" + (fmt % b))


# ── panels ───────────────────────────────────────────────────────────────────

class SCAFFVISOR_PT_main(bpy.types.Panel):
    bl_label = "ScaffVisor"
    bl_idname = "SCAFFVISOR_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ScaffVisor"
    bl_options = {"HIDE_HEADER"}

    def draw(self, context):
        lay = self.layout
        lay.use_property_split = True
        lay.use_property_decorate = False
        root = build.find_root(context.active_object)
        if root is None:
            self.draw_create(context, lay)
            return
        s = root.scaffvisor
        res = _result(root)
        self.draw_status(context, lay, root, res)
        tabs = lay.row()
        tabs.use_property_split = False
        tabs.prop(context.window_manager, "scaffvisor_tab", expand=True)
        lay.separator(factor=0.5)
        tab = context.window_manager.scaffvisor_tab
        if tab == "LAYOUT":
            self.draw_layout(context, lay, root, s, res)
        elif tab == "GROUND":
            self.draw_ground(context, lay, root, s, res)
        elif tab == "PARTS":
            self.draw_parts(context, lay, root, s, res)
        else:
            self.draw_result(context, lay, root, s, res)

    # before a scaffold exists ------------------------------------------------
    def draw_create(self, context, lay):
        o = context.active_object
        if o is None:
            wall, icon = "Nothing selected", "INFO"
        elif o.type == "MESH" and o.mode == "EDIT":
            wall, icon = "Selected faces or edges", "FACESEL"
        elif o.type == "MESH":
            wall, icon = "Base ring of %s" % o.name, "MESH_DATA"
        elif o.type == "CURVE":
            wall, icon = "Curve %s" % o.name, "CURVE_DATA"
        else:
            wall, icon = "Select a mesh or a curve", "INFO"
        col = lay.column()
        _kv(col, "Wall", wall, icon, dim=(icon == "INFO"))
        col.prop(context.scene, "scaffvisor_ground")
        if context.scene.scaffvisor_ground is None:
            _note(col, "Flat ground at the wall base")
        lay.separator()
        r = lay.row()
        r.scale_y = 1.4
        r.operator("scaffvisor.create", icon="MOD_BUILD")
        h = lay.row()
        h.alignment = "RIGHT"
        h.operator("scaffvisor.help", text="Help", icon="HELP", emboss=False)

    # status strip: max. 3 indicators + options ---------------------------------
    def draw_status(self, context, lay, root, res):
        top = lay.row(align=True)
        top.use_property_split = False
        top.label(text=root.name, icon="MOD_BUILD")
        if res and not res.get("empty"):
            top.label(text="%s kg" % _kg(res["total_kg"]))
        n = len(res.get("warnings", []))
        if n:
            top.operator("scaffvisor.show_notes", text=str(n), icon="INFO", emboss=False)
        top.operator("scaffvisor.help", text="", icon="HELP").page = context.window_manager.scaffvisor_tab.lower()
        top.popover("SCAFFVISOR_PT_viewport", text="", icon="OPTIONS")
        top.operator("scaffvisor.remove", text="", icon="TRASH")

        err = root.get("sv_error")
        if err:
            box = lay.box()
            box.alert = True
            for i, t in enumerate(_wrap("Build failed: %s" % err, context)):
                box.label(text=t, icon="ERROR" if i == 0 else "BLANK1")
            box.operator("scaffvisor.rebuild", icon="FILE_REFRESH")
        elif root.get("sv_stale"):
            r = lay.row()
            r.scale_y = 1.4
            r.alert = True
            r.operator("scaffvisor.rebuild", text="Rebuild (Out of Date)", icon="FILE_REFRESH")
        elif res.get("empty"):
            lay.label(text="No bays fit this path", icon="INFO")

    # Layout tab --------------------------------------------------------------
    def draw_layout(self, context, lay, root, s, res):
        chains = res.get("chains", [])
        from_faces = root.get("sv_what") == "selected faces"
        col = lay.column()
        col.prop(s, "preset")
        col.separator()
        if from_faces:
            col.column(heading="Height").prop(s, "use_face_height")
        if from_faces and s.use_face_height:
            col.prop(s, "height_offset")
        else:
            col.prop(s, "height")
        live = [c for c in chains if c.get("n")]
        if live and not res.get("empty"):
            hs = [c["h_deck"] for c in live]
            ns = [c["nmin"] for c in live] + [c["n"] for c in live]
            _note(col, "Top deck %s m · %s lifts" % (_range(min(hs), max(hs), "%.2f"),
                                                     _range(min(ns), max(ns), "%d")))
        col.separator()
        col.prop(s, "gap")
        col.column(heading="Side").prop(s, "flip")
        col.separator()
        col.row().prop(s, "fit_mode", expand=True)
        col.column(heading="Allow").prop(s, "allow_short")
        col.separator()
        sp = col.split(factor=SPLIT)
        k = sp.row()
        k.alignment = "RIGHT"
        k.label(text="Path")
        v = sp.row(align=True)
        sub = v.row()
        sub.active = False
        sub.label(text="%s · %s" % (s.fp_source or "-", root.get("sv_what", "")))
        op = v.operator("scaffvisor.update_path", text="", icon="SELECT_SET")
        op.root_name = root.name

    # Ground tab --------------------------------------------------------------
    def draw_ground(self, context, lay, root, s, res):
        chains = [c for c in res.get("chains", []) if c.get("n")]
        col = lay.column()
        r = col.row(align=True)
        r.prop(s, "ground_obj")
        if s.ground_obj is not None:
            r.operator("scaffvisor.refresh_ground", text="", icon="FILE_REFRESH")
            col.prop(s, "ground_max_slope")
            col.prop(s, "ground_search_up")
            col.prop(s, "ground_pad")
            if chains:
                _note(col, "Ground %s m" % _range(min(c["ground_min"] for c in chains),
                                                  max(c["ground_max"] for c in chains), "%.2f"))
        else:
            _note(col, "Flat ground at the wall base")
        if chains:
            lo = min(max(c["ext_min"], 0.0) for c in chains) * 100
            hi = max(c["ext"] for c in chains) * 100
            comp = sum(c["comp_columns"] for c in chains)
            t = "Jacks %s cm" % _range(lo, hi, "%.0f")
            if comp:
                t += " · %d compensation frame%s" % (comp, "" if comp == 1 else "s")
            _note(col, t)
        head, body = lay.panel("SCAFFVISOR_jacks", default_closed=True)
        head.label(text="Jacks and Tolerance")
        if body is not None:
            b = body.column()
            b.prop(s, "jack_pref")
            if s.ground_obj is not None:
                b.prop(s, "top_tol")

    # Parts tab ---------------------------------------------------------------
    def draw_parts(self, context, lay, root, s, res):
        col = lay.column()
        col.prop(s, "deck_grade")
        add = col.column(heading="Add")
        add.prop(s, "toeboards")
        add.prop(s, "low_decks")
        col.separator()
        col.row().prop(s, "cladding", expand=True)

    # Result tab --------------------------------------------------------------
    def draw_result(self, context, lay, root, s, res):
        if not res or res.get("empty"):
            lay.label(text="No result yet", icon="INFO")
            return
        c = res["counts"]
        col = lay.column()
        _kv(col, "Wall", "%.1f m · %d bays" % (res["wall_length"], c.get("bays", 0)))
        _kv(col, "Frames", "%d · legs %d" % (c.get("frames", 0), c.get("legs", 0)))
        _kv(col, "Braces", "%d · ties %d" % (c.get("braces", 0), c.get("anchors", 0)))
        w = "%.1f kg/m²" % res["kg_m2"]
        if res.get("est_kg", 0) > 0:
            w += " · %s kg estimated" % _kg(res["est_kg"])
        _kv(col, "Weight", w)

        warnings = res.get("warnings", [])
        if warnings:
            lay.separator(factor=0.5)
            box = lay.box()
            box.use_property_split = False
            box.label(text="Notes (%d)" % len(warnings), icon="INFO")
            bc = box.column(align=True)
            for t in warnings[:MAX_NOTES]:
                for i, line in enumerate(_wrap(t, context, indent=2)):
                    bc.label(text=("• " if i == 0 else "   ") + line)
            if len(warnings) > MAX_NOTES:
                bc.label(text="… %d more in the exported CSV" % (len(warnings) - MAX_NOTES))

        head, body = lay.panel("SCAFFVISOR_parts_list", default_closed=True)
        head.label(text="Parts List")
        if body is not None:
            try:
                lines = json.loads(root["sv_bom"])
            except Exception:
                lines = []
            bc = body.column(align=True)
            bc.use_property_split = False
            for d in lines:
                r = bc.row()
                r.label(text=d["desc"])
                q = r.row()
                q.alignment = "RIGHT"
                q.label(text="%d ×  %s kg" % (d["qty"], _kg(d["total_kg"])) + (" *" if d["est"] else ""))

        lay.separator()
        r = lay.row(align=True)
        r.use_property_split = False
        r.scale_y = 1.4
        r.operator("scaffvisor.export_bom", icon="EXPORT")
        sub = r.row(align=True)
        sub.ui_units_x = 2.6
        sub.prop(s, "csv_style", text="")
        r.operator("scaffvisor.open_folder", text="", icon="FILE_FOLDER")
        foot = lay.row()
        foot.active = False
        foot.label(text="Indicative values, not a stability calculation", icon="INFO")


class SCAFFVISOR_PT_viewport(bpy.types.Panel):
    """Viewport options, opened from the status strip (popover only, never drawn in the sidebar)."""
    bl_label = "Viewport"
    bl_idname = "SCAFFVISOR_PT_viewport"
    bl_space_type = "VIEW_3D"
    bl_region_type = "HEADER"
    bl_ui_units_x = 10

    @classmethod
    def poll(cls, context):
        return build.find_root(context.active_object) is not None

    def draw(self, context):
        s = build.find_root(context.active_object).scaffvisor
        lay = self.layout
        col = lay.column(heading="Show")
        col.prop(s, "show_rails")
        col.prop(s, "show_braces")
        col.prop(s, "show_anchors")
        col.prop(s, "show_arrows")
        lay.separator()
        lay.prop(s, "live_update")


classes = (SCAFFVISOR_PT_main, SCAFFVISOR_PT_viewport)


def register():
    _reg.register_classes(classes)


def unregister():
    _reg.unregister_classes(classes)
