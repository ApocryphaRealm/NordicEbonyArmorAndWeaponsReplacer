"""Checks every NIF the missing-weapons build writes, against the vanilla file it was built on. Fails (returns faults) on:
  * a node of vanilla's missing, renamed or moved (the tree, bone transforms and attach points are the game's contract);
  * the collision object hanging on a different node than vanilla's;
  * a skinned shape whose shader lacks SLSF1 Skinned (0x2), or a rigid one that has it (Truly Nordic bow, 2026-11-11);
  * one of OUR shapes pointing at a texture outside textures\\nordwar\\companions\\ (the Wolf atlases);
  * one of OUR rigid shapes with more than 1% of its surface on faces with no UV area, or a tangent / bitangent that is
    not a unit vector - lost UVs draw one texel with no tangent frame, black and flat in game (warhammer 1.1.0);
  * one of OUR rigid shapes with a face whose three vertex normals all lean > 40 deg off it - a hard edge smoothed over
    because PyNifly writes one normal per vertex (the warhammer's teeth drew as a flat disc, 1.1.0);
  * light through the mesh (see_through): rays at OUR shapes that meet a back face first and no front face after - the
    game culls back faces, so the light behind shows through (bow handle and arrow, 1.1.0 2026-11-14); gated on the bow
    and arrow files, the mace and warhammer reported;
  * the bow (bow_checks): gaps in the riser, the riser wider than vanilla's where the arrow rests, a string end with no
    nock (limb tip past it, a notch, the cord round the limb);
  * the arrow file without exactly Arrow1..Arrow6 as single shapes under ArrowQuiver;
  * winding: an edge walked the same way by both its faces, or a surface whose back sees the sky more than its front
    (the game draws one side; review renders draw both - shield 1.0.0) - measured in each shape's WORLD frame.
"""
import os, sys, struct, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import niflib, winding, assemble as A

def node_table(n):
    out = {}
    for b, t in enumerate(n.btypes):
        if t in niflib.NODES:
            _, tr, r, s = n.transform(b); out[n.name(b)] = (t, np.round(tr, 3).tolist(), np.round(r, 4).tolist(), round(s, 4))
    return out

def coll_node(n):
    co = [i for i, t in enumerate(n.btypes) if t == "bhkCollisionObject"]
    return sorted(n.name(struct.unpack_from("<i", n.blocks[c], 0)[0]) for c in co)

def texpaths(n, sh):
    ts = n.i32(sh, A.texset_ref_off(n, sh))
    if ts < 0: return []
    tb = n.blocks[ts]; c = struct.unpack_from("<I", tb, 0)[0]; p = 4; out = []
    for _ in range(c):
        l = struct.unpack_from("<I", tb, p)[0]; out.append(tb[p + 4:p + 4 + l].decode("latin-1")); p += 4 + l
    return out

