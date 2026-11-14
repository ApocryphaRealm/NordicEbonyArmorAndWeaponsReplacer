# The Blender half of the game build of the four missing Ebony Wolf weapons and the quiver.
#
# Runs the three approved design scripts in one namespace, exactly as approved (2026-11-14 01:47):
#   build_designs.py                   - mace, bow, arrow (round 1)
#   build_round2.py (body)             - the quiver and its six quiver arrows (round 2)
#   build_v1face.py (body), "-- ext=5.0 art chamfer=0.8"
#                                      - the warhammer: V1 head, round extension, paw-cap band art, 45-degree gold lip,
#                                        the gnarled face (round 3)
# then makes them game-ready and exports single-shape NIFs for assemble.py:
#   * ONE ATLAS PER ARROW (forced by the engine): the game hides the quiver arrows one by one by the shape names
#     Arrow1..Arrow6, so each quiver arrow must be ONE BSTriShape - one texture set. The approved arrow's shaft was the
#     battle axe's wrapped haft (axe2hebony) while the head, vanes and nock are war axe pieces (axe1hebony). The shaft is
#     rebuilt from the war axe's own wrapped grip (waraxe_25, axe1hebony - the same leather wrap, the piece the bow string
#     already uses), four lengths stacked so the wrap keeps its pitch, at the approved shaft's exact length and radius.
#     Done before the quiver is built, so the loose arrow, the arrow in flight and the six quiver arrows are one design.
#     (A scan of 293 arrow / quiver NIFs in the installed modlists found ArrowN only ever as a BSTriShape.)
#   * the BOW is fitted to vanilla's rig: the string's ends are moved onto vanilla's two string bones' pivots (the bow
#     draw animation turns each half of the string about them) - the bow is scaled along its length to put the tips at
#     the pivots' height, and the limbs bend back (0 at the grip, growing to the tip) to put them at the pivots' depth.
#     Then every shape takes vanilla's bone weights by nearest-face transfer: the string from vanilla's string only
#     (Bow_StringBone1/2), everything else from vanilla's limbs and grip only.
#   * every face is turned OUTWARD (the game draws one side of a triangle): per shape, each island gets one winding,
#     then a ray vote decides which side is outside (orient_outward, as Truly Nordic's game build).
#   * edge blood for the mace and warhammer heads: our head faces pushed 0.012 out, planar UVs over vanilla's blood UVs.
# Run (by tools/build-missing-weapons.py):
#   blender --background --factory-startup --python-exit-code 1 --python build_stage.py -- ext=5.0 art chamfer=0.8
import bpy, bmesh, sys, os, json, math, random
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import niflib
OUTD = os.path.join(os.environ["NEAW_WORK"], "shapes"); os.makedirs(OUTD, exist_ok=True)
REP = {"notes": []}

def run_design(fn, strip_exec):
    src = open(os.path.join(HERE, fn), encoding="utf-8").read()
    if strip_exec:
        lines = [l for l in src.splitlines() if not (l.startswith("exec(compile(") and "build_designs.py" in l)]
        assert len(lines) == len(src.splitlines()) - 1, fn + ": expected exactly one exec of build_designs.py"
        src = "\n".join(lines)
    exec(compile(src, fn, "exec"), NS)

NS = {"__name__": "__main__", "__file__": os.path.join(HERE, "build_designs.py")}
run_design("build_designs.py", False)
P, GROUPS, dup, add, xform, T, S, R = (NS[k] for k in ("P", "GROUPS", "dup", "add", "xform", "T", "S", "R"))

def obb(o):
    P_ = [o.matrix_world @ v.co for v in o.data.vertices]
    lo = Vector([min(p[i] for p in P_) for i in range(3)]); hi = Vector([max(p[i] for p in P_) for i in range(3)]); return lo, hi

# ---------------------------------------------------------------- the arrow's shaft on axe1hebony (see the header)
sh = bpy.data.objects["arrow_shaft"]; lo, hi = obb(sh)
rad = max(hi.x - lo.x, hi.z - lo.z) / 2; cx, cz = (lo.x + hi.x) / 2, (lo.z + hi.z) / 2
g = P["waraxe_25"]; glo, ghi = obb(g); gc = (glo + ghi) / 2; glen = ghi.y - glo.y; grad = max(ghi.x - glo.x, ghi.z - glo.z) / 2
NSEG = 4; seg = (hi.y - lo.y) / NSEG
new = []
for k in range(NSEG):
    s = dup(g, "arrow_shaftseg%d" % k)
    xform(s, T(cx, lo.y + (k + 0.5) * seg, cz) @ S(rad / grad, seg / glen, rad / grad) @ T(-gc.x, -gc.y, -gc.z))
    new.append(s)
