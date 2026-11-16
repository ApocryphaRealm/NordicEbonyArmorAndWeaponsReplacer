import os, sys
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); R = os.path.join(HERE, "render")
CL = os.path.join(os.path.dirname(HERE), "closeups"); os.makedirs(CL, exist_ok=True)
F = lambda s: ImageFont.truetype("arialbd.ttf", s)
PAIRS = {"helmet": ("h3d", "h", (60, 380, 1240, 1290), "Helmet neck mail"),
         "cuirass": ("c3d", "c", (60, 150, 1100, 860), "Cuirass shoulder / arm mail")}
for name in sys.argv[1:] or PAIRS:
    job, t, crop, title = PAIRS[name]
    a = Image.open(os.path.join(R, job, t + "1_close.png")).convert("RGB").crop(crop)
    b = Image.open(os.path.join(R, job, t + "3_close.png")).convert("RGB").crop(crop)
    P = 14; W = P + 2 * (a.width + P); H = 84 + a.height + P
    s = Image.new("RGB", (W, H), (34, 34, 36)); d = ImageDraw.Draw(s)
    d.text((P, 12), "Nordic Ebony - %s: option 1 vs modelled 3D links (demo, same camera and light)" % title, fill=(235, 235, 235), font=F(22))
    d.text((P, 52), "Option 1: link material (texture)", fill=(225, 200, 120), font=F(18))
    d.text((2 * P + a.width, 52), "3D links: modelled 4-in-1 rings", fill=(225, 200, 120), font=F(18))
    s.paste(a, (P, 84)); s.paste(b, (2 * P + a.width, 84))
    out = os.path.join(CL, "chain3d-%s.jpg" % name); s.save(out, quality=92); print(out)