def surface_frame(n, b):
    """a rigid shape's UV and tangent-frame health: the share (by 3D area) of faces with NO UV area - a piece whose UVs
    were lost samples one texel and has no tangent frame, black and flat in game (warhammer extension 1.1.0, 2026-11-14) -
    and the vertices whose tangent or bitangent is not a unit vector. None for a skinned shape (data in the partition)."""
    o = n.av_end(b, 0, [], []); blk = n.blocks[b]; q = o + 28
    desc = struct.unpack_from("<Q", blk, q)[0]; ntri, nv = struct.unpack_from("<HH", blk, q + 8); size = struct.unpack_from("<I", blk, q + 12)[0]
    if not size: return None
    stride, fl = (desc & 0xF) * 4, desc >> 44
    if (fl & 0xFFF) != 0x1b or stride != 28: return {"fault": "vertex layout is not position+UV+normal+tangent (28 bytes)", "flags": hex(fl), "stride": stride}
    raw = np.frombuffer(bytes(blk[q + 16:q + 16 + nv * stride]), np.uint8).reshape(nv, stride)
    P = raw[:, 0:12].copy().view(np.float32).astype(np.float64); bx = raw[:, 12:16].copy().view(np.float32)[:, 0]
    U = raw[:, 16:20].copy().view(np.float16).astype(np.float64)
    Nb = raw[:, 20:24].astype(np.float64) / 127.5 - 1; Tb = raw[:, 24:28].astype(np.float64) / 127.5 - 1
    T = Tb[:, :3]; Bt = np.stack([bx, Nb[:, 3], Tb[:, 3]], 1)
    F = np.frombuffer(bytes(blk[q + 16 + nv * stride:q + 16 + nv * stride + ntri * 6]), np.uint16).reshape(-1, 3).astype(np.int64)
    a3 = 0.5 * np.linalg.norm(np.cross(P[F[:, 1]] - P[F[:, 0]], P[F[:, 2]] - P[F[:, 0]]), axis=1)
    d1, d2 = U[F[:, 1]] - U[F[:, 0]], U[F[:, 2]] - U[F[:, 0]]; auv = 0.5 * np.abs(d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0])
    dens = auv / np.maximum(a3, 1e-12); med = np.median(dens[a3 > 1e-6])
    flat = (a3 > 1e-6) & (dens < med * 1e-3)
    bad_t = int(((np.abs(np.linalg.norm(T, axis=1) - 1) > 0.1) | (np.abs(np.linalg.norm(Bt, axis=1) - 1) > 0.1)).sum())
    # smoothed-over hard edges: a face whose three vertex normals ALL lean more than 40 degrees off the face itself - the
    # vertices are shared with faces at a sharp angle, so the game lights it with an averaged normal (the warhammer's
    # pyramid teeth drew as a flat disc, 1.1.0 2026-11-14; every Legacy of Ysgramor piece measures 0)
    g = np.cross(P[F[:, 1]] - P[F[:, 0]], P[F[:, 2]] - P[F[:, 0]]); g = g / np.maximum(np.linalg.norm(g, axis=1), 1e-12)[:, None]
    Nn = Nb[:, :3] / np.maximum(np.linalg.norm(Nb[:, :3], axis=1), 1e-9)[:, None]
    smoothed = (np.einsum("fkj,fj->fk", Nn[F], g).max(1) < math.cos(math.radians(40))) & (a3 > 1e-6)
    return {"faces": int(len(F)), "no_uv_area_share": round(float(a3[flat].sum() / a3.sum()), 4), "no_uv_area_faces": int(flat.sum()),
            "bad_tangent_frames": bad_t, "smoothed_over_hard_edges": int(smoothed.sum()),
            "uv_range": [np.round(U.min(0), 4).tolist(), np.round(U.max(0), 4).tolist()]}

def two_sided(W, ok):
    """faces that have a reversed twin on the same three (welded) points - a two-sided cap (build_stage double_caps): it has
    no inside to face, so it is left out of the facing-in vote (it still blocks rays)"""
    tw = np.zeros(len(W), bool); seen = {}
    for i in np.where(ok)[0]:
        a, b, c = (int(x) for x in W[i]); k = tuple(sorted((a, b, c)))
        r = min(((a, b, c), (b, c, a), (c, a, b)))                        # this winding, canonical start
        for j, rj in seen.get(k, []):
            if rj != r: tw[i] = tw[j] = True
        seen.setdefault(k, []).append((i, r))
    return tw

def lit_shapes(n):
    """the solid shapes: drawn with the lighting shader (not the arrow's effect trails), not blood"""
    out = []
    for b in A.shapes_of(n):
        sh = struct.unpack_from("<i", n.blocks[b], n.av_end(b, 0, [], []) + 20)[0]
        if sh >= 0 and n.btypes[sh] == "BSLightingShaderProperty" and "blood" not in n.name(b).lower(): out.append(b)
    return out

def see_through(n, ours, rays=1500, seed=11, chunk=48):
    """LIGHT THROUGH THE MESH (bow grip and arrow, 1.1.0 2026-11-14): rays from every side at points on OUR shapes, cast
    against every solid shape; a ray whose first surface is a BACK face looks through a
    hole the game does not draw - it culls back faces - and when no FRONT face stops it further on, the light behind comes
    straight through. Returns the share of such rays among those whose first surface is one of ours. Vanilla's ebony bow measures 0.001, its arrow 0.000."""
    rng = np.random.default_rng(seed); T, own = [], []
    for b in lit_shapes(n):
        W, F = A.shape_world_points(n, b)
        if len(F): T.append(W[F]); own += [ours(n.name(b))] * len(F)
    T = np.concatenate(T); own = np.array(own)
    if not own.any(): return None
    tgt = T[own].mean(1); tgt = tgt[rng.choice(len(tgt), rays)]
    D = rng.normal(size=(rays, 3)); D /= np.linalg.norm(D, axis=1, keepdims=True); O = tgt - D * 200.0
    v0, e1, e2 = T[:, 0], T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]; nrm = np.cross(e1, e2)
    first_ours, looks_through = 0, 0
    for s0 in range(0, rays, chunk):
        o = O[s0:s0 + chunk, None]; d = D[s0:s0 + chunk, None]
        p = np.cross(d, e2[None]); det = np.einsum("rtk,tk->rt", p, e1); good = np.abs(det) > 1e-12
        inv = np.where(good, 1 / np.where(good, det, 1), 0); tv = o - v0[None]; u = np.einsum("rtk,rtk->rt", tv, p) * inv
        q = np.cross(tv, e1[None]); v = np.einsum("rtk,rtk->rt", d, q) * inv; t = np.einsum("tk,rtk->rt", e2, q) * inv
        t = np.where(good & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-4), t, np.inf)
        tmin = t.min(1); j = t.argmin(1); hit = np.isfinite(tmin)
        front = np.einsum("tk,rk->rt", nrm, D[s0:s0 + chunk]) < 0
        anyfront = (np.isfinite(t) & front).any(1)       # culled back faces let the ray on: it is stopped by a FRONT face
        mine = hit & own[j]
        first_ours += int(mine.sum()); looks_through += int((mine & ~anyfront).sum())
    return round(looks_through / max(1, first_ours), 4)