GROUPS["arrow"] = [o for o in GROUPS["arrow"] if o is not sh] + new
for s in new: s["item"] = "arrow"; s["tex"] = g["tex"]
bpy.data.objects.remove(sh)
REP["arrow_shaft"] = {"length": round(hi.y - lo.y, 3), "radius": round(rad, 4), "segments": NSEG,
                      "source": "waraxe_25 (the war axe's wrapped grip, axe1hebony)", "y": [round(lo.y, 2), round(hi.y, 2)]}

def harden(o, deg=35.0):
    """Hard edges the game can see: PyNifly exports ONE normal per vertex, averaged over every face sharing it, so a flat-
    shaded face in Blender still draws smooth in game unless its vertices are its own. Split every edge sharper than deg
    (the warhammer's pyramid teeth drew as a flat disc, 1.1.0 2026-11-14 - all their normals averaged to the face normal)."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    sharp = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > math.radians(deg)]
    bmesh.ops.split_edges(bm, edges=sharp)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")   # loose points export with UV 0,0
    for f in bm.faces: f.smooth = True
    bm.to_mesh(o.data); bm.free(); o.data.update()
    return len(sharp)

# ---------------------------------------------------------------- the arrow's NOCK (owner 2026-11-14 06:48)
# The paw pommel (waraxe_26 x0.3) read as a pommel, with nothing for the string. It becomes a real nock: a short black-
# steel cylinder over the shaft's end with a SLOT across its end for the bowstring, and the war axe's gold collar
# (waraxe_24, the piece round the quiver mouth) as a band where it meets the shaft. The slot runs along x: the string lies
# across the arrow at right angles to the cock vane (vane 0 stands at +z, the other two at +-120 deg), as on a real
# three-vane arrow. The three vanes move back until their rear ends meet the nock.
old = bpy.data.objects["arrow_nock"]; nlo, nhi = obb(old)
YEND = nlo.y                                         # the arrow's rear end (vanilla's nock end, ~ -61.5)
RN = rad * 1.35; DN = 2 * rad                       # nock radius over the shaft; the shaft's diameter
NL, SD, SW = 3.0 * DN, 1.3 * DN, 0.55 * DN           # nock length, slot depth, slot width
NU0, NV0, NUW = 1656 / 2048, 1 - 360 / 2048, 32 / 2048   # plain black steel on axe1hebony (a knotwork panel's field: atlas
                                                         # px 1656-1688 x 328-360; normal map flat, std < 1 of 255)
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=24, radius1=RN, radius2=RN, depth=NL)
bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(-90), 3, "X"))   # cone axis z -> y
bmesh.ops.translate(bm, verts=bm.verts, vec=(cx, YEND + NL / 2, cz))
me = bpy.data.meshes.new("arrow_nock_new"); bm.to_mesh(me); bm.free()
nock = bpy.data.objects.new("arrow_nocknew", me); bpy.context.scene.collection.objects.link(nock)
cut = bpy.data.objects.new("nock_slot", bpy.data.meshes.new("nock_slot")); bpy.context.scene.collection.objects.link(cut)
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
bmesh.ops.scale(bm, verts=bm.verts, vec=(4 * RN, 2 * SD, SW))                 # across x, SD deep from the end, SW wide in z
bmesh.ops.translate(bm, verts=bm.verts, vec=(cx, YEND, cz)); bm.to_mesh(cut.data); bm.free()
bo = nock.modifiers.new("slot", "BOOLEAN"); bo.operation = "DIFFERENCE"; bo.solver = "EXACT"; bo.object = cut
dg = bpy.context.evaluated_depsgraph_get(); me2 = bpy.data.meshes.new_from_object(nock.evaluated_get(dg))
nock.modifiers.clear(); nock.data = me2; bpy.data.objects.remove(cut)
bm = bmesh.new(); bm.from_mesh(nock.data); uvl = bm.loops.layers.uv.new("UVMap"); bm.normal_update()
for f in bm.faces:                                   # box projection into the plain window
    ax = max(range(3), key=lambda i: abs(f.normal[i])); a, b = [i for i in range(3) if i != ax]
    for l in f.loops:
        q = l.vert.co
        o_ = (cx, YEND + NL / 2, cz)                # the nock fits in +-NL/2 of its centre on every axis
        l[uvl].uv = (NU0 + (0.5 + (q[a] - o_[a]) / NL) * NUW, NV0 + (0.5 + (q[b] - o_[b]) / NL) * NUW)
bm.to_mesh(nock.data); bm.free()
nhard = harden(nock)
assert len(nock.data.polygons) > 26, ("the slot boolean failed", len(nock.data.polygons))   # a capped 24-side tube has 26
gap = [v.co for v in nock.data.vertices if v.co.y < YEND + 1e-4]
assert gap and min(abs(p.z - cz) for p in gap) > SW / 2 - 1e-3, "the nock's end is not slotted"
nock["tex"] = "axe1hebony"; nock["item"] = "arrow"; nock["from"] = nock["src"] = "new_nock"
col = dup(P["waraxe_24"], "arrow_nockcollar"); c24 = Vector((0.645, 4.035, -0.035))
RC = RN * 1.12
xform(col, T(cx, YEND + NL, cz) @ S(2 * RC / 3.89, 0.24 * NL / 0.93, 2 * RC / 2.83) @ T(-c24.x, -c24.y, -c24.z))
col["item"] = "arrow"
if col.data.materials: nock.data.materials.append(col.data.materials[0])
vanes = [o for o in GROUPS["arrow"] if o.name.startswith("arrow_vane")]
vrear = min(min((o.matrix_world @ v.co).y for v in o.data.vertices) for o in vanes)
DV = (YEND + NL) - vrear
for o in vanes: xform(o, T(0, DV, 0))
GROUPS["arrow"] = [o for o in GROUPS["arrow"] if o is not old] + [nock, col]
bpy.data.objects.remove(old)
REP["arrow_nock"] = {"end_y": round(YEND, 3), "length": round(NL, 3), "radius": round(RN, 3), "slot_depth": round(SD, 3),
                     "slot_width": round(SW, 3), "slot_runs_along": "x (string across the arrow, square to the cock vane at +z)",
                     "hard_edges_split": nhard, "faces": len(nock.data.polygons), "vanes_moved_back_by": round(-DV, 3),
                     "vane_rear_y": round(vrear + DV, 3), "collar": "waraxe_24 (the war axe's gold collar)"}

# ---------------------------------------------------------------- the quiver (round 2), then the warhammer (round 3)
run_design("build_round2.py", True)
# The quiver turned 180 degrees about its own long axis (owner 2026-11-14 06:48: "the quiver is inside out" - the other
# side shows outward and the steel ring at the mouth faces the wearer's back, still pointing UP). Turned about the
# scabbard body's centre line, so it keeps its place on the back. The six quiver arrows turn with it, so they sit in the
# turned body as they sat in the approved one (left on vanilla's placements, three shafts showed through the body side)
# and still leave by the mouth, which is on the turning axis.
_qd, _e3 = NS["qd"].normalized(), NS["e3"].normalized(); _e2 = _qd.cross(_e3).normalized(); _m = NS["mouth"]
_body = [NS["Q"][i] for i in range(len(NS["Q"])) if NS["Q"][i].name.startswith("q_dagger_")]
_pts = [o.matrix_world @ v.co - _m for o in _body for v in o.data.vertices]
_c = _m + _e2 * ((max(p.dot(_e2) for p in _pts) + min(p.dot(_e2) for p in _pts)) / 2) \
        + _e3 * ((max(p.dot(_e3) for p in _pts) + min(p.dot(_e3) for p in _pts)) / 2)
_turn = Matrix.Translation(_c) @ Matrix.Rotation(math.pi, 4, _qd) @ Matrix.Translation(-_c)
for o in list(NS["Q"]) + list(NS["QA"]): xform(o, _turn)
REP["quiver_turn"] = {"degrees": 180, "about": "the quiver body's long axis", "centre": [round(x, 3) for x in _c],
                      "axis": [round(x, 4) for x in _qd], "body_pieces": len(_body),
                      "quiver_arrow_pieces_turned_with_it": len(NS["QA"])}
QUIVER_BODY, QUIVER_ARROWS, VARROWS = list(NS["Q"]), list(NS["QA"]), list(NS["varrows"])   # v1face reuses the names P / Q
QFRAME = {k: NS[k].copy() for k in ("e3", "mouth", "qd")}
sys.argv += ["ext=5.0", "art", "chamfer=0.8"] if "ext=5.0" not in sys.argv else []
run_design("build_v1face.py", True)
face = json.load(open(os.path.join(NS["OUT3"], "face%s.json" % NS["TAG"])))
want = {"cut_x": -7.25, "teeth": 193, "whole": 137, "walls": 20, "faces": 982}
for k, v in want.items():
    assert abs(face[k] - v) < 1e-6, ("warhammer face differs from the approved round 3", k, face[k], v)
assert NS["TAG"] == "_ext_art_ch", NS["TAG"]
REP["warhammer_face"] = face
# The gnarled face in game (owner 2026-11-14 06:48): a flat tan disc with a diagonal smear, no teeth. Two causes, both
# fixed here on the approved geometry:
#  1. its UVs sat on a window of axe2hebony that is plain in the COLOUR map but not in the NORMAL map - a wavy ridge and
#     a stripe edge run through it (normal map red std 35 of 255), drawn across the whole face as a diagonal smear. The
#     face moves to the battle axe blade's damascus steel, where the normal map is flat (atlas px 1392-1464 x 368-440:
#     red/green std 2-3 of 255, the same in Realistic Armor Overhaul's 4K copy of the atlas).
#  2. PyNifly exports one normal per vertex: the teeth shared their vertices, so every normal averaged to the face
#     normal and the pyramids lit as a flat disc. harden() gives each facet its own vertices.
wf = bpy.data.objects["wh_face"]; OU0, OV0, OUW = face["uv_window"]
FU0, FV0, FUW = 1392 / 2048, 1 - 440 / 2048, 72 / 2048
nre = 0
for d in wf.data.uv_layers.active.data:
    u, v = d.uv
    if OU0 - 1e-4 <= u <= OU0 + OUW + 1e-4 and OV0 - 1e-4 <= v <= OV0 + OUW + 1e-4:
        d.uv = (FU0 + (u - OU0) / OUW * FUW, FV0 + (v - OV0) / OUW * FUW); nre += 1
# the rim walls stand edge-on to the face's planar projection (no UV area, no tangent frame once their vertices are their
# own): project each of them along its own normal instead, into the same window
FR = face["radius"]; nwall = 0
uvd = wf.data.uv_layers.active.data
for p in wf.data.polygons:
    uv = [uvd[li].uv.copy() for li in p.loop_indices]
    if not all(FU0 - 1e-4 <= u <= FU0 + FUW + 1e-4 and FV0 - 1e-4 <= v <= FV0 + FUW + 1e-4 for u, v in uv): continue
    area = abs(sum(uv[i].x * uv[(i + 1) % len(uv)].y - uv[(i + 1) % len(uv)].x * uv[i].y for i in range(len(uv)))) / 2
    if area > 1e-9: continue
    nrm = p.normal; tang = Vector((0, -nrm.z, nrm.y)).normalized()      # round the rim, square to the hammer axis (x)
    for li in p.loop_indices:
        q = wf.data.vertices[wf.data.loops[li].vertex_index].co - Vector((face["cut_x"] - face["ext"], NS["CY"], NS["CZ"]))
        uvd[li].uv = (FU0 + FUW / 2 + q.dot(tang) / (2 * FR) * FUW, FV0 + FUW / 2 + q.x / (2 * FR) * FUW)
    nwall += 1
REP["warhammer_face_fix"] = {"uv_window_was": [OU0, OV0, OUW], "uv_window": [FU0, FV0, FUW], "corners_remapped": nre,
                             "walls_reprojected": nwall, "hard_edges_split": harden(wf)}

# ---------------------------------------------------------------- the parts are the approved design's parts
exp = json.load(open(os.path.join(HERE, "parts_expected.json")))
LOADED = ("waraxe", "battleaxe", "sword", "dagger", "shield")          # the items the three scripts cut parts from
exp = {k: v for k, v in exp.items() if k.rsplit("_", 1)[0] in LOADED}
bad = []
for pid, e in exp.items():
    if pid not in P: bad.append((pid, "missing")); continue
    lo, hi = obb(P[pid])
    if max(abs(lo[i] - e["lo"][i]) for i in range(3)) > 0.011 or max(abs(hi[i] - e["hi"][i]) for i in range(3)) > 0.011 or P[pid]["tex"] != e["tex"]:
        bad.append((pid, [round(x, 2) for x in lo], [round(x, 2) for x in hi], P[pid]["tex"], e))
extra = sorted(set(P) - set(exp))
assert not bad and not extra, ("loose parts differ from the approved design's", bad[:5], extra[:5])
REP["parts_checked"] = len(exp)

ITEMS = {"mace": list(GROUPS["mace"]), "warhammer": list(NS["WH"]), "bow": list(GROUPS["bow"]), "arrow": list(GROUPS["arrow"]),
         "quiver": QUIVER_BODY}
QA = {}
names = [o.name.split(".")[0] for o in VARROWS]
for o in QUIVER_ARROWS:
    k = int(o.name[2:o.name.index("_")]); QA.setdefault(names[k], []).append(o)
assert sorted(QA) == ["Arrow%d" % i for i in range(1, 7)], sorted(QA)
for nm, lst in QA.items():
    assert {o["tex"] for o in lst} == {"axe1hebony"}, (nm, {o["tex"] for o in lst})
for it, lst in ITEMS.items():
    for o in lst:
        assert o.matrix_world == Matrix.Identity(4), (it, o.name)
REP["atlases"] = {it: sorted({o["tex"] for o in lst}) for it, lst in ITEMS.items()}

# the quiver's facing, for the report: its front (+e3, where the fang plate sits) and mouth
REP["quiver_frame"] = {"fang_side_after_turn": [round(-x, 3) for x in QFRAME["e3"]], "mouth": [round(x, 2) for x in QFRAME["mouth"]],
                       "axis_mouth_to_bottom": [round(x, 3) for x in QFRAME["qd"]]}

# ---------------------------------------------------------------- remove every design-only object
keep = set(o for lst in ITEMS.values() for o in lst) | set(o for lst in QA.values() for o in lst)
for o in list(bpy.data.objects):
    if o not in keep: bpy.data.objects.remove(o)

def import_vanilla(name):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.pynifly(filepath=os.path.join(NS["VAN"], name), import_collisions=False)
    return [o for o in bpy.data.objects if o not in before]

def select_only(o):
    for x in bpy.context.scene.objects:      # select_all(DESELECT) leaves hidden objects selected, and a join takes them
        if x.select_get(): x.select_set(False)
    o.hide_set(False); o.hide_viewport = False
    o.select_set(True); bpy.context.view_layer.objects.active = o

def join(objs, name):
    objs = list(objs)
    for o in objs:
        o.data = o.data.copy()
        # ONE UV layer under ONE name on every piece before the join: Blender's join matches UV layers BY NAME, so a piece
        # whose layer has another name (build_v1face.py's new face and extension call theirs "UV", PyNifly's imports
        # "UVMap") lands in a second layer, and the exported first layer holds (0, 0) for all its corners - the warhammer's
        # extension and face drew the atlas's corner texel with no tangent frame: black and flat in game (1.1.0, 2026-11-14)
        uvs = o.data.uv_layers; assert len(uvs) >= 1, (name, o.name, "a piece without UVs")
        keep_uv = uvs.active.name
        for nm in [l.name for l in uvs if l.name != keep_uv]: uvs.remove(uvs[nm])
        uvs[keep_uv].name = "UVMap"
    select_only(objs[0])
    for o in objs[1:]: o.hide_set(False); o.hide_viewport = False; o.select_set(True)
    nsel = sum(1 for x in bpy.context.scene.objects if x.select_get())
    assert nsel == len(objs), (name, 'selected', nsel, 'meant', len(objs))
    if len(objs) > 1: bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active; o.name = name; o.data.name = name
    assert [l.name for l in o.data.uv_layers] == ["UVMap"], (name, "UV layers after the join", [l.name for l in o.data.uv_layers])
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    bm.to_mesh(o.data); bm.free(); o.data.update()
    return o

# ---------------------------------------------------------------- face orientation (Truly Nordic's orient_outward)
def orient_outward(objs, rays=12, samples=300, seed=7):
    rnd = random.Random(seed)
    V, Pl, off = [], [], 0
    for o in objs:
        M = o.matrix_world; V += [M @ v.co for v in o.data.vertices]; Pl += [[off + i for i in p.vertices] for p in o.data.polygons]; off += len(o.data.vertices)
    tree = BVHTree.FromPolygons(V, Pl)
    def cone(n):
        while True:
            d = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1))).normalized()
            if d.dot(n) > 0.5: return d
    rep = {}
    for o in objs:
        me = o.data; before = [tuple(p.normal) for p in me.polygons]
        bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
        # Islands are the surfaces as the game's winding check sees them: faces joined over an edge that exactly two faces
        # share once vertices are WELDED by position (the mesh is split at UV seams). No recalc: Legacy of Ysgramor's
        # pieces are wound consistently, and the design's transforms keep that inside a piece (a mirroring one reverses
        # the whole piece, which the vote then turns back). A recalc on the unwelded mesh flipped scabbard strips whose
        # welded neighbours stayed put (16 edges against a neighbour on the quiver, 2026-11-14).
        key = lambda v: (round(v.co.x, 4), round(v.co.y, 4), round(v.co.z, 4))
        emap = {}
        for f in bm.faces:
            ks = [key(v) for v in f.verts]
            for i in range(len(ks)):
                emap.setdefault(frozenset((ks[i], ks[(i + 1) % len(ks)])), []).append(f.index)
        par = list(range(len(bm.faces)))
        def find(i):
            while par[i] != i: par[i] = par[par[i]]; i = par[i]
            return i
        for fs in emap.values():
            if len(fs) == 2: par[find(fs[0])] = find(fs[1])
        groups = {}
        for f in bm.faces: groups.setdefault(find(f.index), []).append(f)
        islands = list(groups.values())
        # one consistent winding per welded island (a welded recalc): walk the island from its largest face, turning each
        # neighbour so the shared edge is walked in opposite directions - Blender's own recalc cannot see welded edges
        # (the warhammer's skirt at the cut met the paw cap the same way round on all 34 cut edges)
        fk = {f.index: [key(v) for v in f.verts] for f in bm.faces}
        nbr = {}
        for (fs) in emap.values():
            if len(fs) == 2: nbr.setdefault(fs[0], []).append(fs[1]); nbr.setdefault(fs[1], []).append(fs[0])
        def walks(ks, a, b):
            for i in range(len(ks)):
                if ks[i] == a and ks[(i + 1) % len(ks)] == b: return True
            return False
        flipc = set()
        for isl in islands:
            seed = max(isl, key=lambda f: f.calc_area()).index; state = {seed: False}; stack = [seed]
            while stack:
                i = stack.pop()
                for j in nbr.get(i, []):
                    shared = set(fk[i]) & set(fk[j])
                    if len(shared) != 2: continue
                    a, b = tuple(shared)
                    same = walks(fk[i], a, b) == walks(fk[j], a, b)          # both walk a->b: against each other
                    want = state[i] ^ same
                    if j not in state: state[j] = want; stack.append(j)
            flipc |= {i for i, s in state.items() if s}
        if flipc:
            bm.faces.ensure_lookup_table(); bmesh.ops.reverse_faces(bm, faces=[bm.faces[i] for i in flipc])
        bm.normal_update()
        nflip = 0
        for isl in islands:
            pick = isl if len(isl) <= samples else rnd.sample(isl, samples)
            sc = [0.0, 0.0]
            for f in pick:
                c = f.calc_center_median(); n = f.normal; a = f.calc_area()
                if n.length < 0.5 or a <= 0: continue
                for k, s in enumerate((1.0, -1.0)):
                    esc = 0
                    for _ in range(rays):
                        if tree.ray_cast(c + n * s * 1e-3, cone(n * s), 1000.0)[0] is None: esc += 1
                    sc[k] += a * esc / rays
            if sc[1] > sc[0]:
                nflip += 1; bmesh.ops.reverse_faces(bm, faces=isl)
        bm.normal_update(); bm.faces.ensure_lookup_table(); after = [tuple(f.normal) for f in bm.faces]
        bm.to_mesh(me); me.update()
        changed = sum(1 for a, b in zip(before, after) if a[0] * b[0] + a[1] * b[1] + a[2] * b[2] < 0)
        bm.free()
        rep[o.name] = {"islands": len(islands), "faces": len(before), "faces_reversed_vs_design": changed, "islands_flipped_by_vote": nflip}
        print("ORIENT", o.name, json.dumps(rep[o.name]))
    return rep

def dump_points(objs, name):
    """Vertex positions (NIF units, the frame the shapes are exported in) for assemble.py's collision fits."""
    import numpy as np
    np.save(os.path.join(OUTD, "points_%s.npy" % name), np.array([tuple(o.matrix_world @ v.co) for o in objs for v in o.data.vertices], np.float64))

