# Builds the four missing Ebony Wolf weapons (mace, warhammer, bow, arrow) ONLY from pieces cut out of NordwarUA's wolf
# ebony weapons (Legacy of Ysgramor), each piece keeping its own UVs on its own atlas, so the black and gold match exactly.
# Then renders front / three-quarter / close-up of each, and the source-piece panel.
# Part ids are those of parts_dump.py (same loose-part split and sort), e.g. waraxe_04 = the war axe head plate, front.
# Run: blender --background --factory-startup --python-exit-code 1 --python build_designs.py [-- render]
import bpy, bmesh, sys, os, math, json
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wolf_lib import *
L = os.path.join(LOY, "weapons", "ebony")
OUT = os.path.join(WORK, "design"); os.makedirs(OUT, exist_ok=True)
RENDER = "render" in sys.argv
LOG = []

def note(item, part, how):
    LOG.append({"item": item, "part": part, "how": how})

def load_parts(item):
    objs = import_nif(os.path.join(L, item + ".nif"))
    for o in objs:
        bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT"); bpy.ops.mesh.separate(type="LOOSE"); bpy.ops.object.mode_set(mode="OBJECT")
    parts = [o for o in bpy.data.objects if o.type == "MESH" and not o.hide_render and o.get("item") is None and o.get("src") is None]
    parts.sort(key=lambda o: (o.name.split(".")[0], -max(v.co.y for v in o.data.vertices)))
    key = item.replace("ebony", "")
    out = {}
    for i, p in enumerate(parts):
        pid = "%s_%02d" % (key, i)
        mw = p.matrix_world.copy(); p.data.transform(mw); p.matrix_world = Matrix.Identity(4)   # bake to world coords
        p["src"] = pid; p.name = "SRC_" + pid; p.hide_render = True; out[pid] = p
    return out

def dup(src, name):
    o = src.copy(); o.data = src.data.copy(); o.name = name; bpy.context.scene.collection.objects.link(o)
    o.hide_render = False; o["from"] = src["src"]; return o

def keep_faces(o, pred):
    bm = bmesh.new(); bm.from_mesh(o.data)
    kill = [f for f in bm.faces if not pred(f.calc_center_median())]
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    loose = [v for v in bm.verts if not v.link_faces]; bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(o.data); bm.free()

def xform(o, M):
    o.data.transform(M)
    if M.to_3x3().determinant() < 0: o.data.flip_normals()
    o.data.update()

def T(x, y, z): return Matrix.Translation((x, y, z))
def S(x, y=None, z=None): return Matrix.Diagonal((x, x if y is None else y, x if z is None else z, 1.0))
def R(deg, ax): return Matrix.Rotation(math.radians(deg), 4, ax)

def subdivide_long(o, axis=1, maxlen=1.2, cuts=None):
    bm = bmesh.new(); bm.from_mesh(o.data)
    for _ in range(4):
        long = [e for e in bm.edges if abs(e.verts[0].co[axis] - e.verts[1].co[axis]) > maxlen]
        if not long: break
        bmesh.ops.subdivide_edges(bm, edges=long, cuts=1, use_grid_fill=True)
    bm.to_mesh(o.data); bm.free()

GROUPS = {}
def add(item, o, part, how):
    o["item"] = item; GROUPS.setdefault(item, []).append(o); note(item, part, how)

sc, co = setup(48)
P = {}
for it in ["ebonywaraxe", "ebonybattleaxe", "ebonysword"]:
    P.update(load_parts(it))

# ------------------------------------------------------------------ MACE (one-handed) - all war axe, atlas axe1hebony
# haft axis of the war axe: x = 0.65, z = 0
AX = Vector((0.65, 0.0, 0.0))
for pid in ["waraxe_12", "waraxe_21", "waraxe_22", "waraxe_23", "waraxe_24", "waraxe_25", "waraxe_26"] + ["waraxe_%02d" % i for i in range(13, 21)]:
    add("mace", dup(P[pid], "mace_" + pid), pid, "haft, socket, grip and paw pommel kept as the war axe has them")
