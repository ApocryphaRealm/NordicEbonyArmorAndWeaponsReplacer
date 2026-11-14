# Assembles the game NIFs of the four missing Ebony Wolf weapons and the quiver, on VANILLA's own NIFs: every node, its
# transform, the extra data (BSXFlags, BSInvMarker, the Prn attach point, the bow's behaviour graph), the bone tree, the
# blood shapes' shaders and alpha, the arrow's tracer and its controller are kept; our geometry (build_stage.py's
# single-shape NIFs) is spliced into vanilla's shapes, and every shape of ours takes the shader and texture set of the
# Legacy of Ysgramor shape its pieces were cut from - the Wolf weapons' own Xtudo-black atlases at the paths the mod's
# existing Wolf weapons use (textures\nordwar\companions\...). No new texture.
#
#   ebonymace.nif / 1stpersonebonymace.nif           EbonyMace:0 <- the mace; EdgeBlood shapes <- our head's blood;
#                                                     vanilla's 'Scb' belt hook DROPPED (no Wolf piece forms a hook; the
#                                                     war axe's own Scb is a blade cover that does not fit a flanged head)
#   ebonywarhammer.nif / 1stpersonebonywarhammer.nif  the same, no Scb in vanilla
#   ebonybowskinned.nif                               BowMesh:0 <- the bow's sword1hebony shape, a second skinned shape for
#                                                     its axe1hebony shape (spurs + string); NiSkinInstance (vanilla's
#                                                     type), bones re-pointed at vanilla's own Bow_* nodes by name; SLSF1
#                                                     Skinned (0x2) on both shaders (a skinned shape without it draws
#                                                     nothing - Truly Nordic bow 2026-11-11); convex hull rebuilt on
#                                                     Bow_MidBone's frame. The 1st-person STAT (1stPersonEbonyBow) points at
#                                                     this same file.
#   ebonyarrow.nif                                    Arrow:0 <- the arrow; ArrowQuiver:0 <- the quiver body (dagger
#                                                     scabbard, daggerebony) + one added shape for its gold collar and fang
#                                                     plate (axe1hebony); Arrow1..Arrow6 <- the six quiver arrows (one
#                                                     shape each - the game hides them by name); both collision boxes refit
#   ebonyarrowprojectile.nif                          EbonyArrowFlight:0 <- the arrow; the box refit; tracer untouched
# Collision: a convex hull or box is fitted to OUR geometry in the frame of the node the collision object hangs on; a
# plain bhkRigidBody's translation / rotation are zeroed (the game does not apply them - Truly Nordic 2026-11-10).
import os, sys, json, struct, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import niflib, winding
HK = 69.99124

# atlas -> (Legacy of Ysgramor file under weapons\ebony, the shape the pieces were cut from)
LOY_SHADER = {"axe1hebony": ("ebonywaraxe.nif", "AxeEbony"), "axe2hebony": ("ebonybattleaxe.nif", "BattleAxeEbony"),
              "sword1hebony": ("ebonysword.nif", "Blade2"), "daggerebony": ("ebonydagger.nif", "Scb")}

# ------------------------------------------------------------------ block helpers (as Truly Nordic's assemble.py)
def shapes_of(n): return [b for b, t in enumerate(n.btypes) if t == "BSTriShape"]
def shape(n, name):
    s = [b for b in shapes_of(n) if n.name(b) == name]; assert len(s) == 1, (name, s); return s[0]
def only_shape(path):
    n = niflib.Nif(path); s = shapes_of(n); assert len(s) == 1, (path, s); return n, s[0]
def geometry_tail(n, b):
    o = n.av_end(b, 0, [], []); tail = bytearray(n.blocks[b][o:]); struct.pack_into("<3i", tail, 16, -1, -1, -1); return tail
def splice(n, b, tail):
    """our geometry into block b, with an identity transform (our shapes are in the parent node's frame)"""
    o = n.av_end(b, 0, [], []); head = bytearray(n.blocks[b][:o]); refs = struct.unpack_from("<3i", n.blocks[b], o + 16)
    t_off = n.transform(b)[0]
    struct.pack_into("<3f", head, t_off, 0.0, 0.0, 0.0); struct.pack_into("<9f", head, t_off + 12, 1, 0, 0, 0, 1, 0, 0, 0, 1)
    struct.pack_into("<f", head, t_off + 48, 1.0)
    new = head + tail; struct.pack_into("<3i", new, o + 16, *refs); n.blocks[b] = new
