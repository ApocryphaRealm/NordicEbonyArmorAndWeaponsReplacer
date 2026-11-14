# Round 2 (owner review 2026-11-14 00:14): (1) the warhammer's hammer head made uniform - a cylinder body with a FLAT or a
# gently DOMED striking face - and (2) the Wolf ebony QUIVER with its six quiver arrows on vanilla ebonyarrow.nif's layout.
# Still only Wolf-set pieces on their own atlases. Builds on build_designs.py (run inside it, without its renders).
# Run: blender --background --factory-startup --python-exit-code 1 --python build_round2.py
import bpy, bmesh, sys, os, math, json
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv = [a for a in sys.argv if a != "render"]
exec(compile(open(os.path.join(HERE, "build_designs.py"), encoding="utf-8").read(), "build_designs", "exec"))
import wolf_lib
OUT2 = os.path.join(WORK, "round2"); os.makedirs(OUT2, exist_ok=True)
P.update(load_parts("ebonydagger")); P.update(load_parts("ebonyshield"))

# ------------------------------------------------------------------ (1) warhammer heads
base = [o for o in GROUPS["warhammer"] if o.name not in ("wh_hammer", "wh_hammerring")]
HY, HZ = 43.5, 1.1                       # hammer axis height and depth (the battle axe head's own plane)
X0, LEN = -1.5, 10.8                     # body from the socket face out to x = X0 - LEN
def head(tag, depth):
    objs = []
    b = dup(P["battleaxe_21"], "wh%s_body" % tag); c = Vector((0.36, 7.42, 0.635))
    xform(b, T(X0, HY, HZ) @ R(90, "Z") @ S(2.15, 1.0, 2.15) @ T(-c.x, -c.y, -c.z)); objs.append(b)
    note("warhammer_" + tag, "battleaxe_21", "the battle axe's gold-twist langet tube, x2.15 round, laid across as the hammer body")
    for name, xc in (("face", X0 - LEN), ("back", X0 - 0.3)):
        r = dup(P["battleaxe_22"], "wh%s_ring_%s" % (tag, name)); c = Vector((0.16, 6.95, 0.44))
        xform(r, T(xc, HY, HZ) @ R(90, "Z") @ S(2.3, 1.3, 2.3) @ T(-c.x, -c.y, -c.z)); objs.append(r)
    note("warhammer_" + tag, "battleaxe_22", "the battle axe's gold ring, x2.3, as the band at the face edge and at the socket")
    w = dup(P["battleaxe_20"], "wh%s_washer" % tag); c = Vector((0.385, 18.72, 0.685))
    xform(w, T(X0 + 0.1, HY, HZ) @ R(90, "Z") @ S(1.3, 1.0, 1.3) @ T(-c.x, -c.y, -c.z)); objs.append(w)
    note("warhammer_" + tag, "battleaxe_20", "the battle axe's socket disk, x1.3, closing the body against the socket")
    f = dup(P["shield_35"], "wh%s_face" % tag); c = Vector((0.49, -0.285, -3.08))
    xform(f, T(X0 - LEN - 0.2, HY, HZ) @ R(90, "Y") @ S(0.74, 0.74, depth) @ T(-c.x, -c.y, -c.z)); objs.append(f)
    note("warhammer_" + tag, "shield_35", "the shield's centre boss, x0.74 across and x%.2f deep, as the striking face" % depth)
    for o in objs: o["item"] = "warhammer_" + tag
    return base + objs
WH = {"flat": head("flat", 0.10), "domed": head("domed", 0.65)}

# ------------------------------------------------------------------ (2) quiver
van = import_nif(os.path.join(VAN, "ebonyarrow.nif"), True)
vq = [o for o in van if o.name.startswith("ArrowQuiver")][0]
varrows = sorted([o for o in van if o.name[:5] == "Arrow" and o.name[5:6].isdigit()], key=lambda o: o.name)
vfull = [o for o in van if o.name.startswith("Arrow:0")][0]

def pca(pts):
    c = sum(pts, Vector()) / len(pts)
    C = [[sum((p[i] - c[i]) * (p[j] - c[j]) for p in pts) / len(pts) for j in range(3)] for i in range(3)]
    v = Vector((0.3, 1.0, 0.1)).normalized()            # power iteration for the main axis
    for _ in range(60): v = Vector([sum(C[i][j] * v[j] for j in range(3)) for i in range(3)]).normalized()
    return c, v
qp = [vq.matrix_world @ v.co for v in vq.data.vertices]
qc, _ = pca(qp)
qd = Vector()
for o in varrows:                                   # the quiver axis = the six quiver arrows' mean direction
    _, d = pca([o.matrix_world @ v.co for v in o.data.vertices]); qd += d if d.y > 0 else -d
qd.normalize()
ap = sum([[o.matrix_world @ v.co for v in o.data.vertices] for o in varrows], [])
ac = sum(ap, Vector()) / len(ap)
if (ac - qc).dot(qd) > 0: qd = -qd                 # qd points from the mouth (where the arrows come out) to the bottom
proj = [(p - qc).dot(qd) for p in qp]; qlen = max(proj) - min(proj)
axis0 = ac - qd * (ac - qc).dot(qd)                # the quiver axis runs through the arrows' centre, so they leave by the mouth
mouth = axis0 + qd * ((qc - axis0).dot(qd) + min(proj)); bottom = axis0 + qd * ((qc - axis0).dot(qd) + max(proj))
# the quiver's flat side: the axis of least spread across qd
side = [(p - qc) - qd * (p - qc).dot(qd) for p in qp]
_, e2 = pca([qc + s for s in side])
e3 = e2.cross(qd).normalized(); e2 = qd.cross(e3).normalized()
w2 = max(s.dot(e2) for s in side) - min(s.dot(e2) for s in side); w3 = max(s.dot(e3) for s in side) - min(s.dot(e3) for s in side)
print("VQUIVER len %.1f width %.1f thick %.1f mouth %s bottom %s" % (qlen, w2, w3, tuple(round(x, 1) for x in mouth), tuple(round(x, 1) for x in bottom)))