# head core: a second twist-langet tube (waraxe_12) stacked above the first
core = dup(P["waraxe_12"], "mace_core"); xform(core, T(0, 29.5, 0) @ S(1, 0.75, 1) @ T(0, -16.25, 0)); add("mace", core, "waraxe_12", "a second twist-langet tube (x0.75 tall) as the head core")
# six flanges: the war axe BIT (head plate front+back and its edge strips, faces left of the haft), scaled 0.62, arrayed every 60 deg
bit_ids = ["waraxe_04", "waraxe_06", "waraxe_05", "waraxe_07", "waraxe_11"]
for k in range(6):
    for pid in bit_ids:
        f = dup(P[pid], "mace_flange%d_%s" % (k, pid))
        if pid in ("waraxe_04", "waraxe_06"): keep_faces(f, lambda c: c.x < -0.5)
        M = T(AX.x, 0, 0) @ R(60 * k, "Y") @ T(-0.9, 36.0, 0) @ S(0.48, 0.62, 0.62) @ T(-AX.x, -30.6, 0)
        xform(f, M); add("mace", f, pid, "the war axe's knotwork bit as a flange (x0.62 tall, x0.48 deep, 6 around the head)" if k == 0 else None)
# crown: collar ring + the war axe's top spike
ring = dup(P["waraxe_24"], "mace_crownring"); xform(ring, T(0, 41.6 - 4.0, 0)); add("mace", ring, "waraxe_24", "gold collar ring moved up as the head's top band")
ring2 = dup(P["waraxe_24"], "mace_basering"); xform(ring2, T(0, 29.4 - 4.0, 0)); add("mace", ring2, "waraxe_24", "gold collar ring under the flanges")
for pid in ["waraxe_00", "waraxe_01", "waraxe_02", "waraxe_03"]:
    s = dup(P[pid], "mace_" + pid); xform(s, T(AX.x, 42.0, 0) @ S(0.85) @ T(-AX.x, -38.0, 0)); add("mace", s, pid, "the war axe's top spike as the crown point (x0.85)")

# ------------------------------------------------------------------ WARHAMMER (two-handed) - all battle axe, atlas axe2hebony
for i in range(27):
    pid = "battleaxe_%02d" % i
    if pid in ("battleaxe_04", "battleaxe_05", "battleaxe_08"): continue          # the bit's edge strips go with the bit
    o = dup(P[pid], "wh_" + pid)
    if pid in ("battleaxe_00", "battleaxe_03"): keep_faces(o, lambda c: c.x > -1.3 or (c.y > 49.0 and c.x > -2.6))   # head plate minus the bit
    add("warhammer", o, pid, "battle axe kept: haft, grip, butt cap, socket, top spike, back fang" if i == 0 else None)
# hammer: the battle axe's paw butt-cap turned 90 deg so its lobed end is the striking face, x1.75
for pid, why in (("battleaxe_26", "the paw butt-cap, turned to face forward, x1.75 - the striking face"),):
    h = dup(P[pid], "wh_hammer"); c = Vector((-0.6, -42.36, -0.6))
    xform(h, T(-1.1, 43.5, 1.1) @ R(-90, "Z") @ S(1.75) @ T(-c.x, -c.y, -c.z)); add("warhammer", h, pid, why)
rg = dup(P["battleaxe_22"], "wh_hammerring"); c = Vector((0.16, 6.95, 0.44))
xform(rg, T(-2.0, 43.5, 1.1) @ R(-90, "Z") @ S(1.9) @ T(-c.x, -c.y, -c.z)); add("warhammer", rg, "battleaxe_22", "gold ring (x1.9) where the hammer meets the socket")

