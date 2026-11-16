r"""Chain-link material for the Nordic Ebony helmet aventail and the cuirass mail (the owner, 2026-11-15 23:52: option 1,
material only). From the demo in 4. plans\nordic-carved-missing-weapons-20261115\chainmail-demo\tools\chainmail.py.

Called by truepbr.build_textures for the ebony helm and torso atlases, after recolour_black.pbr_maps:
  in : our TruePBR albedo and RMAOS (floats 0..1), NordwarUA's own environment mask _m (rings bright, gaps black) and his
       normal map (DirectX), all at the atlas size
  out: the albedo and RMAOS with the mail region re-materialled; nothing outside the mail is touched
  links: albedo 0.42/0.42/0.445 x his _m detail, metal 1, roughness 0.25..0.35
  gaps : albedo 0.055, metal 0, roughness 0.82, AO from the cavities of a relief integrated from his normal map
  specular 0.5 throughout. The normal map ships unchanged; no height map (option 2 was not chosen).
"""
import numpy as np
from scipy.ndimage import gaussian_filter as G


def _sm(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


# mail UV regions in percent of the atlas (x0, y0, x1, y1), read off NordwarUA's _m atlas
REGIONS = {
    "helm":  [(2, 72, 98, 99)],                                   # the neck aventail under the brow band
    "torso": [(1, 0.5, 10, 16.5), (44, 0.5, 53, 16.5), (23.5, 1.5, 28.5, 16.5),   # mail strips beside the lamellar
              (68, 27.5, 94, 34.5),                                # the mail arc over the pauldron
              (1, 76, 43, 98.5),                                   # the mail skirt round the belt plate
              (68, 59, 99.5, 85)],                                 # the mail horseshoe (shoulder/arm mail)
}


def atlas_of(name):
    """'helm' / 'torso' for the ebony helm and torso diffuse names, else None"""
    n = name.lower()
    if n.startswith("helmebony"):
        return "helm"
    if n.startswith("torsoebony"):
        return "torso"
    return None


def _frankot(nx, ny):
    H, W = nx.shape; fy = np.fft.fftfreq(H)[:, None]; fx = np.fft.fftfreq(W)[None]
    p, q = -nx, -ny
    d = (2j * np.pi) * (fx * np.fft.fft2(p) + fy * np.fft.fft2(q)); den = (2 * np.pi) ** 2 * (fx ** 2 + fy ** 2); den[0, 0] = 1
    Z = d / -den; Z[0, 0] = 0
    return np.real(np.fft.ifft2(Z))


def apply(atlas, alb, rm, M, N):
    """alb HxWx3, rm HxWx4, M HxW (his _m), N HxWx3 (his normal, same size) -> (alb, rm, stats)"""
    H, W = M.shape
    k = W / 1024.0
    # 1. MAIL REGION: UV box AND the ring signature - strong ring-scale contrast in his _m relative to its local level
    box = np.zeros((H, W), np.float32)
    for x0, y0, x1, y1 in REGIONS[atlas]:
        box[int(y0 * H / 100):int(y1 * H / 100), int(x0 * W / 100):int(x1 * W / 100)] = 1
    lm = G(M, 5 * k); hp = M - G(M, 2.5 * k); en = np.sqrt(G(hp * hp, 5 * k))
    ratio = G(en / (lm + 0.05), 6 * k)
    mail = box * _sm(ratio, 0.55, 0.68) * _sm(lm, 0.06, 0.12)
    mail = G((G(mail, 3 * k) > 0.5).astype(np.float32), 1.5 * k)       # clean, soft 1-2 px edge
    # 2. RINGS vs GAPS: his _m, contrast-normalised to its local maximum
    lmax = np.maximum(G(M, 4 * k) * 2.2, 0.15)
    ring = _sm(M / lmax, 0.28, 0.55)
    # 3. relief from his normal map (Frankot-Chellappa), high-passed to ring scale, rings raised; only for the AO
    nx = N[..., 0] * 2 - 1; ny = -(N[..., 1] * 2 - 1); nz = np.maximum(N[..., 2] * 2 - 1, 0.2)
    h = _frankot(nx / nz, -ny / nz); h = h - G(h, 6 * k)
    sel = mail > 0.5
    if sel.sum() < 64:
        raise SystemExit("chainmail: no mail found on the %s atlas - NordwarUA's _m changed?" % atlas)
    if np.corrcoef(h[sel], ring[sel])[0, 1] < 0:
        h = -h
    hs = np.clip(h / (3 * h[sel].std() + 1e-6) * 0.5 + 0.5, 0, 1)
    height = np.clip(0.55 * hs + 0.45 * G(ring, 0.7 * k), 0, 1)
    cav = np.clip(G(height, 3 * k) - height, 0, 1)
    ao = np.clip(1 - cav * 2.2, 0.35, 1) * (1 - 0.55 * (1 - ring))
    rng = np.random.default_rng(7); nz_ = G(rng.standard_normal((H, W)).astype(np.float32), 3 * k); nz_ = nz_ / (nz_.std() + 1e-6)
    # 4. MATERIAL on the mask
    link_col = np.array([0.42, 0.42, 0.445]) * np.clip(0.85 + 0.25 * (M / lmax), 0.8, 1.15)[..., None]
    gap_col = np.array([0.055, 0.055, 0.06])
    mal = link_col * ring[..., None] + gap_col * (1 - ring[..., None])
    rough = (0.30 + 0.035 * np.clip(nz_, -1.5, 1.5)) * ring + 0.82 * (1 - ring)
    metal = ring
    a = mail[..., None]
    o_alb = alb * (1 - a) + mal * a
    o_rm = rm.copy()
    o_rm[..., 0] = rm[..., 0] * (1 - mail) + rough * mail
    o_rm[..., 1] = rm[..., 1] * (1 - mail) + metal * mail
    o_rm[..., 2] = rm[..., 2] * (1 - mail) + ao * mail
    o_rm[..., 3] = rm[..., 3] * (1 - mail) + 0.5 * mail
    stats = "mail %.1f%% of atlas, ring share %.2f, link roughness %.3f..%.3f, gap AO %.2f" % (
        100 * mail.mean(), ring[sel].mean(), *np.percentile(rough[sel & (ring > 0.9)], [5, 95]),
        np.median(ao[sel & (ring < 0.1)]))
    return np.clip(o_alb, 0, 1), np.clip(o_rm, 0, 1), stats
