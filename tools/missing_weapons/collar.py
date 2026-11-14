# The bow's riser collar, its round limb roots and its seated talons (owner 2026-11-14 08:19 and 08:27).
#
# The owner, on the bow's sword-crossguard pieces: the top and bottom of the handle should look the same and not
# "smushed together"; one new CYLINDRICAL piece with the same braiding running round its outside, slightly hollowed at
# its edge for the arrow to slot into. Then: the limbs ROUND where they meet the handle, tapering into their flat section
# further out, so the new collar does not have a flat plate jutting out of it. And the talons on the front of the bow
# kept, but lined up properly.
#
#   * COLLAR - a closed round drum (band radius RC, a gold lip at each edge RC + LIP), made here, not cut from a piece.
#     Its band carries the Wolf sword's own crossguard knotwork (sword_06's front face, sword1hebony): the face is
#     unrolled between its arched top and bottom edges (the band follows the arch) and laid twice round the drum, front
#     half and back half, each copy the whole knot from closure to closure, so the two closures meet at the sides where
#     the arrow passes. The lips and both end discs take the guard's gold rim. One collar at each end of the grip: the
#     lower one is the upper turned 180 degrees about the bow's width axis (z), so it is the same piece and its braid is
#     not mirrored. The arrow groove is carved after the bow is fitted to vanilla's rig (carve_groove): a channel round
#     the arrow's own line, beside vanilla's riser at Bow_MidBone's height, through the collar's top edge on both sides.
#   * ROUND LIMB ROOTS - each limb is round (radius R_ROOT, concentric with the collar) where it leaves the collar and
#     blends to its own flat section over ROOT_LEN by a smoothstep; the cross-section keeps its own angular layout and
#     its fuller (the radius goes as |q| ** 0.3), so the limb's knotwork runs on down into the collar.
#   * TALONS - the war axe's fang on the back (+x, the side facing the target) of each limb. The fang's concave inner
#     edge is laid onto the limb's back line (followed y by y, EMB inside it) and its root set down on the collar's top,
#     so the talon rises flush out of the limb as a swept-back claw with its point along the limb toward the tip. The
#     sliver of the axe head's outline left at the fang's foot (a thin whisker standing 5 units off the limb) is cut off.
import bmesh, math
import numpy as np
from mathutils import Vector

RC, LIP = 2.0, 0.10                 # band radius, the lip's extra radius (RC + LIP <= vanilla's riser 1.99 + 0.2)
LIP_H = 0.20                        # each lip's height
BAND_H = 1.20                       # the knotwork band between the lips
Y1 = 6.60                           # the upper collar's top (before the rig fit); the arrow (Bow_MidBone 6.37) at its top edge
Y0 = Y1 - BAND_H - 2 * LIP_H        # its bottom
R_ROOT, ROOT_LEN = 1.40, 5.0        # the limb's round root radius, and the length over which it flattens out
EMB = 0.15                          # how far the talon's inner edge sits inside the limb
XPAN = 4.85                         # the knot panel on the guard's face, x in [-XPAN, XPAN] (closure to closure)
T_BAND = (0.17, 0.90)               # the band's black field + knot, as a share of the guard face's height
T_GOLD = 0.95                       # the guard's top gold rim
NSEG = 144                          # segments round the drum (2.5 degrees: the groove is carved into these)


