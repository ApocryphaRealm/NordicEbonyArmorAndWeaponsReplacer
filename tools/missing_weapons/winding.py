# Face-direction check of a game NIF (niflib, numpy only - no Blender), used by verify.py on every NIF of the package.
# The game draws a triangle from its front only, and the review renders draw both sides, so a face wound the wrong way
# is invisible in every design sheet and see-through in game (past-mistakes: the shield 1.0.0, the greatsword's ricasso
# wrap 1.0.0). Two checks per shape:
#   1. EDGES AGAINST A NEIGHBOUR - vertices welded by position (the game mesh is split at UV seams and hard edges); every
#      edge shared by exactly two faces must be walked in opposite directions by them. A count above 0 is a fault.
#   2. SURFACES FACING IN - the welded faces split into connected surfaces; each surface is put to a ray vote: from
#      sampled faces (area-weighted), rays in a cone round the face normal and round its opposite are cast against the
#      weapon's own shapes; the side whose rays escape more is the outside. A surface whose back escapes clearly more
#      than its front faces in - a fault. A surface whose two sides both stay blocked (a cap hidden inside the guard)
#      cannot be judged and is not a fault.
# The sheath ('Scb') is voted on its own (the blade inside it would block the weapon's rays and the other way round);
# blood shapes are voted against the weapon (they sit 0.012 outside the steel).
# Skinned shapes (the bow) hold their geometry in the NiSkinPartition; it is read from there.
import struct
import numpy as np

def _tris_from_shape(n, b):
    o = n.av_end(b, 0, [], [])
    sk = struct.unpack_from("<i", n.blocks[b], o + 16)[0]
    blk = n.blocks[b]; q = o + 28
    desc = struct.unpack_from("<Q", blk, q)[0]; ntri, nv = struct.unpack_from("<HH", blk, q + 8); size = struct.unpack_from("<I", blk, q + 12)[0]
    stride = (desc & 0xF) * 4
    if size:
        vd = q + 16; assert size == nv * stride + ntri * 6, ("BSTriShape size", size, nv, stride, ntri)
        V = np.array([struct.unpack_from("<3f", blk, vd + i * stride) for i in range(nv)], np.float64)
        F = np.frombuffer(bytes(blk[vd + nv * stride: vd + nv * stride + ntri * 6]), np.uint16).reshape(-1, 3).astype(np.int64)
        return V, F
    if sk < 0: return np.zeros((0, 3)), np.zeros((0, 3), np.int64)
    # skinned: BSDismemberSkinInstance -> NiSkinPartition (SSE layout: global vertex buffer, partitions with a vertex map)
    part = struct.unpack_from("<i", n.blocks[sk], 4)[0]; pb = n.blocks[part]
    npart, dsize, vsize = struct.unpack_from("<III", pb, 0); pdesc = struct.unpack_from("<Q", pb, 12)[0]
    nvg = dsize // vsize if vsize else 0; vd = 20
    V = np.array([struct.unpack_from("<3f", pb, vd + i * vsize) for i in range(nvg)], np.float64)
    p = vd + dsize; F = []
    for _ in range(npart):
        nvp, ntp, nb, ns, nw = struct.unpack_from("<5H", pb, p); p += 10
        p += 2 * nb
        hasmap = pb[p]; p += 1
        vmap = np.frombuffer(bytes(pb[p:p + 2 * nvp]), np.uint16).astype(np.int64) if hasmap else np.arange(nvp); p += 2 * nvp if hasmap else 0
        hasw = pb[p]; p += 1; p += 4 * nvp * nw if hasw else 0
        slen = struct.unpack_from(f"<{ns}H", pb, p) if ns else (); p += 2 * ns
        hasf = pb[p]; p += 1
        if hasf:
            if ns: p += 2 * sum(slen)   # strips are not used by our shapes
            else:
                t = np.frombuffer(bytes(pb[p:p + 6 * ntp]), np.uint16).reshape(-1, 3).astype(np.int64); p += 6 * ntp
                F.append(vmap[t])
        hasbi = pb[p]; p += 1; p += nvp * nw if hasbi else 0
        p += 1 + 1 + 8 + 6 * ntp     # LOD level, global VB, vertex desc, triangles copy
    F = np.concatenate(F) if F else np.zeros((0, 3), np.int64)
    return V, F

def _weld(V, F, tol=1e-3):
    key = np.round(V / tol).astype(np.int64)
    _, inv = np.unique(key, axis=0, return_inverse=True); inv = inv.reshape(-1)
    W = inv[F]; ok = (W[:, 0] != W[:, 1]) & (W[:, 1] != W[:, 2]) & (W[:, 0] != W[:, 2])
    return W, ok

