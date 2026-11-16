r"""Blender side: modelled 4-in-1 European mail rings over the helmet aventail's UV-mapped mail region.
Called from render_chain.load() for a model with "rings3d": {...}. Rings sit on a UV grid at the TEXTURE's ring pitch
(columns 9 px, rows 6.7 px on the 1024 atlas, measured by autocorrelation of the ring mask), alternate rows offset by
half a column and tilted the opposite way (the 4-in-1 weave: each ring passes through two rings of the row above and two
of the row below). Each ring is oriented to the surface: X along the row (dP/du), Z the surface normal."""
import math, os, numpy as np, bpy, bmesh
from mathutils import Vector

def torus(M, m, R, r):
    V = []; F = []
    for i in range(M):
        a = 2 * math.pi * i / M
        for j in range(m):
            b = 2 * math.pi * j / m
            V.append(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), r * math.sin(b)))
    for i in range(M):
        for j in range(m):
            i2 = (i + 1) % M; j2 = (j + 1) % m
            F.append((i * m + j, i2 * m + j, i2 * m + j2, i * m + j2))
    return np.array(V, np.float64), F

def make(objs, cfg, log=print):
    mk = bpy.data.images.load(cfg["mask"]); W, H = mk.size
    px = np.array(mk.pixels[:], np.float32).reshape(H, W, 4)[..., 0]           # row 0 = bottom = UV v 0
    def mask(u, v):
        x = int(np.clip(u * W, 0, W - 1)); y = int(np.clip(v * H, 0, H - 1)); return px[y, x]
    tris = []
    for o in objs:
        if o.type != "MESH": continue
        # only shapes on the mail's own atlas (the fur / gauntlet shapes have their own UV spaces)
        if cfg.get("mat") and not any(cfg["mat"].lower() in (mt.name.lower() if mt else "") for mt in o.data.materials): continue
        bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.triangulate(bm, faces=bm.faces[:]); uvl = bm.loops.layers.uv.active
        if uvl is None: bm.free(); continue
        Mw = o.matrix_world; Nw = Mw.to_3x3().inverted().transposed()
        for f in bm.faces:
            uv = [l[uvl].uv.copy() for l in f.loops]
            cu = sum(t.x for t in uv) / 3; cv = sum(t.y for t in uv) / 3
            if mask(cu, cv) < 0.3: continue
            P = [Mw @ l.vert.co for l in f.loops]; N = [(Nw @ l.vert.normal).normalized() for l in f.loops]
            tris.append((np.array([[t.x, t.y] for t in uv]), np.array([list(p) for p in P]), np.array([list(n) for n in N])))
        bm.free()
    log("aventail triangles", len(tris))
    # UV buckets
    B = 128; buckets = {}
    for k, (t, P, N) in enumerate(tris):
        x0, y0 = (t.min(0) * B).astype(int); x1, y1 = (t.max(0) * B).astype(int)
        for bx in range(x0, x1 + 1):
            for by in range(y0, y1 + 1): buckets.setdefault((bx, by), []).append(k)
    du = cfg["col_px"] / W; dv = cfg["row_px"] / H; tilt = math.radians(cfg["tilt_deg"])
    allv = np.concatenate([t for t, _, _ in tris]); u0, v0 = allv.min(0); u1, v1 = allv.max(0)
    TV, TF = torus(cfg["M"], cfg["m"], 1.0, cfg["wire"] / cfg["R"])                 # unit major radius
    verts = []; faces = []; rnd = []; rng = np.random.default_rng(3); nring = 0
    j = 0; v = v0
    while v <= v1:
        u = u0 + (0.5 * du if j % 2 else 0.0)
        while u <= u1:
            if mask(u, v) > 0.5:
                for k in buckets.get((int(u * B), int(v * B)), []):
                    t, P, N = tris[k]
                    e1 = t[1] - t[0]; e2 = t[2] - t[0]; d = e1[0] * e2[1] - e1[1] * e2[0]
                    if abs(d) < 1e-12: continue
                    q = np.array([u, v]) - t[0]; b1 = (q[0] * e2[1] - q[1] * e2[0]) / d; b2 = (e1[0] * q[1] - e1[1] * q[0]) / d; b0 = 1 - b1 - b2
                    if min(b0, b1, b2) < -1e-6: continue
                    p = b0 * P[0] + b1 * P[1] + b2 * P[2]; n = b0 * N[0] + b1 * N[1] + b2 * N[2]; n /= np.linalg.norm(n)
                    E = np.stack([P[1] - P[0], P[2] - P[0]], 1); J = E @ np.linalg.inv(np.stack([e1, e2], 1))   # 3x2: dP/du, dP/dv
                    Tu, Tv = J[:, 0], J[:, 1]
                    c = 0.5 * (np.linalg.norm(Tu) * du + np.linalg.norm(Tv) * dv * cfg["col_px"] / cfg["row_px"])   # world column pitch
                    X = Tu - n * n.dot(Tu); X /= np.linalg.norm(X); Y = np.cross(n, X)
                    if Y.dot(Tv) < 0: Y = -Y
                    s = tilt if j % 2 == 0 else -tilt
                    # ring axis starts on the normal, leans about the row axis X
                    Z2 = n * math.cos(s) + Y * math.sin(s); Y2 = np.cross(Z2, X)
                    Rw = cfg["R"] * c
                    ctr = p + n * (cfg["lift"] * c)
                    Lv = TV * Rw
                    wv = ctr + Lv[:, :1] * X + Lv[:, 1:2] * Y2 + Lv[:, 2:3] * Z2
                    base = len(verts) * 0
                    off = nring * len(TV)
                    verts.append(wv); faces += [tuple(i + off for i in f) for f in TF]; rnd.append(np.full(len(TV), rng.random()))
                    nring += 1
            u += du
        v += dv; j += 1
    V = np.concatenate(verts)
    me = bpy.data.meshes.new("mail_rings"); me.from_pydata(V.tolist(), [], faces); me.update()
    at = me.attributes.new("rnd", "FLOAT", "POINT"); at.data.foreach_set("value", np.concatenate(rnd).astype(np.float32))
    for pl in me.polygons: pl.use_smooth = True
    ob = bpy.data.objects.new("mail_rings", me); bpy.context.scene.collection.objects.link(ob)
    mat = bpy.data.materials.new("ring_ebony"); mat.use_nodes = True; nt = mat.node_tree; b = nt.nodes["Principled BSDF"]
    lin = lambda s_: ((s_ + 0.055) / 1.055) ** 2.4
    b.inputs["Base Color"].default_value = (lin(0.42), lin(0.42), lin(0.445), 1); b.inputs["Metallic"].default_value = 1.0
    an = nt.nodes.new("ShaderNodeAttribute"); an.attribute_name = "rnd"; mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = 0.25; mr.inputs["To Max"].default_value = 0.35
    nt.links.new(an.outputs["Fac"], mr.inputs["Value"]); nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    ob.data.materials.append(mat)
    ntri = len(faces) * 2
    log("RINGS3D rings %d  tris %d  tris/ring %d  verts %d" % (nring, ntri, len(TF) * 2, len(V)))
    return ob
