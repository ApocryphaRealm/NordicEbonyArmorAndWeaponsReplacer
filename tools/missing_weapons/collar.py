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
#     the arrow passes, a narrow gold bar over each seam (SEAM_BAR). The lips and end discs are gold (see profile). One collar at each end of the grip: the
#     lower one is the upper turned 180 degrees about the bow's width axis (z), so it is the same piece and its braid is
#     not mirrored. The arrow groove is carved after the bow is fitted to vanilla's rig (carve_groove): a channel round
#     the arrow's own line, beside vanilla's riser at Bow_MidBone's height, through the collar's top edge on both sides.
#   * ROUND LIMB ROOTS (r02, after r01 still showed a flat faceted slab) - each limb is CUT OFF ROOT_STRAIGHT + ROOT_LEN
#     above the collar (the sword blade's flared base and shoulders go with it) and a new loft (loft_root) runs from a
#     smooth rod of radius R_ROOT on the collar's axis, ROOT_SEG+ sides, into the limb's own section at the cut, along a
#     smootherstep (ease-in, ease-out) and a Hermite centre line that meets the limb at its own slope - no step, no
#     facet. The limb's UVs carry on down the loft, so its braid runs into the collar.
#   * TALONS (r02, after r01's flat ragged cut-outs) - one solid claw per limb (build_talon), as the approved design had
#     one war axe fang each: a tapered, slightly flattened section swept along a curve, its root buried in the limb's
#     back just above the collar (clear of the lip), curving out and then up along the limb toward the tip to a sharp
#     point, both edges trimmed in the Wolf sword's gold; the lower talon is the upper mirrored through the grip.
import bmesh, math
import numpy as np
from mathutils import Vector

RC, LIP = 2.0, 0.10                 # band radius, the lip's extra radius (RC + LIP <= vanilla's riser 1.99 + 0.2)
LIP_H = 0.20                        # each lip's height
BAND_H = 1.20                       # the knotwork band between the lips
Y1 = 6.60                           # the upper collar's top (before the rig fit); the arrow (Bow_MidBone 6.37) at its top edge
Y0 = Y1 - BAND_H - 2 * LIP_H        # its bottom
R_ROOT = 1.40                       # the limb's round root: a rod of the grip's radius on the collar's axis
ROOT_STRAIGHT = 0.30                # it stands round this far out of the collar's top before it starts to flatten
ROOT_LEN = 10.0                     # then lofts into the limb's own flat section over this run (ease-in, ease-out)
ROOT_SEG = 64                       # at least this many sides round the root (the limb's cut rim is split to match)
ROOT_RING = 0.20                    # the loft's ring spacing along the limb
ROOT_UV_RUN = 0.80                  # the limb's texture runs down the loft at this share of its own rate (it stays on the
                                    # blade's straight part of the atlas, short of the flared shoulder)
TALON_UR = 1.70                     # the talon's root centre above the collar's top
TALON_A0, TALON_FLAT = 0.95, 0.58   # its root half-width (in the bow's plane) and its thickness as a share of that
TALON_RIDGE = 22.0                  # degrees either side of each edge that take the gold trim
# atlas windows on sword1hebony (as UV): the blade's plain damascus field between its bevel and its braid, and the gold
# bar beside the sword's grip panel
UV_BODY = ((0.40, 0.50), (0.290, 0.312))     # (u along the talon, v across a flank)
UV_GOLD = ((0.6055, 0.6145), (0.958, 0.878)) # (u across the edge, v along the talon)
XPAN = 4.85                         # the knot panel on the guard's face, x in [-XPAN, XPAN] (closure to closure)
T_BAND = (0.17, 0.90)               # the band's black field + knot, as a share of the guard face's height
GOLD_PATCH = ((0.4175, 0.476), (0.4204, 0.4497))   # (u, v) - plain gold, the guard's lower border (2048 px 855..975 x
                                                    # 1127..1187; >= 90% gold by colour)
