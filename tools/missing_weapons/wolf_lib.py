# Shared Blender helpers for the four missing Ebony Wolf weapons and the quiver - the GAME-BUILD variant.
#
# The approved designs (2026-11-14, design study "ebony-wolf-missing-weapons-20261113") were made by build_designs.py,
# build_round2.py and build_v1face.py, which sit beside this file unchanged. They import this module by name. The design
# study's own wolf_lib.py also rendered review sheets with materials decoded from the textures; this variant keeps every
# function those scripts call, with the SAME geometry behaviour, and turns the rendering into no-ops:
#   * LOY  - Legacy of Ysgramor's meshes, extracted at build time by tools/build-missing-weapons.py (env NEAW_LOY_MESHES,
#            the folder holding weapons\ebony\<item>.nif under the vanilla names this mod ships them at);
#   * VAN  - the vanilla ebony meshes, read from the game's Skyrim - Meshes0.bsa at build time (env NEAW_VANILLA);
#   * WORK - a scratch folder (env NEAW_WORK).
# The repository carries no Legacy of Ysgramor or Bethesda art.
#
# One difference from the design study's import_nif: that one hid a shape whose decoded texture PNG was missing from its
# work folder. Every shape the designs used had its PNG, so this variant shows every shape that has a diffuse texture and
# is not blood / collision - and build_stage.py checks the resulting loose parts against parts_expected.json (count and
# bounding box of every part id the designs used), so a different split cannot pass silently.
import bpy, os, math, addon_utils
from mathutils import Vector, Matrix
LOY = os.environ["NEAW_LOY_MESHES"]
VAN = os.path.join(os.environ["NEAW_VANILLA"], "meshes", "weapons", "ebony")
WORK = os.environ["NEAW_WORK"]
PNG = os.path.join(WORK, "png")
addon_utils.enable("io_scene_nifly", default_set=True)
from io_scene_nifly.pyn.pynifly import NifFile
HIDE = ("blood", "bhk", "collision")

def clear():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)

def setup(samples=40):
    clear()
    sc = bpy.context.scene
    cam = bpy.data.cameras.new("cam"); cam.type = "ORTHO"; co = bpy.data.objects.new("cam", cam)
    sc.collection.objects.link(co); sc.camera = co
    return sc, co

_mats = {}
def legacy_material(stem):
    """A plain material named after the atlas stem (the build reads o['tex'], never the material)."""
    if stem not in _mats:
        _mats[stem] = bpy.data.materials.new(stem)
    return _mats[stem]

def diffuse_stems(path, van):
    f = NifFile(path); out = {}
    for s in f.shapes:
        try: d = s.shader.textures.get("Diffuse", "")
        except Exception: d = ""
        st = os.path.splitext(os.path.basename(d.replace("\\", "/")))[0].lower()
        out[s.name] = st + ("_van" if (van and st) else "")
    return out

def import_nif(path, van=False, tag=None):
    tex = diffuse_stems(path, van)
    before = set(bpy.data.objects)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.import_scene.pynifly(filepath=path, import_collisions=False)
    shown = []
    for o in [o for o in bpy.data.objects if o not in before]:
        if o.type != "MESH": continue
        nm = o.name if o.name in tex else o.name.split(".")[0]; st = tex.get(nm, "")
        if any(h in (o.name + " " + st).lower() for h in HIDE) or not st:
            o.hide_render = True; o.hide_viewport = True; continue
        o.data.materials.clear(); o.data.materials.append(legacy_material(st)); o["tex"] = st
        o["shape"] = nm
        if tag: o["item"] = tag
        shown.append(o)
    for o in shown:
        mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
    return shown

def world_pts(objs):
    dg = bpy.context.evaluated_depsgraph_get(); P = []
    for o in objs:
        e = o.evaluated_get(dg); me = e.to_mesh(); P += [e.matrix_world @ v.co for v in me.vertices]; e.to_mesh_clear()
    return P

def bbox(objs):
    P = world_pts(objs)
    lo = Vector([min(p[i] for p in P) for i in range(3)]); hi = Vector([max(p[i] for p in P) for i in range(3)]); return lo, hi

def shoot(*a, **k):
    return None

FIXED = [None]
def frame(*a, **k):
    """No render in the game build."""
    return 0.0, 0.0
