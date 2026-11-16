r"""Turn feat\<atlas>_label/_hpx/_kinds into Blender-ready recipes (no PIL/scipy needed inside Blender):
feat\<atlas>_recipe.npz: rivets (N x 3: x_px, y_px, r_px); patch_* arrays: per patch vertex (x_px, y_px, h_px, patch id),
faces (a, b, c, patch id) and patch kind codes; mail mask as uint8 (if any). Atlas pixel coords: x right, y DOWN."""
import os, sys, json, numpy as np
from PIL import Image
import sys as _s; _s.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import sets
C = sets.get(); H0 = C.work; F = C.feat
KIND = {"scale": 1, "buckle": 2, "strap": 3}
def run(at):
    lab = np.load(os.path.join(F, at + "_label.npy")); hpx = np.load(os.path.join(F, at + "_hpx.npy"))
    kinds = {int(a): b for a, b in json.load(open(os.path.join(F, at + "_kinds.json"))).items()}
    Hh, W = lab.shape; k = W / 1024.0
    from scipy import ndimage as ndi
    objs = ndi.find_objects(lab)
    rivets = []; PV = []; PF = []; PK = []; pid = 0
    for lid, kind in sorted(kinds.items()):
        sl = objs[lid - 1]
        if sl is None: continue
        m = lab[sl] == lid
        if kind == "rivet":
            ys, xs = np.nonzero(m); r = np.sqrt(m.sum() / np.pi)
            rivets.append((xs.mean() + sl[1].start + 0.5, ys.mean() + sl[0].start + 0.5, r)); continue
        h, w = m.shape
        step = {"scale": max(1.5 * k, max(h, w) / 6.0), "buckle": 1.0 * k, "strap": 5.0 * k}[kind]
        gy = np.arange(0, h + 1e-6, step); gx = np.arange(0, w + 1e-6, step)
        if gy[-1] < h - 1: gy = np.append(gy, h - 1)
        if gx[-1] < w - 1: gx = np.append(gx, w - 1)
        # a grid point is inside if the texel under it is the feature
        iy = np.clip(np.round(gy).astype(int), 0, h - 1); ix = np.clip(np.round(gx).astype(int), 0, w - 1)
        ins = m[iy][:, ix]
        idx = -np.ones(ins.shape, int); n0 = len(PV); cnt = 0
        for a in range(len(gy)):
            for b in range(len(gx)):
                if ins[a, b]:
                    idx[a, b] = n0 + cnt; cnt += 1
                    PV.append((gx[b] + sl[1].start + 0.5, gy[a] + sl[0].start + 0.5, float(hpx[sl][iy[a], ix[b]]), pid))
        nf = 0
        for a in range(len(gy) - 1):
            for b in range(len(gx) - 1):
                q = idx[a, b], idx[a, b + 1], idx[a + 1, b + 1], idx[a + 1, b]
                if min(q) >= 0: PF += [(q[0], q[1], q[2], pid), (q[0], q[2], q[3], pid)]; nf += 2
        if nf == 0:
            del PV[n0:]; continue
        PK.append(KIND[kind]); pid += 1
    out = dict(rivets=np.array(rivets, np.float32).reshape(-1, 3), pv=np.array(PV, np.float32).reshape(-1, 4),
               pf=np.array(PF, np.int64).reshape(-1, 4), pk=np.array(PK, np.int32), size=np.array([W, Hh]))
    mp = C.mail(at)
    if os.path.isfile(mp): out["mail"] = (np.asarray(Image.open(mp).convert("L")) > 127).astype(np.uint8)
    np.savez_compressed(os.path.join(F, at + "_recipe.npz"), **out)
    print(at, "rivets", len(rivets), "patches", pid, "patch verts", len(PV), "patch tris", len(PF))
for a in sys.argv[1:] or ["helm", "torso", "bgpb", "shield"]: run(a)