def winding_world(n, ours, seed=7):
    rng = np.random.default_rng(seed); shapes = {}
    for b in A.shapes_of(n):
        W, F = A.shape_world_points(n, b)
        if len(F): shapes[b] = (n.name(b), W, F)
    def tris(bs): return np.concatenate([shapes[b][1][shapes[b][2]] for b in bs]) if bs else np.zeros((0, 3, 3))
    solid = [b for b, (nm, _, _) in shapes.items() if "blood" not in nm.lower()]
    rows, faults = [], 0
    for b, (nm, V, F) in shapes.items():
        if not ours(nm): continue
        Wd, ok = winding._weld(V, F); tw = two_sided(Wd, ok); bad, _ = winding.edges_against(Wd, ok)
        ok = ok & ~tw; _, pairs = winding.edges_against(Wd, ok)          # the surfaces voted on: without the two-sided caps
        T = tris(sorted(set(solid) | {b})); inward = []
        for cp in winding.components(len(F), pairs, ok):
            front, back = winding.outward_vote(V, F, cp, T, rng)
            if back > front + 0.15 and back > 0.25: inward.append((len(cp), round(front, 2), round(back, 2)))
        faults += bad + len(inward)
        rows.append({"shape": nm, "faces": int(ok.sum()), "two_sided_faces": int(tw.sum()), "edges_against_neighbour": bad, "surfaces_facing_in": len(inward), "facing_in": inward[:4]})
    return rows, faults

def check(built, vanilla, ours_shapes):
    n, v = niflib.Nif(built), niflib.Nif(vanilla); faults = []; surf = {}
    tn, tv = node_table(n), node_table(v)
    if tn != tv: faults.append(("node tree differs from vanilla", sorted(set(tv) ^ set(tn)) or [k for k in tv if tv[k] != tn.get(k)]))
    if coll_node(n) != coll_node(v): faults.append(("collision on another node", coll_node(n), coll_node(v)))
    for b in A.shapes_of(n):
        nm = n.name(b); o = n.av_end(b, 0, [], []); sk, sh, _ = struct.unpack_from("<3i", n.blocks[b], o + 16)
        if sh < 0 or n.btypes[sh] != "BSLightingShaderProperty": continue
        f1 = struct.unpack_from("<I", n.blocks[sh], n.net_end(sh, 4, [], []))[0]
        if bool(f1 & 0x2) != (sk >= 0): faults.append(("SLSF1 Skinned disagrees with the skin", nm, hex(f1), sk))
        if nm in ours_shapes:
            bad = [p for p in texpaths(n, sh) if p and not p.lower().startswith(("textures\\nordwar\\companions\\", "textures\\cubemaps\\"))]
            if bad: faults.append(("texture outside the Wolf set", nm, bad))
            sf = surface_frame(n, b); surf[nm] = sf
            if sf and ("fault" in sf or sf["no_uv_area_share"] > 0.01 or sf["bad_tangent_frames"]):
                faults.append(("UVs lost or tangent frame broken (draws black and flat in game)", nm, sf))
            if sf and sf.get("smoothed_over_hard_edges"):
                faults.append(("hard edges smoothed over - vertices shared across a sharp edge (draws flat in game)", nm, sf))
    st = see_through(n, lambda nm: nm in ours_shapes)
    if st is not None and st > SEE_THROUGH_MAX and os.path.basename(built).lower() in SEE_THROUGH_GATED:
        faults.append(("light through the mesh: rays meet a back face first and no front face after", st))
    rows, wf = winding_world(n, lambda nm: nm in ours_shapes)
    if wf: faults.append(("winding", [r for r in rows if r["edges_against_neighbour"] or r["surfaces_facing_in"]]))
    return {"faults": faults, "winding": rows, "surface": surf, "see_through_share": st}

