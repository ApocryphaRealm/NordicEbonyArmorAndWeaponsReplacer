import os
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); R = os.path.join(HERE, "render")
PLANS = os.path.dirname(HERE); CL = os.path.join(PLANS, "closeups"); os.makedirs(CL, exist_ok=True)
F = lambda s: ImageFont.truetype("arialbd.ttf", s)
COLS = [("cur", "current"), ("1", "option1-material"), ("2", "option2-material-parallax")]
COLT = ["Current (as built)", "Option 1: link material", "Option 1 + 2: + parallax height"]
ROWS = [("helmet", "h", "close", (60, 420, 1240, 1290), 1, "Helmet neck mail - close-up"),
        ("helmet", "h", "far", None, 2, "Helmet - game distance (170 px render, shown 2x)"),
        ("cuirass", "c", "close", (60, 150, 1100, 860), 1, "Cuirass shoulder / arm mail - close-up"),
        ("cuirass", "c", "far", None, 1, "Cuirass - game distance (560 px tall, shown 1:1)")]
written = []; rows = []
for job, t, view, crop, up, title in ROWS:
    ims = []
    for v, slug in COLS:
        im = Image.open(os.path.join(R, job, "%s%s_%s.png" % (t, v, view))).convert("RGB")
        if crop: im = im.crop(crop)
        if up > 1: im = im.resize((im.width * up, im.height * up), Image.NEAREST)
        p = os.path.join(CL, "chain-%s-%s-%s.jpg" % (job, view, slug)); im.save(p, quality=92); written.append(p); ims.append(im)
    rows.append((title, ims))
CW = 600; PAD = 14; HT = 40
cells = []
for title, ims in rows:
    s = min(CW / ims[0].width, 1.0 if ims[0].width <= CW else CW / ims[0].width); hh = int(ims[0].height * CW / ims[0].width) if ims[0].width > CW else ims[0].height
    cells.append((title, [im.resize((CW, hh), Image.LANCZOS) if im.width > CW else im for im in ims], hh))
W = PAD + 3 * (CW + PAD); H = 70 + sum(HT + c[2] + PAD for c in cells)
sh = Image.new("RGB", (W, H), (34, 34, 36)); d = ImageDraw.Draw(sh)
d.text((PAD, 14), "Nordic Ebony - chain links as black metal (design demo, not in the package)", fill=(235, 235, 235), font=F(24))
for i, c in enumerate(COLT): d.text((PAD + i * (CW + PAD), 46), c, fill=(225, 200, 120), font=F(17))
y = 70
for title, ims, hh in cells:
    d.text((PAD, y + 10), title, fill=(220, 220, 220), font=F(18)); y += HT
    for i, im in enumerate(ims):
        x = PAD + i * (CW + PAD) + (CW - im.width) // 2; sh.paste(im, (x, y))
    y += hh + PAD
out = os.path.join(PLANS, "ebony-chainmail-demo.jpg"); sh.save(out, quality=90)
print(out); [print(p) for p in written]
