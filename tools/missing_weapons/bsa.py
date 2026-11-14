"""Read named files out of a Skyrim Special Edition .bsa (version 105; LZ4 frame compression) - enough to take the vanilla
meshes this build starts from out of the player's own Skyrim - Meshes0.bsa, so the repository carries none of them."""
import struct


def extract(bsa_path, wanted, strict=True):
    """wanted: archive paths like 'meshes\\weapons\\ebony\\ebonymace.nif' (any case). Returns {wanted path: bytes}."""
    import lz4.frame
    want = {w.lower().replace("/", "\\"): w for w in wanted}
    out = {}
    with open(bsa_path, "rb") as f:
        d = f.read()
    magic, ver, off, aflags, nfold, nfile, lfold, lfile, fflags = struct.unpack_from("<4sIIIIIIIH", d, 0)
    if magic != b"BSA\0" or ver != 105:
        raise ValueError("%s: not a Skyrim SE archive (magic %r, version %d)" % (bsa_path, magic, ver))
    if not (aflags & 1 and aflags & 2):
        raise ValueError("%s: archive without folder or file names" % bsa_path)
    compressed, embed = bool(aflags & 4), bool(aflags & 0x100)
    folders = [struct.unpack_from("<QIIQ", d, off + 24 * i) for i in range(nfold)]
    p = off + 24 * nfold
    recs = []
    for _, count, _, _ in folders:
        ln = d[p]; name = d[p + 1:p + ln].decode("latin-1").lower(); p += 1 + ln
        for _ in range(count):
            _, size, foff = struct.unpack_from("<QII", d, p); p += 16; recs.append((name, size, foff))
    names = d[p:p + lfile].split(b"\0")
    for (folder, size, foff), fn in zip(recs, names):
        path = folder + "\\" + fn.decode("latin-1").lower()
        if path not in want:
            continue
        comp = compressed ^ bool(size & 0x40000000); size &= 0x3FFFFFFF; q = foff
        if embed:
            q += 1 + d[q]; size -= 1 + d[foff]
        if comp:
            raw = struct.unpack_from("<I", d, q)[0]; data = lz4.frame.decompress(d[q + 4:q + size])
            assert len(data) == raw, (path, len(data), raw)
        else:
            data = d[q:q + size]
        out[want[path]] = data
    missing = [w for w in wanted if w not in out]
    if missing and strict:          # strict=False: return what this archive has (the meshes span two archives)
        raise FileNotFoundError("%s has no %s" % (bsa_path, ", ".join(missing)))
    return out