SEE_THROUGH_MAX = 0.004
# gated where the owner saw the light come through (bow and arrow, 2026-11-14); the mace and warhammer measure 0.0047 /
# 0.006 and are reported in the build report, not yet gated - the warhammer's head was approved as it stands
SEE_THROUGH_GATED = {"ebonybowskinned.nif", "ebonyarrow.nif", "ebonyarrowprojectile.nif"}

OURS = {"ebonymace.nif": {"EbonyMace:0"}, "1stpersonebonymace.nif": {"1stPersonEbonyMace:0"},
        "ebonywarhammer.nif": {"EbonyWarhammer:0"}, "1stpersonebonywarhammer.nif": {"1stPersonEbonyWarhammer:0"},
        "ebonybowskinned.nif": {"BowMesh:0", "BowMesh:1"},
        "ebonyarrow.nif": {"Arrow:0", "ArrowQuiver:0", "ArrowQuiver:1"} | {"Arrow%d" % k for k in range(1, 7)},
        "ebonyarrowprojectile.nif": {"EbonyArrowFlight:0"}}

def _slice(T, y):
    """points where the triangles T cross the plane at height y"""
    d = T[:, :, 1] - y; out = []
    for i, k in ((0, 1), (1, 2), (2, 0)):
        m = d[:, i] * d[:, k] < 0
        a, b = T[m, i], T[m, k]; da, db = d[m, i][:, None], d[m, k][:, None]
        out.append(a + (b - a) * da / (da - db))
    return np.concatenate(out)

def _bones(n):
    out = {}
    for b, t in enumerate(n.btypes):
        if t == "NiNode": out[n.name(b)] = A.world_xf(n, b)[1]
    return out

def _tris(n, names=None):
    T = [A.shape_world_points(n, b) for b in lit_shapes(n) if names is None or n.name(b) in names]
    return np.concatenate([W[F] for W, F in T if len(F)])

