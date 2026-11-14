"""Checks every NIF the missing-weapons build writes, against the vanilla file it was built on. Fails (returns faults) on:
  * a node of vanilla's missing, renamed or moved (the tree, bone transforms and attach points are the game's contract);
  * the collision object hanging on a different node than vanilla's;
  * a skinned shape whose shader lacks SLSF1 Skinned (0x2), or a rigid one that has it (Truly Nordic bow, 2026-11-11);
  * one of OUR shapes pointing at a texture outside textures\\nordwar\\companions\\ (the Wolf atlases);
  * the arrow file without exactly Arrow1..Arrow6 as single shapes under ArrowQuiver;
  * winding: an edge walked the same way by both its faces, or a surface whose back sees the sky more than its front
    (the game draws one side; review renders draw both - shield 1.0.0) - measured in each shape's WORLD frame.
"""
import os, sys, struct
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import niflib, winding, assemble as A

def node_table(n):
    out = {}
    for b, t in enumerate(n.btypes):
        if t in niflib.NODES:
            _, tr, r, s = n.transform(b); out[n.name(b)] = (t, np.round(tr, 3).tolist(), np.round(r, 4).tolist(), round(s, 4))
    return out

def coll_node(n):
    co = [i for i, t in enumerate(n.btypes) if t == "bhkCollisionObject"]
    return sorted(n.name(struct.unpack_from("<i", n.blocks[c], 0)[0]) for c in co)

def texpaths(n, sh):
    ts = n.i32(sh, A.texset_ref_off(n, sh))
    if ts < 0: return []
    tb = n.blocks[ts]; c = struct.unpack_from("<I", tb, 0)[0]; p = 4; out = []
    for _ in range(c):
        l = struct.unpack_from("<I", tb, p)[0]; out.append(tb[p + 4:p + 4 + l].decode("latin-1")); p += 4 + l
    return out

def winding_world(n, ours, seed=7):
    rng = np.random.default_rng(seed); shapes = {}
    for b in A.shapes_of(n):
        W, F = A.shape_world_points(n, b)
        if len(F): shapes[b] = (n.name(b), W, F)
    def tris(bs): return np.concatenate([shapes[b][1][shapes[b][2]] for b in bs]) if bs else np.zeros((0, 3, 3))
    solid = [b for b, (nm, _, _) in shapes.items() if "blood" not in nm.lower()]
    rows, faults = [], 0
    for b, (nm, V, F) in shapes.items():
        if not ours(nm): continue
        Wd, ok = winding._weld(V, F); bad, pairs = winding.edges_against(Wd, ok)
        T = tris(sorted(set(solid) | {b})); inward = []
        for cp in winding.components(len(F), pairs, ok):
            front, back = winding.outward_vote(V, F, cp, T, rng)
            if back > front + 0.15 and back > 0.25: inward.append((len(cp), round(front, 2), round(back, 2)))
        faults += bad + len(inward)
        rows.append({"shape": nm, "faces": int(ok.sum()), "edges_against_neighbour": bad, "surfaces_facing_in": len(inward), "facing_in": inward[:4]})
    return rows, faults

def check(built, vanilla, ours_shapes):
    n, v = niflib.Nif(built), niflib.Nif(vanilla); faults = []
    tn, tv = node_table(n), node_table(v)
    if tn != tv: faults.append(("node tree differs from vanilla", sorted(set(tv) ^ set(tn)) or [k for k in tv if tv[k] != tn.get(k)]))
    if coll_node(n) != coll_node(v): faults.append(("collision on another node", coll_node(n), coll_node(v)))
    for b in A.shapes_of(n):
        nm = n.name(b); o = n.av_end(b, 0, [], []); sk, sh, _ = struct.unpack_from("<3i", n.blocks[b], o + 16)
        if sh < 0 or n.btypes[sh] != "BSLightingShaderProperty": continue
        f1 = struct.unpack_from("<I", n.blocks[sh], n.net_end(sh, 4, [], []))[0]
        if bool(f1 & 0x2) != (sk >= 0): faults.append(("SLSF1 Skinned disagrees with the skin", nm, hex(f1), sk))
        if nm in ours_shapes:
            bad = [p for p in texpaths(n, sh) if p and not p.lower().startswith(("textures\\nordwar\\companions\\", "textures\\cubemaps\\"))]
            if bad: faults.append(("texture outside the Wolf set", nm, bad))
    rows, wf = winding_world(n, lambda nm: nm in ours_shapes)
    if wf: faults.append(("winding", [r for r in rows if r["edges_against_neighbour"] or r["surfaces_facing_in"]]))
    return {"faults": faults, "winding": rows}

OURS = {"ebonymace.nif": {"EbonyMace:0"}, "1stpersonebonymace.nif": {"1stPersonEbonyMace:0"},
        "ebonywarhammer.nif": {"EbonyWarhammer:0"}, "1stpersonebonywarhammer.nif": {"1stPersonEbonyWarhammer:0"},
        "ebonybowskinned.nif": {"BowMesh:0", "BowMesh:1"},
        "ebonyarrow.nif": {"Arrow:0", "ArrowQuiver:0", "ArrowQuiver:1"} | {"Arrow%d" % k for k in range(1, 7)},
        "ebonyarrowprojectile.nif": {"EbonyArrowFlight:0"}}

def verify_all(out_dir, van_dir):
    rep, total = {}, 0
    for fn, ours in OURS.items():
        r = check(os.path.join(out_dir, fn), os.path.join(van_dir, fn), ours); rep[fn] = r; total += len(r["faults"])
    n = niflib.Nif(os.path.join(out_dir, "ebonyarrow.nif"))
    q = [b for b in range(len(n.blocks)) if n.btypes[b] == "NiNode" and n.name(b) == "ArrowQuiver"][0]
    kids = [n.name(c) for c in n.children(q)[0] if c >= 0 and n.btypes[c] == "BSTriShape"]
    arrows = sorted(k for k in kids if k.startswith("Arrow") and k[5:].isdigit())
    if arrows != ["Arrow%d" % k for k in range(1, 7)]:
        rep["ebonyarrow.nif"]["faults"].append(("quiver arrows", arrows)); total += 1
    return rep, total

if __name__ == "__main__":
    import json
    r, t = verify_all(sys.argv[1], sys.argv[2]); print(json.dumps(r, indent=1, default=str)); print("FAULTS", t); sys.exit(1 if t else 0)
