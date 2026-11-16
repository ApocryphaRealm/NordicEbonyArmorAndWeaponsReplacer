r"""EXPERIMENTAL full-3D Ebony build, Blender side (pynifly import -> add skinned parts -> export).
blender -b --factory-startup --python-exit-code 1 --python build3d.py -- <cfg.json>
cfg: {"feat_dir", "pieces": [{"name", "files": [[src_1, dst_1], [src_0, dst_0]], "atlases": {"<diffuse stem>": "<feat atlas>"}}],
      "ring": {...}, "stats": path}
The FIRST file of a piece defines every added vertex as (source shape, triangle, barycentric) + local parameters; every
other file of the piece (the other weight) is evaluated from that same recipe, so _0 and _1 get identical vertex counts
and order (the engine blends them by index). Added parts are skinned with the containing triangle's own bone weights
(barycentric blend, top 4 bones), carry the source shape's partition, and are split under 60,000 vertices per shape.
Shape names: <source>_3D_Rings_<n> (chain rings, own chainlink material - texture set rewritten after export) and
<source>_3D_Raised_<n> (rivets, scales, buckles, straps - the source's atlas, no parallax)."""
import bpy, bmesh, sys, os, json, math, numpy as np, addon_utils
from mathutils import Matrix, Vector
addon_utils.enable("io_scene_nifly", default_set=True)
from io_scene_nifly.pyn.pynifly import NifFile
CFG = json.load(open(sys.argv[sys.argv.index("--") + 1])); FEAT = CFG["feat_dir"]; RING = CFG["ring"]
MAXV = 60000; MAXT = 64000

def stem(p): return os.path.splitext(p.replace("/", "\\").split("\\")[-1])[0].lower()

def clear():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    for m in list(bpy.data.meshes): bpy.data.meshes.remove(m)

def load(src):
    clear(); bpy.ops.import_scene.pynifly(filepath=src, import_collisions=False)
    nf = NifFile(src); diff = {}
    for s in nf.shapes:
        try: diff[s.name] = stem(s.shader.textures.get("Diffuse", ""))
        except Exception: diff[s.name] = ""
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    return meshes, diff

class Surf:
    """all triangles of the shapes that use one atlas: uv (T,3,2), world pos (T,3,3), world corner normals (T,3,3),
    vertex indices, object index"""
    def __init__(self, objs):
        self.objs = objs; U = []; P = []; N = []; VI = []; OI = []; TI = []
        for oi, o in enumerate(objs):
            me = o.data; me.calc_loop_triangles(); uvl = me.uv_layers.active.data; Mw = o.matrix_world; Nw = Mw.to_3x3().inverted().transposed()
            cn = me.corner_normals
            for t in me.loop_triangles:
                U.append([tuple(uvl[l].uv) for l in t.loops]); P.append([tuple(Mw @ me.vertices[v].co) for v in t.vertices])
                N.append([tuple((Nw @ cn[l].vector).normalized()) for l in t.loops]); VI.append(tuple(t.vertices)); OI.append(oi); TI.append(t.index)
        self.U = np.array(U, np.float64).reshape(-1, 3, 2); self.P = np.array(P, np.float64).reshape(-1, 3, 3)
        self.N = np.array(N, np.float64).reshape(-1, 3, 3); self.VI = np.array(VI, np.int64).reshape(-1, 3); self.OI = np.array(OI); self.TI = np.array(TI)
        self.B = 128; self.bk = {}
        if len(self.U):
            lo = np.floor(self.U.min(1) * self.B).astype(int); hi = np.floor(self.U.max(1) * self.B).astype(int)
            for i in range(len(self.U)):
                for bx in range(lo[i, 0], hi[i, 0] + 1):
                    for by in range(lo[i, 1], hi[i, 1] + 1): self.bk.setdefault((bx, by), []).append(i)
    def contains(self, uv):
        c = self.bk.get((int(math.floor(uv[0] * self.B)), int(math.floor(uv[1] * self.B))), [])
        if not c: return []
        c = np.array(c); t = self.U[c]; e1 = t[:, 1] - t[:, 0]; e2 = t[:, 2] - t[:, 0]; q = np.asarray(uv) - t[:, 0]
        d = e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]; ok = np.abs(d) > 1e-14; d = np.where(ok, d, 1)
        b1 = (q[:, 0] * e2[:, 1] - q[:, 1] * e2[:, 0]) / d; b2 = (e1[:, 0] * q[:, 1] - e1[:, 1] * q[:, 0]) / d; b0 = 1 - b1 - b2
        good = ok & (b0 >= -1e-6) & (b1 >= -1e-6) & (b2 >= -1e-6)
        return [(int(c[i]), np.array([b0[i], b1[i], b2[i]])) for i in np.nonzero(good)[0]]
    def frame(self, ti, bary):
        """position, normal, dP/du, dP/dv (world) at a triangle point"""
        P = self.P[ti]; t = self.U[ti]; p = bary @ P; n = bary @ self.N[ti]; n /= np.linalg.norm(n) + 1e-12
        e1 = t[1] - t[0]; e2 = t[2] - t[0]; E = np.stack([P[1] - P[0], P[2] - P[0]], 1)
        J = E @ np.linalg.inv(np.stack([e1, e2], 1)); return p, n, J[:, 0], J[:, 1]
    def weights(self, ti, bary):
        o = self.objs[self.OI[ti]]; acc = {}
        for vi, b in zip(self.VI[ti], bary):
            for g in o.data.vertices[vi].groups:
                nm = o.vertex_groups[g.group].name
                if nm.startswith("SBP_"): continue
                acc[nm] = acc.get(nm, 0) + b * g.weight
        top = sorted(acc.items(), key=lambda x: -x[1])[:4]; s = sum(w for _, w in top) or 1
        return [(n_, w / s) for n_, w in top]