def export_single(o, path):
    select_only(o)
    r = bpy.ops.export_scene.pynifly(filepath=path, target_game="SKYRIMSE", export_colors=False, blender_xf=False, intuit_defaults=False)
    print("EXPORT", path, r)

def shapes_by_atlas(item, objs):
    groups = {}
    for o in objs: groups.setdefault(o["tex"], []).append(o)      # grouped first: a join removes the objects it merges
    out = {}
    for tex in sorted(groups):
        out[tex] = join(groups[tex], "%s_%s" % (item, tex))
    return out

# ---------------------------------------------------------------- blood (TN's make_blood)
def blood_uv_box(van_objs):
    us, vs = [], []
    for o in van_objs:
        if "blood" not in o.name.lower() or o.type != "MESH": continue
        for d in o.data.uv_layers.active.data: us.append(d.uv[0]); vs.append(d.uv[1])
    return (min(us), min(vs)), (max(us), max(vs))

def make_blood(srcs, ylo, name, uvbox, offset=0.012, cap=900):
    parts = []
    for s in srcs:
        b = s.copy(); b.data = s.data.copy(); bpy.context.scene.collection.objects.link(b); parts.append(b)
    b = join(parts, name); me = b.data
    bm = bmesh.new(); bm.from_mesh(me)
    kill = [f for f in bm.faces if not all(v.co.y >= ylo for v in f.verts)]
    bmesh.ops.delete(bm, geom=kill, context="FACES"); bm.to_mesh(me); bm.free()
    n = len(me.polygons)
    if n > cap:
        select_only(b); m = b.modifiers.new("dec", "DECIMATE"); m.decimate_type = "COLLAPSE"; m.ratio = cap / n
        bpy.ops.object.modifier_apply(modifier=m.name)
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3]); bm.normal_update()
    for v in bm.verts: v.co += v.normal * offset
    lo = Vector([min(v.co[i] for v in bm.verts) for i in range(3)]); hi = Vector([max(v.co[i] for v in bm.verts) for i in range(3)])
    uvl = bm.loops.layers.uv.active; (u0, v0), (u1, v1) = uvbox
    for f in bm.faces:
        for l in f.loops:
            l[uvl].uv = (u0 + (u1 - u0) * (l.vert.co.y - lo.y) / (hi.y - lo.y), v0 + (v1 - v0) * (l.vert.co.x - lo.x) / (hi.x - lo.x))
    bm.to_mesh(me); bm.free(); me.update()
    return b

