r"""Before/after sheets of a set's full-3D build (NSET) from render_set.py's renders:
  closeups\full3d-<set>-<piece>.jpg  shipped | full 3D, front view, same camera and light
  <plans>\<set>-full-3d-set-sheet.jpg  every piece, shipped | 3D pairs
Triangle counts come from build\stats_full.json (first file of the piece)."""
import os, sys, json
from PIL import Image, ImageDraw, ImageFont
T = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, T)
import sets
C = sets.get(); PL = os.path.dirname(sets.ROOT); CL = os.path.join(PL, "closeups"); os.makedirs(CL, exist_ok=True)
F = lambda s: ImageFont.truetype("arialbd.ttf", s)
ST = json.load(open(os.path.join(C.build, "stats_full.json")))
BG = (34, 34, 36); TX = (235, 235, 235); AC = (225, 200, 120)


def tris(piece):
    pc = next(p for p in C.pieces if p.get("render") == piece); f = ST[pc["name"]]["files"][0]; return f["shipped_tris"], f["built_tris"]


pairs = []
for pc in [p for p in C.pieces if p.get("render")]:
    p = pc["render"]; d = os.path.join(C.render, "f3d_" + p)
    if not os.path.isfile(os.path.join(d, "x3_v.png")): print("no render", p); continue
    a = Image.open(os.path.join(d, "o1_v.png")).convert("RGB"); b = Image.open(os.path.join(d, "x3_v.png")).convert("RGB")
    s0, s1 = tris(p); P = 14; horiz = a.width > a.height * 1.6
    if horiz:   # weapons: one above the other
        W = P * 2 + a.width; Hh = 60 + 2 * (a.height + 40) + P
        s = Image.new("RGB", (W, Hh), BG); dr = ImageDraw.Draw(s)
        dr.text((P, 12), "%s - %s: shipped vs full 3D (same camera and light)" % (C.label, p), fill=TX, font=F(22))
        dr.text((P, 56), "Shipped (%d triangles)" % s0, fill=AC, font=F(18)); s.paste(a, (P, 84))
        y = 84 + a.height + 8; dr.text((P, y), "Full 3D: raised studs + parallax on the carving (%d triangles)" % s1, fill=AC, font=F(18)); s.paste(b, (P, y + 28))
    else:
        W = P + 2 * (a.width + P); Hh = 84 + a.height + P
        s = Image.new("RGB", (W, Hh), BG); dr = ImageDraw.Draw(s)
        dr.text((P, 12), "%s - %s: shipped vs full 3D (front, same camera and light)" % (C.label, p), fill=TX, font=F(22))
        dr.text((P, 52), "Shipped: %d triangles" % s0, fill=AC, font=F(18))
        dr.text((2 * P + a.width, 52), "Full 3D: %d triangles" % s1, fill=AC, font=F(18))
        s.paste(a, (P, 84)); s.paste(b, (2 * P + a.width, 84))
    out = os.path.join(CL, "full3d-%s-%s.jpg" % (C.name, p)); s.save(out, quality=90); print(out); pairs.append((p, a, b, horiz, s0, s1))

# whole-set sheet: armour pairs in rows of three, weapons stacked below
TH = 460; P = 12; arm = [x for x in pairs if not x[3]]; wep = [x for x in pairs if x[3]]
cells = []
for p, a, b, h, s0, s1 in arm:
    sc = TH / a.height; cells.append((p, a.resize((int(a.width * sc), TH)), b.resize((int(b.width * sc), TH)), s0, s1))
rows = [cells[i:i + 3] for i in range(0, len(cells), 3)]
WW = 1700
for r in rows: WW = max(WW, sum(c[1].width * 2 + 3 * P for c in r) + P)
wc = []
for p, a, b, h, s0, s1 in wep:
    sc = (WW / 2 - 2 * P) / a.width; wc.append((p, a.resize((int(a.width * sc), int(a.height * sc))), b.resize((int(b.width * sc), int(a.height * sc))), s0, s1))
wrows = [wc[i:i + 2] for i in range(0, len(wc), 2)]
wh = (wc[0][1].height * 2 + 70) if wc else 0
Hh = 70 + len(rows) * (TH + 48 + P) + len(wrows) * (wh + P) + 40
s = Image.new("RGB", (WW, Hh), BG); dr = ImageDraw.Draw(s)
tot = json.load(open(os.path.join(C.build, "stats_full.json")))
dr.text((P, 14), "%s - full set: shipped (left / top of each pair) vs full 3D + parallax (right / below)" % C.label, fill=TX, font=F(26))
y = 64
for r in rows:
    x = P
    for p, a, b, s0, s1 in r:
        dr.text((x, y + 2), p, fill=AC, font=F(17)); dr.text((x, y + 22), "shipped %s | 3D %s tris" % (f"{s0:,}", f"{s1:,}"), fill=TX, font=F(14))
        s.paste(a, (x, y + 44)); s.paste(b, (x + a.width + P, y + 44)); x += a.width * 2 + 3 * P
    y += TH + 48 + P
for r in wrows:
    x = P
    for p, a, b, s0, s1 in r:
        dr.text((x, y + 4), "%s:  shipped %d  |  3D %d triangles" % (p, s0, s1), fill=AC, font=F(17))
        s.paste(a, (x, y + 30)); s.paste(b, (x, y + 34 + a.height)); x += int(WW / 2)
    y += wh + P
out = os.path.join(PL, "%s-full-3d-set-sheet.jpg" % C.name); s.save(out, quality=88); print(out)
