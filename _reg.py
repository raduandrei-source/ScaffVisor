"""Defensive class registration.

Reinstalling over a running session (or a failed earlier unregister) can leave a class with the
same RNA name registered from the old code. Unregister that one first, then register ours.
"""
import bpy


def register_classes(classes):
    for cls in classes:
        # 1) the same class object is still registered (register() called twice)
        if getattr(cls, "is_registered", False):
            try:
                bpy.utils.unregister_class(cls)
            except Exception:
                pass
        # 2) a class with the same name from older code. Operators and panels are reachable
        #    through bpy.types; PropertyGroups are NOT, so case 1 is the only guard for them.
        old = getattr(bpy.types, cls.__name__, None)
        if old is not None and old is not cls:
            try:
                bpy.utils.unregister_class(old)
            except Exception:
                pass
        bpy.utils.register_class(cls)


def unregister_classes(classes):
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass
