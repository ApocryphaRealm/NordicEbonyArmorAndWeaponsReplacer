# Proof renders of the BUILT bow (ebonybowskinned.nif) for the owner's 2026-11-14 08:19 / 08:27 requests: the round
# collar at both ends of the grip (the same braid all round), the arrow's groove in its edge, the limbs round at the
# root and flattening out, and the talons seated on the limbs. Same set-up as bow_proof.py (imported from the game NIF,
# shipped Wolf atlases + normal maps, BACKFACE CULLING ON, Cycles), which this script runs up to its first view.
#   Blender:  blender --background --factory-startup --python bow_collar_proof.py -- <bow nif> <textures root> <out folder>
#   Sheet:    python bow_collar_proof.py --sheet <out folder> <sheet.jpg> [title]
import os, sys


def sheet(src, out, title):
    from PIL import Image, ImageDraw
    rows = [("1. THE WHOLE BOW", [("full_side", "side (string at left)"), ("full_front", "from the front (the target's side)"), ("full_tq", "three-quarter")]),
            ("2. THE TWO COLLARS - one piece, the lower the upper turned over; the braid runs all round (front and back shown)",
             [("col_up_front", "upper collar, front"), ("col_up_back", "upper collar, back"), ("col_lo_front", "lower collar, front"), ("col_lo_back", "lower collar, back")]),
            ("3. THE ARROW GROOVE - red rod: an arrow (r 0.3) on its line beside vanilla's riser at Bow_MidBone; the groove (r 0.5) round it",
             [("groove_string", "from the string, arrow end-on"), ("groove_side", "from the arrow's side"), ("groove_tq", "three-quarter"), ("groove_top", "from above")]),
            ("4. THE TALONS - seated on each limb's back, root on the collar, point along the limb toward the tip",
             [("talon_side", "upper, side"), ("talon_tq", "upper, three-quarter"), ("talon_lo_side", "lower, side"), ("talon_lo_tq", "lower, three-quarter")]),
            ("5. THE LIMB ROOT - round where it leaves the collar, flattening to the limb's own section",
             [("root_side", "upper root, side"), ("root_front", "upper root, front"), ("root_lo_side", "lower root, side"), ("root_lo_front", "lower root, front")]),
            ("6. BACKLIT - bright panel behind, back faces culled as in game: white inside the bow = light through",
             [("backlit_side", "side"), ("backlit_front", "front"), ("backlit_tq", "three-quarter")])]
    tw, th, hd = 420, 520, 30
    W = 4 * tw; H = 40 + sum(hd + th + 22 for _ in rows)
    sh = Image.new("RGB", (W, H), (34, 35, 38)); d = ImageDraw.Draw(sh)
    d.text((8, 10), title, fill=(235, 235, 235)); y = 40
    for head, cells in rows:
        d.text((8, y + 8), head, fill=(255, 205, 120)); y += hd
        for k, (nm, lab) in enumerate(cells):
            p = os.path.join(src, "bc_%s.png" % nm)
            if os.path.isfile(p):
                im = Image.open(p).convert("RGB"); im.thumbnail((tw - 8, th)); sh.paste(im, (k * tw + (tw - im.width) // 2, y))
            d.text((k * tw + 8, y + th + 4), lab, fill=(220, 220, 220))
        y += th + 22
    sh.save(out, quality=90); print("sheet", out, sh.size)


if "--sheet" in sys.argv:
    a = sys.argv[sys.argv.index("--sheet") + 1:]
    sheet(a[0], a[1], a[2] if len(a) > 2 else "Ebony Wolf bow - collar, groove, talons, limb roots (built NIF, backface culling on)")
    raise SystemExit(0)

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "bow_proof.py"), encoding="utf-8").read()
cut = src.index("\nthree_suns()\n# 1.")
a = sys.argv[sys.argv.index("--") + 1:]
sys.argv = sys.argv[:sys.argv.index("--") + 1] + a[:3] + ["bc"]
exec(compile(src[:cut], "bow_proof.py", "exec"))
import bpy, math
from mathutils import Vector

three_suns()
Y = 6.0                                                     # the collars' middle height
shoot("full_side", Vector((-4, 0, 0)), (0, 0, -1), (0, 1, 0), 120, 520, 1100)
shoot("full_front", Vector((0, 0, 0)), (-1, 0, 0.0001), (0, 1, 0), 120, 520, 1100)
shoot("full_tq", Vector((-3, 0, 0)), (-0.6, 0, -0.8), (0, 1, 0), 120, 520, 1100)
for nm, sg in (("up", 1), ("lo", -1)):
    c = Vector((0, sg * Y, 0))
    shoot("col_%s_front" % nm, c, (-0.8, -0.25 * sg, -0.55), (0, 1, 0), 6.5, 900, 1000)
    shoot("col_%s_back" % nm, c, (0.8, -0.25 * sg, 0.55), (0, 1, 0), 6.5, 900, 1000)
# the arrow on its line, as verify.py's arrow-rest check: vanilla's riser half-width at Bow_MidBone + the arrow's radius
ZR = 1.989 + 0.3; rods = []
for sg in (1, -1):
    bpy.ops.mesh.primitive_cylinder_add(radius=0.3, depth=30, location=(-6.0, mid.y, sg * ZR), rotation=(0, math.radians(90), 0))
    r = bpy.context.active_object; r.data.materials.append(emit("arrow", (0.9, 0.05, 0.05), 2.0)); rods.append(r)
gc = Vector((0, mid.y, 0))
shoot("groove_string", gc, (1, 0, 0.0001), (0, 1, 0), 7, 900, 1000)
shoot("groove_side", gc + Vector((0, 0, 0)), (0, 0, -1), (0, 1, 0), 7, 900, 1000)
shoot("groove_tq", gc, (0.55, -0.3, -0.78), (0, 1, 0), 7, 900, 1000)
shoot("groove_top", gc, (0, -1, 0.0001), (1, 0, 0), 9, 1000, 900)
for r in rods: bpy.data.objects.remove(r)
for nm, sg in (("", 1), ("_lo", -1)):
    c = Vector((1.0, sg * 9.5, 0))
    shoot("talon%s_side" % nm, c, (0, 0, -1), (0, 1, 0), 9, 900, 1000)
    shoot("talon%s_tq" % nm, c, (-0.55, -0.15 * sg, -0.82), (0, 1, 0), 9, 900, 1000)
    c = Vector((0, sg * 9.0, 0))
    shoot("root%s_side" % nm, c, (0, 0, -1), (0, 1, 0), 10, 900, 1000)
    shoot("root%s_front" % nm, c, (-1, 0, 0.0001), (0, 1, 0), 10, 900, 1000)
three_suns(False); bg.inputs["Color"].default_value = (0.02, 0.02, 0.02, 1)
for view, look in (("side", (0, 0, -1)), ("front", (1, 0, 0)), ("tq", (0.6, 0, -0.8))):
    L = Vector(look).normalized()
    bpy.ops.mesh.primitive_plane_add(size=80, location=tuple(L * 40))
    pl = bpy.context.active_object; pl.rotation_mode = "QUATERNION"; pl.rotation_quaternion = (-L).to_track_quat("Z", "Y")
    pl.data.materials.append(emit("panel", (1, 1, 1), 6.0))
    fl = bpy.data.lights.new("front", "SUN"); fl.energy = 0.6; fo = bpy.data.objects.new("front", fl); sc.collection.objects.link(fo)
    fo.rotation_mode = "QUATERNION"; fo.rotation_quaternion = L.to_track_quat("-Z", "Y")
    shoot("backlit_%s" % view, Vector((0.5, 0, 0)), look, (0, 1, 0), 32, 800, 1100)
    bpy.data.objects.remove(pl); bpy.data.objects.remove(fo)
print("BOW COLLAR PROOF DONE")
