# Minimal SSE (20.2.0.7, bsver 100) NIF reader/writer for block-level splicing.
# Blocks are kept as raw bytes; for the block types we touch, ref_offsets() returns
# the byte offsets of every block reference / pointer and string index inside the block,
# so blocks can be copied between files with remapped references.
import struct

class Nif:
    def __init__(self, path):
        d = open(path, "rb").read()
        self.path = path
        p = d.index(b"\n") + 1
        self.headline = d[:p]
        self.version, self.endian, self.user, nblocks, self.bsver = struct.unpack_from("<IBIII", d, p); p += 17
        self.bs_strings = []
        for _ in range(3):
            n = d[p]; self.bs_strings.append(d[p + 1:p + 1 + n]); p += 1 + n
        ntypes, = struct.unpack_from("<H", d, p); p += 2
        self.types = []
        for _ in range(ntypes):
            n, = struct.unpack_from("<I", d, p); p += 4
            self.types.append(d[p:p + n].decode()); p += n
        tidx = struct.unpack_from(f"<{nblocks}H", d, p); p += 2 * nblocks
        sizes = struct.unpack_from(f"<{nblocks}I", d, p); p += 4 * nblocks
        nstr, self.maxlen = struct.unpack_from("<II", d, p); p += 8
        self.strings = []
        for _ in range(nstr):
            n, = struct.unpack_from("<I", d, p); p += 4
            self.strings.append(d[p:p + n].decode("latin-1")); p += n
        ngroups, = struct.unpack_from("<I", d, p); p += 4
        assert ngroups == 0
        self.btypes = [self.types[t & 0x7FFF] for t in tidx]
        self.blocks = []
        for s in sizes:
            self.blocks.append(bytearray(d[p:p + s])); p += s
        nroots, = struct.unpack_from("<I", d, p); p += 4
        self.roots = list(struct.unpack_from(f"<{nroots}i", d, p)); p += 4 * nroots
        assert p == len(d), (p, len(d))

    def save(self, path):
        types = []
        for t in self.btypes:
            if t not in types: types.append(t)
        out = bytearray(self.headline)
        out += struct.pack("<IBIII", self.version, self.endian, self.user, len(self.blocks), self.bsver)
        for s in self.bs_strings:
            out += bytes([len(s)]) + s
        out += struct.pack("<H", len(types))
        for t in types:
            out += struct.pack("<I", len(t)) + t.encode()
        out += struct.pack(f"<{len(self.blocks)}H", *[types.index(t) for t in self.btypes])
        out += struct.pack(f"<{len(self.blocks)}I", *[len(b) for b in self.blocks])
        out += struct.pack("<II", len(self.strings), max([len(s) for s in self.strings] + [0]))
        for s in self.strings:
            e = s.encode("latin-1"); out += struct.pack("<I", len(e)) + e
        out += struct.pack("<I", 0)
        for b in self.blocks: out += b
        out += struct.pack("<I", len(self.roots)) + struct.pack(f"<{len(self.roots)}i", *self.roots)
        open(path, "wb").write(out)

    # ---- field helpers -------------------------------------------------
    def i32(self, b, o): return struct.unpack_from("<i", self.blocks[b], o)[0]
    def u32(self, b, o): return struct.unpack_from("<I", self.blocks[b], o)[0]

    def name(self, b):
        t = self.btypes[b]
        o = 4 if t == "BSLightingShaderProperty" else 0
        if not has_net(t): return None
        i = self.i32(b, o)
        return self.strings[i] if 0 <= i < len(self.strings) else None

    def net_end(self, b, o, refs, strs):
        """Parse NiObjectNET at offset o, append ref/str offsets, return end offset."""
        strs.append(o); o += 4
        n = self.u32(b, o); o += 4
        for _ in range(n): refs.append(o); o += 4
        refs.append(o); o += 4  # controller
        return o

    def av_end(self, b, o, refs, strs):
        o = self.net_end(b, o, refs, strs)
        o += 4 + 12 + 36 + 4  # flags, translation, rotation, scale
        refs.append(o); o += 4  # collision object
        return o

    def transform(self, b):
        refs, strs = [], []
        o = self.net_end(b, 0, refs, strs) + 4
        t = struct.unpack_from("<3f", self.blocks[b], o)
        r = struct.unpack_from("<9f", self.blocks[b], o + 12)
        s = struct.unpack_from("<f", self.blocks[b], o + 48)[0]
        return o, t, r, s

    def children(self, b):
        refs, strs = [], []
        o = self.av_end(b, 0, refs, strs)
        n = self.u32(b, o); o += 4
        return list(struct.unpack_from(f"<{n}i", self.blocks[b], o)), o - 4

    def ref_offsets(self, b):
        """Return (ref_offsets, string_offsets) for block b."""
        t = self.btypes[b]; refs = []; strs = []
        if t in NODES:
            o = self.av_end(b, 0, refs, strs)
            n = self.u32(b, o); o += 4
            for _ in range(n): refs.append(o); o += 4
            n = self.u32(b, o); o += 4
            for _ in range(n): refs.append(o); o += 4
        elif t == "BSTriShape":
            o = self.av_end(b, 0, refs, strs)
            o += 16
            refs += [o, o + 4, o + 8]  # skin, shader, alpha
        elif t == "BSLightingShaderProperty":
            o = self.net_end(b, 4, refs, strs)
            o += 8 + 16
            refs.append(o)  # texture set
        elif t in ("BSEffectShaderProperty", "NiAlphaProperty", "BSXFlags",
                   "NiStringExtraData"):
            if t == "NiStringExtraData":
                strs += [0, 4]
            elif t == "BSXFlags":
                strs.append(0)
            else:
                self.net_end(b, 0, refs, strs)
        elif t in ("BSShaderTextureSet", "NiFloatData", "NiTransformData", "NiBoolData",
                   "NiPosData", "bhkCompressedMeshShapeData"):
            pass
        elif t in CONTROLLERS:
            refs += [0]          # next controller
            refs += [4 + 2 + 16]  # target (ptr)
            refs += [26]          # interpolator
        elif t in ("NiFloatInterpolator", "NiBoolInterpolator"):
            refs.append(len(self.blocks[b]) - 4)
        elif t == "NiPoint3Interpolator":
            refs.append(16)
        elif t == "NiTransformInterpolator":
            refs.append(len(self.blocks[b]) - 4)
        elif t == "bhkCollisionObject":
            refs += [0, 6]
        elif t == "bhkRigidBody":
            refs.append(0)
        elif t == "bhkMoppBvTreeShape":
            refs.append(0)
        elif t == "bhkCompressedMeshShape":
            refs += [0, len(self.blocks[b]) - 4]
        else:
            raise NotImplementedError(t)
        return refs, strs