NSEG = 144                          # segments round the drum (2.5 degrees: the groove is carved into these)
SEAM_BAR = 5.0                      # degrees each side of the two panel seams (the sides) given a gold bar (r02: the closures
                                    # met there as a visible break)


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
    a float >= 0 = the band's share of its height, a NEGATIVE float = gold, -(1 + its row) counted from a disc's centre
    (rows 1..8 the disc, 8..14 the lip). The gold goes onto GOLD_PATCH, the broadest plain gold on the atlas (the
    guard's lower gold border): the lips and the discs' outer rings along it by the angle, a half turn at a time as the
    band (the seams at the sides, under the arrow groove), and across it by their row; each disc's middle (r <= 1, under
    the limb root or the grip) by a planar map, so its centre has one tangent direction. r01 laid all the gold on ONE row
    of the guard's rim - no UV area, no tangent frame in game (verify's read-back of the skinned bow, r02, 2026-11-14)"""
    disc = [0.0, 0.5, 1.0, 1.4, 1.65, 1.8, 1.9, 1.97]                 # rows 1..8 (as -t)
    lip = [(RC + 0.03, 0.0), (RC + 0.08, 0.02), (RC + LIP, 0.06), (RC + LIP, 0.14), (RC + 0.06, 0.18), (RC, LIP_H)]
    ng = len(disc) + len(lip); g = [-(1.0 + k) for k in range(ng)]
    pts = [(r, Y0, g[k]) for k, r in enumerate(disc)] + [(r, Y0 + h, g[len(disc) + k]) for k, (r, h) in enumerate(lip)]
    nb = int(round(BAND_H / 0.05))
    pts += [(RC, Y0 + LIP_H + BAND_H * k / nb, k / nb) for k in range(1, nb)]
    pts += [(r, Y1 - h, g[len(disc) + k]) for k, (r, h) in reversed(list(enumerate(lip)))] + [(r, Y1, g[k]) for k, r in reversed(list(enumerate(disc)))]
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
            gold = t0 < 0 and t1 < 0          # a lip or disc face; else a band face (its lip-side corners at the band's edge)
            if gold:
                mid_ = max(-t0, -t1) <= 3.0           # the disc's middle (rows 1..3: r 0, 0.5, 1.0)
                for k, l in zip(keep, f.loops):
                    if mid_:
                        cu_, cv_ = 0.5 + 0.5 * (q[k].co.x - xc), 0.5 + 0.5 * q[k].co.z
                    else:
                        thp = (360.0 * i / NSEG + 90.0) % 360.0 - 180.0 * half + (0.0 if k in (0, 3) else 360.0 / NSEG)
                        cu_, cv_ = thp / 180.0, (-tt[k] - 3.0) / 11.0
                    l[uvl].uv = (GOLD_PATCH[0][0] + cu_ * (GOLD_PATCH[0][1] - GOLD_PATCH[0][0]), GOLD_PATCH[1][0] + cv_ * (GOLD_PATCH[1][1] - GOLD_PATCH[1][0]))
                continue
            th0 = (360.0 * i / NSEG + 90.0) % 360.0 - 180.0 * half
            bar = th0 < SEAM_BAR - 1e-6 or th0 > 180.0 - SEAM_BAR - 1e-6
            for k, l in zip(keep, f.loops):
                thp = th0 + (0.0 if k in (0, 3) else 360.0 / NSEG)
                tb = tt[k] if tt[k] >= 0 else (0.0 if q[k].co.y < (Y0 + Y1) / 2 else 1.0)
                if bar:                       # a gold bar over the seam where the two knot panels meet (at the sides)
                    d_ = thp if thp < 90.0 else thp - 180.0
                    l[uvl].uv = (GOLD_PATCH[0][0] + (d_ + SEAM_BAR) / (2 * SEAM_BAR) * (GOLD_PATCH[0][1] - GOLD_PATCH[0][0]),
                                 GOLD_PATCH[1][0] + tb * (GOLD_PATCH[1][1] - GOLD_PATCH[1][0]))
                    continue
                xp = XPAN - 2 * XPAN * (thp - SEAM_BAR) / (180.0 - 2 * SEAM_BAR)
                row = T_BAND[0] + (T_BAND[1] - T_BAND[0]) * tb
                l[uvl].uv = band_uv(xp, row)
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
    # the disc and lip rings the channel pressed onto one surface now coincide: welded, and the faces left with no area
    # between them dissolved - a vertex with only those had no tangent frame (bow r02 read-back). The caller re-splits
    # the collar's hard edges after this (harden), as the weld also closes any it had split there.
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-4)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    bm.to_mesh(o.data); bm.free(); o.data.update()
    return moved


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


def _smoother(h):
    h = min(1.0, max(0.0, h)); return h * h * h * (h * (6 * h - 15) + 10)


def _section(bm, s, u):
    """the points where the mesh's edges cross the plane u = s*y"""
    pts = []
    for e in bm.edges:
        a, b = e.verts[0].co, e.verts[1].co; ua, ub = s * a.y, s * b.y
        if (ua - u) * (ub - u) < 0: pts.append(a.lerp(b, (u - ua) / (ub - ua)))
    return pts


