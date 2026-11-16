r"""Full-3D demo, texture side: find the parts to model or parallax on each atlas, from NordwarUA's own maps.
out: feat\<atlas>_label.png (uint16 in a .npy too: feat\<atlas>_label.npy), feat\<atlas>_hpx.npy (raise height in atlas
pixels), feat\<atlas>_kinds.json (label -> kind), feat\<atlas>_p.png (parallax height, 0.5 = none), overlay jpg.
kinds: rivet (dome over the dot), scale (lamellar tile, lifted at its lower edge in Blender), buckle (raised frame),
strap (raised leather strip). Gold knotwork, carved panels, medallions -> parallax only (the _p map)."""
import os, sys, json, numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.ndimage import gaussian_filter as G
from skimage.measure import label, regionprops
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sets
C = sets.get(); H0 = C.work; S = C.src; OUT = C.feat
# armour atlases share one sculpt across sets; a set whose ornament is not gold (steel) takes the gilt mask of the set
# named in gold_from; weapon atlases have their own sculpt per set, so they always use their own albedo
os.makedirs(OUT, exist_ok=True)
def rd(p, mode="RGBA"): return np.asarray(Image.open(p).convert(mode), np.float32) / 255
def sm(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
def frankot(nx, ny):
    Hh, W = nx.shape; fy = np.fft.fftfreq(Hh)[:, None]; fx = np.fft.fftfreq(W)[None]
    d = (2j * np.pi) * (fx * np.fft.fft2(-nx) + fy * np.fft.fft2(-ny)); den = (2 * np.pi) ** 2 * (fx ** 2 + fy ** 2); den[0, 0] = 1
    Z = d / -den; Z[0, 0] = 0; return np.real(np.fft.ifft2(Z))
def hsv_gold(rgb):
    mx = rgb.max(-1); mn = rgb.min(-1); s = (mx - mn) / np.maximum(mx, 1e-4)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    hue = np.degrees(np.arctan2(np.sqrt(3) * (g - b), 2 * r - g - b)) % 360
    return (hue > 18) & (hue < 55) & (s > 0.35) & (mx > 0.35)
LAMELLAR = sets.LAMELLAR
def run(at):
    alb = rd(os.path.join(S, C.alb(at) + ".png")); rm = rd(os.path.join(S, C.alb(at) + "_rmaos.png"))
    N = rd(os.path.join(S, C.nrm(at) + ".png")); M = rd(C.mfile(at), "L")
    weapon = at not in sets.ARMOUR
    galb = alb
    if C.gold_from != "self" and not weapon:
        G_ = sets.get(C.gold_from); galb = rd(os.path.join(G_.src, G_.alb(at) + ".png"))
    Hh, W = M.shape
    if N.shape[0] != Hh: N = np.asarray(Image.fromarray((N * 255).astype(np.uint8)).resize((W, Hh), Image.BILINEAR), np.float32) / 255
    if alb.shape[0] != Hh: alb = np.asarray(Image.fromarray((alb * 255).astype(np.uint8)).resize((W, Hh), Image.BILINEAR), np.float32) / 255
    if galb.shape[0] != Hh: galb = np.asarray(Image.fromarray((galb * 255).astype(np.uint8)).resize((W, Hh), Image.BILINEAR), np.float32) / 255
    if rm.shape[0] != Hh: rm = np.asarray(Image.fromarray((rm * 255).astype(np.uint8)).resize((W, Hh), Image.BILINEAR), np.float32) / 255
    k = W / 1024.0
    mp = C.mail(at)
    mail = (rd(mp, "L") > 0.5) if os.path.isfile(mp) else np.zeros((Hh, W), bool)
    metal = rm[..., 1] > 0.5; cover = alb[..., :3].max(-1) > 0.03
    nx = N[..., 0] * 2 - 1; ny = -(N[..., 1] * 2 - 1); nz = np.maximum(N[..., 2] * 2 - 1, 0.2)
    h = frankot(nx / nz, -ny / nz); h = h - G(h, 10 * k)
    # sign: the gold knotwork and the rivet domes are raised in his sculpt
    gold = hsv_gold(galb[..., :3]) & cover
    if gold.sum() > 100 and h[gold].mean() < h[cover & ~gold].mean(): h = -h
    hn = h / (h[cover].std() + 1e-6)
    lab = np.zeros((Hh, W), np.int32); hpx = np.zeros((Hh, W), np.float32); kinds = {}; nid = 0
    lam = np.zeros((Hh, W), bool)
    for x0, y0, x1, y1 in LAMELLAR.get(at, []): lam[int(y0 * Hh / 100):int(y1 * Hh / 100), int(x0 * W / 100):int(x1 * W / 100)] = True
    # --- SCALES (torso lamellar): bright tiles of his _m, split at the dark gaps
    if lam.any():
        lm = G(M, 6 * k); tile = lam & (M > np.maximum(lm * 0.75, 0.12)) & cover
        tile = ndi.binary_opening(tile, iterations=max(1, int(round(1 * k))))
        tile = ndi.binary_fill_holes(tile)
        L = label(tile)
        for rp in regionprops(L):
            if not (60 * k * k <= rp.area <= 2500 * k * k): continue
            nid += 1; sl = L == rp.label; lab[sl] = nid; kinds[nid] = "scale"
            dt = ndi.distance_transform_edt(sl[rp.bbox[0]:rp.bbox[2], rp.bbox[1]:rp.bbox[3]])
            hpx[rp.bbox[0]:rp.bbox[2], rp.bbox[1]:rp.bbox[3]][dt > 0] = (2.2 * k * sm(dt, 0, 2.5 * k))[dt > 0]
    # --- BUCKLES: frame-shaped components (a hole, thin) - gold frames, or bright steel frames in his _m
    cand = (gold | (M > 0.55)) & cover & ~mail & ~lam
    L = label(ndi.binary_closing(cand, iterations=1))
    for rp in regionprops(L):
        h_, w_ = rp.bbox[2] - rp.bbox[0], rp.bbox[3] - rp.bbox[1]
        if rp.euler_number <= 0 and 10 * k <= max(h_, w_) <= 70 * k and min(h_, w_) >= 7 * k and rp.solidity < 0.55 and rp.area < 900 * k * k:
            sl = (L == rp.label) & (lab == 0)
            if sl.sum() < 20 * k * k: continue
            # a buckle sits on leather: the ring of texels just outside it is mostly NOT metal (a medallion ring or
            # gilt wear on a plate is surrounded by metal)
            ring_ = ndi.binary_dilation(L == rp.label, iterations=int(3 * k)) & ~ndi.binary_dilation(L == rp.label, iterations=1) & cover
            if ring_.sum() and (metal[ring_] & ~gold[ring_]).mean() > 0.45: continue
            nid += 1; lab[sl] = nid; kinds[nid] = "buckle"
            sub = sl[rp.bbox[0]:rp.bbox[2], rp.bbox[1]:rp.bbox[3]]; dt = ndi.distance_transform_edt(sub)
            hh = 2.0 * k * sm(dt, 0, 1.2 * k); hpx[rp.bbox[0]:rp.bbox[2], rp.bbox[1]:rp.bbox[3]][sub] = hh[sub]
    # --- RIVETS / STUDS: round domes in his height (scale-normalised LoG), plus small round gold dots
    import domes
    gl = label(gold & ~mail); golddot = np.zeros_like(gold)
    for rp in regionprops(gl):
        h_, w_ = rp.bbox[2] - rp.bbox[0], rp.bbox[3] - rp.bbox[1]
        if 3 * k <= max(h_, w_) <= 14 * k and rp.solidity > 0.8 and max(h_, w_) / max(1, min(h_, w_)) < 1.5: golddot[gl == rp.label] = True
    knot = ndi.binary_dilation(gold & ~golddot, iterations=int(3 * k))
    pk, _ = domes.find(nx, N[..., 1] * 2 - 1, metal, cover, mail | lam | knot | (lab > 0), k, thr=0.5, sign=1.0)
    if weapon:
        # weapons (2026-11-16, full-3D Skyforged): the steel weapons' carved knotwork is not gilt, so the gold exclusion
        # misses it and every strand crossing scores as a dome. A real rivet sits on a smooth plate or wrap: keep a
        # candidate only if the ring around it (1.8r..3.2r) is quiet in the normal map (median tilt below WEAPON_QUIET)
        tilt = np.sqrt(nx ** 2 + (N[..., 1] * 2 - 1) ** 2); keep = []; q = float(os.environ.get("WEAPON_QUIET", "0.12"))
        for y, x, r, sc in pk:
            R2 = int(np.ceil(3.2 * r)); y0, y1, x0, x1 = max(0, y - R2), min(Hh, y + R2 + 1), max(0, x - R2), min(W, x + R2 + 1)
            yy_, xx_ = np.mgrid[y0:y1, x0:x1]; d_ = np.sqrt((yy_ - y) ** 2 + (xx_ - x) ** 2); ann = (d_ >= 1.8 * r) & (d_ <= 3.2 * r) & cover[y0:y1, x0:x1]
            if ann.sum() > 8 and np.median(tilt[y0:y1, x0:x1][ann]) < q: keep.append((y, x, r, sc))
        print(at, "weapon dome candidates", len(pk), "kept", len(keep)); pk = keep
    blobs = [(y, x, r / 1.414) for y, x, r, sc in pk]
    for rp in (regionprops(label(golddot)) if not weapon else []):   # weapons: gilt bits in knot panels are not studs
        h_, w_ = rp.bbox[2] - rp.bbox[0], rp.bbox[3] - rp.bbox[1]
        if not any(abs(rp.centroid[0] - b[0]) < 3 * k and abs(rp.centroid[1] - b[1]) < 3 * k for b in blobs): blobs.append((rp.centroid[0], rp.centroid[1], max(h_, w_) / 2 / 1.414))
    yy, xx = np.mgrid[0:Hh, 0:W]; nr = 0
    for y, x, s_ in blobs:
        r = max(2.0 * k, min(s_ * 1.414 * 1.15, 7 * k)); y0, y1 = int(max(0, y - r - 1)), int(min(Hh, y + r + 2)); x0, x1 = int(max(0, x - r - 1)), int(min(W, x + r + 2))
        d = np.sqrt((yy[y0:y1, x0:x1] - y) ** 2 + (xx[y0:y1, x0:x1] - x) ** 2); disc = (d <= r) & (lab[y0:y1, x0:x1] == 0)
        if disc.sum() < 6 or not cover[int(y), int(x)]: continue
        nid += 1; nr += 1; lab[y0:y1, x0:x1][disc] = nid; kinds[nid] = "rivet"
        hpx[y0:y1, x0:x1][disc] = 0.75 * r * np.sqrt(np.clip(1 - (d[disc] / r) ** 2, 0, 1))
    # --- STRAPS: elongated, non-metal UV islands (leather belts and straps), raised with a rounded edge
    isl = label(ndi.binary_opening(cover, iterations=2))
    for rp in (regionprops(isl) if not weapon else []):   # weapons: a grip wrap is a whole island, already modelled
        if rp.area < 400 * k * k or rp.axis_minor_length <= 0: continue
        sl = isl == rp.label
        nm = 1 - metal[sl].mean(); el = rp.axis_major_length / rp.axis_minor_length
        if nm > 0.6 and el > 2.6 and rp.axis_minor_length < 130 * k and not (gold[sl].mean() > 0.2) and not mail[sl].any():
            free = sl & (lab == 0)
            nid += 1; lab[free] = nid; kinds[nid] = "strap"
            sub = free[rp.bbox[0]:rp.bbox[2], rp.bbox[1]:rp.bbox[3]]; dt = ndi.distance_transform_edt(sub)
            hpx[rp.bbox[0]:rp.bbox[2], rp.bbox[1]:rp.bbox[3]][sub] = (2.5 * k * sm(dt, 0, 4 * k))[sub]
    # --- PARALLAX (_p): carved panels, gold knotwork, medallions = the metal outside mail/scales/modelled parts
    par = metal & cover & ~mail & (lab == 0) & ~lam
    par_s = G(par.astype(np.float32), 1.0 * k)
    p = np.clip(0.5 + 0.18 * np.clip(hn, -2.5, 2.5) * par_s, 0, 1)
    np.save(os.path.join(OUT, at + "_label.npy"), lab.astype(np.int32)); np.save(os.path.join(OUT, at + "_hpx.npy"), hpx)
    json.dump({str(a): b for a, b in kinds.items()}, open(os.path.join(OUT, at + "_kinds.json"), "w"))
    Image.fromarray(np.round(p * 255).astype(np.uint8), "L").save(os.path.join(OUT, at + "_p.png"))
    # overlay: rivet red, scale cyan, buckle yellow, strap magenta, parallax green tint
    ov = alb[..., :3].copy() * 0.6
    col = {"rivet": (1, 0.1, 0.1), "scale": (0.1, 0.9, 1), "buckle": (1, 0.95, 0.1), "strap": (1, 0.2, 1)}
    kk = np.zeros(nid + 1, np.int32); names = list(col)
    for a, b in kinds.items(): kk[a] = names.index(b) + 1
    km = kk[lab]
    for i, n in enumerate(names):
        ov[km == i + 1] = ov[km == i + 1] * 0.3 + np.array(col[n]) * 0.7
    ov[..., 1] = np.clip(ov[..., 1] + 0.25 * par_s * (km == 0), 0, 1)
    Image.fromarray(np.round(ov * 255).astype(np.uint8)).resize((1200, 1200), Image.BILINEAR).save(os.path.join(OUT, at + "_overlay.jpg"), quality=88)
    cnt = {n: sum(1 for v in kinds.values() if v == n) for n in names}
    print(at, cnt, "parallax %.1f%%" % (100 * par.mean()))
for a in sys.argv[1:] or ["helm", "torso", "bgpb", "shield"]: run(a)