def shader_of(n, b): return struct.unpack_from("<i", n.blocks[b], n.av_end(b, 0, [], []) + 20)[0]
def set_shader_ref(n, b, sh): struct.pack_into("<i", n.blocks[b], n.av_end(b, 0, [], []) + 20, sh)
def texset_ref_off(n, sh): return n.ref_offsets(sh)[0][-1]
def parent_of(n, b):
    for p, t in enumerate(n.btypes):
        if t in niflib.NODES and b in n.children(p)[0]: return p
def new_string(n, s): n.strings.append(s); return len(n.strings) - 1
def append_child(n, parent, child):
    kids, off = n.children(parent); blk = n.blocks[parent]
    n.blocks[parent] = blk[:off] + struct.pack("<I", len(kids) + 1) + blk[off + 4:off + 4 + 4 * len(kids)] + struct.pack("<i", child) + blk[off + 4 + 4 * len(kids):]
def detach_child(n, parent, child):
    kids, off = n.children(parent); assert child in kids
    rest = [k for k in kids if k != child]; blk = n.blocks[parent]
    n.blocks[parent] = blk[:off] + struct.pack("<I", len(rest)) + b"".join(struct.pack("<i", k) for k in rest) + blk[off + 4 + 4 * len(kids):]

# reference offsets for the block types niflib does not list (all found in the vanilla files we build on)
def refs_of(n, b):
    t = n.btypes[b]; blk = n.blocks[b]
    if t in ("bhkBoxShape", "bhkConvexVerticesShape", "NiSkinData", "NiSkinPartition", "BSInvMarker", "BSBehaviorGraphExtraData"): return []
    if t == "bhkConvexTransformShape": return [0]
    if t == "bhkListShape":
        c = struct.unpack_from("<I", blk, 0)[0]; return [4 + 4 * i for i in range(c)]
    if t in ("bhkRigidBody", "bhkRigidBodyT"): return [0]
    if t in ("NiSkinInstance", "BSDismemberSkinInstance"):
        c = struct.unpack_from("<I", blk, 12)[0]; return [0, 4, 8] + [16 + 4 * i for i in range(c)]
    if t == "bhkCollisionObject": return [0, 6]
    return n.ref_offsets(b)[0]

def remove_blocks(n, dead):
    """delete blocks and renumber every reference; a reference to a deleted block is a fault"""
    dead = set(dead); keep = [b for b in range(len(n.blocks)) if b not in dead]; new = {b: i for i, b in enumerate(keep)}
    for b in keep:
        for o in refs_of(n, b):
            r = struct.unpack_from("<i", n.blocks[b], o)[0]
            if r < 0: continue
            assert r not in dead, ("a kept block still refers to a removed one", n.btypes[b], b, r)
            struct.pack_into("<i", n.blocks[b], o, new[r])
    n.blocks = [n.blocks[b] for b in keep]; n.btypes = [n.btypes[b] for b in keep]; n.roots = [new[r] for r in n.roots]

def reachable(n):
    seen, stack = set(), list(n.roots)
    while stack:
        b = stack.pop()
        if b < 0 or b in seen: continue
        seen.add(b)
        for o in refs_of(n, b):
            r = struct.unpack_from("<i", n.blocks[b], o)[0]
            if r >= 0 and not (n.btypes[b] in niflib.CONTROLLERS and o == 22): stack.append(r)
    return seen

def drop_orphans(n):
    dead = [b for b in range(len(n.blocks)) if b not in reachable(n)]
    if dead: remove_blocks(n, dead)
    return len(dead)

