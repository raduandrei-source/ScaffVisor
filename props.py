import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, PointerProperty, StringProperty
from .core import preset as P
from . import _reg

_ITEMS = []


def preset_items(self, context):
    global _ITEMS
    _ITEMS = [(pid, name, "") for pid, name, _ in P.list_presets()] or [("none", "(no preset)", "")]
    return _ITEMS


_GRADES = []


def grade_items(self, context):
    """Deck types of the selected system (a Plettac timber grade, a Layher steel deck, ...)."""
    global _GRADES
    try:
        pr = P.load_preset(self.preset)
        _GRADES = [(g, pr.grade_label(g), "") for g in pr.deck_grades()]
    except Exception:
        _GRADES = []
    return _GRADES or [("none", "(none)", "")]


def _upd(self, context):
    """Property callback: rebuild live, or mark the scaffold as out of date."""
    from . import build
    root = self.id_data
    if self.live_update:
        try:
            build.rebuild_safe(root, context, live=True)
        except Exception:
            pass                        # the error is stored on the root and shown in the panel
    else:
        root["sv_stale"] = 1


def _upd_live(self, context):
    """Turning Live Update back on brings an out-of-date scaffold up to date."""
    from . import build
    root = self.id_data
    if self.live_update and root.get("sv_stale"):
        try:
            build.rebuild_safe(root, context)
        except Exception:
            pass


def _ground_poll(self, o):
    return o.type == "MESH" and o.get("sv_part") is None


