# Round 3 (owner 2026-11-14 00:36): the V1 warhammer kept as it was (battle axe minus its bit, the paw butt-cap turned
# forward as the hammer, the gold ring) - ONLY the striking end changes: the paw cap's rounded front is cut off flat at
# its widest section and a FLAT CIRCULAR face is built from scratch on our end, gnarled edge to edge with a grid of square
# pyramid teeth (the meat-tenderiser face of our Truly Nordic warhammer: 45-degree facets, every pyramid clipped to the
# outline, a wall closing each clipped edge) - here clipped to a circle. The face takes plain damascus steel of the battle
# axe's own atlas (axe2hebony), no Truly Nordic texture.
# Run: blender --background --factory-startup --python-exit-code 1 --python build_v1face.py
import bpy, bmesh, sys, os, math, json
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
ST = float(next((x.split("=")[1] for x in sys.argv if x.startswith("stretch=")), "1"))   # 1 = cut as is; >1 = the cut head lengthened along its axis
EXT = float(next((x.split("=")[1] for x in sys.argv if x.startswith("ext=")), "0"))   # >0 = a plain round steel extension of this length before the face (owner 01:09)
CH = float(next((x.split("=")[1] for x in sys.argv if x.startswith("chamfer=")), "0"))   # owner 01:30: the gold lip tapered in at 45 degrees
ART = "art" in sys.argv                     # owner 01:17: the extension carries the paw cap band, not bare steel
TAG = ("" if ST == 1 else "_long") + ("_ext" if EXT else "") + ("_art" if ART else "") + ("_ch" if CH else "")
sys.argv = [a for a in sys.argv if a != "render"]
exec(compile(open(os.path.join(HERE, "build_designs.py"), encoding="utf-8").read(), "build_designs", "exec"))
import wolf_lib
OUT3 = os.path.join(WORK, "round3"); os.makedirs(OUT3, exist_ok=True)
PITCH, HT, NSEG = 0.62, 0.31, 96            # TN face: pitch 0.54-0.58, height 0.28, 44-46 deg facets; ours a touch coarser for a 2x wider face
U0, V0, UW = 0.703, 0.1406, 0.047           # plain black steel window on axe2hebony (atlas px 1440-1536 x 1664-1760: the haft end strip between its rivets; lowest variance on the atlas)

ham = bpy.data.objects["wh_hammer"]; CY, CZ = 43.5, 1.1
vs = [ham.matrix_world @ v.co for v in ham.data.vertices]
xs = [p.x for p in vs]; xmin, xmax = min(xs), max(xs)
# radial profile along the hammer axis; cut where the front half is widest
bins = {}
for p in vs:
    k = round(p.x * 4) / 4; r = math.hypot(p.y - CY, p.z - CZ); bins[k] = max(bins.get(k, 0), r)
front = {k: r for k, r in bins.items() if k < (xmin + xmax) / 2}
XC = max(front, key=lambda k: front[k]); print("PROFILE", sorted((k, round(r, 2)) for k, r in bins.items()), "CUT", XC)
bm = bmesh.new(); bm.from_mesh(ham.data)
bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(XC, 0, 0), plane_no=(-1, 0, 0), clear_outer=True)
bm.to_mesh(ham.data); bm.free()
if ST != 1:                                # lengthen the cut head about its socket end (x = -1.1), then re-place the cut plane
    for v in ham.data.vertices: v.co.x = -1.1 + (v.co.x + 1.1) * ST
    ham.data.update(); XC = -1.1 + (XC + 1.1) * ST
bnd = []
bm = bmesh.new(); bm.from_mesh(ham.data)
for e in bm.edges:
    if len(e.link_faces) == 1 and all(abs(v.co.x - XC) < 1e-3 for v in e.verts): bnd.append((e.verts[0].co.copy(), e.verts[1].co.copy()))
bm.free()
R = max(math.hypot(p.y - CY, p.z - CZ) for e in bnd for p in e); print("FACE radius", round(R, 3), "boundary edges", len(bnd))

# ---- the new face, built from scratch
fb = bmesh.new(); uvl = fb.loops.layers.uv.new("UV")
def uv_of(p): return (U0 + (p.y - CY + R) / (2 * R) * UW, V0 + (p.z - CZ + R) / (2 * R) * UW)
def poly(pts, outward):
    vv = [fb.verts.new(p) for p in pts]
    f = fb.faces.new(vv)
    f.normal_update()
    if f.normal.dot(outward) < 0: f.normal_flip()
    f.smooth = False
    for l in f.loops: l[uvl].uv = uv_of(l.vert.co)
    return f