# ------------------------------------------------------------------ the Wolf shaders
_loy = {}
def loy_shader(loy_dir, atlas):
    """(shader block, texture-set block) of the Legacy of Ysgramor shape this atlas's pieces came from"""
    if atlas not in _loy:
        fn, nm = LOY_SHADER[atlas]; n = niflib.Nif(os.path.join(loy_dir, fn)); b = shape(n, nm); sh = shader_of(n, b)
        blk = bytearray(n.blocks[sh]); assert n.btypes[sh] == "BSLightingShaderProperty"
        assert struct.unpack_from("<I", blk, 8)[0] == 0, "Legacy of Ysgramor shader with extra data"
        struct.pack_into("<i", blk, 4, -1); struct.pack_into("<i", blk, 12, -1)       # no name, no controller
        ts = n.i32(sh, texset_ref_off(n, sh)); tsb = bytearray(n.blocks[ts])
        assert ("\\" + atlas + ".dds").encode() in tsb.lower(), (atlas, tsb)
        _loy[atlas] = (blk, tsb)
    return _loy[atlas]

def give_shader(n, b, loy_dir, atlas, skinned=False):
    """a NEW shader + texture-set pair for shape b (the old pair is dropped as an orphan afterwards)"""
    blk, tsb = loy_shader(loy_dir, atlas)
    ts = len(n.blocks); n.btypes.append("BSShaderTextureSet"); n.blocks.append(bytearray(tsb))
    sh = len(n.blocks); n.btypes.append("BSLightingShaderProperty"); n.blocks.append(bytearray(blk))
    struct.pack_into("<i", n.blocks[sh], texset_ref_off(n, sh), ts)
    fo = n.net_end(sh, 4, [], []); f1 = struct.unpack_from("<I", n.blocks[sh], fo)[0]
    struct.pack_into("<I", n.blocks[sh], fo, (f1 | 0x2) if skinned else (f1 & ~0x2))
    set_shader_ref(n, b, sh); return sh

def add_shape(n, like, tail, name, parent):
    """a new rigid shape (a copy of 'like''s head) under parent"""
    o = n.av_end(like, 0, [], []); head = bytearray(n.blocks[like][:o]); struct.pack_into("<i", head, 0, new_string(n, name))
    ne = struct.unpack_from("<I", head, 4)[0]; assert ne == 0
    sb = len(n.blocks); n.btypes.append("BSTriShape"); n.blocks.append(head + tail)
    struct.pack_into("<3i", n.blocks[sb], o + 16, -1, -1, -1); splice(n, sb, tail); append_child(n, parent, sb); return sb

# ------------------------------------------------------------------ transforms and collision
def world_xf(n, b):
    R, t, cur = np.eye(3), np.zeros(3), b
    while cur is not None:
        _, tl, rl, sl = n.transform(cur); Rl = np.array(rl, np.float64).reshape(3, 3)
        R, t = Rl @ R * sl, Rl @ t * sl + np.array(tl); cur = parent_of(n, cur)
    return R, t

def shape_world_points(n, b):
    V, F = winding._tris_from_shape(n, b); R, t = world_xf(n, b)
    return (V @ R.T) + t, F

def refit_list_boxes(n, P, split_y):
    """vanilla's two bhkConvexTransformShape boxes (head, haft) refitted to our points: the box with the higher centre
    takes the points at or above split_y, the other the rest; each keeps its rotation"""
    rb = [i for i, t in enumerate(n.btypes) if t == "bhkRigidBody"]; assert len(rb) == 1
    struct.pack_into("<3f", n.blocks[rb[0]], 52, 0.0, 0.0, 0.0); struct.pack_into("<4f", n.blocks[rb[0]], 68, 0.0, 0.0, 0.0, 1.0)
    cts = [i for i, t in enumerate(n.btypes) if t == "bhkConvexTransformShape"]; assert len(cts) == 2, cts
    ty = {c: struct.unpack_from("<16f", n.blocks[c], 20)[13] for c in cts}
    head, haft = sorted(cts, key=lambda c: -ty[c]); out = {}
    for c, sel in ((head, P[:, 1] >= split_y), (haft, P[:, 1] < split_y)):
        m = np.array(struct.unpack_from("<16f", n.blocks[c], 20), np.float64); cols = np.array([m[0:3], m[4:7], m[8:11]])   # the box's three axes (a 45-degree or 180-degree turn: rows or columns give the same box)
        Q = P[sel]; L = Q @ cols.T; lo, hi = L.min(0), L.max(0); half = (hi - lo) / 2; cen = cols.T @ ((hi + lo) / 2)
        box = struct.unpack_from("<i", n.blocks[c], 0)[0]; assert n.btypes[box] == "bhkBoxShape"
        before = {"centre": np.round(m[12:15] * HK, 2).tolist(), "half": np.round(np.array(struct.unpack_from("<3f", n.blocks[box], 16)) * HK, 2).tolist()}
        struct.pack_into("<3f", n.blocks[box], 16, *(half / HK)); struct.pack_into("<3f", n.blocks[c], 20 + 48, *(cen / HK))
        out["head" if c == head else "haft"] = {"points": int(sel.sum()), "before": before, "after": {"centre": np.round(cen, 2).tolist(), "half": np.round(half, 2).tolist()}}
    return out

