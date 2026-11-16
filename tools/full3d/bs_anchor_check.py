# blender -b --factory-startup --python bs_anchor_check.py -- <out.nif> <anchors.json>
# each exported added vertex must sit near its anchor point (barycentric point of its source triangle): proves the export
# kept the added shapes' vertex order and count, which the slider data indexes
import sys, json, numpy as np, addon_utils
addon_utils.enable("io_scene_nifly", default_set=True)
from io_scene_nifly.pyn.pynifly import NifFile
a = sys.argv[sys.argv.index("--") + 1:]; nf = NifFile(a[0]); A = json.load(open(a[1]))
V = {s.name: np.array(s.verts) for s in nf.shapes}
for name, anc in sorted(A.items()):
    if name not in V: print("ANCHOR", name, "NOT IN NIF"); continue
    v = V[name]
    if len(v) != len(anc): print("ANCHOR", name, "count", len(v), "vs", len(anc)); continue
    P = np.array([np.array(b) @ V[s][idx] for s, idx, b in anc])
    d = np.linalg.norm(v - P, axis=1)
    print("ANCHOR %-36s n=%6d  dist median %.3f  p99 %.3f  max %.3f" % (name, len(v), np.median(d), np.percentile(d, 99), d.max()))