def torus(M, m):
    V = []; F = []; UV = []
    for i in range(M):
        a = 2 * math.pi * i / M
        for j in range(m):
            b = 2 * math.pi * j / m; V.append((math.cos(a), math.sin(a), b)); UV.append((i / M, j / m))
    for i in range(M):
        for j in range(m):
            i2 = (i + 1) % M; j2 = (j + 1) % m; F += [(i * m + j, i2 * m + j, i2 * m + j2), (i * m + j, i2 * m + j2, i * m + j2)]
    return V, F, UV

# ---------------- recipe (first file of a piece) ----------------
def recipe(surfs, atl):
    """returns items: list of dicts {kind, atlas, inst: [(ti, bary, ...)], ...}"""
    R = {"rings": [], "rivets": [], "patches": []}
    for dstem, fa in atl.items():
        S = surfs.get(dstem)
        if S is None or not len(S.U): continue
        rc = np.load(os.path.join(FEAT, fa + "_recipe.npz")); W, H = rc["size"]
        # chain rings on the mail mask: UV grid at the texture's ring pitch, alternate rows offset and tilted opposite
        if "mail" in rc:
            mail = rc["mail"]; du = RING["col_px"] / W; dv = RING["row_px"] / H
            u0, v0 = S.U[..., 0].min(), S.U[..., 1].min(); u1, v1 = S.U[..., 0].max(), S.U[..., 1].max()
            j = 0; v = v0
            while v <= v1:
                u = u0 + (0.5 * du if j % 2 else 0.0)
                while u <= u1:
                    x = int(np.clip(u * W, 0, W - 1)); y = int(np.clip((1 - v) * H, 0, H - 1))
                    if mail[y, x]:
                        for ti, b in S.contains((u, v)): R["rings"].append((dstem, ti, b, j % 2))
                    u += du
                v += dv; j += 1
        for x, y, r in rc["rivets"]:
            uv = (x / W, 1 - y / H)
            for ti, b in S.contains(uv): R["rivets"].append((dstem, ti, b, float(r), uv, int(W), int(H)))
        pv, pf, pk = rc["pv"], rc["pf"], rc["pk"]
        for pid in range(len(pk)):
            vs = pv[pv[:, 3] == pid]; fs = pf[pf[:, 3] == pid][:, :3]
            if not len(vs): continue
            first = int(np.nonzero(pv[:, 3] == pid)[0][0]); fs = fs - first
            uvs = np.stack([vs[:, 0] / W, 1 - vs[:, 1] / H], 1); cu = uvs.mean(0)
            anchors = S.contains(tuple(cu))
            if not anchors:
                k_ = int(np.argmin(((uvs - cu) ** 2).sum(1))); anchors = S.contains(tuple(uvs[k_]))
            for ati, ab in anchors:
                A = ab @ S.P[ati]; loc = []
                for i in range(len(vs)):
                    c = S.contains(tuple(uvs[i]))
                    if not c: loc.append(None); continue
                    d = [np.linalg.norm(b @ S.P[t] - A) for t, b in c]; t, b = c[int(np.argmin(d))]
                    loc.append((t, b) if min(d) < 40 else None)
                R["patches"].append((dstem, ati, int(pk[pid]), loc, uvs, vs[:, 2].copy(), fs.copy(), int(W), int(H)))
    return R