def set_box(n, body, P):
    """a bhkBoxShape on a bhkRigidBodyT (0 or 180 degrees about z) fitted to P, given in the frame of its node"""
    qx, qy, qz, qw = struct.unpack_from("<4f", n.blocks[body], 68)
    assert abs(abs(qz) - 1) < 1e-4 or abs(abs(qw) - 1) < 1e-4, ("box body rotation is not 0 / 180 about z", qx, qy, qz, qw)
    box = struct.unpack_from("<i", n.blocks[body], 0)[0]; assert n.btypes[box] == "bhkBoxShape", n.btypes[box]
    lo, hi = P.min(0), P.max(0); c, h = (lo + hi) / 2, (hi - lo) / 2
    before = dict(centre=np.round(np.array(struct.unpack_from("<3f", n.blocks[body], 52)) * HK, 2).tolist(), half=np.round(np.array(struct.unpack_from("<3f", n.blocks[box], 16)) * HK, 2).tolist())
    struct.pack_into("<3f", n.blocks[body], 52, *(c / HK)); struct.pack_into("<3f", n.blocks[box], 16, *(h / HK))
    return dict(before=before, after=dict(centre=np.round(c, 2).tolist(), half=np.round(h, 2).tolist()))

def rewrite_hull(n, P):
    """the bow's bhkConvexVerticesShape: a convex hull of our points (<= 40) in the frame of the node it hangs on"""
    from scipy.spatial import ConvexHull
    b = [i for i, t in enumerate(n.btypes) if t == "bhkConvexVerticesShape"]; assert len(b) == 1; b = b[0]
    rb = [i for i, t in enumerate(n.btypes) if t == "bhkRigidBody"][0]
    struct.pack_into("<3f", n.blocks[rb], 52, 0.0, 0.0, 0.0); struct.pack_into("<4f", n.blocks[rb], 68, 0.0, 0.0, 0.0, 1.0)
    co = [i for i, t in enumerate(n.btypes) if t == "bhkCollisionObject"][0]; node = struct.unpack_from("<i", n.blocks[co], 0)[0]
    R, t = world_xf(n, node)
    h = ConvexHull(P); Q = P[h.vertices]
    if len(Q) > 40:
        sel = [int(np.argmax(Q[:, 1])), int(np.argmin(Q[:, 1]))]; d = np.minimum(np.linalg.norm(Q - Q[sel[0]], axis=1), np.linalg.norm(Q - Q[sel[1]], axis=1))
        while len(sel) < 40:
            i = int(np.argmax(d)); sel.append(i); d = np.minimum(d, np.linalg.norm(Q - Q[i], axis=1))
        Q = Q[sel]
    L = ((Q - t) @ R) / HK; hh = ConvexHull(L); eq = {}
    for e in hh.equations: eq[tuple(np.round(e, 4))] = e
    E = np.array(list(eq.values()), np.float32); Lv = L[hh.vertices].astype(np.float32); nv = len(Lv)
    n.blocks[b] = bytearray(n.blocks[b][:32]) + struct.pack("<I", nv) + np.concatenate([Lv, np.zeros((nv, 1), np.float32)], 1).tobytes() + struct.pack("<I", len(E)) + E.tobytes()
    back = (Lv.astype(np.float64) * HK) @ R.T + t
    return {"hull_points": nv, "planes": len(E), "node": n.name(node), "lo": np.round(back.min(0), 2).tolist(), "hi": np.round(back.max(0), 2).tolist()}

