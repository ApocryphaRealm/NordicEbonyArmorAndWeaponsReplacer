# blender -b --factory-startup --python stats_set.py -- <set>  -> <work>\build\stats_full.json: per piece and file, shipped
# vs built shape / vertex / triangle counts (pynifly read-back), whether the originals are unchanged, _0/_1 added counts equal
import bpy, sys, os, json, addon_utils
addon_utils.enable("io_scene_nifly", default_set=True)
from io_scene_nifly.pyn.pynifly import NifFile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import sets
C = sets.get(sys.argv[sys.argv.index("--") + 1])
def shapes(p): return [(s.name, len(s.verts), len(s.tris)) for s in NifFile(p).shapes]
res = {}; TOT = dict(shipped=0, built=0)
for pc in C.pieces:
    opt = pc.get("opt"); per = []
    for rel in pc["files"]:
        a = shapes(C.snap_of(rel, opt)); b = shapes(C.out_of(rel, opt)); add = [s for s in b if "_3D_" in s[0]]
        per.append(dict(file=rel, shipped_tris=sum(s[2] for s in a), built_tris=sum(s[2] for s in b), added_tris=sum(s[2] for s in add),
                        rings_tris=sum(s[2] for s in add if "_Rings_" in s[0]), raised_tris=sum(s[2] for s in add if "_Raised_" in s[0]),
                        added_shapes=len(add), originals_unchanged=sorted(x[1:] for x in b if "_3D_" not in x[0]) == sorted(x[1:] for x in a),
                        max_shape_verts=max(s[1] for s in b), max_shape_tris=max(s[2] for s in b)))
    same = len(set((p["added_tris"], p["added_shapes"]) for p in per)) == 1
    res[pc["name"]] = dict(files=per, weights_match=same, opt=opt)
    f0 = per[0]
    if not opt: TOT["shipped"] += f0["shipped_tris"]; TOT["built"] += f0["built_tris"]
    print("STAT %-24s shipped %7d  built %8d  added %8d (rings %7d raised %6d)  orig-unchanged %s  weights-match %s  max-shape v%d t%d%s" % (
        pc["name"], f0["shipped_tris"], f0["built_tris"], f0["added_tris"], f0["rings_tris"], f0["raised_tris"],
        all(p["originals_unchanged"] for p in per), same, max(p["max_shape_verts"] for p in per), max(p["max_shape_tris"] for p in per),
        ("  [option %s]" % opt) if opt else ""))
print("TOTAL first-file triangles over all non-option pieces: shipped %d built %d" % (TOT["shipped"], TOT["built"]))
json.dump(res, open(os.path.join(C.build, "stats_full.json"), "w"), indent=1)
