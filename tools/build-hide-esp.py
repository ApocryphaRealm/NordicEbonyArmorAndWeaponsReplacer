#!/usr/bin/env python3
r"""Generate the OPTIONAL light plugin that takes the four unmatched ebony weapons out of the game.

Legacy of Ysgramor has no wolf counterpart for the ebony MACE, WARHAMMER, BOW and ARROW, so with the
replacer installed those four are the only vanilla-looking ebony pieces a player would still meet.
The changelog promised an optional plugin that hides them; until 2026-09-17 it had never been built
(the owner: "confirm that the missing ebony weapons are deactivated" - they were not). This is it.

WHAT "HIDE" MEANS HERE - three things, all record overrides, nothing deleted:

  1. Every levelled item list (LVLI, in Skyrim.esm and the four DLC masters) that hands out one of
     the targets loses those entries. Enchanted variants are included: the targets are found by MODEL
     PATH, not by editor id, so every EnchEbonyMaceFire03 that shares ebonymace.nif is caught too.
     A list left with no entries is itself treated as a target, so the lists that contained it drop
     it as well - repeated to a fixpoint. That is what empties the loot tables, the vendors and the
     enemy hands of these weapons.
  2. Every constructible-object recipe (COBJ) whose product is a target gets one condition that can
     never be true - GetLevel < 0 on the crafter - so the forge and the workbench no longer offer it.
  3. The four base weapons themselves are left playable and unchanged: one already in a save, or
     given by console, keeps working. Nothing is made non-playable, so no save can break.

MASTERS. The standard prefix (Skyrim, Update, Dawnguard, HearthFires, Dragonborn), truncated to the
shortest that covers every index this plugin's records use, exactly as build-arma-esl.py does, so no
FormID inside a copied record needs translating. Asserted, not assumed.

Usage:  python tools/build-hide-esp.py [output .esp path]
"""
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))

GAME_DATA = os.environ.get("SKYRIM_DATA", r"D:\modlists\Njordlinger\Stock Game\Data")
DLC_DIR = os.environ.get("SKYRIM_DLC", r"D:\modlists\Njordlinger\mods\Base Game DLC Content")
STANDARD = ["Skyrim.esm", "Update.esm", "Dawnguard.esm", "HearthFires.esm", "Dragonborn.esm"]

PLUGIN_NAME = "Nordic Ebony - Hide Unmatched Weapons.esp"
AUTHOR = "ApocryphaRealm"
DESCRIPTION = "Takes the ebony mace, warhammer, bow and arrow - which have no wolf counterpart - out of levelled lists and crafting."
FORM_VERSION = 44
FLAG_LIGHT = 0x200

# The unmatched pieces, by the vanilla model that every variant of them shares.
TARGET_MODELS = (
    "weapons/ebony/ebonymace.nif",
    "weapons/ebony/ebonywarhammer.nif",
    "weapons/ebony/ebonybowskinned.nif",
    "weapons/ebony/ebonyarrow.nif",          # AMMO MODL
)


def fail(msg):
    sys.stderr.write("ERROR: %s\n" % msg)
    sys.exit(1)


def plugin_path(name):
    for base in (GAME_DATA, DLC_DIR):
        p = os.path.join(base, name)
        if os.path.isfile(p):
            return p
    return None


def subrecords(data):
    i = 0
    while i + 6 <= len(data):
        tag = data[i:i + 4]
        size = struct.unpack_from("<H", data, i + 4)[0]
        yield tag, data[i + 6:i + 6 + size]
        i += 6 + size


def sub(tag, payload):
    return tag + struct.pack("<H", len(payload)) + payload


def record(tag, formid, body, flags=0):
    return (tag + struct.pack("<I", len(body)) + struct.pack("<I", flags) + struct.pack("<I", formid) +
            struct.pack("<I", 0) + struct.pack("<HH", FORM_VERSION, 0) + body)


def group(label, payload):
    return b"GRUP" + struct.pack("<I", len(payload) + 24) + label + struct.pack("<i", 0) + struct.pack("<I", 0) + struct.pack("<HH", 0, 0) + payload


