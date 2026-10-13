"""Exercise every draw() path of the sidebar headless, with a recording layout.

Blender cannot draw panels in background mode, so a stand-in layout checks each call against
the real UILayout RNA: method names, keyword names, property names on the data, icon names,
operator ids and their properties, popover panel ids. It also prints a text outline per tab and
the widget count (compactness check). Run after tests/test_ground.py (uses /tmp/sv_ground.blend).
"""
import sys, os, json, types
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import bpy
import scaffvisor as sp
sp.register()

UL = bpy.types.UILayout.bl_rna
FUN = {n: [p.identifier for p in f.parameters] for n, f in UL.functions.items()}
LPROPS = set(UL.properties.keys())
ICONS = {i.identifier for i in UL.functions["label"].parameters["icon"].enum_items}
OPEN = {"value": True}
errors = []


def check(cond, msg):
    if not cond:
        errors.append(msg)


class OpProps:
    def __init__(self, idname, rna):
        object.__setattr__(self, "_id", idname)
        object.__setattr__(self, "_keys", set(rna.properties.keys()))

    def __setattr__(self, k, v):
        check(k in self._keys, "operator %s has no property %r" % (self._id, k))


class Rec:
    def __init__(self, out, depth=0):
        object.__setattr__(self, "_out", out)
        object.__setattr__(self, "_d", depth)

    def __setattr__(self, k, v):
        check(k in LPROPS, "UILayout has no attribute %r" % k)
        object.__setattr__(self, k, v)

    def _log(self, kind, text):
        self._out.append(("  " * self._d) + "%-8s %s" % (kind, text))

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        check(name in FUN, "UILayout has no method %r" % name)
        params = FUN.get(name, [])

        def call(*args, **kw):
            bad = set(kw) - set(params)
            check(not bad, "%s(): unknown keywords %s" % (name, bad))
            icon = kw.get("icon", "NONE")
            check(icon in ICONS, "unknown icon %r" % icon)
            if name in ("row", "column", "box", "split", "grid_flow", "column_flow"):
                child = Rec(self._out, self._d + 1)
                if name in ("box", "split") or kw.get("heading"):
                    self._log(name, kw.get("heading", ""))
                return child
            if name == "label":
                self._log("label", (kw.get("text", args[0] if args else "")) + ("  [%s]" % icon if icon != "NONE" else ""))
                return None
            if name in ("prop", "prop_search"):
                data, prop = args[0], args[1]
                check(prop in data.bl_rna.properties.keys(), "%s has no property %r" % (data.bl_rna.identifier, prop))
                if name == "prop_search":
                    check(args[3] in args[2].bl_rna.properties.keys(), "prop_search collection %r" % args[3])
                txt = kw.get("text")
                lab = data.bl_rna.properties[prop].name if prop in data.bl_rna.properties.keys() else prop
                self._log("prop", "%s%s%s" % (lab if txt is None else (txt or "<no label>"),
                                             "  (expanded)" if kw.get("expand") else "", "  [%s]" % icon if icon != "NONE" else ""))
                return None
            if name == "operator":
                idname = args[0]
                mod, fn = idname.split(".")
                try:
                    rna = getattr(getattr(bpy.ops, mod), fn).get_rna_type()
                except Exception:
                    check(False, "unknown operator %s" % idname)
                    return OpProps(idname, bpy.types.Operator.bl_rna)
                self._log("button", "%s%s" % (kw.get("text", rna.name) or "<icon>", "  [%s]" % icon if icon != "NONE" else ""))
                return OpProps(idname, rna)
            if name == "popover":
                pid = kw.get("panel", args[0] if args else "")
                check(hasattr(bpy.types, pid), "popover panel %s not registered" % pid)
                self._log("popover", "%s [%s]" % (pid, icon))
                return None
            if name == "separator":
                check(kw.get("type", "AUTO") in {"AUTO", "SPACE", "LINE"}, "separator type")
                return None
            if name == "panel":
                head = Rec(self._out, self._d + 1)
                self._log("fold", "%s (%s)" % (args[0], "open" if OPEN["value"] else "closed"))
                return head, (Rec(self._out, self._d + 1) if OPEN["value"] else None)
            self._log(name, "")
            return None
        return call


def ctx(active, width=320):
    return types.SimpleNamespace(active_object=active, window_manager=bpy.context.window_manager,
                                 scene=bpy.context.scene, preferences=bpy.context.preferences,
                                 region=types.SimpleNamespace(width=width))


