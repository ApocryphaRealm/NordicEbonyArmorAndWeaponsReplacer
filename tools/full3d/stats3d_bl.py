# blender -b --factory-startup --python stats3d_bl.py -- <demo dir>   -> build\stats3d.json (pynifly counts; skinned
# SSE shapes keep their vertex data in the skin partition, so the BSTriShape header counts read 0)
import bpy, sys, os, json, addon_utils
addon_utils.enable("io_scene_nifly", default_set=True)
from io_scene_nifly.pyn.pynifly import NifFile
H = sys.argv[sys.argv.index("--") + 1]
def shapes(p): return [(s.name, len(s.verts), len(s.tris), len(s.bone_names)) for s in NifFile(p).shapes]
PIECES = {"helmet": (r"NordicEbony\m\helmet_%d.nif", (1, 0)), "cuirass": (r"NordicEbony\m\cuirass_%d.nif", (1, 0)),
          "gauntlets": (r"NordicEbony\m\gauntlets_%d.nif", (1, 0)), "boots": (r"NordicEbony\m\boots_%d.nif", (1, 0)),
          "shield": (r"weapons\ebony\ebonyshield.nif", (None,))}
res = {}
for pc, (rel, ws) in PIECES.items():
    per = {}
    for w in ws:
        r = rel % w if w is not None else rel
        per[w] = (shapes(os.path.join(H, "pkg_snapshot", "meshes", r)), shapes(os.path.join(H, "build", "out", "meshes", r)))
    a, b = per[ws[0]]; added = [s for s in b if "_3D_" in s[0]]
    match = True
    if len(ws) == 2: match = [x[1:3] for x in b] == [x[1:3] for x in per[0][1]]
    res[pc] = dict(shipped_shapes=len(a), shipped_verts=sum(s[1] for s in a), shipped_tris=sum(s[2] for s in a),
                   added_shapes=len(added), added_verts=sum(s[1] for s in added), added_tris=sum(s[2] for s in added),
                   rings_tris=sum(s[2] for s in added if "_Rings_" in s[0]), rings_verts=sum(s[1] for s in added if "_Rings_" in s[0]),
                   raised_tris=sum(s[2] for s in added if "_Raised_" in s[0]), raised_verts=sum(s[1] for s in added if "_Raised_" in s[0]),
                   total_shapes=len(b), total_verts=sum(s[1] for s in b), total_tris=sum(s[2] for s in b), weights_0_1_match=match,
                   originals_unchanged=[x[1:3] for x in b if "_3D_" not in x[0]] == [x[1:3] for x in a] or sorted(x[1:3] for x in b if "_3D_" not in x[0]) == sorted(x[1:3] for x in a),
                   max_shape_verts=max(s[1] for s in b), max_shape_tris=max(s[2] for s in b))
    print("STAT", pc, json.dumps(res[pc]))
json.dump(res, open(os.path.join(H, "build", "stats3d.json"), "w"), indent=1)