RF = R - CH                                # the tooth face, inside the chamfered lip
circle = [(RF * math.cos(2 * math.pi * i / NSEG), RF * math.sin(2 * math.pi * i / NSEG)) for i in range(NSEG)]
def clip(poly2):                       # Sutherland-Hodgman against the (convex, CCW) circle polygon; points (u, v, h)
    out = poly2
    for i in range(NSEG):
        a, b = circle[i], circle[(i + 1) % NSEG]; inp = out; out = []
        if not inp: break
        def side(p): return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
        for j in range(len(inp)):
            P, Q = inp[j], inp[(j + 1) % len(inp)]; sp, sq = side(P), side(Q)
            if sp >= 0: out.append(P)
            if (sp >= 0) != (sq >= 0):
                t = sp / (sp - sq); out.append(tuple(P[k] + (Q[k] - P[k]) * t for k in range(3)))
    return out
XF = XC - EXT                              # the gnarled face sits at the end of the extension
def W(u, v, h): return Vector((XF - h, CY + u, CZ + v))
n = int(math.ceil(2 * RF / PITCH)); off = -n * PITCH / 2
teeth = whole = 0; walls = 0
for i in range(n):
    for j in range(n):
        u0, v0 = off + i * PITCH, off + j * PITCH; u1, v1 = u0 + PITCH, v0 + PITCH; ap = ((u0 + u1) / 2, (v0 + v1) / 2, HT)
        corners = [(u0, v0, 0), (u1, v0, 0), (u1, v1, 0), (u0, v1, 0)]
        if all(math.hypot(c[0], c[1]) <= RF for c in corners): whole += 1
        any_in = False
        for k in range(4):
            tri = [corners[k], corners[(k + 1) % 4], ap]
            cp = clip(tri)
            if len(cp) < 3: continue
            area = abs(sum(cp[m][0] * cp[(m + 1) % len(cp)][1] - cp[(m + 1) % len(cp)][0] * cp[m][1] for m in range(len(cp)))) / 2
            if area < 1e-6: continue
            any_in = True
            poly([W(*p) for p in cp], Vector((-1, 0, 0)))
            for m in range(len(cp)):            # wall down to the face plane along every clipped edge lying on the circle
                P, Q = cp[m], cp[(m + 1) % len(cp)]
                if abs(math.hypot(P[0], P[1]) - RF) < 1e-4 and abs(math.hypot(Q[0], Q[1]) - RF) < 1e-4 and (P[2] > 1e-5 or Q[2] > 1e-5):
                    mid = Vector((0, (P[0] + Q[0]) / 2, (P[1] + Q[1]) / 2))
                    poly([W(*P), W(*Q), W(Q[0], Q[1], 0), W(P[0], P[1], 0)], mid); walls += 1
        teeth += any_in
# skirt: the cut section of the paw cap out to the face circle, flat in the face plane
for a, b in bnd:
    pa = [W(a.y - CY, a.z - CZ, 0)]
    def to_circle(p):
        dy, dz = p.y - CY, p.z - CZ; r = math.hypot(dy, dz) or 1; return Vector((XC, CY + dy * R / r, CZ + dz * R / r))
    if (to_circle(a) - a).length < 1e-4 and (to_circle(b) - b).length < 1e-4: continue
    poly([a, b, to_circle(b), to_circle(a)] if (to_circle(b) - b).length > 1e-4 and (to_circle(a) - a).length > 1e-4 else
         ([a, b, to_circle(b)] if (to_circle(b) - b).length > 1e-4 else [a, b, to_circle(a)]), Vector((-1, 0, 0)))