def loft_root(o, s, xc, y_top_collar):
    """limb s (+1 upper, -1 lower) given a ROUND ROOT (owner 2026-11-14 08:27; r02 after Main Agent's r01 review): the
    limb is cut off ROOT_STRAIGHT + ROOT_LEN above the collar's top - everything below goes, the sword blade's flared
    base and shoulders with it - and a new loft is built from a rod of radius R_ROOT on the collar's axis (z = 0, x = xc),
    standing straight out of the collar, into the limb's own section at the cut. The rim at the cut is split to at least
    ROOT_SEG points; each point is matched to the circle by its angle round the section (the section's half extents
    normalised, blended with arc length so the order never folds) and moved along a smootherstep, the centre line along
    a Hermite curve that leaves the collar's axis straight and meets the limb with the limb's own slope. The loft's UVs
    carry on from the limb's faces at the cut, down the blade's own direction on the atlas."""
    u_s = y_top_collar + ROOT_STRAIGHT; u_cut = u_s + ROOT_LEN; u_bot = y_top_collar - 1.0
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)        # harden() split its sharp edges: one surface again
    uvl = bm.loops.layers.uv.active
    above = _section(bm, s, u_cut + 0.6)                           # the limb's slope at the cut
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, s * u_cut, 0), plane_no=(0, -s, 0), clear_outer=True)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    rim = [e for e in bm.edges if e.is_boundary]
    loops, left = [], set(rim)
    while left:
        e0 = left.pop(); chain = [e0.verts[0], e0.verts[1]]
        while True:
            nxt = [e for e in chain[-1].link_edges if e in left]
            if not nxt: break
            e = nxt[0]; left.remove(e); w = e.other_vert(chain[-1])
            if w is chain[0]: break
            chain.append(w)
        loops.append(chain)
    per = lambda L: sum((L[i].co - L[(i + 1) % len(L)].co).length for i in range(len(L)))
    loops.sort(key=lambda L: -per(L))
    assert len(loops) == 1, ("the limb's cut should leave one rim", [(len(L), round(per(L), 3)) for L in loops])
    # split the rim's edges so it has at least ROOT_SEG points, evenly by length
    L = loops[0]; P = per(L); step = P / ROOT_SEG
    edges = [next(e for e in L[i].link_edges if e.other_vert(L[i]) is L[(i + 1) % len(L)]) for i in range(len(L))]
    bycut = {}
    for e in edges:
        k = int(math.ceil(e.calc_length() / step)) - 1
        if k > 0: bycut.setdefault(k, []).append(e)
    for k, es in bycut.items(): bmesh.ops.subdivide_edges(bm, edges=es, cuts=k, use_grid_fill=False)
    rim = [e for e in bm.edges if e.is_boundary]
    v0 = rim[0].verts[0]; ring = [v0]; prev = None
    while True:
        nxt = [e for e in ring[-1].link_edges if e.is_boundary and e.other_vert(ring[-1]) is not prev]
        w = nxt[0].other_vert(ring[-1])
        if w is v0: break
        prev = ring[-1]; ring.append(w)
    n = len(ring); assert n == len(rim), (n, len(rim))
    X = np.array([v.co.x for v in ring]); Z = np.array([v.co.z for v in ring])
    cx, cz = (X.min() + X.max()) / 2, (Z.min() + Z.max()) / 2; hx, hz = (X.max() - X.min()) / 2, (Z.max() - Z.min()) / 2
    ang = np.unwrap(np.arctan2((Z - cz) / hz, (X - cx) / hx))
    if ang[-1] < ang[0]:                                        # walk the rim the way the angle grows
        idx = [0] + list(range(n - 1, 0, -1)); ring = [ring[i] for i in idx]; X, Z = X[idx], Z[idx]
        ang = np.unwrap(np.arctan2((Z - cz) / hz, (X - cx) / hx))
    folds = int((np.diff(ang) < 0).sum())
    seg = np.hypot(np.diff(np.r_[X, X[0]]), np.diff(np.r_[Z, Z[0]])); arc = np.r_[0, np.cumsum(seg)[:-1]] / seg.sum() * 2 * np.pi
    mono = np.maximum.accumulate(ang - ang[0])                  # the angle, never turning back, over one full turn
    phi = ang[0] + 0.5 * mono + 0.5 * arc
    if above:
        ax_ = [p.x for p in above]; az_ = [p.z for p in above]
        mx = ((min(ax_) + max(ax_)) / 2 - cx) / 0.6; mz = ((min(az_) + max(az_)) / 2 - cz) / 0.6
    else:
        mx = mz = 0.0
    def face_of(a, b):                                          # the limb face above a rim edge, its UVs at both ends
        e = next(e for e in a.link_edges if e.other_vert(a) is b); f = e.link_faces[0]
        la = next(l for l in f.loops if l.vert is a); lb = next(l for l in f.loops if l.vert is b)
        return f, la[uvl].uv.copy(), lb[uvl].uv.copy(), la.link_loop_next is lb
    cols = [face_of(ring[j], ring[(j + 1) % n]) for j in range(n)]
    # the limb's UV gradient along its length and across, per side (faces just above the cut, by their normal)
    def side(nrm): return ("x+" if nrm.x > 0 else "x-") if abs(nrm.x) >= abs(nrm.z) else ("z+" if nrm.z > 0 else "z-")
    fit, rows = {}, {}
    for f in bm.faces:
        c = f.calc_center_median()
        if u_cut < s * c.y < u_cut + 4.0:
            k = side(f.normal)
            for l in f.loops:
                lat = l.vert.co.z if k[0] == "x" else l.vert.co.x
                rows.setdefault(k, []).append((1.0, l.vert.co.y, lat, l[uvl].uv.x, l[uvl].uv.y))
    for k, r in rows.items():
        r = np.array(r)
        if len(r) >= 8: fit[k] = np.linalg.lstsq(r[:, :3], r[:, 3:], rcond=None)[0]   # [[u0, v0], [du/dy, dv/dy], [du/dlat, dv/dlat]]
    assert "x+" in fit or "x-" in fit, ("no UV fit on the limb's faces above the cut", sorted(rows))
    fit.setdefault("x+", fit.get("x-")); fit.setdefault("x-", fit.get("x+"))
    U = np.arange(u_bot, u_cut - 1e-6, ROOT_RING); U = np.r_[U, u_cut]
    rings = []; W = [_smoother((u - u_s) / ROOT_LEN) for u in U]
    for i, u in enumerate(U):
        if i == len(U) - 1: rings.append(ring); break
        h = (u - u_s) / ROOT_LEN; w = _smoother(h)
        if u <= u_s: ox, oz = xc, 0.0
        else:
            hh = min(1.0, h); h00 = 3 * hh * hh - 2 * hh ** 3; h11 = hh ** 3 - hh * hh
            ox = xc + (cx - xc) * h00 + mx * ROOT_LEN * h11; oz = cz * h00 + mz * ROOT_LEN * h11
        rings.append([bm.verts.new((ox + (1 - w) * R_ROOT * math.cos(phi[j]) + w * (X[j] - cx), s * u,
                                    oz + (1 - w) * R_ROOT * math.sin(phi[j]) + w * (Z[j] - cz))) for j in range(n)])
    new = []
    for k in range(len(rings) - 1):
        for j in range(n):
            j1 = (j + 1) % n
            new.append(bm.faces.new([rings[k][j], rings[k][j1], rings[k + 1][j1], rings[k + 1][j]]))
    ctr = bm.verts.new((xc, s * u_bot, 0.0))
    cap = [bm.faces.new([ctr, rings[0][(j + 1) % n], rings[0][j]]) for j in range(n)]
    # winding: our top quad runs its rim edge j+1 -> j, so the limb face above must run j -> j+1
    flipped = not cols[0][3]
    if flipped: bmesh.ops.reverse_faces(bm, faces=new + cap)
    # UVs, blended ring by ring with the shape's own weight w: at the cut (w = 1) each column carries its limb face's UVs
    # on down the blade; round (w = 0) the rod is wrapped by the blade's two faces - the half facing +x by the +x face's
    # map, the other by the -x face's, the angle laid linearly across the face's width (the braid on the rod's back and
    # belly, the edges at its sides) - so no column is pinched to a line where the blade's thin edge strip was
    def wrap(a): return (a + math.pi) % (2 * math.pi) - math.pi
    for k in range(len(rings) - 1):
        for j in range(n):
            j1 = (j + 1) % n; f = new[k * n + j]; fc, uva, uvb, _ = cols[j]; sd = side(fc.normal)
            gy = fit[sd][1] if sd in fit and fit[sd] is not None else fit["x+"][1]
            pm = math.atan2(math.sin(phi[j]) + math.sin(phi[j1]), math.cos(phi[j]) + math.cos(phi[j1]))
            rs = "x+" if math.cos(pm) >= 0 else "x-"; F = fit[rs]
            for l in f.loops:
                jj = j if (l.vert is rings[k][j] or l.vert is rings[k + 1][j]) else j1
                kk = k if l.vert in rings[k] else k + 1; w = W[kk]
                top = ring[jj]; base = uva if jj == j else uvb
                dy = (l.vert.co.y - top.co.y) * ROOT_UV_RUN
                ex = (base.x + gy[0] * dy, base.y + gy[1] * dy)
                a_ = wrap(phi[jj]) if rs == "x+" else wrap(math.pi - phi[jj]); lat = hz * a_ / (math.pi / 2)
                yr = top.co.y + dy
                ro = (F[0][0] + F[1][0] * yr + F[2][0] * lat, F[0][1] + F[1][1] * yr + F[2][1] * lat)
                l[uvl].uv = (w * ex[0] + (1 - w) * ro[0], w * ex[1] + (1 - w) * ro[1])
    b0 = cols[0][1]
    for f in cap:                                               # the end disc, hidden inside the collar
        for l in f.loops: l[uvl].uv = (b0.x + 0.01 * (l.vert.co.x - xc), b0.y + 0.01 * l.vert.co.z)
    for f in new + cap: f.smooth = True
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    bm.normal_update(); bm.to_mesh(o.data); bm.free(); o.data.update()
    return {"cut_at": round(u_cut, 3), "straight_to": round(u_s, 3), "from": round(u_bot, 3), "radius": R_ROOT, "sides": n,
            "rings": len(rings), "rim_half_extents_x_z": [round(float(hx), 3), round(float(hz), 3)],
            "rim_centre_x_z": [round(float(cx), 3), round(float(cz), 3)], "limb_slope_x_z": [round(mx, 4), round(mz, 4)],
            "angle_folds_blended_out": folds, "uv_sides_fitted": sorted(rows), "faces_reversed_to_match": flipped}