# ---------------------------------------------------------------- static items
HEAD_Y = {"mace": 26.0, "warhammer": 38.0}     # where the head starts (blood region, collision split) - from the designs
REP["head_split_y"] = HEAD_Y
for item in ("mace", "warhammer"):
    sh_ = shapes_by_atlas(item, ITEMS[item])
    REP.setdefault("orient", {}).update(orient_outward(list(sh_.values())))
    for tex, o in sh_.items(): export_single(o, os.path.join(OUTD, "%s_%s.nif" % (item, tex)))
    dump_points(list(sh_.values()), item)
    van = import_vanilla("ebony%s.nif" % item); uvb = blood_uv_box(van)
    for o in van: bpy.data.objects.remove(o)
    b = make_blood(list(sh_.values()), HEAD_Y[item], "%s_blood" % item, uvb)
    export_single(b, os.path.join(OUTD, "%s_blood.nif" % item))
    REP.setdefault("blood", {})[item] = {"faces": len(b.data.polygons), "uv_box": [list(uvb[0]), list(uvb[1])]}
    bpy.data.objects.remove(b)

# ---------------------------------------------------------------- arrow (loose / flight) and the quiver
qn = niflib.Nif(os.path.join(NS["VAN"], "ebonyarrow.nif"))
aq = [b for b in range(len(qn.blocks)) if qn.btypes[b] == "NiNode" and qn.name(b) == "ArrowQuiver"][0]
_, qt, qr, qs = qn.transform(aq)
assert max(abs(qr[i] - (1, 0, 0, 0, 1, 0, 0, 0, 1)[i]) for i in range(9)) < 1e-5 and abs(qs - 1) < 1e-6, ("ArrowQuiver is turned or scaled", qr, qs)
REP["arrowquiver_node_translation"] = list(qt)
arrow = shapes_by_atlas("arrow", ITEMS["arrow"]); assert list(arrow) == ["axe1hebony"], list(arrow)
quiver = shapes_by_atlas("quiver", ITEMS["quiver"])
qarrows = {nm: join(lst, nm) for nm, lst in sorted(QA.items())}
# every quiver-arrow point deeper than 1 unit past the mouth must be INSIDE the quiver: rays across the quiver axis in
# 12 directions all meet the quiver's walls (a shaft showing through the body side lets one escape)
def outside_points(arrows, body):
    V, Pl, off = [], [], 0
    for o in body:
        V += [o.matrix_world @ v.co for v in o.data.vertices]; Pl += [[off + i for i in p.vertices] for p in o.data.polygons]; off += len(o.data.vertices)
    tree = BVHTree.FromPolygons(V, Pl); qd, m = QFRAME["qd"].normalized(), QFRAME["mouth"]
    a = qd.orthogonal().normalized(); b_ = qd.cross(a).normalized()
    dirs = [a * math.cos(2 * math.pi * k / 12) + b_ * math.sin(2 * math.pi * k / 12) for k in range(12)]
    out = {}
    for o in arrows:
        n = 0
        for v in o.data.vertices:
            p = o.matrix_world @ v.co
            if (p - m).dot(qd) < 1.0: continue
            if any(tree.ray_cast(p, d, 100.0)[0] is None for d in dirs): n += 1
        out[o.name] = n
    return out