def draw(panel_cls, c, title):
    out = []
    fake = types.SimpleNamespace(layout=Rec(out))
    # bind the panel's own helper methods
    for n in dir(panel_cls):
        if n.startswith("draw_"):
            setattr(fake, n, getattr(panel_cls, n).__get__(fake))
    panel_cls.draw(fake, c)
    widgets = sum(1 for l in out if l.strip().split(" ")[0] in ("prop", "button", "label", "popover"))
    print("\n== %s  (%d widgets)" % (title, widgets))
    print("\n".join(out))
    return widgets


bpy.ops.wm.open_mainfile(filepath="/tmp/sv_ground.blend")
from scaffvisor import ui
root = next(o for o in bpy.data.objects if o.get("sv_fp") is not None)
box = bpy.data.objects.get("box")
wm = bpy.context.window_manager

counts = {}
counts["create"] = draw(ui.SCAFFVISOR_PT_main, ctx(box), "no scaffold selected (create)")
for tab in ("LAYOUT", "GROUND", "PARTS", "RESULT"):
    wm.scaffvisor_tab = tab
    for state in (False, True):
        OPEN["value"] = state
        counts[tab, state] = draw(ui.SCAFFVISOR_PT_main, ctx(root), "%s, folds %s" % (tab, "open" if state else "closed"))
OPEN["value"] = False
wm.scaffvisor_tab = "LAYOUT"
draw(ui.SCAFFVISOR_PT_main, ctx(root, width=200), "narrow sidebar")
root.scaffvisor.ground_obj = None
draw(ui.SCAFFVISOR_PT_main, ctx(root), "GROUND tab without ground") if wm.__setattr__("scaffvisor_tab", "GROUND") is None else None
root["sv_stale"] = 1
draw(ui.SCAFFVISOR_PT_main, ctx(root), "out of date")
root["sv_stale"] = 0
root["sv_error"] = "Mixed add-on versions are loaded. Disable the add-on, restart Blender, then enable it again."
draw(ui.SCAFFVISOR_PT_main, ctx(root, width=240), "build error")
del root["sv_error"]
draw(ui.SCAFFVISOR_PT_viewport, ctx(root), "viewport popover")

# live update off -> a change marks the scaffold out of date; back on -> rebuilt
root.scaffvisor.live_update = False
root.scaffvisor.gap = 0.2
check(root.get("sv_stale") == 1, "change with live update off must mark the scaffold out of date")
root.scaffvisor.live_update = True
check(not root.get("sv_stale"), "turning live update on must rebuild")
# a failing live rebuild is stored, not raised into the property callback
from scaffvisor import build
orig = build.rebuild
build.rebuild = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
root.scaffvisor.gap = 0.25
check(root.get("sv_error") == "boom", "live rebuild error must be stored on the scaffold")
build.rebuild = orig
bpy.ops.scaffvisor.rebuild()
check("sv_error" not in root.keys(), "successful rebuild must clear the error")
# notes link switches the section
wm.scaffvisor_tab = "LAYOUT"
bpy.ops.scaffvisor.show_notes()
check(wm.scaffvisor_tab == "RESULT", "show_notes must open Result")
# tab state is not saved in the file
check("scaffvisor_tab" not in bpy.context.scene.bl_rna.properties.keys(), "tab must not live on the scene")

# open folds are lists the user asked to see; the limit applies to the default (closed) views
# help button: every page it can open exists in the docs folder, and the URL is well formed
from scaffvisor import info
docs = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")
for page, target in info.PAGES.items():
    url = info.docs_url(page)
    check(url.startswith("https://") and url.startswith(info.DOCS_URL), "bad help url %r" % url)
    fn = target.split("#")[0] or "index.html"
    check(os.path.exists(os.path.join(docs, fn[:-5] + ".md")), "help page %r has no source file %s" % (page, fn))
    if "#" in target:
        anchor = target.split("#")[1]
        md = open(os.path.join(docs, fn[:-5] + ".md"), encoding="utf-8").read().lower()
        check(("## " + anchor) in md, "help anchor #%s not found in %s" % (anchor, fn))
check(bpy.ops.scaffvisor.help.poll(), "help operator must always be available")
for tab in ("LAYOUT", "GROUND", "PARTS", "RESULT"):
    check(tab.lower() in info.PAGES, "no help page for tab %s" % tab)

worst = max(v for k, v in counts.items() if k != "create" and not k[1])
print("\nwidgets per view:", counts)
check(counts["create"] <= 6, "create view should stay minimal (%d widgets)" % counts["create"])
check(worst <= 30, "a section shows too many widgets by default (%d)" % worst)
if errors:
    print("\nFAILED:")
    for e in errors:
        print(" -", e)
    sys.exit(1)
print("OK UI checks")