class BandUV:
    """UVs on the guard's front face: (panel x, share of the face height at that x) -> atlas UV, by barycentric lookup in
    the face's triangles, projected onto the guard's x-y plane (its front face looks along +z)."""
    def __init__(self, obj):
        me = obj.data; me.calc_loop_triangles(); uv = me.uv_layers.active.data
        C, U = [], []
        for t in me.loop_triangles:
            if t.normal.z > 0.5:
                C.append([tuple(me.vertices[me.loops[l].vertex_index].co)[:2] for l in t.loops]); U.append([tuple(uv[l].uv) for l in t.loops])
        self.C, self.U = np.array(C), np.array(U)
        xs = np.linspace(-5.6, 5.6, 561); lo, hi = [], []
        for x in xs:
            a, b = self.C, np.roll(self.C, -1, axis=1)
            m = ((a[:, :, 0] - x) * (b[:, :, 0] - x) <= 0) & (a[:, :, 0] != b[:, :, 0])
            y = a[:, :, 1] + (x - a[:, :, 0]) / np.where(m, b[:, :, 0] - a[:, :, 0], 1) * (b[:, :, 1] - a[:, :, 1])
            lo.append(y[m].min()); hi.append(y[m].max())
        self.xs, self.lo, self.hi = xs, np.array(lo), np.array(hi)

    def __call__(self, xp, t):
        y = np.interp(xp, self.xs, self.lo) + t * (np.interp(xp, self.xs, self.hi) - np.interp(xp, self.xs, self.lo))
        p = np.array([xp, y]); a = self.C[:, 0]; v0 = self.C[:, 1] - a; v1 = self.C[:, 2] - a; v2 = p - a
        den = v0[:, 0] * v1[:, 1] - v1[:, 0] * v0[:, 1]
        l1 = (v2[:, 0] * v1[:, 1] - v1[:, 0] * v2[:, 1]) / den; l2 = (v0[:, 0] * v2[:, 1] - v2[:, 0] * v0[:, 1]) / den
        l0 = 1 - l1 - l2; worst = np.minimum(np.minimum(l0, l1), l2); k = int(np.argmax(worst))   # inside, or the nearest
        w = np.clip([l0[k], l1[k], l2[k]], 0, 1); w = w / w.sum()
        return tuple(self.U[k, 0] * w[0] + self.U[k, 1] * w[1] + self.U[k, 2] * w[2])


def profile():
    """(radius, y, t) from the bottom disc's centre round the outside to the top disc's centre; t is the texture row:
    None = gold rim, a float = the band's share of its height"""
    disc = [0.0, 0.5, 1.0, 1.4, 1.65, 1.8, 1.9, 1.97]
    lip = [(RC + 0.03, 0.0), (RC + 0.08, 0.02), (RC + LIP, 0.06), (RC + LIP, 0.14), (RC + 0.06, 0.18), (RC, LIP_H)]
    pts = [(r, Y0, None) for r in disc] + [(r, Y0 + h, None) for r, h in lip]
    nb = int(round(BAND_H / 0.05))
    pts += [(RC, Y0 + LIP_H + BAND_H * k / nb, k / nb) for k in range(1, nb)]
    pts += [(r, Y1 - h, None) for r, h in reversed(lip)] + [(r, Y1, None) for r in reversed(disc)]
    return pts