# ------------------------------------------------------------------ BOW - sword pieces (sword1hebony) + war axe wrap for the string
bow = []
g = dup(P["sword_08"], "bow_grip"); xform(g, T(0, 0.81, 0)); bow.append(g); add("bow", g, "sword_08", "the sword's ridged grip as the bow grip")
for sgn in (1, -1):
    for pid in ("sword_06", "sword_07"):
        o = dup(P[pid], "bow_guard%d_%s" % (sgn, pid)); xform(o, S(1, sgn, 1) @ T(0, 6.1, 0) @ S(0.62, 0.62, 1.0) @ T(0, -5.91, 0)); bow.append(o)
        add("bow", o, pid, "the sword's scroll-band crossguard (x0.62) at each end of the grip - limbs seated like blades in a hilt" if sgn == 1 else None)
    for pid in ("sword_00", "sword_01", "sword_02", "sword_03", "sword_04", "sword_05"):
        o = dup(P[pid], "bow_limb%d_%s" % (sgn, pid)); subdivide_long(o)
        xform(o, S(1, sgn, 1) @ T(0, 7.0, 0) @ S(0.86, 0.86, 1.3) @ T(0, -6.71, 0)); o["limb"] = sgn; bow.append(o)
        add("bow", o, pid, "the sword's blade (fuller + gold interlace) as each limb, x0.86, thickened x1.3, bent and recurved" if sgn == 1 else None)
for sgn in (1, -1):        # fang spurs on the back of the bow, sweeping up each limb from the guard
    for pid in ("waraxe_04", "waraxe_06", "waraxe_08", "waraxe_09", "waraxe_10"):
        f = dup(P[pid], "bow_spur%d_%s" % (sgn, pid))
        if pid in ("waraxe_04", "waraxe_06"): keep_faces(f, lambda c: c.x > 2.0)
        for v in f.data.vertices:
            x, y, z = v.co
            v.co = Vector((z * 0.7, sgn * (7.4 + (x - 2.0) * 0.72), 0.45 + (y - 31.5) * 0.72))
        f.data.update()
        if sgn < 0: f.data.flip_normals()
        bow.append(f); add("bow", f, pid, "the war axe's back fang (x0.72) as a spur on the back of each limb above the guard" if sgn == 1 else None)
# bend the limbs in the (y, z) plane, toward -z (the string side once turned), with a recurve at the tip
L0, LEN = 7.0, 50.4
def centre(t):                        # centre line point and tangent angle at arc length t along the limb (0..LEN)
    u = t / LEN; back = 15.5 * u ** 2.1; rec = 5.0 * max(0.0, (u - 0.72) / 0.28) ** 2.2
    return back - rec
def frame_at(t):
    e = 0.05; z0 = centre(t); z1 = centre(t + e); zm = centre(max(0, t - e))
    ang = math.atan2(z1 - zm, 2 * e); return z0, ang
for o in bow:
    if o.get("limb") is None: continue
    sg = o["limb"]
    for v in o.data.vertices:
        y = v.co.y * sg - L0
        if y <= 0: continue
        zc, ang = frame_at(y)
        # straight-limb coords: along = y, off-axis = v.co.z -> rotate the cross-section with the tangent
        off = v.co.z
        ny = L0 + y * math.cos(ang * 0.0) - off * math.sin(ang) ; nz = -zc + off * math.cos(ang)
        v.co.y = sg * ny; v.co.z = nz
    o.data.update()
tip_z = -centre(LEN); tip_y = L0 + LEN
s = dup(P["waraxe_25"], "bow_string"); c = Vector((0.63, -2.8, -0.03))
xform(s, T(0, 0, tip_z) @ S(0.11, 2 * tip_y / 12.83, 0.11) @ T(-c.x, -c.y, -c.z)); bow.append(s)
add("bow", s, "waraxe_25", "the war axe's wrapped grip, thinned to x0.11 and stretched tip to tip, as the twisted string")
for o in bow: xform(o, R(90, "Y"))       # z -> x: limbs bend back toward the string at -x, as vanilla's bow

