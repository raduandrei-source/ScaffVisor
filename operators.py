import csv
import json
import os
import time
import bpy

from . import build, _reg
from .info import docs_url
from .footprint import extract_footprint, FootprintError


def _root(context):
    return build.find_root(context.active_object)


def export_dir():
    """Folder for exported lists: '<blend name>_scaffvisor' next to the .blend file.

    Unsaved files use Blender's temporary folder. The folder is created on first export.
    """
    if bpy.data.filepath:
        base = os.path.splitext(bpy.data.filepath)[0]
        return base + "_scaffvisor"
    return os.path.join(bpy.app.tempdir or os.path.expanduser("~"), "scaffvisor")


class SCAFFVISOR_OT_create(bpy.types.Operator):
    bl_idname = "scaffvisor.create"
    bl_label = "Generate Scaffold"
    bl_description = ("Generate a scaffold along the selected wall faces, or along the active curve or mesh edges. "
                      "Face normals point to the scaffold side")
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        o = context.active_object
        if o is None or o.type not in {"CURVE", "MESH"}:
            cls.poll_message_set("Select the wall mesh (faces in Edit Mode) or a curve")
            return False
        if build.find_root(o) is not None:
            cls.poll_message_set("The active object is already a scaffold")
            return False
        return True

    def execute(self, context):
        try:
            fp = extract_footprint(context)
        except FootprintError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        if context.object and context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        root = bpy.data.objects.new("ScaffVisor", None)
        root.empty_display_type = "ARROWS"
        root.empty_display_size = 0.5
        context.scene.collection.objects.link(root)
        root["sv_fp"] = json.dumps(fp)
        root.scaffvisor.fp_source = fp["source"]
        ground = context.scene.scaffvisor_ground
        if ground is not None:
            build._BUSY = True          # assigning the pointer must not trigger a rebuild by itself
            try:
                root.scaffvisor.ground_obj = ground
            finally:
                build._BUSY = False
        try:
            build.rebuild_safe(root)
        except Exception as e:
            self.report({"ERROR"}, "Build failed: %s" % e)
            bpy.data.objects.remove(root, do_unlink=True)
            return {"CANCELLED"}
        for o in context.selected_objects:
            o.select_set(False)
        root.select_set(True)
        context.view_layer.objects.active = root
        context.window_manager.scaffvisor_tab = "LAYOUT"
        self.report({"INFO"}, "Scaffold created from %s (%d chain(s))" % (fp["what"], len(fp["chains"])))
        return {"FINISHED"}


class SCAFFVISOR_OT_rebuild(bpy.types.Operator):
    bl_idname = "scaffvisor.rebuild"
    bl_label = "Rebuild"
    bl_description = "Rebuild the scaffold from its path and settings"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return _root(context) is not None

    def execute(self, context):
        try:
            build.rebuild_safe(_root(context))
        except Exception as e:
            self.report({"ERROR"}, "Build failed: %s" % e)
            return {"CANCELLED"}
        return {"FINISHED"}


class SCAFFVISOR_OT_update_path(bpy.types.Operator):
    bl_idname = "scaffvisor.update_path"
    bl_label = "New Path from Selection"
    bl_description = ("Replace the path of this scaffold with the active curve or mesh, "
                      "or with its selected faces in Edit Mode")
    bl_options = {"REGISTER", "UNDO"}
    root_name: bpy.props.StringProperty()

    def execute(self, context):
        root = bpy.data.objects.get(self.root_name)
        if root is None:
            return {"CANCELLED"}
        try:
            fp = extract_footprint(context)
        except FootprintError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        root["sv_fp"] = json.dumps(fp)
        root.scaffvisor.fp_source = fp["source"]
        try:
            build.rebuild_safe(root)
        except Exception as e:
            self.report({"ERROR"}, "Build failed: %s" % e)
            return {"CANCELLED"}
        return {"FINISHED"}


class SCAFFVISOR_OT_refresh_ground(bpy.types.Operator):
    bl_idname = "scaffvisor.refresh_ground"
    bl_label = "Re-read Ground"
    bl_description = "Read the terrain mesh again after editing it, then rebuild"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        r = _root(context)
        if r is None or r.scaffvisor.ground_obj is None:
            cls.poll_message_set("Set a ground mesh first")
            return False
        return True

    def execute(self, context):
        build.clear_ground_cache()
        try:
            build.rebuild_safe(_root(context))
        except Exception as e:
            self.report({"ERROR"}, "Build failed: %s" % e)
            return {"CANCELLED"}
        return {"FINISHED"}


class SCAFFVISOR_OT_remove(bpy.types.Operator):
    bl_idname = "scaffvisor.remove"
    bl_label = "Delete Scaffold"
    bl_description = "Delete this scaffold and all its parts"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return _root(context) is not None

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        root = _root(context)
        coll = bpy.data.collections.get("ScaffVisor_" + root.name)
        if coll:
            for o in list(coll.objects):
                if o.get("sv_part"):
                    bpy.data.objects.remove(o, do_unlink=True)
            bpy.data.collections.remove(coll)
        bpy.data.objects.remove(root, do_unlink=True)
        return {"FINISHED"}