def build_collar(name, xc, band_uv):
    """the upper collar as a closed drum round the axis x = xc, z = 0 (y up)"""
    import bpy
    me = bpy.data.meshes.new(name); bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    prof = profile(); rings = []
    for r, y, t in prof:
        if r == 0.0: rings.append([bm.verts.new((xc, y, 0.0))] * NSEG); continue
        rings.append([bm.verts.new((xc + r * math.cos(2 * math.pi * i / NSEG), y, r * math.sin(2 * math.pi * i / NSEG))) for i in range(NSEG)])
    for j in range(len(prof) - 1):
        t0, t1 = prof[j][2], prof[j + 1][2]
        for i in range(NSEG):
            i1 = (i + 1) % NSEG
            q = [rings[j][i], rings[j][i1], rings[j + 1][i1], rings[j + 1][i]]
            tt = [t0, t0, t1, t1]
            if len(set(q)) < 3: continue
            keep = [k for k in range(4) if q[k] not in q[:k]]
            f = bm.faces.new([q[k] for k in keep])
            # one panel per face: a face straddling a side seam takes its panel from its first corner
            half = int(((360.0 * i / NSEG + 90.0) % 360.0) // 180.0)
            for k, l in zip(keep, f.loops):
                thp = (360.0 * i / NSEG + 90.0) % 360.0 - 180.0 * half + (0.0 if k in (0, 3) else 360.0 / NSEG)
                xp = XPAN - 2 * XPAN * thp / 180.0
                l[uvl].uv = band_uv(xp, T_GOLD if tt[k] is None else T_BAND[0] + (T_BAND[1] - T_BAND[0]) * tt[k])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    return o


def turn_lower(o, xc):
    """the lower collar: the same piece turned 180 degrees about the z axis through x = xc"""
    for v in o.data.vertices:
        v.co.x = 2 * xc - v.co.x; v.co.y = -v.co.y
    o.data.update()


def carve_groove(o, xc, ya, za, rg):
    """the arrow's slot: every point of the collar inside the cylinder of radius rg round the arrow's line (along x, at
    height ya, z = +-za) is moved in radially onto that cylinder's surface - a channel through the collar's edge"""
    moved = 0
    for v in o.data.vertices:
        dx, z = v.co.x - xc, v.co.z; rho = math.hypot(dx, z)
        if rho < 1e-6: continue
        s = abs(z) / rho; sg = 1 if z > 0 else -1
        dy = v.co.y - ya
        if abs(dy) >= rg or s < 0.3: continue
        if math.hypot(dy, z - sg * za) >= rg: continue
        rn = (za - math.sqrt(rg * rg - dy * dy)) / s
        if rn < rho:
            k = rn / rho; v.co.x = xc + dx * k; v.co.z = z * k; moved += 1
    o.data.update()
    return moved


def round_root(o, s, xc, y_start):
    """limb s (+1 upper, -1 lower): round at its root, blending to its own flat section over ROOT_LEN from y_start"""
    me = o.data; V = np.array([tuple(v.co) for v in me.vertices]); u = s * V[:, 1]
    # the section's centre and half extents, measured on the ring-cut planes (every vertex of a ring lies on its plane)
    # and interpolated between them - a bin of loose interior vertices (the fuller's floor) would give a false section
    planes = np.round(np.arange(y_start - 0.4, y_start + ROOT_LEN + 1e-9, 0.25), 4); pu, px0, px1, pz = [], [], [], []
    for y in planes:
        m = np.abs(u - y) < 1e-3
        if m.sum() >= 8: pu.append(y); px0.append(V[m, 0].min()); px1.append(V[m, 0].max()); pz.append(np.abs(V[m, 2]).max())
    pu, px0, px1, pz = map(np.array, (pu, px0, px1, pz))
    before = {}
    for p in me.polygons: before[p.index] = p.area
    for i, v in enumerate(me.vertices):
        if u[i] > y_start + ROOT_LEN: continue
        xa, xb, hz = (float(np.interp(u[i], pu, a_)) for a_ in (px0, px1, pz)); xcen = (xa + xb) / 2; hx = max((xb - xa) / 2, 1e-3)
        qx, qz = (V[i, 0] - xcen) / hx, V[i, 2] / max(hz, 1e-3); q = math.hypot(qx, qz)
        phi = math.atan2(qz, qx); rho = R_ROOT * min(1.0, q) ** 0.3
        rx, rz = xc + rho * math.cos(phi), rho * math.sin(phi)
        w = min(1.0, max(0.0, (u[i] - y_start) / ROOT_LEN)); w = w * w * (3 - 2 * w)
        v.co.x = rx + (V[i, 0] - rx) * w; v.co.z = rz + (V[i, 2] - rz) * w
    me.update()
    ratio = [p.area / before[p.index] for p in me.polygons if before[p.index] > 1e-6 and y_start - 0.5 < s * p.center.y < y_start + ROOT_LEN]
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=[v for v in bm.verts if s * v.co.y < y_start + 0.7 * ROOT_LEN], dist=1e-4)
    bm.to_mesh(me); bm.free(); me.update()
    return ratio


def ring_cuts(o, s, y_from, y_to, step):
    bm = bmesh.new(); bm.from_mesh(o.data)
    y = y_from
    while y <= y_to + 1e-9:
        g = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=g, plane_co=(0, s * y, 0), plane_no=(0, 1, 0)); y += step
    bm.to_mesh(o.data); bm.free(); o.data.update()