def edges_against(W, ok):
    """Edges shared by exactly two faces that walk it the same way; and the face adjacency over two-face edges."""
    Fw = W[ok]; idx = np.where(ok)[0]
    e = np.concatenate([Fw[:, [0, 1]], Fw[:, [1, 2]], Fw[:, [2, 0]]]); fi = np.tile(idx, 3)
    und = np.sort(e, 1); fwd = e[:, 0] < e[:, 1]
    order = np.lexsort((und[:, 1], und[:, 0])); und, fwd, fi = und[order], fwd[order], fi[order]
    same = np.all(und[1:] == und[:-1], 1)
    # runs of equal undirected edges
    starts = np.r_[0, np.where(~same)[0] + 1]; ends = np.r_[starts[1:], len(und)]; cnt = ends - starts
    two = starts[cnt == 2]
    bad = int((fwd[two] == fwd[two + 1]).sum())
    pairs = np.stack([fi[two], fi[two + 1]], 1)
    return bad, pairs

def components(nf, pairs, ok):
    par = np.arange(nf)
    def find(i):
        r = i
        while par[r] != r: r = par[r]
        while par[i] != r: par[i], i = r, par[i]
        return r
    for a, b in pairs:
        ra, rb = find(a), find(b)
        if ra != rb: par[ra] = rb
    roots = np.array([find(i) for i in range(nf)])
    return [np.where((roots == r) & ok)[0] for r in np.unique(roots[ok])]

def _ray_escape(orig, dirs, T, chunk=48):
    """For each ray: True when it hits no triangle of T (Moller-Trumbore, numpy)."""
    v0, e1, e2 = T[:, 0], T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]
    out = np.ones(len(orig), bool)
    for s in range(0, len(orig), chunk):
        O = orig[s:s + chunk, None, :]; D = dirs[s:s + chunk, None, :]
        p = np.cross(D, e2[None]); det = np.einsum("rtk,tk->rt", p, e1)
        good = np.abs(det) > 1e-12; inv = np.where(good, 1.0 / np.where(good, det, 1.0), 0.0)
        tv = O - v0[None]; u = np.einsum("rtk,rtk->rt", tv, p) * inv
        q = np.cross(tv, e1[None]); v = np.einsum("rtk,rtk->rt", D, q) * inv
        t = np.einsum("tk,rtk->rt", e2, q) * inv
        hit = good & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-4)
        out[s:s + chunk] = ~hit.any(1)
    return out

def outward_vote(V, F, comp, blockers, rng, samples=40, rays=6):
    P = V[F[comp]]; n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]); a = np.linalg.norm(n, axis=1) / 2
    keep = a > 1e-9
    if not keep.any(): return 0.0, 0.0
    P, n, a = P[keep], n[keep] / (2 * a[keep, None]), a[keep]
    k = min(samples, len(P)); pick = rng.choice(len(P), k, replace=False, p=a / a.sum()) if len(P) > k else np.arange(len(P))
    c = P[pick].mean(1); nn = n[pick]
    sc = []
    for s in (1.0, -1.0):
        d = rng.normal(size=(k, rays, 3)); d /= np.linalg.norm(d, axis=2, keepdims=True)
        ax = (nn * s)[:, None, :]
        d = d + ax * 1.6; d /= np.linalg.norm(d, axis=2, keepdims=True)   # a cone of about 40 degrees round the axis
        o = np.repeat(c + nn * s * 1e-3, rays, 0)
        esc = _ray_escape(o, d.reshape(-1, 3), blockers).reshape(k, rays).mean(1)
        sc.append(float(esc.mean()))
    return sc[0], sc[1]

def check_nif(n, ours=lambda name: True, seed=7):
    """Per shape: edges against a neighbour, surfaces facing in. Returns (report rows, fault count over OUR shapes)."""
    rng = np.random.default_rng(seed)
    shapes = {}
    for b, t in enumerate(n.btypes):
        if t != "BSTriShape": continue
        V, F = _tris_from_shape(n, b)
        if len(F): shapes[b] = (n.name(b), V, F)
    def tris(bs): return np.concatenate([shapes[b][1][shapes[b][2]] for b in bs]) if bs else np.zeros((0, 3, 3))
    weapon = [b for b, (nm, _, _) in shapes.items() if nm != "Scb" and "blood" not in nm.lower()]
    rows, faults = [], 0
    for b, (nm, V, F) in shapes.items():
        W, ok = _weld(V, F); bad, pairs = edges_against(W, ok)
        group = [b] if nm == "Scb" else sorted(set(weapon) | {b})
        T = tris(group); inward = []; comps = components(len(F), pairs, ok)
        for cp in comps:
            front, back = outward_vote(V, F, cp, T, rng)
            if back > front + 0.15 and back > 0.25: inward.append((len(cp), round(front, 2), round(back, 2)))
        mine = ours(nm)
        f = bad + len(inward)
        if mine: faults += f
        rows.append(dict(shape=nm, faces=int(ok.sum()), surfaces=len(comps), edges_against_neighbour=bad,
                         surfaces_facing_in=len(inward), faces_facing_in=int(sum(x[0] for x in inward)),
                         facing_in=inward[:6], ours=mine, fault=bool(f and mine)))
    return rows, faults
