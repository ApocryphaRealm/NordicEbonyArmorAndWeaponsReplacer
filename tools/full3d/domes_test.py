import os, sys, numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import domes
H0 = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); S = os.path.join(H0, "src_png")
at = sys.argv[1]; thr = float(sys.argv[2]) if len(sys.argv) > 2 else 0.42
rd = lambda p, m="RGBA": np.asarray(Image.open(p).convert(m), np.float32) / 255
alb = rd(os.path.join(S, at + "ebony.png")); rm = rd(os.path.join(S, at + "ebony_rmaos.png")); N = rd(os.path.join(S, at + "_n.png"))
W = N.shape[1]; k = W / 1024
nx = N[..., 0] * 2 - 1; nyd = N[..., 1] * 2 - 1
metal = rm[..., 1] > 0.5; cover = alb[..., :3].max(-1) > 0.03
mp = os.path.join(H0, "masks", at + "_mail.png"); ex = (rd(mp, "L") > 0.5) if os.path.isfile(mp) else np.zeros(metal.shape, bool)
for sg in (1.0, -1.0):
    pk, b = domes.find(nx, nyd, metal, cover, ex, k, thr=thr, sign=sg)
    print(at, "sign", sg, "peaks", len(pk))
    im = Image.fromarray((alb[..., :3] * 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    for y, x, r, s in pk: d.ellipse([x - r, y - r, x + r, y + r], outline=(255, 0, 0), width=max(1, int(k)))
    im.resize((1200, 1200)).save(os.path.join(H0, "feat", "domes_%s_%+d.jpg" % (at, int(sg))), quality=88)