REP["quiver_arrows_outside_body"] = outside_points(list(qarrows.values()), list(quiver.values()))
print("QUIVER ARROWS OUTSIDE", REP["quiver_arrows_outside_body"])   # measured, reported; not yet a gate (see the 1.1.0 changelog)
REP["orient"].update(orient_outward([arrow["axe1hebony"]]))
REP["orient"].update(orient_outward(list(quiver.values()) + list(qarrows.values())))
export_single(arrow["axe1hebony"], os.path.join(OUTD, "arrow.nif")); dump_points([arrow["axe1hebony"]], "arrow")
for o in list(quiver.values()) + list(qarrows.values()):     # into the ArrowQuiver node's frame (identity shape transforms)
    o.data.transform(Matrix.Translation((-qt[0], -qt[1], -qt[2]))); o.data.update()
dump_points(list(quiver.values()), "quiver")
for tex, o in quiver.items(): export_single(o, os.path.join(OUTD, "quiver_%s.nif" % tex))
for nm, o in qarrows.items(): export_single(o, os.path.join(OUTD, "quiver_%s.nif" % nm))

# ---------------------------------------------------------------- the bow: fit to vanilla's rig, skin, export
bow = ITEMS["bow"]
van = import_vanilla("ebonybowskinned.nif")
arm = [o for o in van if o.type == "ARMATURE"][0]; vm = [o for o in van if o.type == "MESH"][0]
heads = {b.name: arm.matrix_world @ b.head_local for b in arm.data.bones}
p1, p2 = heads["Bow_StringBone1"], heads["Bow_StringBone2"]      # lower (-y) and upper (+y) string pivots
string = [o for o in bow if o.name.startswith("bow_string")]; assert len(string) == 1, [o.name for o in string]
# the string is the war axe's grip stretched tip to tip, with vertices only near its ends: cut it into short lengths, so
# each half can bend about its own pivot when the bow is drawn (vanilla's string: 118 vertices along its length)
bm = bmesh.new(); bm.from_mesh(string[0].data)
for _ in range(12):
    long_ = [e for e in bm.edges if abs(e.verts[0].co.y - e.verts[1].co.y) > 1.5]
    if not long_: break
    bmesh.ops.subdivide_edges(bm, edges=long_, cuts=1, use_grid_fill=True)
