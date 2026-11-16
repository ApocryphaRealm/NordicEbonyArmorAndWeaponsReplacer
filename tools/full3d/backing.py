# option-3 demo backing: the aventail's textured mail is replaced by a dark padded backing (the rings are modelled)
import os, numpy as np
from PIL import Image
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import sets
C = sets.get(); H = C.work
AT = sys.argv[1] if len(sys.argv) > 1 else "helm"
S = C.src; O = os.path.join(C.out, AT, "opt3"); os.makedirs(O, exist_ok=True)
m = np.asarray(Image.open(C.mail(AT)), np.float32)[..., None] / 255
a = np.asarray(Image.open(os.path.join(S, C.alb(AT) + ".png")).convert("RGBA"), np.float32) / 255
r = np.asarray(Image.open(os.path.join(S, C.alb(AT) + "_rmaos.png")).convert("RGBA"), np.float32) / 255
n = np.asarray(Image.open(os.path.join(S, AT + "_n.png")).convert("RGBA"), np.float32) / 255
a[..., :3] = a[..., :3] * (1 - m) + np.array([0.05, 0.05, 0.055]) * m
r = r * (1 - m) + np.array([0.85, 0.0, 1.0, 0.5]) * m
n[..., :3] = n[..., :3] * (1 - m) + np.array([0.5, 0.5, 1.0]) * m
for nm, x in ((C.alb(AT), a), (C.alb(AT) + "_rmaos", r), (AT + "_n", n)):
    Image.fromarray(np.clip(np.round(x * 255), 0, 255).astype(np.uint8), "RGBA").save(os.path.join(O, nm + ".png"))
print("ok")