def build_talon(name, s, limbs, y_top_collar, nt=48):
    """one solid claw on the back (+x) of limb s (owner 2026-11-14 08:27, "lined up properly"; r02): a tapered,
    slightly flattened round section swept along a cubic curve in the bow's plane (x, y) - its root seated INSIDE the
    limb TALON_UR above the collar's top (clear of the lip), leaving the limb's back outward, turning to run along the
    limb toward the tip, and closing to a sharp point. The section is an ellipse, TALON_A0 * (1 - q) ** 0.85 across in
    the bow's plane and TALON_FLAT of that thick (z); both edges (the convex outer and the concave inner) take a gold
    trim (the gold bar beside the Wolf sword's grip panel), the flanks the blade's plain damascus field. The lower
    talon is the same piece mirrored through the grip (s = -1). One per limb, as the approved design had one fang each."""
    import bpy
    u_r = y_top_collar + TALON_UR
    bu, bx = ray_line(limbs, s, u_r - 1.0, u_r + 1.0, 20.0, zs=(0.0,), step=0.1)
    assert len(bu), ("no limb back found for the talon", s)
    bx0 = float(np.interp(u_r, bu, bx))
    C = [np.array(p) for p in ((bx0 - 0.50, u_r), (bx0 + 1.05, u_r + 0.15), (bx0 + 2.35, u_r + 1.55), (bx0 + 2.65, u_r + 4.75))]
    def bez(t): return (1 - t) ** 3 * C[0] + 3 * (1 - t) ** 2 * t * C[1] + 3 * (1 - t) * t * t * C[2] + t ** 3 * C[3]
    def dbez(t): return 3 * (1 - t) ** 2 * (C[1] - C[0]) + 6 * (1 - t) * t * (C[2] - C[1]) + 3 * t * t * (C[3] - C[2])
    tt = np.linspace(0, 1, 801); pts = np.array([bez(t) for t in tt]); L = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    ts = np.interp(np.linspace(0, L[-1], nt + 1), L, tt)          # rings evenly by length
    R = TALON_RIDGE
    th = np.r_[np.linspace(-R, R, 5)[:-1], np.linspace(R, 180 - R, 13)[:-1], np.linspace(180 - R, 180 + R, 5)[:-1], np.linspace(180 + R, 360 - R, 13)[:-1]]
    na = len(th); thr = np.radians(th)
    me = bpy.data.meshes.new(name); bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    rings = []
    for i, t in enumerate(ts[:-1]):
        p = bez(t); d = dbez(t); d = d / np.linalg.norm(d); nrm = np.array([d[1], -d[0]])        # toward the convex side
        q = i / nt; a = TALON_A0 * (1 - q) ** 0.85; b = TALON_FLAT * a
        rings.append([bm.verts.new((p[0] + a * math.cos(x) * nrm[0], s * (p[1] + a * math.cos(x) * nrm[1]), b * math.sin(x))) for x in thr])
    pe = bez(1.0); tip = bm.verts.new((pe[0], s * pe[1], 0.0))
    p0 = bez(0.0); root = bm.verts.new((p0[0], s * p0[1], 0.0))
    def uv(q, x, edge):               # q along the talon (0 root .. 1 point), x the angle in degrees (-R .. 360 - R)
        if edge:                                                                # an edge: gold, across the bar
            c = (x + R) / (2 * R) if x <= R + 1e-6 else (x - 180 + R) / (2 * R)
            return (UV_GOLD[0][0] + c * (UV_GOLD[0][1] - UV_GOLD[0][0]), UV_GOLD[1][0] + q * (UV_GOLD[1][1] - UV_GOLD[1][0]))
        c = (x - R) / (180 - 2 * R) if x < 180 else (x - 180 - R) / (180 - 2 * R)   # a flank: the plain field
        return (UV_BODY[0][0] + q * (UV_BODY[0][1] - UV_BODY[0][0]), UV_BODY[1][0] + c * (UV_BODY[1][1] - UV_BODY[1][0]))
    for i in range(len(rings)):
        q0 = i / nt; q1 = (i + 1) / nt
        for j in range(na):
            j1 = (j + 1) % na; x0 = th[j]; x1 = th[j1] if j1 else 360.0 + th[0]
            if i < len(rings) - 1:
                vs, qs, xs = [rings[i][j], rings[i][j1], rings[i + 1][j1], rings[i + 1][j]], [q0, q0, q1, q1], [x0, x1, x1, x0]
            else:
                vs, qs, xs = [rings[i][j], rings[i][j1], tip], [q0, q0, 1.0], [x0, x1, (x0 + x1) / 2]
            f = bm.faces.new(vs)
            xm = (x0 + x1) / 2; edge = xm < R or 180 - R < xm < 180 + R                # the face's own region
            for l, q, x in zip(f.loops, qs, xs): l[uvl].uv = uv(q, x, edge)
    for j in range(na):                                           # the root disc, buried in the limb
        f = bm.faces.new([root, rings[0][(j + 1) % na], rings[0][j]])
        for l in f.loops: l[uvl].uv = (UV_BODY[0][0] + 0.004 * (s * l.vert.co.y - u_r), UV_BODY[1][0] + 0.01 + 0.004 * l.vert.co.z)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces: f.smooth = True
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    return o, {"root_centre_u": round(u_r, 3), "root_spans_u": [round(u_r - TALON_A0, 3), round(u_r + TALON_A0, 3)],
               "collar_top": round(y_top_collar, 3), "limb_back_x_at_root": round(bx0, 3),
               "point_x_u": [round(float(pe[0]), 3), round(float(pe[1]), 3)], "length": round(float(L[-1]), 3),
               "root_half_width": TALON_A0, "thickness_share": TALON_FLAT, "rings": nt, "sides": na}
