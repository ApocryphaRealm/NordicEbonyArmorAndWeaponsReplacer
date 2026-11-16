r"""After the Blender export: give every shape its TruePBR texture set (the exporter keeps the TruePBR flags but drops
slot 5), add the parallax map on the ORIGINAL shapes, and splice the shield's added (unskinned) shape into the
untouched shield NIF.
  originals : [albedo, normal, "", <stem>_p.dds, "", <stem>_rmaos.dds]  + Lighting Effect 2 (CS displacement scale)
  _3D_Raised: [albedo, normal, "", "",            "", <stem>_rmaos.dds]  (no parallax on modelled parts)
  _3D_Rings : chainlink.dds / chainlink_n.dds / chainlink_rmaos.dds
A shader block shared by shapes that need different sets is duplicated first.
usage: py -3 postfix.py <nif> [...]      |      py -3 postfix.py --splice <orig.nif> <added.nif> <out.nif>"""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repo's tools\ (truepbr, niflib, body_fits)
import niflib, truepbr
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import sets
C = sets.get()
PRE = C.pre
# parallax on every original shape whose albedo has a built _p map (armour atlases; weapon atlases with a feature map)
PARALLAX = {f[:-6].lower() for f in os.listdir(C.texout) if f.lower().endswith("_p.dds")} if os.path.isdir(C.texout) else set()
DISP = float(os.environ.get("DISP_SCALE", "0.3"))
TRUEPBR = 0x00800000

def stem(p): return os.path.splitext(p.replace("/", "\\").split("\\")[-1])[0].lower()
def texset_bytes(paths): return truepbr._texset_block(paths)

def shape_refs(n, b):
    refs, strs = n.ref_offsets(b); return refs[-3], refs[-2], refs[-1]   # skin, shader, alpha offsets

def fix(path, out=None):
    n = niflib.Nif(path); log = []
    users = {}
    for b, t in enumerate(n.btypes):
        if t == "BSTriShape":
            _, so, _ = shape_refs(n, b); users.setdefault(n.i32(b, so), []).append(b)
    for b, t in enumerate(n.btypes):
        if t != "BSTriShape": continue
        name = n.name(b) or ""; _, so, _ = shape_refs(n, b); sh = n.i32(b, so)
        if sh < 0 or n.btypes[sh] != "BSLightingShaderProperty": continue
        ts, paths = truepbr._texset(n, sh)
        d = stem(paths[0]) if paths and paths[0] else ""
        # only the set's own shapes (blood decals, vanilla textures stay as they are)
        if "_3D_" not in name and not (paths and paths[0].lower().startswith(PRE.lower())): log.append("%-30s untouched" % name); continue
        nm = stem(paths[1]) if len(paths) > 1 and paths[1] else ""
        if "_3D_Rings_" in name: want = [PRE + "chainlink.dds", PRE + "chainlink_n.dds", "", "", "", PRE + "chainlink_rmaos.dds", "", "", ""]; le2 = 0.0
        elif "_3D_Raised_" in name: want = [PRE + d + ".dds", PRE + nm + ".dds", "", "", "", PRE + d + "_rmaos.dds", "", "", ""]; le2 = 0.0
        else:
            par = d in PARALLAX
            want = [PRE + d + ".dds", PRE + nm + ".dds", "", PRE + d + "_p.dds" if par else "", "", PRE + d + "_rmaos.dds", "", "", ""]; le2 = DISP if par else 0.0
        if len(users.get(sh, [])) > 1:
            # duplicate shader + texture set for this shape
            ns = len(n.blocks); n.blocks.append(bytearray(n.blocks[sh])); n.btypes.append("BSLightingShaderProperty")
            nt = len(n.blocks); n.blocks.append(texset_bytes(want)); n.btypes.append("BSShaderTextureSet")
            struct.pack_into("<i", n.blocks[ns], n.ref_offsets(ns)[0][-1], nt); struct.pack_into("<i", n.blocks[b], so, ns)
            users[sh].remove(b); sh = ns
        else:
            n.blocks[ts] = texset_bytes(want)
        f1, f2 = truepbr._flags(n, sh)
        if not f2 & TRUEPBR: log.append("NOT TRUEPBR " + name)
        blk = n.blocks[sh]; struct.pack_into("<f", blk, len(blk) - 4, le2)
        log.append("%-30s %s" % (name, [i for i, p in enumerate(want) if p]))
    n.save(out or path)
    return log

def splice(orig, added, out, skip=("scb",)):
    # skip: added shapes grown on the sheath ("Scb" - the engine hides that one shape by name when the weapon is drawn, a
    # spliced sibling would stay floating beside the blade) are left out
    """append the added NIF's BSTriShapes (+ their shader / texture set / alpha) under the original root"""
    N = niflib.Nif(orig); A = niflib.Nif(added); mp = {}
    def copy(ab):
        if ab in mp: return mp[ab]
        nb = len(N.blocks); mp[ab] = nb; N.blocks.append(bytearray(A.blocks[ab])); N.btypes.append(A.btypes[ab])
        refs, strs = A.ref_offsets(ab)
        for o in strs:
            si = A.i32(ab, o)
            if si >= 0:
                s = A.strings[si]
                if s not in N.strings: N.strings.append(s)
                struct.pack_into("<i", N.blocks[nb], o, N.strings.index(s))
        for o in refs:
            r = A.i32(ab, o)
            if r >= 0 and A.btypes[r] in ("BSLightingShaderProperty", "BSShaderTextureSet", "NiAlphaProperty"):
                struct.pack_into("<i", N.blocks[nb], o, copy(r))
            else:
                struct.pack_into("<i", N.blocks[nb], o, -1)
        return nb
    new = [copy(b) for b, t in enumerate(A.btypes) if t == "BSTriShape" and not (A.name(b) or "").lower().startswith(skip)]
    root = N.roots[0]; kids, off = N.children(root); blk = N.blocks[root]
    end = off + 4 + 4 * len(kids)
    N.blocks[root] = bytearray(blk[:off] + struct.pack("<I", len(kids) + len(new)) + struct.pack("<%di" % len(kids), *kids) + struct.pack("<%di" % len(new), *new) + blk[end:])
    N.save(out); return new

if __name__ == "__main__":
    if sys.argv[1] == "--splice":
        print("spliced", splice(*sys.argv[2:5])); print("\n".join(fix(sys.argv[4])))
    else:
        for p in sys.argv[1:]:
            print("==", p); print("\n".join(fix(p)))