def has_net(t):
    return t in NODES or t in ("BSTriShape", "BSLightingShaderProperty", "BSEffectShaderProperty",
                               "NiAlphaProperty")

NODES = {"NiNode", "BSFadeNode", "BSOrderedNode", "BSValueNode", "NiBillboardNode"}
CONTROLLERS = {"BSLightingShaderPropertyFloatController", "BSEffectShaderPropertyFloatController",
               "BSEffectShaderPropertyColorController", "NiTransformController"}

def dump(nif, b=None, depth=0, seen=None):
    if seen is None:
        seen = set(); b = nif.roots[0]
    if b < 0 or b in seen: return
    seen.add(b)
    t = nif.btypes[b]
    line = "  " * depth + f"[{b}] {t} '{nif.name(b)}'"
    if t in NODES or t == "BSTriShape":
        _, tr, r, s = nif.transform(b)
        line += f" T=({tr[0]:.2f},{tr[1]:.2f},{tr[2]:.2f}) S={s:.3f}"
        if abs(r[0] - 1) > 1e-4 or abs(r[4] - 1) > 1e-4: line += " R=" + ",".join(f"{x:.2f}" for x in r)
    print(line)
    try:
        refs, _ = nif.ref_offsets(b)
    except NotImplementedError:
        return
    for o in refs:
        r = nif.i32(b, o)
        if r >= 0 and r not in seen and not (t in CONTROLLERS and o == 22):
            dump(nif, r, depth + 1, seen)