def main_box(n):
    k = [b for b in shapes_of(n) if "blood" not in n.name(b).lower() and n.name(b) != "Scb"]; assert len(k) == 1, [n.name(b) for b in k]
    W, _ = shape_world_points(n, k[0]); return W.min(0), W.max(0)

def first_person_offset(van3, van1):
    """the shift vanilla gives its 1st-person mesh against the 3rd-person one (same mesh, moved - battleaxe and greatsword)"""
    l3, h3 = main_box(niflib.Nif(van3)); l1, h1 = main_box(niflib.Nif(van1))
    assert np.allclose(h3 - l3, h1 - l1, atol=1.0), ("1st- and 3rd-person meshes differ in size", van3, h3 - l3, h1 - l1)
    return np.round((l1 + h1) / 2 - (l3 + h3) / 2, 3)

def save(n, path):
    os.makedirs(os.path.dirname(path), exist_ok=True); n.save(path); niflib.Nif(path)     # read back

# ------------------------------------------------------------------ the items
def build_static(item, van_path, out_path, shapes_dir, loy_dir, split_y, offset):
    n = niflib.Nif(van_path); rep = {"vanilla": os.path.basename(van_path)}
    assert np.allclose(offset, 0, atol=0.1), (item, "1st-person offset", offset)
    sh = shapes_of(n); blood = [b for b in sh if "blood" in n.name(b).lower()]; scb = [b for b in sh if n.name(b) == "Scb"]
    main = [b for b in sh if b not in blood and b not in scb]; assert len(main) == 1, [n.name(b) for b in sh]; main = main[0]
    atl = [f for f in os.listdir(shapes_dir) if f.startswith(item + "_") and f.endswith(".nif") and not f.endswith("_blood.nif")]
    assert len(atl) == 1, (item, atl); atlas = atl[0][len(item) + 1:-4]
    sn, sb = only_shape(os.path.join(shapes_dir, atl[0])); splice(n, main, geometry_tail(sn, sb)); give_shader(n, main, loy_dir, atlas)
    bn, bb = only_shape(os.path.join(shapes_dir, item + "_blood.nif")); bt = geometry_tail(bn, bb)
    for b in blood: splice(n, b, bt)
    rep["main"] = {"shape": n.name(main), "atlas": atlas}; rep["blood_shapes"] = [n.name(b) for b in blood]
    for b in scb:
        detach_child(n, parent_of(n, b), b); rep["dropped"] = "Scb (vanilla's belt hook)"
    P = np.load(os.path.join(shapes_dir, "points_%s.npy" % item))
    rep["collision"] = refit_list_boxes(n, P, split_y)
    rep["orphans_dropped"] = drop_orphans(n)
    save(n, out_path); rep["blocks"] = len(n.blocks); return rep