bm.to_mesh(string[0].data); bm.free(); string[0].data.update()
REP["bow_string_vertices"] = len(string[0].data.vertices)
sv = [v.co for v in string[0].data.vertices]
ymin, ymax = min(v.y for v in sv), max(v.y for v in sv); xs = sum(v.x for v in sv) / len(sv)
kyn, kyp = p1.y / ymin, p2.y / ymax; dx = (p1.x + p2.x) / 2 - xs
tip = max(abs(ymin), abs(ymax)); G = 7.0
for o in bow:
    is_str = o in string
    for v in o.data.vertices:
        y = v.co.y
        s = 1.0 if is_str else min(1.0, max(0.0, (abs(y) - G) / (tip - G))) ** 2
        v.co.x += dx * s; v.co.y = y * (kyp if y > 0 else kyn)
    o.data.update()
REP["bow_fit"] = {"string_ends_before": [round(ymin, 2), round(ymax, 2)], "string_x_before": round(xs, 3),
                  "pivots": [[round(c, 2) for c in p1], [round(c, 2) for c in p2]], "length_scale": [round(kyn, 4), round(kyp, 4)],
                  "tip_shift_x": round(dx, 3)}

def split_vanilla(keep_string):
    c = vm.copy(); c.data = vm.data.copy(); bpy.context.scene.collection.objects.link(c)
    names = {g.index: g.name for g in c.vertex_groups}
    bm = bmesh.new(); bm.from_mesh(c.data); dl = bm.verts.layers.deform.active; kill = []
    for v in bm.verts:
        w = [(wt, names[gi]) for gi, wt in v[dl].items() if names[gi].startswith("Bow_")]
        is_s = bool(w) and "String" in max(w)[1]
        if is_s != keep_string: kill.append(v)
    bmesh.ops.delete(bm, geom=kill, context="VERTS"); bm.to_mesh(c.data); bm.free(); c.data.update()
    return c
