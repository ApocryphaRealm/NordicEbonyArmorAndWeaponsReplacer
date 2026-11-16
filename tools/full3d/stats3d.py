import os, sys, struct, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repo's tools\ (truepbr, niflib, body_fits)
import niflib
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def shapes(p):
    n = niflib.Nif(p); out = []
    for b, t in enumerate(n.btypes):
        if t == "BSTriShape":
            refs, strs = [], []; o = n.av_end(b, 0, refs, strs) + 16 + 12 + 8
            nt, nv = struct.unpack_from("<HH", n.blocks[b], o)
            out.append((n.name(b), nv, nt))
    return out
PIECES = {"helmet": ("NordicEbony\\m\\helmet_%d.nif", (1, 0)), "cuirass": ("NordicEbony\\m\\cuirass_%d.nif", (1, 0)),
          "gauntlets": ("NordicEbony\\m\\gauntlets_%d.nif", (1, 0)), "boots": ("NordicEbony\\m\\boots_%d.nif", (1, 0)),
          "shield": ("weapons\\ebony\\ebonyshield.nif", (None,))}
res = {}
for pc, (rel, ws) in PIECES.items():
    per = {}
    for w in ws:
        r = rel % w if w is not None else rel
        a = shapes(os.path.join(H, "pkg_snapshot", "meshes", r)); b = shapes(os.path.join(H, "build", "out", "meshes", r))
        per[w] = (a, b)
    a, b = per[ws[0]]
    added = [s for s in b if "_3D_" in s[0]]
    rings = [s for s in added if "_Rings_" in s[0]]; raised = [s for s in added if "_Raised_" in s[0]]
    match = True
    if len(ws) == 2:
        b0 = per[0][1]; match = [x[1:] for x in b] == [x[1:] for x in b0] and len(b) == len(b0)
    res[pc] = dict(shipped_shapes=len(a), shipped_verts=sum(s[1] for s in a), shipped_tris=sum(s[2] for s in a),
                   added_shapes=len(added), added_verts=sum(s[1] for s in added), added_tris=sum(s[2] for s in added),
                   rings_tris=sum(s[2] for s in rings), raised_tris=sum(s[2] for s in raised),
                   total_shapes=len(b), total_tris=sum(s[2] for s in b), total_verts=sum(s[1] for s in b),
                   weights_match=match, max_shape_verts=max(s[1] for s in b), max_shape_tris=max(s[2] for s in b))
    print(pc, res[pc])
json.dump(res, open(os.path.join(H, "build", "stats3d.json"), "w"), indent=1)
