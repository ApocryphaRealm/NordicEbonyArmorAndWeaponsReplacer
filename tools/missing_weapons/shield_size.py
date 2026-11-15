# The shield's size (the owner, 2026-11-15, looking at the 1.1.0 set in game): "make the shield the same size as the
# nordic carved clean shield" - the Truly Nordic Carved Weapons Replacer's "Shield - Clean" option (1.4.0,
# meshes\dlc02\armor\nordicshield\nordicshield.nif).
#
# Legacy of Ysgramor's ShieldEbony.nif is shipped at weapons\ebony\ebonyshield.nif as it comes out of the download,
# so the size change is made here, at build time, on that file - the repository carries no art.
#
# WHAT IS MEASURED. Both shields are round and faced along -z. The size matched is the FACE - the round rim's
# diameter - not the bounding box: the Wolf shield carries four rim fittings at 0/90/180/270 degrees that stand up to
# 1.2 units proud of the rim and sit exactly on the x and y extents (bounding box 63.98 x 63.80; rim 62.3). The rim is
# found as the outermost vertex in each 5-degree sector, a circle fitted through those, the sectors more than 0.4 off
# the circle (the fittings, and the notch at 125 degrees) dropped and the circle refitted. Carved Clean's face, its
# board, measured the same way: diameter 52.774 (bounding box 52.78 x 52.80; measured 2026-11-15, PyNifly in Blender
# 5.2 and niflib agree). The scale is worked out from the file each build, not hard-coded.
#
# THE PIVOT. A shield hangs on the skeleton's SHIELD node (the forearm; on the back, the same model on SHIELD's back
# placement) at the NIF's origin, with its back against the arm. The scale is about the point on the shield's axis
# (x = y = 0) at the depth of its back at the centre, where the arm rests - so the grip stays where it is in the hand
# and on the back, and the rim's curl toward the arm only shrinks (it cannot start to clip the arm).
#
# WHAT CHANGES. Only the existing mesh: every vertex of every BSTriShape, baked into its vertex data (no node scale
# left for another tool to drop), with its bounding sphere; and the convex collision hull - points and planes - by the
# same transform. Normals and tangents are unchanged by a uniform scale. Nothing is added or removed.
import struct
import numpy as np
import niflib

HK = 69.99124
TARGET_DIAMETER = 52.774            # Truly Nordic Carved Weapons Replacer 1.4.0, "31 Shield - Clean": rim_circle() of its board


def _shapes(n):
    return [b for b, t in enumerate(n.btypes) if t == "BSTriShape"]


def _xf(n, b):
    _, t, r, s = n.transform(b)
    return np.array(t, np.float64), np.array(r, np.float64).reshape(3, 3), s


def _geom(n, b):
    o = n.av_end(b, 0, [], []); q = o + 28; blk = n.blocks[b]
    desc = struct.unpack_from("<Q", blk, q)[0]; ntri, nv = struct.unpack_from("<HH", blk, q + 8)
    size = struct.unpack_from("<I", blk, q + 12)[0]; stride = (desc & 0xF) * 4
    assert size == nv * stride + ntri * 6, ("BSTriShape size", n.name(b), size, nv, stride, ntri)
    assert struct.unpack_from("<i", blk, o + 16)[0] < 0, ("the shield has a skinned shape", n.name(b))
    return o, q + 16, nv, stride


def _parent_is_root(n, b):
    kids = n.children(n.roots[0])[0]
    if b in kids:
        return True
    return False


def world_points(n):
    """every vertex of every shape, in the root frame (shapes may hang under one NiNode, as Carved Clean's do)"""
    out = []
    for b in _shapes(n):
        o, vd, nv, stride = _geom(n, b)
        V = np.array([struct.unpack_from("<3f", n.blocks[b], vd + i * stride) for i in range(nv)], np.float64)
        cur, R, t = b, np.eye(3), np.zeros(3)
        while True:
            tl, Rl, sl = _xf(n, cur); R, t = Rl @ R * sl, Rl @ t * sl + tl
            par = [p for p, ty in enumerate(n.btypes) if ty in niflib.NODES and cur in n.children(p)[0]]
            if not par: break
            cur = par[0]
        out.append(V @ R.T + t)
    return np.concatenate(out)


def face_size(P):
    return float(P[:, 0].max() - P[:, 0].min()), float(P[:, 1].max() - P[:, 1].min())


def _circle(Q):
    A = np.c_[2 * Q[:, 0], 2 * Q[:, 1], np.ones(len(Q))]; b = (Q ** 2).sum(1)
    cx, cy, k = np.linalg.lstsq(A, b, rcond=None)[0]
    return np.array([cx, cy]), float(np.sqrt(k + cx * cx + cy * cy))