# ------------------------------------------------------------------ ARROW (points -y, nock at 0, as vanilla) - war axe + battle axe pieces
sh = dup(P["battleaxe_23"], "arrow_shaft"); c = Vector((-0.08, -12.21, 0.08))
xform(sh, T(0, -28.25, 0) @ S(0.15, 53.5 / 37.34, 0.15) @ T(-c.x, -c.y, -c.z)); add("arrow", sh, "battleaxe_23", "the battle axe's long wrapped haft, thinned to x0.15, as the shaft")
for pid in ["waraxe_00", "waraxe_01", "waraxe_02", "waraxe_03"]:
    hd = dup(P[pid], "arrow_" + pid); xform(hd, T(0, -55.0, 0) @ R(180, "Z") @ S(0.78) @ T(-0.6, -38.03, 0))
    add("arrow", hd, pid, "the war axe's top spike (x0.78) as the arrowhead")
for k in range(3):
    for pid in ["waraxe_04", "waraxe_06", "waraxe_08", "waraxe_09", "waraxe_10"]:
        f = dup(P[pid], "arrow_vane%d_%s" % (k, pid))
        if pid in ("waraxe_04", "waraxe_06"): keep_faces(f, lambda c: c.x > 2.0)
        # fang: x 2..11.2 along, y 31.5..39.2 radial -> along the shaft (hook trailing to the nock), radial out from it
        for v in f.data.vertices:          # along the shaft (hook trailing at the nock end), radial above the fang's own lower edge
            x, y, z = v.co; ylow = 34.0 - (x - 2.0) * (2.5 / 9.2)
            v.co = Vector((z * 0.5, -4.5 + (x - 11.2) * 0.9, 0.33 + max(0.0, y - ylow) * 0.30))
        f.data.update(); xform(f, R(120 * k, "Y")); add("arrow", f, pid, "the war axe's back fang (x0.9 long, x0.3 high) as each of three vanes" if k == 0 else None)
nk = dup(P["waraxe_26"], "arrow_nock"); c = Vector((0.58, -14.73, -0.03))
xform(nk, T(0, 0, 0) @ R(180, "Z") @ S(0.3) @ T(-c.x, -c.y, -c.z)); add("arrow", nk, "waraxe_26", "the war axe's paw pommel (x0.3) as the nock")

# vanilla's arrow points +y (head near y 0, nock near y -60.7) - turn ours to match (2026-11-14; the first sheet drew it reversed)
for o in GROUPS["arrow"]: xform(o, T(0, -61.5, 0) @ R(180, "Z"))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "designs.blend"))
json.dump([x for x in LOG if x["how"]], open(os.path.join(OUT, "provenance.json"), "w"), indent=1)
for k, v in GROUPS.items():
    lo, hi = bbox(v); print("GROUP", k, len(v), "lo", tuple(round(x, 1) for x in lo), "hi", tuple(round(x, 1) for x in hi), "faces", sum(len(o.data.polygons) for o in v))

if RENDER:
    import wolf_lib; wolf_lib.FIXED[0] = 128.0
    views = {"mace": [("front", 0, 0, None, 700, 1400), ("tq", 35, 18, None, 700, 1400), ("close", 30, 20, (24, 48), 900, 900)],
             "warhammer": [("front", 0, 0, None, 700, 1400), ("tq", 35, 18, None, 700, 1400), ("close", 30, 20, (34, 59), 900, 900)],
             "bow": [("front", 0, 0, None, 700, 1400), ("tq", 50, 18, None, 700, 1400), ("close", 60, 15, (-12, 14), 900, 900)],
             "arrow": [("front", 0, 0, None, 700, 1400), ("tq", 35, 18, None, 700, 1400), ("close", 40, 20, (-10, 0.5), 900, 900), ("close2", 30, 20, (-62, -50), 900, 900)]}
    only = [a for a in sys.argv if a.startswith("only=")]
    for k, vs in views.items():
        if only and k not in only[0][5:].split(","): continue
        for (name, yaw, pitch, yr, W, H) in vs:
            frame(sc, co, GROUPS[k], os.path.join(OUT, "%s_%s.png" % (k, name)), math.radians(yaw), math.radians(pitch), W=W, H=H, yr=yr)