def build_bow(van_path, out_path, shapes_dir, loy_dir):
    n = niflib.Nif(van_path); s = niflib.Nif(os.path.join(shapes_dir, "bow_skinned.nif"))
    bones_v = {n.name(b): b for b, t in enumerate(n.btypes) if t == "NiNode"}
    main = shape(n, "BowMesh:0")
    ne0 = struct.unpack_from("<I", n.blocks[main], 4)[0]; vflags = struct.unpack_from("<I", n.blocks[main], 8 + 4 * ne0 + 4)[0]
    vskin = n.i32(main, n.av_end(main, 0, [], []) + 16); vdata, vpart = struct.unpack_from("<ii", n.blocks[vskin], 0)
    assert n.btypes[vskin] == "NiSkinInstance"
    skel_root = struct.unpack_from("<i", n.blocks[vskin], 8)[0]          # vanilla's skeleton root, kept
    src = {s.name(b): b for b in shapes_of(s)}; rep = {"vanilla_skin": n.btypes[vskin]}
    order = ["bow_sword1hebony", "bow_axe1hebony"]; assert sorted(src) == sorted(order), sorted(src)
    for role in order:
        sb = src[role]; so = s.av_end(sb, 0, [], []); sk = s.i32(sb, so + 16); sd, sp = struct.unpack_from("<ii", s.blocks[sk], 0)
        assert s.btypes[sk] in ("NiSkinInstance", "BSDismemberSkinInstance"), s.btypes[sk]
        if role == order[0]:
            idx_shape, idx_skin, idx_data, idx_part = main, vskin, vdata, vpart; nm = struct.unpack_from("<i", n.blocks[main], 0)[0]
        else:
            idx_shape, idx_skin, idx_data, idx_part = (len(n.blocks) + i for i in range(4))
            for t in ("BSTriShape", "NiSkinInstance", "NiSkinData", "NiSkinPartition"): n.btypes.append(t); n.blocks.append(bytearray())
            nm = new_string(n, "BowMesh:1"); append_child(n, parent_of(n, main), idx_shape)
        blk = bytearray(s.blocks[sb]); struct.pack_into("<i", blk, 0, nm); struct.pack_into("<3i", blk, so + 16, idx_skin, -1, -1)
        n.btypes[idx_shape] = "BSTriShape"; n.blocks[idx_shape] = blk
        k = bytearray(s.blocks[sk]); nb = struct.unpack_from("<I", k, 12)[0]; k = k[:16 + 4 * nb]
        struct.pack_into("<iii", k, 0, idx_data, idx_part, skel_root)
        names = []
        for j in range(nb):
            nmj = s.name(struct.unpack_from("<i", k, 16 + 4 * j)[0]); names.append(nmj); struct.pack_into("<i", k, 16 + 4 * j, bones_v[nmj])
        n.btypes[idx_skin] = "NiSkinInstance"; n.blocks[idx_skin] = k
        n.btypes[idx_data] = "NiSkinData"; n.blocks[idx_data] = bytearray(s.blocks[sd])
        n.btypes[idx_part] = "NiSkinPartition"; n.blocks[idx_part] = bytearray(s.blocks[sp])
        give_shader(n, idx_shape, loy_dir, role.split("_", 1)[1], skinned=True)
        ne = struct.unpack_from("<I", n.blocks[idx_shape], 4)[0]; struct.pack_into("<I", n.blocks[idx_shape], 8 + 4 * ne + 4, vflags)
        rep[role] = {"shape": n.name(idx_shape), "bones": names}
    rep["collision"] = rewrite_hull(n, np.load(os.path.join(shapes_dir, "points_bow.npy")))
    rep["orphans_dropped"] = drop_orphans(n)
    save(n, out_path); rep["blocks"] = len(n.blocks); return rep

def build_arrow(van_path, flight_path, out_arrow, out_flight, shapes_dir, loy_dir):
    rep = {}
    n = niflib.Nif(van_path)
    an, ab = only_shape(os.path.join(shapes_dir, "arrow.nif")); arrow_tail = geometry_tail(an, ab)
    a0 = shape(n, "Arrow:0"); splice(n, a0, arrow_tail); give_shader(n, a0, loy_dir, "axe1hebony")
    q0 = shape(n, "ArrowQuiver:0"); qn, qb = only_shape(os.path.join(shapes_dir, "quiver_daggerebony.nif"))
    splice(n, q0, geometry_tail(qn, qb)); give_shader(n, q0, loy_dir, "daggerebony")
    tn, tb = only_shape(os.path.join(shapes_dir, "quiver_axe1hebony.nif"))
    trim = add_shape(n, q0, geometry_tail(tn, tb), "ArrowQuiver:1", parent_of(n, q0)); give_shader(n, trim, loy_dir, "axe1hebony")
    for k in range(1, 7):
        b = shape(n, "Arrow%d" % k); sn, sb = only_shape(os.path.join(shapes_dir, "quiver_Arrow%d.nif" % k))
        assert parent_of(n, b) == parent_of(n, q0)
        splice(n, b, geometry_tail(sn, sb)); give_shader(n, b, loy_dir, "axe1hebony")
    bodies = {}
    for co in [i for i, t in enumerate(n.btypes) if t == "bhkCollisionObject"]:
        node, _, body = struct.unpack_from("<iHi", n.blocks[co], 0); bodies[n.name(node)] = body
    rep["collision"] = {"Arrow (root) - the loose arrow": set_box(n, bodies["Arrow"], np.load(os.path.join(shapes_dir, "points_arrow.npy"))),
                        "ArrowQuiver - the quiver": set_box(n, bodies["ArrowQuiver"], np.load(os.path.join(shapes_dir, "points_quiver.npy")))}
    rep["orphans_dropped"] = drop_orphans(n); save(n, out_arrow); rep["blocks"] = len(n.blocks)
    f = niflib.Nif(flight_path); b = shape(f, "EbonyArrowFlight:0"); splice(f, b, arrow_tail); give_shader(f, b, loy_dir, "axe1hebony")
    co = [i for i, t in enumerate(f.btypes) if t == "bhkCollisionObject"][0]; body = struct.unpack_from("<iHi", f.blocks[co], 0)[2]
    rep["flight"] = {"collision": set_box(f, body, np.load(os.path.join(shapes_dir, "points_arrow.npy"))), "orphans_dropped": drop_orphans(f)}
    save(f, out_flight); rep["flight"]["blocks"] = len(f.blocks)
    return rep