def rim_circle(P):
    """(centre xy, diameter, sectors kept) of the round face's rim - see WHAT IS MEASURED"""
    ang = np.degrees(np.arctan2(P[:, 1], P[:, 0])) % 360; r = np.hypot(P[:, 0], P[:, 1]); Q = []
    for a in range(0, 360, 5):
        m = (ang >= a) & (ang < a + 5)
        if m.any(): Q.append(P[m][np.argmax(r[m]), :2])
    Q = np.array(Q); c, R = _circle(Q)
    keep = np.abs(np.hypot(*(Q - c).T) - R) < 0.4
    c, R = _circle(Q[keep])
    return c, 2 * R, int(keep.sum())


def resize(path, out_path=None, target=TARGET_DIAMETER):
    n = niflib.Nif(path)
    shapes = _shapes(n)
    for b in shapes:
        assert _parent_is_root(n, b), ("the shield's shape is not directly under the root", n.name(b))
    tr, Rr, sr = _xf(n, n.roots[0])
    assert np.allclose(tr, 0) and np.allclose(Rr, np.eye(3)) and abs(sr - 1) < 1e-6, "the shield's root is not identity"
    P = world_points(n)
    w, h = face_size(P); c0, d0, k0 = rim_circle(P)
    assert k0 >= 54, ("the rim circle fitted fewer than 54 of 72 sectors - is the shield still round?", k0)
    s = target / d0
    near = np.hypot(P[:, 0], P[:, 1]) < 4.0
    pivot = np.array([0.0, 0.0, P[near, 2].max()])

    for b in shapes:
        o, vd, nv, stride = _geom(n, b)
        t, R, sc = _xf(n, b)
        assert abs(sc - 1) < 1e-6, ("shape already scaled", n.name(b), sc)
        pl = R.T @ (pivot - t)                      # the pivot in the shape's own frame
        blk = n.blocks[b]
        for i in range(nv):
            v = np.array(struct.unpack_from("<3f", blk, vd + i * stride))
            struct.pack_into("<3f", blk, vd + i * stride, *(pl + s * (v - pl)))
        c = np.array(struct.unpack_from("<3f", blk, o)); r = struct.unpack_from("<f", blk, o + 12)[0]
        struct.pack_into("<4f", blk, o, *(pl + s * (c - pl)), r * s)

    # collision: one convex hull on a plain bhkRigidBody hung on the root (identity frame), in Havok units
    hulls = [i for i, t in enumerate(n.btypes) if t == "bhkConvexVerticesShape"]
    assert len(hulls) == 1, ("expected one convex hull", len(hulls))
    co = [i for i, t in enumerate(n.btypes) if t == "bhkCollisionObject"]
    assert len(co) == 1 and struct.unpack_from("<i", n.blocks[co[0]], 0)[0] == n.roots[0], "the hull is not on the root"
    hb = n.blocks[hulls[0]]; nv = struct.unpack_from("<I", hb, 32)[0]
    V = np.frombuffer(bytes(hb[36:36 + 16 * nv]), np.float32).reshape(-1, 4).astype(np.float64)
    e0 = 36 + 16 * nv; ne = struct.unpack_from("<I", hb, e0)[0]
    E = np.frombuffer(bytes(hb[e0 + 4:e0 + 4 + 16 * ne]), np.float32).reshape(-1, 4).astype(np.float64)
    assert e0 + 4 + 16 * ne == len(hb), "hull block has trailing data"
    ph = pivot / HK
    hull_before = (V[:, :3].min(0) * HK, V[:, :3].max(0) * HK)
    V[:, :3] = ph + s * (V[:, :3] - ph)
    E[:, 3] = s * E[:, 3] + (s - 1) * (E[:, :3] @ ph)
    n.blocks[hulls[0]] = bytearray(hb[:36]) + V.astype(np.float32).tobytes() + struct.pack("<I", ne) + E.astype(np.float32).tobytes()
    # every hull point must still lie on or inside every plane
    worst = float((V[:, :3] @ E[:, :3].T + E[:, 3]).max())
    assert worst < 1e-3, ("hull planes no longer bound the hull", worst)

    n.save(out_path or path)
    back = niflib.Nif(out_path or path); Q = world_points(back); w2, h2 = face_size(Q); c2, d2, _ = rim_circle(Q)
    assert abs(d2 - target) < 0.05, ("read-back rim diameter", d2, target)
    return {"scale": round(s, 5), "pivot": np.round(pivot, 3).tolist(),
            "rim_diameter_before": round(d0, 3), "rim_diameter_after": round(d2, 3), "target_rim_diameter": target,
            "rim_centre_before": np.round(c0, 3).tolist(), "rim_sectors_fitted": k0,
            "bbox_before": [round(w, 3), round(h, 3)], "bbox_after": [round(w2, 3), round(h2, 3)],
            "depth_before": round(float(P[:, 2].max() - P[:, 2].min()), 3),
            "depth_after": round(float(Q[:, 2].max() - Q[:, 2].min()), 3),
            "hull_before": [np.round(hull_before[0], 2).tolist(), np.round(hull_before[1], 2).tolist()],
            "hull_after": [np.round(V[:, :3].min(0) * HK, 2).tolist(), np.round(V[:, :3].max(0) * HK, 2).tolist()]}


if __name__ == "__main__":
    import sys, json
    print(json.dumps(resize(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None), indent=1))
