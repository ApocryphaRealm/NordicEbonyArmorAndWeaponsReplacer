r"""DEMO: chain-link material for the Nordic Ebony helmet aventail and cuirass mail (no package change).
in : src_png\<atlas>ebony.png (current TruePBR albedo), <atlas>ebony_rmaos.png, <atlas>_n.png (NordwarUA's normal),
     src_png\orig\<atlas>ebony_m.png (NordwarUA's original environment mask: rings bright, gaps black)
out: out\<atlas>\opt1\  albedo/rmaos (+ the normal, unchanged), out\<atlas>\opt2\ the same + <atlas>ebony_p.png (height)
     masks\<atlas>_mail.png, _ring.png, _height.png for inspection"""
import os, sys, numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter as G
import sys as _s; _s.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import sets
C = sets.get(); HERE = C.work
def rd(p, mode="RGBA"): return np.asarray(Image.open(p).convert(mode), np.float32) / 255
def wr(p, a, mode):
    os.makedirs(os.path.dirname(p), exist_ok=True); Image.fromarray(np.clip(np.round(a * 255), 0, 255).astype(np.uint8), mode).save(p)
def sm(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
# mail UV regions in percent of the atlas (x0, y0, x1, y1), read off NordwarUA's _m atlas
REGIONS = {
    "helm":  [(2, 72, 98, 99)],                                   # the neck aventail under the brow band
    "torso": [(1, 0.5, 10, 16.5), (44, 0.5, 53, 16.5), (23.5, 1.5, 28.5, 16.5),   # mail strips beside the lamellar
              (68, 27.5, 94, 34.5),                                # the mail arc over the pauldron
              (1, 76, 43, 98.5),                                   # the mail skirt round the belt plate
              (68, 59, 99.5, 85)],                                 # the mail horseshoe (shoulder/arm mail)
}
def frankot(nx, ny):
    H, W = nx.shape; fy = np.fft.fftfreq(H)[:, None]; fx = np.fft.fftfreq(W)[None]
    p, q = -nx, -ny
    d = (2j * np.pi) * (fx * np.fft.fft2(p) + fy * np.fft.fft2(q)); den = (2 * np.pi) ** 2 * (fx ** 2 + fy ** 2); den[0, 0] = 1
    Z = d / -den; Z[0, 0] = 0
    return np.real(np.fft.ifft2(Z))
def build(atlas):
    S = C.src
    alb = rd(os.path.join(S, C.alb(atlas) + ".png")); rm = rd(os.path.join(S, C.alb(atlas) + "_rmaos.png"))
    N = rd(os.path.join(S, atlas + "_n.png")); M = rd(C.mfile(atlas), "L")
    H, W = M.shape
    if N.shape[0] != H: N = np.asarray(Image.fromarray((N * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), np.float32) / 255
    k = W / 1024.0
    # 1. MAIL REGION: UV box AND the ring signature - strong ring-scale contrast in his _m relative to its local level
    box = np.zeros((H, W), np.float32)
    for x0, y0, x1, y1 in REGIONS[atlas]: box[int(y0 * H / 100):int(y1 * H / 100), int(x0 * W / 100):int(x1 * W / 100)] = 1
    lm = G(M, 5 * k); hp = M - G(M, 2.5 * k); en = np.sqrt(G(hp * hp, 5 * k))
    ratio = G(en / (lm + 0.05), 6 * k)
    mail = box * sm(ratio, 0.55, 0.68) * sm(lm, 0.06, 0.12)
    mail = G((G(mail, 3 * k) > 0.5).astype(np.float32), 1.5 * k)       # clean, soft 1-2 px edge
    # 2. RINGS vs GAPS: his _m (rings lit, gaps black), contrast-normalised to its local maximum
    lmax = np.maximum(G(M, 4 * k) * 2.2, 0.15)
    ring = sm(M / lmax, 0.28, 0.55)
    # 3. HEIGHT from his normal map (DirectX: green = -y): Frankot-Chellappa integration, high-passed to ring scale,
    #    sign chosen so the rings come out raised; blended with the ring mask so the gaps read as holes
    nx = N[..., 0] * 2 - 1; ny = -(N[..., 1] * 2 - 1); nz = np.maximum(N[..., 2] * 2 - 1, 0.2)
    h = frankot(nx / nz, -ny / nz); h = h - G(h, 6 * k)
    sel = mail > 0.5
    if np.corrcoef(h[sel], ring[sel])[0, 1] < 0: h = -h
    hs = np.clip(h / (3 * h[sel].std() + 1e-6) * 0.5 + 0.5, 0, 1)
    height = np.clip(0.55 * hs + 0.45 * G(ring, 0.7 * k), 0, 1)
    # cavity AO from the relief: below its neighbourhood = occluded
    cav = np.clip(G(height, 3 * k) - height, 0, 1)
    ao_gap = np.clip(1 - cav * 2.2, 0.35, 1) * (1 - 0.55 * (1 - ring))      # gaps 0.25..0.45, ring inner edges ~0.8
    # per-ring variation (a noise at ring size)
    rng = np.random.default_rng(7); nz_ = G(rng.standard_normal((H, W)).astype(np.float32), 3 * k); nz_ = nz_ / (nz_.std() + 1e-6)
    # 4. MATERIAL on the mask
    link_col = np.array([0.42, 0.42, 0.445]) * np.clip(0.85 + 0.25 * (M / lmax), 0.8, 1.15)[..., None]   # sRGB, a step above the plate (0.27)
    gap_col = np.array([0.055, 0.055, 0.06])
    mal = link_col * ring[..., None] + gap_col * (1 - ring[..., None])
    rough = (0.30 + 0.035 * np.clip(nz_, -1.5, 1.5)) * ring + 0.82 * (1 - ring)          # links 0.25..0.35, gaps 0.82
    metal = ring * 1.0 + (1 - ring) * 0.0
    ao = ao_gap
    a = mail[..., None]
    o_alb = alb.copy(); o_alb[..., :3] = alb[..., :3] * (1 - a) + mal * a
    o_rm = rm.copy()
    o_rm[..., 0] = rm[..., 0] * (1 - mail) + rough * mail
    o_rm[..., 1] = rm[..., 1] * (1 - mail) + metal * mail
    o_rm[..., 2] = rm[..., 2] * (1 - mail) + ao * mail
    o_rm[..., 3] = rm[..., 3] * (1 - mail) + 0.5 * mail
    p = 0.5 * (1 - mail) + height * mail                                              # 0.5 = no displacement outside the mail
    O = os.path.join(C.out, atlas)
    for opt in ("opt1", "opt2"):
        wr(os.path.join(O, opt, C.alb(atlas) + ".png"), o_alb, "RGBA"); wr(os.path.join(O, opt, C.alb(atlas) + "_rmaos.png"), o_rm, "RGBA")
        Image.open(os.path.join(S, atlas + "_n.png")).save(os.path.join(O, opt, atlas + "_n.png"))
    wr(os.path.join(O, "opt2", C.alb(atlas) + "_p.png"), p, "L")
    MK = C.masks; os.makedirs(MK, exist_ok=True)
    wr(os.path.join(MK, atlas + "_mail.png"), mail, "L"); wr(os.path.join(MK, atlas + "_ring.png"), ring * mail, "L"); wr(os.path.join(MK, atlas + "_height.png"), p, "L")
    print(atlas, "mail %.1f%% of atlas" % (100 * mail.mean()), "ring share in mail %.2f" % ring[sel].mean(),
          "rough links %.3f..%.3f" % tuple(np.percentile(rough[sel & (ring > 0.9)], [5, 95])), "AO gaps %.2f" % np.median(ao[sel & (ring < 0.1)]))
for a in sys.argv[1:] or ["helm", "torso"]: build(a)