# ------------------------------------------------------------------ first-person copies of the six Wolf weapons
WOLF_FIRST = {"ebonysword.nif": "1stpersonebonysword.nif", "ebonygreatsword.nif": "1stpersonebonygreatsword.nif",
              "ebonywaraxe.nif": "1stpersonebonywaraxe.nif", "ebonybattleaxe.nif": "1stpersonebonybattleaxe.nif",
              "ebonydagger.nif": "1stpersonebonydagger.nif"}
def first_person_copy(third, van3, van1, out_path):
    """the Wolf weapon's 3rd-person model as its 1st-person file, its root named as vanilla's 1st-person root. Not moved:
    vanilla's own 1st- and 3rd-person ebony meshes are the same model within 0.25 units (measured per weapon, recorded
    below), and Legacy of Ysgramor's own items use their 3rd-person file for both views."""
    n = niflib.Nif(third); off = first_person_offset(van3, van1); root = n.roots[0]
    assert np.abs(off).max() < 0.3, ("vanilla moves this 1st-person mesh - copy would sit wrong", third, off)
    v1 = niflib.Nif(van1); n.blocks[root][0:4] = struct.pack("<i", new_string(n, v1.name(v1.roots[0])))
    save(n, out_path)
    return {"root": v1.name(v1.roots[0]), "vanilla_1st_vs_3rd_offset": off.tolist()}

def build_all(shapes_dir, van_dir, loy_dir, out_meshes, stage_report=None):
    """van_dir / loy_dir: folders holding vanilla's / Legacy of Ysgramor's weapons\\ebony NIFs (vanilla names)"""
    E = lambda *p: os.path.join(*p)
    O = E(out_meshes, "weapons", "ebony"); rep = {}
    split = (stage_report or {}).get("head_split_y", {"mace": 26.0, "warhammer": 38.0})
    for item in ("mace", "warhammer"):
        off = first_person_offset(E(van_dir, "ebony%s.nif" % item), E(van_dir, "1stpersonebony%s.nif" % item))
        rep["ebony%s.nif" % item] = build_static(item, E(van_dir, "ebony%s.nif" % item), E(O, "ebony%s.nif" % item), shapes_dir, loy_dir, split[item], [0, 0, 0])
        rep["1stpersonebony%s.nif" % item] = build_static(item, E(van_dir, "1stpersonebony%s.nif" % item), E(O, "1stpersonebony%s.nif" % item), shapes_dir, loy_dir, split[item], off)
    rep["ebonybowskinned.nif"] = build_bow(E(van_dir, "ebonybowskinned.nif"), E(O, "ebonybowskinned.nif"), shapes_dir, loy_dir)
    rep["ebonyarrow.nif"] = build_arrow(E(van_dir, "ebonyarrow.nif"), E(van_dir, "ebonyarrowprojectile.nif"), E(O, "ebonyarrow.nif"), E(O, "ebonyarrowprojectile.nif"), shapes_dir, loy_dir)
    for third, first in WOLF_FIRST.items():
        rep[first] = first_person_copy(E(loy_dir, third), E(van_dir, third), E(van_dir, first), E(O, first))
    return rep

if __name__ == "__main__":
    sd, vd, ld, om = sys.argv[1:5]
    print(json.dumps(build_all(sd, vd, ld, om), indent=1, default=str))