# Property identifiers stay unchanged between versions (saved files keep working);
# only names and descriptions follow the UI writing rules (Title Case, no "Use"/"Enable",
# tooltips start with a verb, no trailing period, no default values).
class ScaffVisorSettings(bpy.types.PropertyGroup):
    preset: EnumProperty(name="System", items=preset_items, update=_upd,
                         description="Scaffold system. Dimensions and weights come from its preset")
    height: FloatProperty(name="Height", default=6.3, min=2.1, max=60.0, step=10, precision=2,
                          unit="LENGTH", update=_upd,
                          description="Height of the top working deck above the ground")
    use_face_height: BoolProperty(name="From Faces", default=True, update=_upd,
                                  description="Take the height of each wall from its selected faces")
    height_offset: FloatProperty(name="Offset", default=0.0, min=-10.0, max=10.0, step=10, precision=2,
                                 unit="LENGTH", update=_upd,
                                 description="Add to the face height. A negative value stops the top deck below the wall top")
    gap: FloatProperty(name="Wall Offset", default=0.15, min=0.0, max=1.5, step=1, precision=3,
                       unit="LENGTH", update=_upd,
                       description="Clear distance between the wall and the inner face of the frames. "
                                   "Above 0.30 m inner guard rails are added")
    fit_mode: EnumProperty(name="Ends", update=_upd, default="COVER",
                           items=[("COVER", "Cover", "Let the bays reach or pass the end of the wall"),
                                  ("NEAREST", "Nearest", "Keep the total length as close to the wall as possible"),
                                  ("UNDER", "Inside", "Never pass the end of the wall")])
    allow_short: BoolProperty(name="Short Bays", default=True, update=_upd,
                              description="Allow the short bays of the system (0.74 and 1.10 m for Plettac) for a closer fit")
    cladding: EnumProperty(name="Cladding", update=_upd, default="NONE",
                           items=[("NONE", "None", "Leave the scaffold open"),
                                  ("NET", "Net", "Add a protection net. Ties are multiplied by 1.5 (rule of thumb)"),
                                  ("TARP", "Sheeting", "Close the scaffold with sheeting. Ties are multiplied by 2 (rule of thumb)")])
    flip: BoolProperty(name="Flip", default=False, update=_upd,
                       description="Put the scaffold on the other side of the wall")
    deck_grade: EnumProperty(name="Decks", items=grade_items, update=_upd,
                             description="Deck type of the system. It sets the weights in the bill of materials")
    show_rails: BoolProperty(name="Guard Rails", default=True, update=_upd,
                             description="Display the guard rails. They stay in the bill of materials")
    toeboards: BoolProperty(name="Toeboards", default=True, update=_upd,
                            description="Add 15 cm toeboards along the open edges. They complete the three-part edge "
                                        "protection and are normally mandatory on working decks")
    low_decks: BoolProperty(name="Low Decks", default=True, update=_upd,
                            description="Lay a deck on top of each compensation frame where the ground is high, "
                                        "so the lower wall is reached from a deck")
    show_braces: BoolProperty(name="Braces", default=True, update=_upd,
                              description="Display the diagonal braces. They stay in the bill of materials")
    show_anchors: BoolProperty(name="Ties", default=True, update=_upd,
                               description="Display the wall ties. They stay in the bill of materials")
    show_arrows: BoolProperty(name="Side Arrows", default=True, update=_upd,
                              description="Display arrows pointing to the side of each wall the scaffold is on")
    live_update: BoolProperty(name="Live Update", default=True, update=_upd_live,
                              description="Rebuild after every change. Very large scaffolds wait for Rebuild")
    csv_style: EnumProperty(name="CSV Format", default="SEMI_COMMA",
                            items=[("SEMI_COMMA", "EU", "Semicolon separator, decimal comma (European Excel)"),
                                   ("COMMA_DOT", "US", "Comma separator, decimal point (US and UK Excel)")])
    ground_obj: PointerProperty(name="Ground", type=bpy.types.Object, update=_upd, poll=_ground_poll,
                                description="Terrain mesh the scaffold stands on, through its jacks. "
                                            "Empty means flat ground at the base of the wall")
    ground_max_slope: FloatProperty(name="Max Slope (°)", default=60.0, min=5.0, max=89.0, precision=0,
                                    update=_upd,
                                    description="Count only terrain faces flatter than this angle as ground, "
                                                "so ruin walls in a scan are ignored")
    ground_search_up: FloatProperty(name="Search Height", default=2.0, min=0.2, max=30.0, unit="LENGTH", update=_upd,
                                    description="Probe the ground downwards from this height above the wall base. "
                                                "Keep it below overhangs and wall tops")
    ground_pad: FloatProperty(name="Base Pad", default=0.0, min=0.0, max=0.5, precision=3, unit="LENGTH", update=_upd,
                              description="Thickness of the sole boards or pads under the jacks")
    jack_pref: FloatProperty(name="Jack Extension", default=0.30, min=0.10, max=0.60, precision=2, unit="LENGTH", update=_upd,
                             description="Preferred extension of the base jacks when compensation frames are chosen")
    top_tol: FloatProperty(name="Top Deck Tolerance", default=0.0, min=0.0, max=1.0, precision=2, unit="LENGTH", update=_upd,
                           description="Let the top deck sit up to this much lower than asked, "
                                       "to need fewer compensation frames on sloping ground")
    fp_source: StringProperty(default="")


TABS = [("LAYOUT", "Layout", "Height, offset and fit of the scaffold"),
        ("GROUND", "Ground", "Terrain, jacks and compensation frames"),
        ("PARTS", "Parts", "Decks, edge protection and cladding"),
        ("RESULT", "Result", "Quantities, weight, notes and export")]

classes = (ScaffVisorSettings,)


def register():
    _reg.register_classes(classes)
    bpy.types.Object.scaffvisor = bpy.props.PointerProperty(type=ScaffVisorSettings)
    bpy.types.Scene.scaffvisor_ground = bpy.props.PointerProperty(
        name="Ground", type=bpy.types.Object, poll=_ground_poll,
        description="Terrain mesh for the next scaffold. It can be changed later on the scaffold")
    # Interface state lives on the window manager: it is not saved in the .blend file.
    bpy.types.WindowManager.scaffvisor_tab = bpy.props.EnumProperty(name="Section", items=TABS, default="LAYOUT")


def unregister():
    for owner, attr in ((bpy.types.WindowManager, "scaffvisor_tab"),
                        (bpy.types.Scene, "scaffvisor_ground"),
                        (bpy.types.Object, "scaffvisor")):
        try:
            delattr(owner, attr)
        except Exception:
            pass
    _reg.unregister_classes(classes)
