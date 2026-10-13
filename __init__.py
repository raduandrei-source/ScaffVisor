bl_info = {
    "name": "ScaffVisor",
    "author": "radu",
    "version": (0, 5, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > ScaffVisor",
    "description": "Generate site scaffolding along wall faces or paths, with adjustable height, bill of materials and weight. Plettac SL 70.",
    "category": "3D View",
}

if "bpy" in locals():
    import importlib
    import sys
    for _m in ("_reg", "info", "core.preset", "core.layout", "core.rules", "core.bom", "geometry", "footprint",
               "props", "build", "operators", "ui"):
        _mod = sys.modules.get(__name__ + "." + _m)
        if _mod is not None:
            importlib.reload(_mod)

import bpy
from . import props, build, operators, ui


def _on_load(*_a):
    build.reset_flags()


def register():
    build.reset_flags()          # also on reinstall over a running session (no load_post then)
    props.register()
    operators.register()
    ui.register()
    h = bpy.app.handlers.load_post
    if _on_load not in h:
        h.append(_on_load)


def unregister():
    h = bpy.app.handlers.load_post
    while _on_load in h:
        h.remove(_on_load)
    ui.unregister()
    operators.unregister()
    props.unregister()