# build in the dagger scabbard's own frame (mouth y 4.7 -> chape tip y 34.3, front face +z), then scale + align to vanilla
Q = []
for i in range(7, 42):
    pid = "dagger_%02d" % i; Q.append(dup(P[pid], "q_" + pid))
note("quiver", "dagger_07..41", "the dagger's whole scabbard (leather body, knotwork chape, two strap bands, ring locket) scaled up as the quiver body")
col = dup(P["waraxe_24"], "q_collar"); c = Vector((0.645, 3.57, -0.035))
xform(col, T(0, 4.55, 0) @ S(1.28, 0.9, 1.45) @ T(-c.x, -c.y, -c.z)); Q.append(col)
note("quiver", "waraxe_24", "the war axe's gold collar, fitted oval, round the quiver mouth")
for pid in ("waraxe_04", "waraxe_06", "waraxe_08", "waraxe_09", "waraxe_10"):
    f = dup(P[pid], "q_fang_" + pid)
    if pid in ("waraxe_04", "waraxe_06"): keep_faces(f, lambda c: c.x > 2.0)
    for v in f.data.vertices:
        x, y, z = v.co
        v.co = Vector(((y - 35.3) * 0.36, 20.8 + (x - 2.0) * 0.52, 1.62 + (z + 0.6) * 0.35))
    f.data.update(); Q.append(f)
note("quiver", "waraxe fang", "the war axe's back fang, x0.52, laid on the front of the quiver between the lower strap and the chape, hook toward the chape")
sy = qlen / (34.3 - 4.7); sx = min(max(w2 / 5.6, 1.6), 3.0); sz = min(max(w3 / 3.4, 1.6), 2.8)   # capped so the knotwork chape is not smeared
print("QUIVER scale", round(sx, 2), round(sy, 2), round(sz, 2))
Mbasis = Matrix((e2, qd, e3)).transposed().to_4x4()      # local x -> e2, y -> qd, z -> e3
MQ = T(*mouth) @ Mbasis @ S(sx, sy, sz) @ T(0, -4.7, 0)
for o in Q: xform(o, MQ); o["item"] = "quiver"

# six quiver arrows: our arrow's nock half, laid on each vanilla ArrowN (nock = its end farthest out of the mouth)
arrow = GROUPS["arrow"]
QA = []
for k, va in enumerate(varrows):
    pts = [va.matrix_world @ v.co for v in va.data.vertices]; c, d = pca(pts)
    pr = [(p - c).dot(d) for p in pts]; e_a = c + d * min(pr); e_b = c + d * max(pr)
    nock, inner = (e_a, e_b) if (e_a - mouth).dot(-qd) > (e_b - mouth).dot(-qd) else (e_b, e_a)
    L = (inner - nock).length; dirv = (inner - nock).normalized()
    rot = Vector((0, 1, 0)).rotation_difference(dirv).to_matrix().to_4x4()
    for o in arrow:
        n = dup(o, "qa%d_%s" % (k, o.name)); keep_faces(n, lambda cc: cc.y < -61.5 + L)
        if not n.data.polygons: bpy.data.objects.remove(n); continue
        xform(n, T(*nock) @ rot @ R(40 * k, "Y") @ T(0, 61.5, 0)); n["item"] = "quiver"; QA.append(n)
note("quiver", "arrow", "six of the new arrows (nock half, vanes and paw nock) on vanilla's six quiver-arrow placements")
QUIVER = Q + QA
VQ = [vq] + varrows
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT2, "round2.blend"))
json.dump([x for x in LOG if x["how"]], open(os.path.join(OUT2, "provenance2.json"), "w"), indent=1)

# ------------------------------------------------------------------ renders
wolf_lib.FIXED[0] = None
def shots(objs, pref, views):
    for (name, yaw, pitch, yr, W, H) in views:
        frame(sc, co, objs, os.path.join(OUT2, "%s_%s.png" % (pref, name)), math.radians(yaw), math.radians(pitch), W=W, H=H, yr=yr)
for tag, objs in WH.items():
    shots(objs, "wh_" + tag, [("front", 0, 0, None, 700, 1400), ("tq", 35, 18, None, 700, 1400), ("close", 30, 20, (34, 59), 900, 900), ("closeface", -58, 8, (36, 51), 900, 900), ("prof", 0, 0, (37, 50), 900, 900)])
# the quiver: orient views on its own frame - front looks at its front face (+e3), back from behind
def yaw_pitch(v): return math.degrees(math.atan2(v.x, v.z)), math.degrees(math.asin(max(-1, min(1, v.y))))
fy, fp = yaw_pitch(e3); by, bp = yaw_pitch(-e3)
for objs, pref in ((QUIVER, "quiver"), (VQ, "vquiver")):
    shots(objs, pref, [("front", fy, fp, None, 1000, 1200), ("back", by, bp, None, 1000, 1200), ("tq", fy + 35, fp + 15, None, 1000, 1200)])
    # close-up on the mouth end
    ys = sorted(p.y for p in world_pts(objs)); mid = (ys[0] + ys[-1]) / 2
    shots(objs, pref, [("close", fy + 25, fp + 15, (mouth.y - 14, mouth.y + 14) if mouth.y < mid else (mouth.y - 14, mouth.y + 14), 900, 900)])