# ---------------- evaluate a recipe on the loaded file ----------------
def drop_covered(surfs, R, meshes):
    """a ring is kept only if nothing lies over it: rays along the surface normal from the ring's centre and from four
    points on its rim (at the centre's height), up to 1.5 x the tilted ring's top, must not hit any shape of the item (all its
    shapes, the fur too). Decided once on the recipe's file, so every weight keeps the same rings."""
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get(); V = []; F = []
    for o in meshes:
        me = o.data; Mw = o.matrix_world; b0 = len(V); V += [Mw @ v.co for v in me.vertices]
        me.calc_loop_triangles(); F += [tuple(b0 + i for i in t.vertices) for t in me.loop_triangles]
    if not F: return R
    bvh = BVHTree.FromPolygons(V, F, all_triangles=True)
    keep = []; drop = 0
    for item in R["rings"]:
        dstem, ti, b, par = item; S = surfs[dstem]; p, n, Tu, Tv = S.frame(ti, b)
        W_, H_ = RING["size"][dstem]; du = RING["col_px"] / W_; dv = RING["row_px"] / H_
        c = 0.5 * (np.linalg.norm(Tu) * du + np.linalg.norm(Tv) * dv * RING["col_px"] / RING["row_px"])
        X = Tu - n * n.dot(Tu); X /= np.linalg.norm(X) + 1e-12; Y = np.cross(n, X)
        # from the ring's centre height (a rim point on the tangent plane of a concave surface would start under it)
        # up past the top of the tilted ring
        reach = 1.5 * (RING["R"] * math.sin(math.radians(RING["tilt_deg"])) + RING["wire"]) * c; hit = False
        for o2 in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            q = p + (o2[0] * X + o2[1] * Y) * RING["R"] * c + n * (RING["lift"] * c)
            loc, nor, idx, dist = bvh.ray_cast(Vector(q), Vector(n), reach)
            if loc is not None: hit = True; break
        if hit: drop += 1
        else: keep.append(item)
    print("RINGS COVERED dropped", drop, "of", len(R["rings"]))
    R["rings"] = keep; return R

def build(surfs, R, stats):
    TV, TF, TUV = torus(RING["M"], RING["m"]); tilt = math.radians(RING["tilt_deg"])
    out = {}   # (anchor object name, kind) -> lists
    def acc(key):
        A_ = out.setdefault(key, {"V": [], "F": [], "UV": [], "W": [], "N": [], "ANC": [], "n": 0, "starts": []}); A_["starts"].append(len(A_["V"])); return A_
    for dstem, ti, b, par in R["rings"]:
        S = surfs[dstem]; p, n, Tu, Tv = S.frame(ti, b)
        W_, H_ = RING["size"][dstem]; du = RING["col_px"] / W_; dv = RING["row_px"] / H_
        c = 0.5 * (np.linalg.norm(Tu) * du + np.linalg.norm(Tv) * dv * RING["col_px"] / RING["row_px"])
        X = Tu - n * n.dot(Tu); X /= np.linalg.norm(X) + 1e-12; Y = np.cross(n, X)
        if Y.dot(Tv) < 0: Y = -Y
        s = tilt if par == 0 else -tilt; Z2 = n * math.cos(s) + Y * math.sin(s); Y2 = np.cross(Z2, X)
        R_ = RING["R"] * c; r_ = RING["wire"] * c; ctr = p + n * (RING["lift"] * c)
        ob = S.objs[S.OI[ti]]; A = acc((ob.name, "Rings")); base = len(A["V"])
        for (ca, sa, bb) in TV:
            q = ctr + (R_ + r_ * math.cos(bb)) * (ca * X + sa * Y2) + r_ * math.sin(bb) * Z2; A["V"].append(q)
            A["N"].append((ca * X + sa * Y2) * math.cos(bb) + Z2 * math.sin(bb))
        A["F"] += [(base + f[0], base + f[1], base + f[2]) for f in TF]; A["UV"] += TUV
        w = S.weights(ti, b); A["W"] += [w] * len(TV); A["n"] += 1; A["ANC"] += [anc(S, ti, b)] * len(TV)
    for dstem, ti, b, rpx, uv0, W_, H_ in R["rivets"]:
        S = surfs[dstem]; p, n, Tu, Tv = S.frame(ti, b)
        wpp = 0.5 * (np.linalg.norm(Tu) / W_ + np.linalg.norm(Tv) / H_); r = rpx * wpp; h = 0.6 * r
        X = Tu / (np.linalg.norm(Tu) + 1e-12); X = X - n * n.dot(X); X /= np.linalg.norm(X) + 1e-12; Y = np.cross(n, X)
        if Y.dot(Tv) < 0: Y = -Y
        ob = S.objs[S.OI[ti]]; A = acc((ob.name, "Raised")); base = len(A["V"]); K = 8; lift = 0.01
        ring = [(1.0, lift), (0.72, lift + 0.75 * h)]
        for rr, hh in ring:
            for i in range(K):
                a = 2 * math.pi * i / K; ox, oy = rr * r * math.cos(a), rr * r * math.sin(a)
                A["V"].append(p + X * ox + Y * oy + n * hh); A["N"].append(n)
                A["UV"].append((uv0[0] + ox / (np.linalg.norm(Tu) + 1e-12), uv0[1] + oy / (np.linalg.norm(Tv) + 1e-12)))
        A["V"].append(p + n * (lift + h)); A["UV"].append(tuple(uv0)); A["N"].append(n)
        for i in range(K):
            i2 = (i + 1) % K; A["F"] += [(base + i, base + i2, base + K + i2), (base + i, base + K + i2, base + K + i), (base + K + i, base + K + i2, base + 2 * K)]
        w = S.weights(ti, b); A["W"] += [w] * (2 * K + 1); A["n"] += 1; A["ANC"] += [anc(S, ti, b)] * (2 * K + 1)
    for dstem, ati, kind, loc, uvs, hpx, fs, W_, H_ in R["patches"]:
        S = surfs[dstem]; ob = S.objs[S.OI[ati]]; A = acc((ob.name, "Raised")); base = len(A["V"]); idx = {}
        pts = []
        for i, l in enumerate(loc):
            if l is None: continue
            t, b = l; p, n, Tu, Tv = S.frame(t, b); wpp = 0.5 * (np.linalg.norm(Tu) / W_ + np.linalg.norm(Tv) / H_)
            pts.append((i, p, n, hpx[i] * wpp, wpp, S.weights(t, b), anc(S, t, b)))
        if not pts: continue
        z = np.array([q[1][2] for q in pts]); zmax, zmin = z.max(), z.min(); hmax = max(q[3] for q in pts)
        for i, p, n, hw, wpp, w, an in pts:
            lift = 0.012
            if kind == 1 and zmax - zmin > 1e-6: lift += 0.55 * hmax * 2.5 * (zmax - p[2]) / (zmax - zmin)   # scales: lower edge stands off
            idx[i] = len(A["V"]); A["V"].append(p + n * (hw + lift)); A["UV"].append(tuple(uvs[i])); A["W"].append(w); A["N"].append(n); A["ANC"].append(an)
        for a, b_, c_ in fs:
            if a in idx and b_ in idx and c_ in idx: A["F"].append((idx[a], idx[b_], idx[c_]))
        A["n"] += 1
    return out

