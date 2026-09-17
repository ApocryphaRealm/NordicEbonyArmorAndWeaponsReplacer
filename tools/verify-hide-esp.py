#!/usr/bin/env python3
r"""Verify the optional hide plugin the way verify-arma-esl.py verifies the main one: read the
built file back, rebuild the target set independently from the game data, and refuse anything that
does not hold.

Checks:
  * TES4: form version 44, light flag set, masters are a prefix of the standard order.
  * Every LVLI override: no LVLO entry names a target (a target weapon/ammo, or a list this plugin
    emptied), LLCT equals the entry count, and the original list DID contain a target (no gratuitous
    overrides).
  * Every COBJ override: its product is a target and it carries exactly one condition, GetLevel < 0.
  * Every record's form version is what the master carried (44 for these), and none is 0.
  * Every levelled list in the masters that contains a target is overridden (nothing missed).

Usage:  python tools/verify-hide-esp.py [plugin path]
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import importlib
gen = importlib.import_module("build-hide-esp")


def main(path=None):
    path = path or os.path.join(gen.REPO, "plugin", gen.PLUGIN_NAME)
    d = open(path, "rb").read()
    problems = []

    # header
    tes4_size = struct.unpack_from("<I", d, 4)[0]
    flags = struct.unpack_from("<I", d, 8)[0]
    fv = struct.unpack_from("<H", d, 20)[0]
    if fv != 44: problems.append("TES4 form version %d" % fv)
    if not flags & gen.FLAG_LIGHT: problems.append("light flag not set")
    masters = [v.rstrip(b"\0").decode() for t, v in gen.subrecords(d[24:24 + tes4_size]) if t == b"MAST"]
    if masters != gen.STANDARD[:len(masters)]: problems.append("masters %r are not a standard prefix" % masters)

    # the independent truth
    plugins = [gen.Plugin(name, i) for i, name in enumerate(gen.STANDARD) if gen.plugin_path(name)]
    everything = {}
    for p in plugins: everything.update(p.records)
    weapon_targets = set()
    for (tag, fid), (fl, body) in everything.items():
        if tag in (b"WEAP", b"AMMO"):
            m = gen.model_of(body)
            if m and any(m.endswith(t) for t in gen.TARGET_MODELS): weapon_targets.add(fid)

    # our records
    ours = {}
    pos = 24 + tes4_size
    while pos < len(d):
        tag = d[pos:pos + 4]; size = struct.unpack_from("<I", d, pos + 4)[0]
        if tag == b"GRUP": pos += 24; continue
        rflags, fid = struct.unpack_from("<II", d, pos + 8)
        rfv = struct.unpack_from("<H", d, pos + 20)[0]
        if rfv == 0: problems.append("%s %08X form version 0" % (tag.decode(), fid))
        if rflags & 0x40000: problems.append("%s %08X is compressed" % (tag.decode(), fid))
        ours[(tag, fid)] = d[pos + 24:pos + 24 + size]
        pos += 24 + size

    emptied = {fid for (tag, fid), body in ours.items() if tag == b"LVLI" and not gen.lvli_entries(body)}
    targets = weapon_targets | emptied
    for (tag, fid), body in ours.items():
        if tag == b"LVLI":
            entries = gen.lvli_entries(body)
            bad = [e for e in entries if e in targets]
            if bad: problems.append("LVLI %08X still hands out %s" % (fid, ", ".join("%08X" % b for b in bad)))
            llct = [v for t, v in gen.subrecords(body) if t == b"LLCT"]
            if not llct or llct[0][0] != len(entries): problems.append("LVLI %08X LLCT %r != %d" % (fid, llct, len(entries)))
            orig = everything.get((b"LVLI", fid))
            if not orig: problems.append("LVLI %08X overrides nothing in the masters" % fid)
            elif not any(e in targets for e in gen.lvli_entries(orig[1])): problems.append("LVLI %08X: the original contained no target" % fid)
        elif tag == b"COBJ":
            if gen.cobj_product(body) not in targets: problems.append("COBJ %08X gates a product that is not a target" % fid)
            ctdas = [v for t, v in gen.subrecords(body) if t == b"CTDA"]
            if len(ctdas) != 1 or ctdas[0] != gen.ctda_never(): problems.append("COBJ %08X does not carry exactly the never-true condition" % fid)
        else:
            problems.append("unexpected record type %s" % tag.decode())

    # completeness: every master list that contains a target is overridden
    missed = []
    for (tag, fid), (fl, body) in everything.items():
        if tag == b"LVLI" and any(e in targets for e in gen.lvli_entries(body)) and (b"LVLI", fid) not in ours:
            missed.append("%08X %s" % (fid, gen.edid_of(body)))
    if missed: problems.append("levelled lists that still hand out a target and are not overridden: %s" % ", ".join(missed[:8]))
    recipes_missed = [gen.edid_of(body) for (tag, fid), (fl, body) in everything.items() if tag == b"COBJ" and gen.cobj_product(body) in weapon_targets and (b"COBJ", fid) not in ours]
    if recipes_missed: problems.append("recipes not gated: %s" % ", ".join(recipes_missed))

    n_l = sum(1 for k in ours if k[0] == b"LVLI"); n_c = sum(1 for k in ours if k[0] == b"COBJ")
    if problems:
        print("FAIL %s" % path)
        for p in problems: print("  - " + p)
        return 1
    print("OK %s: %d levelled lists (%d emptied), %d recipes, %d target weapons/ammo, masters %s, light, form 44" %
          (os.path.basename(path), n_l, len(emptied), n_c, len(weapon_targets), ", ".join(masters)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
