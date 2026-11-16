import os, sys
from PIL import Image, ImageDraw, ImageFont
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); R = os.path.join(H, "render")
PL = os.path.dirname(H); CL = os.path.join(PL, "closeups"); os.makedirs(CL, exist_ok=True)
F = lambda s: ImageFont.truetype("arialbd.ttf", s)
NAMES = {"helmet": "Helmet", "cuirass": "Cuirass (fur)", "gauntlets": "Gauntlets", "boots": "Boots", "shield": "Shield"}
pairs = []
for p in sys.argv[1:] or NAMES:
    a = Image.open(os.path.join(R, "f3d_" + p, "o1_v.png")).convert("RGB"); b = Image.open(os.path.join(R, "f3d_" + p, "x3_v.png")).convert("RGB")
    P = 14; W = P + 2 * (a.width + P); Hh = 84 + a.height + P
    s = Image.new("RGB", (W, Hh), (34, 34, 36)); d = ImageDraw.Draw(s)
    d.text((P, 12), "Nordic Ebony - %s: shipped vs EXPERIMENTAL full 3D (same camera and light)" % NAMES[p], fill=(235, 235, 235), font=F(22))
    d.text((P, 52), "Now: option 1 (texture + material)", fill=(225, 200, 120), font=F(18))
    d.text((2 * P + a.width, 52), "Experimental: 3D rings, rivets, scales, buckles, straps + parallax", fill=(225, 200, 120), font=F(18))
    s.paste(a, (P, 84)); s.paste(b, (2 * P + a.width, 84))
    out = os.path.join(CL, "full3d-%s.jpg" % p); s.save(out, quality=90); print(out); pairs.append((p, a, b))
if len(pairs) == 5:
    TH = 520; P = 12; cells = []
    for p, a, b in pairs:
        sc = TH / a.height; cells.append((p, a.resize((int(a.width * sc), TH)), b.resize((int(b.width * sc), TH))))
    W = max(P + c[1].width * 2 + 3 * P for c in cells)
    rows = [cells[0:2], cells[2:4], cells[4:5]]
    W = max(sum(c[1].width * 2 + 3 * P for c in r) + P for r in rows)
    Hh = 70 + len(rows) * (TH + 40 + P)
    s = Image.new("RGB", (W, Hh), (34, 34, 36)); d = ImageDraw.Draw(s)
    d.text((P, 14), "Nordic Ebony - full set: shipped (left of each pair) vs EXPERIMENTAL full 3D + parallax (right)", fill=(235, 235, 235), font=F(24))
    y = 64
    for r in rows:
        x = P
        for p, a, b in r:
            d.text((x, y + 6), NAMES[p] + ":  now  |  experimental 3D", fill=(225, 200, 120), font=F(17))
            s.paste(a, (x, y + 36)); s.paste(b, (x + a.width + P, y + 36)); x += a.width * 2 + 3 * P
        y += TH + 40 + P
    out = os.path.join(PL, "ebony-full-3d-demo.jpg"); s.save(out, quality=88); print(out)