ANCH = {}
def anc(S, ti, b):
    o = S.objs[S.OI[ti]]
    return (o.get("pynNodeName", o.name), [int(x) for x in S.VI[ti]], [float(x) for x in b])

def emit(out, objs_by_name, stats):
    made = []
    for (oname, kind), A in sorted(out.items()):
        src = objs_by_name[oname]; Minv = src.matrix_world.inverted()
        V = np.array(A["V"]); F = np.array(A["F"], np.int64).reshape(-1, 3); UV = A["UV"]; Wt = A["W"]
        # winding: every triangle faces the way its surface does (a patch built on image rows, y down, comes out mirrored)
        NN = np.array(A["N"]); fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
        flip = (fn * (NN[F[:, 0]] + NN[F[:, 1]] + NN[F[:, 2]])).sum(1) < 0; F[flip] = F[flip][:, [0, 2, 1]]
        stats.append(dict(shape=oname + '_' + kind, flipped=int(flip.sum()), of=int(len(F)), kind='winding', verts=0, tris=0, items=0, lost_tris=0))
        # split into chunks under MAXV vertices at item boundaries (a ring / rivet / patch is never cut)
        # ... and under MAXT triangles: SSE BSTriShape stores its triangle count as a 16-bit number
        bounds = A["starts"] + [len(V)]
        item_of_face = np.searchsorted(np.array(bounds), F.min(1), side="right") - 1
        fcount = np.bincount(item_of_face, minlength=len(A["starts"]))
        cuts = [0]; cv = 0; cf = 0
        for ii in range(len(A["starts"])):
            nv = bounds[ii + 1] - bounds[ii]; nf = int(fcount[ii])
            if cv + nv > MAXV or cf + nf > MAXT:
                cuts.append(bounds[ii]); cv = 0; cf = 0
            cv += nv; cf += nf
        cuts.append(len(V)); cuts = sorted(set(cuts)); chunks = []
        for ci in range(len(cuts) - 1):
            a, b = cuts[ci], cuts[ci + 1]
            sel = (F.min(1) >= a) & (F.max(1) < b)
            chunks.append((a, b, F[sel] - a))
        lost = len(F) - sum(len(c[2]) for c in chunks)
        for ci, (a, b, f) in enumerate(chunks):
            used = np.unique(f); remap = -np.ones(b - a, np.int64); remap[used] = np.arange(len(used)); f2 = remap[f]
            vv = [tuple(Minv @ Vector(V[a + u])) for u in used]
            me = bpy.data.meshes.new("%s_3D_%s_%d" % (oname, kind, ci)); me.from_pydata(vv, [], [tuple(x) for x in f2.tolist()]); me.update()
            uvl = me.uv_layers.new(name="UVMap")
            for poly in me.polygons:
                poly.use_smooth = True
                for li in poly.loop_indices:
                    vi = me.loops[li].vertex_index; uvl.data[li].uv = UV[a + used[vi]]
            ob = bpy.data.objects.new(me.name, me); bpy.context.scene.collection.objects.link(ob)
            ob.parent = src.parent; ob.matrix_world = src.matrix_world.copy()
            for k_ in src.keys():
                if k_ not in ("pynNodeName",): ob[k_] = src[k_]
            ob["pynNodeName"] = me.name
            for g in src.vertex_groups:
                ob.vertex_groups.new(name=g.name)
            sbp = [g.name for g in src.vertex_groups if g.name.startswith("SBP_")]
            for vi, u in enumerate(used):
                for bn, w in Wt[a + u]:
                    if bn in ob.vertex_groups: ob.vertex_groups[bn].add([vi], float(w), "REPLACE")
            if sbp: ob.vertex_groups[sbp[0]].add(list(range(len(used))), 1.0, "REPLACE")
            for m in src.modifiers:
                if m.type == "ARMATURE":
                    mm = ob.modifiers.new("Armature", "ARMATURE"); mm.object = m.object
            if kind == "Rings":
                mat = src.data.materials[0].copy(); mat.name = me.name + ".Mat"
            else:
                mat = src.data.materials[0]
            ob.data.materials.append(mat)
            made.append(ob); ANCH[me.name] = [A["ANC"][a + u] for u in used]
            stats.append(dict(shape=me.name, kind=kind, verts=len(used), tris=len(f2), items=A["n"] if ci == 0 else 0, lost_tris=lost if ci == 0 else 0))
    return made