class Plugin:
    """Every WEAP/AMMO/LVLI/COBJ record of one master, decompressed, keyed by FormID (master-local
    index kept as the plugin's own index in the STANDARD order, which is what the invariant needs)."""

    def __init__(self, name, index):
        self.name = name
        self.index = index
        self.records = {}   # (tag, formid) -> (flags, body)
        path = plugin_path(name)
        if not path:
            fail("%s not found under %s or %s" % (name, GAME_DATA, DLC_DIR))
        d = open(path, "rb").read()
        self.masters = []
        tes4_size = struct.unpack_from("<I", d, 4)[0]
        for tag, v in subrecords(d[24:24 + tes4_size]):
            if tag == b"MAST":
                self.masters.append(v.rstrip(b"\0").decode("latin1"))
        for i, m in enumerate(self.masters):
            if STANDARD[i].lower() != m.lower():
                fail("%s master %d is %s, not %s - the no-translation invariant does not hold" % (name, i, m, STANDARD[i]))
        self._walk(d, 24 + tes4_size, len(d))

    def _walk(self, d, pos, end):
        while pos < end:
            tag = d[pos:pos + 4]
            size = struct.unpack_from("<I", d, pos + 4)[0]
            if tag == b"GRUP":
                label = d[pos + 8:pos + 12]
                gtype = struct.unpack_from("<i", d, pos + 12)[0]
                if gtype == 0 and label not in (b"WEAP", b"AMMO", b"LVLI", b"COBJ"):
                    pos += size
                    continue
                self._walk(d, pos + 24, pos + size)
                pos += size
                continue
            flags, fid = struct.unpack_from("<II", d, pos + 8)
            if tag in (b"WEAP", b"AMMO", b"LVLI", b"COBJ"):
                body = d[pos + 24:pos + 24 + size]
                if flags & 0x40000:
                    body = zlib.decompress(body[4:])
                # a FormID whose top byte names a master keeps it; one that names this plugin gets the
                # plugin's STANDARD index, which is the same number - asserted above
                if (fid >> 24) >= len(self.masters):
                    fid = (self.index << 24) | (fid & 0xFFFFFF)
                self.records[(tag, fid)] = (flags & ~0x40000, body)
            pos += 24 + size


def model_of(body):
    for tag, v in subrecords(body):
        if tag == b"MODL":
            return v.rstrip(b"\0").decode("latin1").replace("\\", "/").lower()
    return None


def edid_of(body):
    for tag, v in subrecords(body):
        if tag == b"EDID":
            return v.rstrip(b"\0").decode("latin1")
    return "?"


def lvli_entries(body):
    """The FormIDs a levelled list hands out (LVLO entries)."""
    out = []
    for tag, v in subrecords(body):
        if tag == b"LVLO" and len(v) >= 12:
            out.append(struct.unpack_from("<I", v, 4)[0])
    return out


def strip_lvli(body, targets):
    """Rebuild the list without the target entries (and a COED riding on a removed entry)."""
    out = []
    drop_next_coed = False
    kept = 0
    for tag, v in subrecords(body):
        if tag == b"LVLO":
            fid = struct.unpack_from("<I", v, 4)[0]
            if fid in targets:
                drop_next_coed = True
                continue
            drop_next_coed = False
            kept += 1
            out.append((tag, v))
        elif tag == b"COED" and drop_next_coed:
            continue
        else:
            drop_next_coed = False
            out.append((tag, v))
    rebuilt = b""
    for tag, v in out:
        if tag == b"LLCT":
            v = struct.pack("<B", kept)
        rebuilt += sub(tag, v)
    return rebuilt, kept


def cobj_product(body):
    for tag, v in subrecords(body):
        if tag == b"CNAM":
            return struct.unpack("<I", v)[0]
    return None


def ctda_never():
    # 32 bytes: op(1) pad(3) value(4f) func(2) pad(2) p1(4) p2(4) runOn(4) ref(4) unknown(4)
    # op 0x80 = "<" ... comparison sits in the top three bits: 0 ==, 1 !=, 2 >, 3 >=, 4 <, 5 <=.
    # 4 << 5 = 0x80. Function 80 = GetLevel. "GetLevel < 0" is never true of anything.
    return struct.pack("<B3xfH2xII", 0x80, 0.0, 80, 0, 0) + struct.pack("<III", 0, 0, -1 & 0xFFFFFFFF)


def gate_cobj(body):
    """The recipe with every existing condition removed and one impossible one in its place."""
    out = b""
    placed = False
    for tag, v in subrecords(body):
        if tag == b"CTDA":
            if not placed:
                out += sub(b"CTDA", ctda_never())
                placed = True
            continue
        if tag == b"CNAM" and not placed:
            out += sub(b"CTDA", ctda_never())
            placed = True
        out += sub(tag, v)
    return out