def bow_checks(n, v):
    """The bow as the owner tested it (2026-11-14 07:15), against vanilla's ebony bow:
      * GAPS IN THE RISER - light came through between the grip and its guards: from points on the riser's centre line
        (every 0.1 from the lower limb's base to the upper's) rays in 26 directions must all meet the bow;
      * THE ARROW REST - the arrow lies beside the riser above the hand: from y 2.5 to Bow_MidBone's height + 0.6 our
        riser must be no wider sideways than vanilla's at the same height + 0.2, and an arrow (radius 0.3) lying against
        vanilla's riser at Bow_MidBone's height must clear ours on both sides;
      * STRING NOCKS - at each string-bone pivot (where the string ends and turns when drawn): the limb goes on >= 1.5
        past it (vanilla 2.9), its width is notched there (narrower than 0.6 above and below it), and the cord (BowMesh:1)
        passes it on both sides and on the back of the limb - the loop round the limb."""
    faults, rep = [], {}
    T = _tris(n); C = T.mean(1); Tr = T[C[:, 0] > -9]                         # the riser and limbs, not the string
    Tv = _tris(v); Tv = Tv[Tv.mean(1)[:, 0] > -9]
    B = _bones(n); mid = B["Bow_MidBone"]
    # gaps
    dirs = np.array([(i, j, k) for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1) if (i, j, k) != (0, 0, 0)], float)
    dirs /= np.linalg.norm(dirs, axis=1, keepdims=True); escapes = []
    for y in np.arange(-7.5, 7.51, 0.1):
        P = _slice(Tr, y)
        if not len(P): escapes.append((round(float(y), 2), "nothing at this height")); continue
        P = P[(P[:, 0] > -3) & (P[:, 0] < 1.2)] if ((P[:, 0] > -3) & (P[:, 0] < 1.2)).any() else P   # the core, not the spurs
        c = np.array([(P[:, 0].min() + P[:, 0].max()) / 2, y, (P[:, 2].min() + P[:, 2].max()) / 2])
        esc = winding._ray_escape(np.repeat(c[None], len(dirs), 0), dirs, T)
        if esc.any(): escapes.append((round(float(y), 2), int(esc.sum())))
    rep["riser_gap_heights"] = len(escapes)
    if escapes: faults.append(("gaps in the riser: light passes between its pieces", escapes[:12]))
    # arrow rest
    rows, worst = [], -9.0
    for y in np.arange(2.5, mid[1] + 0.6, 0.1):
        P, Q = _slice(Tr, y), _slice(Tv, y)
        if not len(P) or not len(Q): continue
        ours, van = float(np.abs(P[:, 2]).max()), float(np.abs(Q[:, 2]).max()); worst = max(worst, ours - van)
        if ours > van + 0.2: rows.append((round(float(y), 2), round(ours, 2), round(van, 2)))
    zv = max(float(np.abs(_slice(Tv, mid[1])[:, 2]).max()), 0.0); RA = 0.3; clear = []
    V = T.reshape(-1, 3); V = V[(V[:, 0] > -9) & (np.abs(V[:, 1] - mid[1]) < 2)]
    for sg in (1, -1):
        d = np.hypot(V[:, 1] - mid[1], V[:, 2] - sg * (zv + RA))       # distance to the arrow's axis (along x)
        clear.append(round(float(d.min() - RA), 3))
    rep["arrow_rest"] = {"band_y": [2.5, round(float(mid[1]) + 0.6, 2)], "widest_over_vanilla": round(worst, 3),
                         "arrow_axis_y": round(float(mid[1]), 2), "arrow_axis_z": [round(zv + RA, 2), -round(zv + RA, 2)],
                         "clearance_plus_z_minus_z": clear}
    if rows: faults.append(("the riser is wider than vanilla's where the arrow rests", rows[:8]))
    if min(clear) < 0: faults.append(("an arrow resting against vanilla's riser meets ours", clear))
    # nocks
    Tl = _tris(n, {"BowMesh:0"}); Tc = _tris(n, {"BowMesh:1"}); nk = {}
    for bn in ("Bow_StringBone1", "Bow_StringBone2"):
        p = B[bn]; sg = 1 if p[1] > 0 else -1
        Vl = Tl.reshape(-1, 3); past = float((Vl[:, 1] * sg).max() - p[1] * sg)
        def half_w(y):
            P = _slice(Tl, y); P = P[np.abs(P[:, 0] - p[0]) < 3]
            return float(np.abs(P[:, 2]).max()) if len(P) else 0.0
        w0, wa, wb = half_w(p[1]), half_w(p[1] - 0.6 * sg), half_w(p[1] + 0.6 * sg)
        P = _slice(Tc, p[1]); P = P[np.hypot(P[:, 0] - p[0], P[:, 2] - p[2]) < 4]
        Pl = _slice(Tl, p[1]); Pl = Pl[np.abs(Pl[:, 0] - p[0]) < 3]
        back = float(Pl[:, 0].max()) if len(Pl) else p[0]
        both = bool(len(P)) and P[:, 2].max() > 0.5 * w0 and P[:, 2].min() < -0.5 * w0
        on_back = bool(len(P)) and P[:, 0].max() > back
        nk[bn] = {"limb_past_pivot": round(past, 2), "half_width_at_nock": round(w0, 3), "above_below": [round(wa, 3), round(wb, 3)],
                  "cord_both_sides": both, "cord_round_the_back": on_back}
        if past < 1.5: faults.append(("the limb ends at the string: no tip past the nock", bn, past))
        if not (w0 < min(wa, wb) - 0.05): faults.append(("no notch cut at the nock", bn, w0, wa, wb))
        if not (both and on_back): faults.append(("the string does not loop round the limb at the nock", bn, nk[bn]))
    rep["nocks"] = nk
    return faults, rep

def verify_all(out_dir, van_dir):
    rep, total = {}, 0
    for fn, ours in OURS.items():
        r = check(os.path.join(out_dir, fn), os.path.join(van_dir, fn), ours); rep[fn] = r; total += len(r["faults"])
    bf, br = bow_checks(niflib.Nif(os.path.join(out_dir, "ebonybowskinned.nif")), niflib.Nif(os.path.join(van_dir, "ebonybowskinned.nif")))
    rep["ebonybowskinned.nif"]["bow"] = br; rep["ebonybowskinned.nif"]["faults"] += bf; total += len(bf)
    n = niflib.Nif(os.path.join(out_dir, "ebonyarrow.nif"))
    q = [b for b in range(len(n.blocks)) if n.btypes[b] == "NiNode" and n.name(b) == "ArrowQuiver"][0]
    kids = [n.name(c) for c in n.children(q)[0] if c >= 0 and n.btypes[c] == "BSTriShape"]
    arrows = sorted(k for k in kids if k.startswith("Arrow") and k[5:].isdigit())
    if arrows != ["Arrow%d" % k for k in range(1, 7)]:
        rep["ebonyarrow.nif"]["faults"].append(("quiver arrows", arrows)); total += 1
    return rep, total

if __name__ == "__main__":
    import json
    r, t = verify_all(sys.argv[1], sys.argv[2]); print(json.dumps(r, indent=1, default=str)); print("FAULTS", t); sys.exit(1 if t else 0)
