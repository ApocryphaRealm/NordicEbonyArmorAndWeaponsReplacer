r"""Full-3D textures for a set (NSET) -> <work>\build\out\textures\pbr\<folder>\ (DDS):
  helm/torso albedo, rmaos, normal: the mail areas become a dark padded backing (the rings are modelled; backing.py
    out\<at>\opt3); outside the mail the set's own shipped material
  <albedo stem>_p.dds  parallax height (BC4; 0.5 = none) for every feature atlas built (feat\<at>_p.png)
  chainlink.dds / _n / _rmaos  the modelled rings' material:
    ebony     the option-1 link values the flat package ships (albedo 0.42 sRGB, roughness 0.30)
    skyforged the set's own ring texels (median albedo and roughness of NordwarUA's rings in the shipped helm + torso)
  metal 1, AO 1, spec 0.5, a slight per-texel roughness variation.
usage: NSET=<set> py -3 make_tex.py [weapon atlases with a _p map ...]"""
import os, sys, subprocess, numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import sets
C = sets.get(); H = C.work
TC = sets.TEXCONV
OUT = C.texout; WK = os.path.join(C.build, "texwork"); os.makedirs(OUT, exist_ok=True); os.makedirs(WK, exist_ok=True)
def conv(png, fmt, srgb=False):
    a = [TC, "-nologo", "-y", "-f", fmt, "-o", OUT] + (["-srgb"] if srgb else []) + [png]
    r = subprocess.run(a, capture_output=True, text=True)
    nm = os.path.splitext(os.path.basename(png))[0] + ".dds"
    assert r.returncode == 0 and os.path.isfile(os.path.join(OUT, nm)), r.stdout + r.stderr
    print("dds", nm)
for at in ("helm", "torso"):
    src = os.path.join(C.out, at, "opt3")
    conv(os.path.join(src, C.alb(at) + ".png"), "BC7_UNORM_SRGB", True)
    conv(os.path.join(src, C.alb(at) + "_rmaos.png"), "BC7_UNORM")
    conv(os.path.join(src, at + "_n.png"), "BC7_UNORM")
for at in list(sets.ARMOUR) + sys.argv[1:]:
    p = os.path.join(WK, C.alb(at) + "_p.png"); Image.open(os.path.join(C.feat, at + "_p.png")).save(p); conv(p, "BC4_UNORM")
if C.name == "ebony":
    link = [107, 107, 114]; r0 = 0.30
else:
    A = []; R_ = []
    for at in ("helm", "torso"):
        ring = np.asarray(Image.open(os.path.join(C.masks, at + "_ring.png")).convert("L")) > 204
        A.append(np.asarray(Image.open(os.path.join(C.src, C.alb(at) + ".png")).convert("RGB"))[ring])
        R_.append(np.asarray(Image.open(os.path.join(C.src, C.alb(at) + "_rmaos.png")))[ring][:, 0] / 255.0)
    link = [int(round(x)) for x in np.median(np.concatenate(A), 0)]; r0 = float(np.median(np.concatenate(R_)))
print("chainlink albedo", link, "roughness %.3f" % r0)
rng = np.random.default_rng(5); S = 64
alb = np.full((S, S, 4), 255, np.uint8); alb[..., :3] = link
nrm = np.zeros((S, S, 4), np.uint8); nrm[..., :] = [128, 128, 255, 255]
rough = np.clip(r0 + 0.03 * rng.standard_normal((S, S)), r0 - 0.05, r0 + 0.05)
rm = np.stack([rough, np.ones((S, S)), np.ones((S, S)), np.full((S, S), 0.5)], -1)
for nm, a, fmt, srgb in (("chainlink", alb, "BC7_UNORM_SRGB", True), ("chainlink_n", nrm, "BC7_UNORM", False), ("chainlink_rmaos", (rm * 255).round().astype(np.uint8), "BC7_UNORM", False)):
    p = os.path.join(WK, nm + ".png"); Image.fromarray(a, "RGBA").save(p); conv(p, fmt, srgb)
