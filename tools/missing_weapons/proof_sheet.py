"""Lays proof.py's renders out as one sheet: a row per piece, front / back / three-quarter, labelled."""
import os, sys
from PIL import Image, ImageDraw
SRC, OUT = sys.argv[1:3]
rows = ["mace", "warhammer", "bow", "arrow", "quiver", "mace_1st"]
views = ["front", "back", "tq"]
tw, th = 300, 470
sheet = Image.new("RGB", (len(rows) * tw, len(views) * th + 40), (40, 41, 44)); d = ImageDraw.Draw(sheet)
d.text((8, 8), "Built game NIFs, backface culling ON (a wrong-way face renders see-through) - columns: pieces; rows: front / back / three-quarter", fill=(230, 230, 230))
for c, r in enumerate(rows):
    for k, v in enumerate(views):
        p = os.path.join(SRC, "%s_%s.png" % (r, v))
        if os.path.isfile(p):
            im = Image.open(p).convert("RGB"); im.thumbnail((tw, th)); sheet.paste(im, (c * tw + (tw - im.width) // 2, 40 + k * th))
        d.text((c * tw + 6, 44 + k * th), "%s - %s" % (r, v), fill=(255, 220, 120))
sheet.save(OUT, quality=90)
print("sheet", OUT, sheet.size)