class SCAFFVISOR_OT_export_bom(bpy.types.Operator):
    bl_idname = "scaffvisor.export_bom"
    bl_label = "Export Bill of Materials"
    bl_description = ("Save the bill of materials as CSV in a folder next to the .blend file. "
                      "Each export gets a time stamp, so earlier ones are kept")

    @classmethod
    def poll(cls, context):
        r = _root(context)
        if r is None or "sv_bom" not in r.keys():
            cls.poll_message_set("Build a scaffold first")
            return False
        return True

    def execute(self, context):
        root = _root(context)
        res = json.loads(root["sv_result"])
        lines = json.loads(root["sv_bom"])
        folder = export_dir()
        name = bpy.path.clean_name(root.name)
        path = os.path.join(folder, "%s_bom_%s.csv" % (name, time.strftime("%Y%m%d_%H%M%S")))
        eu = root.scaffvisor.csv_style == "SEMI_COMMA"
        f = (lambda x: ("%.2f" % x).replace(".", ",")) if eu else (lambda x: "%.2f" % x)
        try:
            os.makedirs(folder, exist_ok=True)
            # UTF-8 with BOM: opens with correct characters in Excel on every system.
            with open(path, "w", newline="", encoding="utf-8-sig") as fh:
                w = csv.writer(fh, delimiter=";" if eu else ",")
                w.writerow(["System", res.get("preset", "")])
                w.writerow(["Wall length (m)", f(res["wall_length"])])
                for i, ch in enumerate(res["chains"]):
                    w.writerow(["Top deck height, chain %d (m)" % (i + 1), f(ch["h_deck"])])
                w.writerow([])
                w.writerow(["Category", "Code", "Description", "Quantity", "kg each", "kg total", "Estimated"])
                for d in lines:
                    w.writerow([d["cat"], d["code"], d["desc"], d["qty"], f(d["unit_kg"]), f(d["total_kg"]), "yes" if d["est"] else ""])
                w.writerow([])
                w.writerow(["TOTAL kg", "", "", "", "", f(res["total_kg"]), ""])
                w.writerow(["kg/m2 of facade", "", "", "", "", f(res["kg_m2"]), ""])
                w.writerow(["Note", "Indicative catalog values; rows marked 'yes' are estimated. Not a substitute for a stability calculation."])
                if res.get("warnings"):
                    w.writerow([])
                    w.writerow(["Notes"])
                    for t in res["warnings"]:
                        w.writerow(["", t])
        except OSError as e:
            self.report({"ERROR"}, "Cannot write the file: %s" % e)
            return {"CANCELLED"}
        if not bpy.data.filepath:
            self.report({"WARNING"}, "File not saved yet: exported to the temporary folder %s" % folder)
        else:
            self.report({"INFO"}, "Saved: %s" % path)
        return {"FINISHED"}


class SCAFFVISOR_OT_open_folder(bpy.types.Operator):
    bl_idname = "scaffvisor.open_folder"
    bl_label = "Open Export Folder"
    bl_description = "Open the folder with the exported lists in the file browser of the system"

    @classmethod
    def poll(cls, context):
        if not os.path.isdir(export_dir()):
            cls.poll_message_set("Nothing exported yet")
            return False
        return True

    def execute(self, context):
        bpy.ops.wm.path_open(filepath=export_dir())
        return {"FINISHED"}


class SCAFFVISOR_OT_help(bpy.types.Operator):
    bl_idname = "scaffvisor.help"
    bl_label = "Online Help"
    bl_description = "Open the ScaffVisor documentation in the web browser"
    page: bpy.props.StringProperty(default="", options={"SKIP_SAVE", "HIDDEN"})

    def execute(self, context):
        bpy.ops.wm.url_open(url=docs_url(self.page))
        return {"FINISHED"}


class SCAFFVISOR_OT_show_notes(bpy.types.Operator):
    bl_idname = "scaffvisor.show_notes"
    bl_label = "Show Notes"
    bl_description = "Show the notes about this scaffold in the Result section"

    def execute(self, context):
        context.window_manager.scaffvisor_tab = "RESULT"
        return {"FINISHED"}


classes = (SCAFFVISOR_OT_help, SCAFFVISOR_OT_show_notes, SCAFFVISOR_OT_create, SCAFFVISOR_OT_rebuild, SCAFFVISOR_OT_update_path, SCAFFVISOR_OT_refresh_ground,
           SCAFFVISOR_OT_remove, SCAFFVISOR_OT_export_bom, SCAFFVISOR_OT_open_folder)


def register():
    _reg.register_classes(classes)


def unregister():
    _reg.unregister_classes(classes)