def export(dst, only=None):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    for o in bpy.data.objects: o.select_set(only is None or o in only)
    bpy.context.view_layer.objects.active = (only or [o for o in bpy.data.objects if o.type == "MESH"])[0]
    r = bpy.ops.export_scene.pynifly(filepath=dst, target_game="SKYRIMSE")
    print("EXPORTED", dst, r)

ALL = {}
for pc in CFG["pieces"]:
    R = None; per = []
    for src, dst in pc["files"]:
        meshes, diff = load(src)
        orig = [dict(shape=o.name, verts=len(o.data.vertices), tris=sum(len(p.vertices) - 2 for p in o.data.polygons)) for o in meshes]
        surfs = {}
        for dstem in pc["atlases"]:
            objs = [o for o in meshes if diff.get(o.name, diff.get(o.name.split(".")[0], "")) == dstem]
            surfs[dstem] = Surf(objs)
        RING["size"] = {d: tuple(int(x) for x in np.load(os.path.join(FEAT, fa + "_recipe.npz"))["size"]) for d, fa in pc["atlases"].items()}
        if R is None:
            R = recipe(surfs, pc["atlases"])
            if not pc.get("keep_covered"): R = drop_covered(surfs, R, meshes)
        st = []; made = emit(build(surfs, R, st), {o.name: o for o in meshes}, st)
        if pc.get("splice") and not made:
            # nothing raised on this unskinned item: no added NIF (the post step keeps the original + parallax);
            # export(only=[]) would otherwise fall back to writing every shape
            if os.path.isfile(dst): os.remove(dst)
            print("NOTHING ADDED", dst)
        else:
            export(dst, made if pc.get("splice") else None)
        per.append(dict(src=src, dst=dst, original=orig, added=st))
        if CFG.get("anchors"):
            json.dump({k: v for k, v in ANCH.items()}, open(os.path.splitext(dst)[0] + ".anchors.json", "w"))
        ANCH.clear()
        print("PIECE", pc["name"], os.path.basename(dst), "added shapes", len(st), "verts", sum(s["verts"] for s in st), "tris", sum(s["tris"] for s in st))
    ALL[pc["name"]] = per
json.dump(ALL, open(CFG["stats"], "w"), indent=1)
print("BUILD DONE")