if EXT > 0:                                # the extension: a plain cylinder of radius R from the cut (XC) out to the face (XF)
    circ = 2 * math.pi * R
    bands = [(XC, R, XF + CH, R)] + ([(XF + CH, R, XF, R - CH)] if CH > 0 else [])   # the drum, then the 45-degree chamfer of the gold lip
    for (xa, ra, xb, rb), i in [(b, i) for b in bands for i in range(NSEG)]:
        a0, a1 = 2 * math.pi * i / NSEG, 2 * math.pi * (i + 1) / NSEG
        P = [Vector((xa, CY + ra * math.cos(a0), CZ + ra * math.sin(a0))), Vector((xa, CY + ra * math.cos(a1), CZ + ra * math.sin(a1))),
             Vector((xb, CY + rb * math.cos(a1), CZ + rb * math.sin(a1))), Vector((xb, CY + rb * math.cos(a0), CZ + rb * math.sin(a0)))]
        vv = [fb.verts.new(q) for q in P]; f = fb.faces.new(vv); f.normal_update()
        mid = Vector((0, math.cos((a0 + a1) / 2), math.sin((a0 + a1) / 2)))
        if f.normal.dot(mid) < 0: f.normal_flip()
        f.smooth = True
        if ART:   # the paw cap's own band continued: its UV rows mirrored about the cut (v 0.917 at the cut -> 0.868, its gold rim, at the face),
                  # its own angle -> u (0.772..0.979 round the circle, measured in the cap's original frame so the pattern meets the cap at the seam)
            angs = [math.atan2(l.vert.co.z - CZ, -(l.vert.co.y - CY)) for l in f.loops]
            if max(angs) - min(angs) > math.pi:   # a face touching the cap's seam: put its odd corner on the same side as the rest
                neg = sum(1 for a in angs if a < 0)
                angs = [a - 2 * math.pi if a > 0 else a for a in angs] if neg * 2 >= len(angs) else [a + 2 * math.pi if a < 0 else a for a in angs]
            angs = [max(-math.pi, min(math.pi, a)) for a in angs]
            cone = min(l.vert.co.x for l in f.loops) < XF + CH - 1e-4
            for l, a in zip(f.loops, angs):
                fr = (a + math.pi) / (2 * math.pi)
                if cone:    # the chamfered lip takes the band's solid gold rows (v 0.874-0.879) inside the island's dark border
                    l[uvl].uv = (0.785 + fr * 0.180, 0.879 - (XF + CH - l.vert.co.x) / CH * 0.005)
                else:
                    t = (XC - l.vert.co.x) / EXT
                    l[uvl].uv = (0.775 + fr * 0.201, 0.917 - t * (0.917 - 0.868))
        else:
            for l in f.loops:
                q = l.vert.co; ang = math.atan2(q.z - CZ, q.y - CY) % (2 * math.pi)
                if ang < a0 - 1e-6: ang += 2 * math.pi
                l[uvl].uv = (U0 + ang / (2 * math.pi) * UW, V0 + (XC - q.x) / circ * UW)
bmesh.ops.remove_doubles(fb, verts=fb.verts[:], dist=1e-5)
me = bpy.data.meshes.new("wh_face"); fb.to_mesh(me); fb.free()
face = bpy.data.objects.new("wh_face", me); bpy.context.scene.collection.objects.link(face)
face.data.materials.append(legacy_material("axe2hebony")); face["tex"] = "axe2hebony"; face["item"] = "warhammer"
for p in me.polygons: p.use_smooth = p.use_smooth and EXT > 0 and abs(p.normal.x) < 0.2
print("TEETH", teeth, "whole", whole, "clipped", teeth - whole, "walls", walls, "faces", len(me.polygons), "grid", n)
note("warhammer", "new", "a flat circular striking face, made from scratch: %d square pyramid teeth (pitch %.2f, height %.2f, 45 deg), clipped to the circle (R %.2f), on plain black steel of axe2hebony" % (teeth, PITCH, HT, R))
WH = [o for o in GROUPS["warhammer"]] + [face]
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT3, "round3%s.blend" % TAG))
json.dump({"cut_x": XC, "radius": R, "pitch": PITCH, "height": HT, "teeth": teeth, "whole": whole, "walls": walls, "faces": len(me.polygons),
           "uv_window": [U0, V0, UW], "stretch": ST, "ext": EXT, "art": ART, "chamfer": CH, "face_radius": RF}, open(os.path.join(OUT3, "face%s.json" % TAG), "w"), indent=1)

wolf_lib.FIXED[0] = 128.0
for (name, yaw, pitch, yr, Wp, Hp) in [("front", 0, 0, None, 700, 1400), ("tq", 35, 18, None, 700, 1400)]:
    frame(sc, co, WH, os.path.join(OUT3, "wh%s_%s.png" % (TAG, name)), math.radians(yaw), math.radians(pitch), W=Wp, H=Hp)
for (name, yaw, pitch, yr, Wp, Hp) in [("face", -90, 0, (36, 51), 900, 900), ("prof", 0, 0, (36, 51), 900, 900), ("close", -40, 18, (34, 59), 900, 900), ("close2", 30, 20, (34, 59), 900, 900)]:
    frame(sc, co, WH, os.path.join(OUT3, "wh%s_%s.png" % (TAG, name)), math.radians(yaw), math.radians(pitch), W=Wp, H=Hp, yr=yr)