v_str, v_limb = split_vanilla(True), split_vanilla(False)
REP["bow_vanilla_split_verts"] = {"string": len(v_str.data.vertices), "limbs": len(v_limb.data.vertices)}
for o in bow:
    srcm = v_str if o in string else v_limb
    for g_ in vm.vertex_groups:
        if g_.name not in o.vertex_groups: o.vertex_groups.new(name=g_.name)
    select_only(o); m = o.modifiers.new("dt", "DATA_TRANSFER"); m.object = srcm; m.use_vert_data = True
    m.data_types_verts = {"VGROUP_WEIGHTS"}; m.vert_mapping = "POLYINTERP_NEAREST"
    m.layers_vgroup_select_src = "ALL"; m.layers_vgroup_select_dst = "NAME"
    bpy.ops.object.modifier_apply(modifier=m.name)
bshapes = shapes_by_atlas("bow", bow)
REP["orient"].update(orient_outward(list(bshapes.values())))
dom = {}
for tex, o in bshapes.items():
    d = {}
    for v in o.data.vertices:
        w = [(g.weight, o.vertex_groups[g.group].name) for g in v.groups if o.vertex_groups[g.group].name.startswith("Bow_")]
        assert w, (tex, "a vertex without a bow bone weight", tuple(v.co))
        d[max(w)[1]] = d.get(max(w)[1], 0) + 1
    dom[tex] = d
REP["bow_dominant_bone_counts"] = dom
for o in (v_str, v_limb, vm): bpy.data.objects.remove(o)
dump_points(list(bshapes.values()), "bow")
for o in bshapes.values():
    o.parent = arm; am = o.modifiers.new("arm", "ARMATURE"); am.object = arm
select_only(arm)
for o in bshapes.values(): o.select_set(True)
arm.select_set(True); bpy.context.view_layer.objects.active = list(bshapes.values())[0]
r = bpy.ops.export_scene.pynifly(filepath=os.path.join(OUTD, "bow_skinned.nif"), target_game="SKYRIMSE", export_colors=False, blender_xf=False, intuit_defaults=False)
print("EXPORT skinned", r)
json.dump(REP, open(os.path.join(os.environ["NEAW_WORK"], "stage_report.json"), "w"), indent=1, default=str)
print("STAGE DONE")
