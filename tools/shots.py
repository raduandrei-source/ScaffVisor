"""Panel screenshots for the guide (after LiquiVisor's tools/shots.py).

    set BLENDER_USER_RESOURCES=<empty temp folder>
    blender --factory-startup "<project>.blend" --python tools/shots.py -- <ABSOLUTE output dir>

Runs Blender with its window on a real project (the Deleni test file). The panel is moved to the NLA editor's
sidebar so nothing else is in the picture; a timer walks through the states, takes a window screenshot, crops it
to the sidebar and quits without saving the project.
"""
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else os.path.join(HERE, "..", "docs", "img")
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))   # folder that holds the add-on folder
import importlib
sv = importlib.import_module(os.path.basename(os.path.dirname(HERE)))

sv.ui.SCAFFVISOR_PT_main.bl_space_type = "NLA_EDITOR"
sv.ui.SCAFFVISOR_PT_main.bl_region_type = "UI"
sv.register()

prefs = bpy.context.preferences
prefs.view.show_splash = False
prefs.view.ui_scale = 1.15
scene = bpy.context.scene
WM = bpy.context.window_manager
ROOT_NAME = os.environ.get("SV_ROOT", "ScaffVisor")
WALL_NAME = os.environ.get("SV_WALL", "Mesh.002_Model")
GROUND_NAME = os.environ.get("SV_GROUND", "Deleni crop")


def activate(o):
    bpy.context.view_layer.update()
    for x in scene.objects:
        x.select_set(False)
    bpy.context.view_layer.objects.active = o
    if o is not None:
        o.select_set(True)


root = bpy.data.objects.get(ROOT_NAME)
wall = bpy.data.objects.get(WALL_NAME)
ground = bpy.data.objects.get(GROUND_NAME)


def s_start():
    activate(None)


def s_wall():
    scene.scaffvisor_ground = ground
    activate(wall)


def s_layout():
    activate(root)
    s = root.scaffvisor
    if s.preset != "plettac_sl70":
        s.preset = "plettac_sl70"          # the file was made when Plettac was the only system
    WM.scaffvisor_tab = "LAYOUT"


def s_ground():
    WM.scaffvisor_tab = "GROUND"


def s_parts():
    WM.scaffvisor_tab = "PARTS"


def s_result():
    WM.scaffvisor_tab = "RESULT"


STATES = [s_start, s_wall, s_layout, s_ground, s_parts, s_result]
state = {"i": 0, "phase": 0}


def area():
    win = WM.windows[0]
    big = max(win.screen.areas, key=lambda a: a.width * a.height)
    if big.type != "NLA_EDITOR":
        big.type = "NLA_EDITOR"
    return win, big


def crop(path, r, win):
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    sx, sy = w / win.width, h / win.height
    x0, y0 = int(r.x * sx), int(r.y * sy)
    x1, y1 = int((r.x + r.width) * sx), int((r.y + r.height) * sy)
    sub = px[y0:y1, x0:x1]
    skip = int(48 * sy)                             # the region's scroll arrow sits in the bottom corner
    body = sub[skip:]
    bg = sub[skip:skip + 1, 24:25, :3]               # a pixel inside the region, away from its border
    rows = np.where(np.abs(body[:, 8:-8, :3] - bg).sum(axis=2).max(axis=1) > 0.02)[0]
    if len(rows):                                   # trim the empty space under the panel (rows run bottom-up)
        sub = sub[max(skip + rows.min() - 14, 0):]
    out = bpy.data.images.new("crop", sub.shape[1], sub.shape[0], alpha=False)
    out.pixels = sub.ravel()
    out.filepath_raw = path
    out.file_format = "PNG"
    out.save()
    bpy.data.images.remove(out)
    bpy.data.images.remove(img)


def tick():
    try:
        win, a = area()
        a.spaces.active.show_region_ui = True
        if state["phase"] == 0:
            STATES[state["i"]]()
            state["phase"] = 1
            for r in a.regions:
                r.tag_redraw()
            return 2.0 if STATES[state["i"]] is s_layout else 0.9
        r = [r for r in a.regions if r.type == "UI"][0]
        name = "panel-%s.png" % STATES[state["i"]].__name__[2:].replace("_", "-")
        path = os.path.join(OUT, name)
        with bpy.context.temp_override(window=win, area=a):
            bpy.ops.screen.screenshot(filepath=path)
        crop(path, r, win)
        print("SHOT", name)
        state["i"] += 1
        state["phase"] = 0
        if state["i"] >= len(STATES):
            bpy.ops.wm.quit_blender()
            return None
        return 0.3
    except Exception:
        import traceback
        traceback.print_exc()
        bpy.ops.wm.quit_blender()
        return None


bpy.app.timers.register(tick, first_interval=3.0)