def main(out_path=None):
    out_path = out_path or os.path.join(REPO, "plugin", PLUGIN_NAME)
    plugins = []
    for i, name in enumerate(STANDARD):
        if plugin_path(name):
            plugins.append(Plugin(name, i))
        else:
            print("  (no %s here; skipped)" % name)
            break

    everything = {}
    for p in plugins:
        everything.update(p.records)

    # 1. the targets: every WEAP/AMMO whose model is one of the four
    targets = set()
    by_model = {}
    for (tag, fid), (flags, body) in everything.items():
        if tag in (b"WEAP", b"AMMO"):
            m = model_of(body)
            if m and any(m.endswith(t) for t in TARGET_MODELS):
                targets.add(fid)
                by_model.setdefault(m, []).append(edid_of(body))
    if not targets:
        fail("no weapon or ammo record uses any of the target models - wrong game data?")
    for m, names in sorted(by_model.items()):
        print("  %-38s %3d record(s): %s%s" % (m, len(names), ", ".join(names[:4]), " ..." if len(names) > 4 else ""))

    # 2. levelled lists, to a fixpoint (a list emptied by the removal becomes a target itself)
    lvli_over = {}
    while True:
        grew = False
        for (tag, fid), (flags, body) in everything.items():
            if tag != b"LVLI" or fid in lvli_over:
                continue
            entries = lvli_entries(body)
            if not entries or not any(e in targets for e in entries):
                continue
            rebuilt, kept = strip_lvli(body, targets)
            lvli_over[fid] = (flags, rebuilt, kept, edid_of(body), len(entries))
            if kept == 0 and fid not in targets:
                targets.add(fid)
                grew = True
        # a list overridden earlier may have lost its last entry to a list that only just became a target
        for fid, (flags, rebuilt, kept, name, total) in list(lvli_over.items()):
            if kept > 0 and any(e in targets for e in lvli_entries(rebuilt)):
                rebuilt2, kept2 = strip_lvli(rebuilt, targets)
                lvli_over[fid] = (flags, rebuilt2, kept2, name, total)
                if kept2 == 0 and fid not in targets:
                    targets.add(fid)
                    grew = True
        if not grew:
            break
    emptied = [v[3] for v in lvli_over.values() if v[2] == 0]
    print("  levelled lists overridden: %d (%d emptied: %s%s)" % (len(lvli_over), len(emptied), ", ".join(emptied[:6]), " ..." if len(emptied) > 6 else ""))

    # 3. recipes
    cobj_over = {}
    for (tag, fid), (flags, body) in everything.items():
        if tag == b"COBJ" and cobj_product(body) in targets:
            cobj_over[fid] = (flags, gate_cobj(body), edid_of(body))
    print("  recipes gated: %d (%s%s)" % (len(cobj_over), ", ".join(v[2] for v in list(cobj_over.values())[:6]), " ..." if len(cobj_over) > 6 else ""))

    # masters: the shortest STANDARD prefix covering every index used
    used = set()
    for fid in list(lvli_over) + list(cobj_over):
        used.add(fid >> 24)
    for fid, (flags, body, kept, name, total) in lvli_over.items():
        for e in lvli_entries(body):
            used.add(e >> 24)
    highest = max(used)
    masters = STANDARD[:highest + 1]
    for m in masters:
        if not plugin_path(m):
            fail("record indices need master %s, which is not here" % m)

    lvli_group = b"".join(record(b"LVLI", fid, body, flags) for fid, (flags, body, kept, name, total) in sorted(lvli_over.items()))
    cobj_group = b"".join(record(b"COBJ", fid, body, flags) for fid, (flags, body, name) in sorted(cobj_over.items()))
    count = len(lvli_over) + len(cobj_over)

    hedr = struct.pack("<fiI", 1.7, count, 0x800)
    tes4 = sub(b"HEDR", hedr) + sub(b"CNAM", AUTHOR.encode() + b"\0") + sub(b"SNAM", DESCRIPTION.encode() + b"\0")
    for m in masters:
        tes4 += sub(b"MAST", m.encode() + b"\0") + sub(b"DATA", struct.pack("<Q", 0))
    header = record(b"TES4", 0, tes4, FLAG_LIGHT)
    out = header + group(b"LVLI", lvli_group) + group(b"COBJ", cobj_group)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    open(out_path, "wb").write(out)
    print("wrote %s (%d bytes): %d records, masters %s, light flag set, no new records (0 form ids of its own)" %
          (out_path, len(out), count, ", ".join(masters)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