def ray_line(objs, s, u0, u1, x_from, zs=(-0.2, 0.0, 0.2), step=0.1):
    """the first surface met by rays along x (from x_from toward the other side) at heights u = s*y, z in zs: per u the
    outermost hit (from +x: the largest x, from -x: the smallest); heights with no hit are dropped"""
    from mathutils.bvhtree import BVHTree
    import bpy
    trees = [BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get()) for o in objs]
    d = Vector((-1, 0, 0)) if x_from > 0 else Vector((1, 0, 0)); us, xs = [], []
    for u in np.arange(u0, u1 + 1e-9, step):
        hits = []
        for z in zs:
            for t in trees:
                h = t.ray_cast(Vector((x_from, s * u, z)), d, 100.0)
                if h[0] is not None: hits.append(h[0].x)
        if hits: us.append(u); xs.append(max(hits) if x_from > 0 else min(hits))
    return np.array(us), np.array(xs)


def smooth(x, k=2):
    return np.array([x[max(0, i - k):i + k + 1].mean() for i in range(len(x))])


def seat_talon(o, s, limbs, y_root):
    """cut the whisker, then lay the fang's inner edge on the limb's back and its root on the collar's top"""
    # one straight cut along the fang body's lower outer edge, from (2.4, 7.2) at 45 degrees: the whisker beyond it goes
    # and the cut is one clean loop for cap_holes (deleting faces left a ragged rim that capped as shards)
    bm = bmesh.new(); bm.from_mesh(o.data)
    # welded back first: harden() split its sharp edges into open rims, which cap_holes would read as holes
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4); nv0 = len(bm.verts)
    n_ = Vector((1.35, -1.35 * s, 0)).normalized()
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(2.4, s * 7.2, 0), plane_no=n_, clear_outer=True)
    # and a level cut at its foot (u = 7.6): a flat root, set down into the collar's top
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, s * 7.6, 0), plane_no=(0, -s, 0), clear_outer=True)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    # only the fang's body stays: any loose sliver the cut left (a corner of the whisker) goes
    left = set(bm.faces); isl = []
    while left:
        f0 = left.pop(); grp = {f0}; st_ = [f0]
        while st_:
            f = st_.pop()
            for e in f.edges:
                for g in e.link_faces:
                    if g in left: left.remove(g); grp.add(g); st_.append(g)
        isl.append(grp)
    isl.sort(key=lambda g: -sum(f.calc_area() for f in g)); big = sum(f.calc_area() for f in isl[0])
    def stray(g):                                   # small, and wholly out in the whisker's corner
        return sum(f.calc_area() for f in g) < 0.05 * big and min(v.co.x for f in g for v in f.verts) > 2.0
    islands = [(round(sum(f.calc_area() for f in g), 3), round(min(v.co.x for f in g for v in f.verts), 2), stray(g)) for g in isl]
    bmesh.ops.delete(bm, geom=[f for g in isl if stray(g) for f in g], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    kill = nv0 - len(bm.verts)
    bm.to_mesh(o.data); bm.free(); o.data.update()
    V = np.array([tuple(v.co) for v in o.data.vertices]); u = s * V[:, 1]
    cu, cx = ray_line([o], s, u.min(), u.max(), -20.0, zs=(-0.1, 0.0, 0.1), step=0.1); cx = smooth(cx)   # its inner edge
    du = y_root - u.min()
    back_u, back_x = ray_line(limbs, s, y_root - 0.5, u.max() + du + 0.5, 20.0); back_x = smooth(back_x)   # the limb's back
    for i, v in enumerate(o.data.vertices):
        xin = float(np.interp(u[i], cu, cx)); un = u[i] + du
        v.co.x = V[i, 0] - xin + float(np.interp(un, back_u, back_x)) - EMB; v.co.y = s * un
    o.data.update()
    return {"whisker_vertices_cut": kill, "islands_area_minx_stray": islands, "moved_down": round(float(du), 3), "root": round(float(y_root), 3),
            "point": round(float(u.max() + du), 3), "inner_edge_x_was": [round(float(cx.min()), 3), round(float(cx.max()), 3)]}
