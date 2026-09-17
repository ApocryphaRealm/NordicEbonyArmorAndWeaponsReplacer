#!/usr/bin/env python3
r"""Build the HIMBO and CBBE 3BA body options for a mod made from NordwarUA's Legacy of Ysgramor art.

The owner, 2026-09-17: "see if you can include himbo and cbbe files for these 2 as they are nordwarua
mods". Two refits of Legacy of Ysgramor exist on Nexus and both cover the steel ("Normal") and the
Ebony variants that Nordic Skyforged and Nordic Ebony are built from:

  * Legacy of Ysgramor - HIMBO Conversion  (Nexus 110002, Trexasle) - prebuilt HIMBO-zeroed male
    meshes at LoY's paths plus BodySlide slider sets and shape data.
  * Legacy of Ysgramor - 3BA Bodyslide     (Nexus 111209, Xonek)   - CBBE 3BA slider sets and shape
    data only (no prebuilt meshes, no physics).

The archives live in "2. Mod Types\Equipment or Record Based\Legacy of Ysgramor refits" (see its
NOTE.md). This script turns them into installer folders for ONE of our mods:

  <out>\<n> HIMBO meshes                      the prebuilt male meshes, renamed to our mesh names and
                                              moved under our mesh folder, texture paths rewritten to
                                              our texture folder (same-length rewrite, as the base meshes)
  <out>\<n+1> BodySlide - HIMBO               SliderSets + ShapeData, sets renamed "<Mod> - HIMBO - <piece>",
                                              OutputPath pointed at our mesh folder, our output file names,
                                              shape-data meshes texture-rewritten the same way
  <out>\<n+2> BodySlide - CBBE 3BA            likewise for the female sets

A profile names the variant (steel or ebony), the mesh folder, the texture rewrite and the file names.
The rewrite refuses to run if the replacement would change a mesh's length (the NIF block sizes would
be wrong), exactly as the mods' own package builders do.

Usage:  python loy-refits.py --profile skyforged|ebony --out <package root> [--refits <folder>]
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

REFITS_DEFAULT = r"D:\Claude output\2. Mod Types\Equipment or Record Based\Legacy of Ysgramor refits"
ARCHIVES = {"himbo": "LoY-HIMBO-464314.7z", "3ba": "LoY-3BA-468982.rar"}
SEVENZIP = [r"C:\Program Files\7-Zip\7z.exe", r"C:\Program Files (x86)\7-Zip\7z.exe", "7z"]

OLD_TEX = b"textures\\NordWar\\Companions\\"
TEX_RE = re.compile(rb"textures[\\/]NordWar[\\/]Companions[\\/]", re.IGNORECASE)

# One profile per mod. "loy" is the LoY base name (without the _0/_1 / F/M suffix), "ours" the name our
# mesh folder uses. HIMBO prebuilt meshes are <loy>M_0/_1.nif; 3BA shape data is per piece.
PROFILES = {
    "skyforged": {
        "title": "Nordic Skyforged",
        "mesh_dir": "meshes\\NordicSkyforge\\armor",
        "new_tex": b"textures\\NordicSkyforge\\Set\\",
        "pieces": {  # loy base -> ours base (male/female suffix kept)
            "Armor": "Armor", "Boots": "Boots", "Gauntlets": "Gauntlets", "Helmet": "Helmet", "1stpersonArmor": "1stpersonArmor",
        },
        "himbo_sets": {"Body": "Armor", "Boots": "Boots", "Gauntlets": "Gauntlets", "Helm": "Helmet", "1st": "1stpersonArmor"},
        "tba_sets": {"Armor 3BA": "Armor", "Boots 3BA": "Boots", "Gauntles 3BA": "Gauntlets", "1st Person 3BA": "1stpersonArmor"},
        "variant": "",  # LoY steel set: no suffix in the set names
    },
    "ebony": {
        "title": "Nordic Ebony",
        "mesh_dir": "meshes\\NordicEbony",
        "new_tex": None,  # the ebony replacer keeps LoY's texture folder (its textures ship there)
        "pieces": {
            "ArmorEbony": "cuirass", "BootsEbony": "boots", "GauntletsEbony": "gauntlets", "EbonyHelmet": "helmet", "1stpersonArmorEbony": "1stpersoncuirass",
        },
        "himbo_sets": {"Body (Ebony)": "cuirass", "Boots (Ebony)": "boots", "Gauntlets (Ebony)": "gauntlets", "Helm (Ebony)": "helmet", "1st (Ebony)": "1stpersoncuirass",
                       "Body (Ebony No Fur)": "cuirass (no fur collar)"},
        "tba_sets": {"Ebony - Armor 3BA": "cuirass", "Ebony - Boots 3BA": "boots", "Ebony - Gauntles 3BA": "gauntlets", "Ebony - 1st Person 3BA": "1stpersoncuirass",
                     "Ebony - Armor No Fur 3BA": "cuirass (no fur collar)"},
        "variant": "Ebony",
        "sexed_dirs": True,  # our ebony meshes live in m\ and f\ subfolders with unsexed names
        # the installer's collarless cuirass: its own prebuilt HIMBO folder, overriding the cuirass
        "nofur": {"ArmorNoFurEbony": "cuirass"},
    },
}


def fail(msg):
    raise SystemExit("loy-refits: " + msg)


def sevenzip():
    for c in SEVENZIP:
        if os.path.isfile(c) or shutil.which(c):
            return c
    fail("7-Zip not found")


def extract(archive, into):
    subprocess.run([sevenzip(), "x", "-y", "-o" + into, archive], check=True, stdout=subprocess.DEVNULL)


def rewrite_tex(raw, new_tex):
    if not new_tex:
        return raw
    if len(new_tex) != len(OLD_TEX):
        fail("texture prefix %r is not the same length as %r" % (new_tex, OLD_TEX))
    out = TEX_RE.sub(lambda m: new_tex, raw)
    if len(out) != len(raw):
        fail("texture rewrite changed a mesh's length")
    return out


def copy_mesh(src, dst, new_tex):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(src, "rb") as f:
        raw = f.read()
    with open(dst, "wb") as f:
        f.write(rewrite_tex(raw, new_tex))


def our_mesh_rel(prof, base, sex, weight):
    """Relative path (under the package folder) of our mesh for a LoY base name, sex M/F and weight 0/1."""
    ours = prof["pieces"][base]
    if prof.get("sexed_dirs"):
        return os.path.join(prof["mesh_dir"], "m" if sex == "M" else "f", "%s_%s.nif" % (ours, weight))
    return os.path.join(prof["mesh_dir"], "%s%s_%s.nif" % (ours, sex, weight))


def build_himbo_meshes(prof, src_root, out):
    n = 0
    for base in prof["pieces"]:
        for weight in ("0", "1"):
            src = os.path.join(src_root, "meshes", "NordWar", "Companions", "%sM_%s.nif" % (base, weight))
            if not os.path.isfile(src):
                # the HIMBO archive ships no prebuilt helmet (a helmet has no body under it to refit);
                # its .tri still comes along below so BodySlide can build one
                print("  (no prebuilt %s in the HIMBO archive; skipped)" % os.path.basename(src))
                break
            copy_mesh(src, os.path.join(out, our_mesh_rel(prof, base, "M", weight)), prof["new_tex"])
            n += 1
        tri = os.path.join(src_root, "meshes", "NordWar", "Companions", "%sM.tri" % base)
        if os.path.isfile(tri):
            ours = prof["pieces"][base]
            if prof.get("sexed_dirs"):
                dst = os.path.join(out, prof["mesh_dir"], "m", "%s.tri" % ours)
            else:
                dst = os.path.join(out, prof["mesh_dir"], "%sM.tri" % ours)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(tri, dst)
            n += 1
    return n


def build_bodyslide(prof, src_root, out, kind):
    """Copy the slider sets and shape data for our pieces, renamed and retargeted."""
    sets = prof["himbo_sets"] if kind == "himbo" else prof["tba_sets"]
    prefix = "HIMBO - Legacy of Ysgramor - " if kind == "himbo" else "Legacy of Ysgramor - "
    osp_src = next((os.path.join(dp, f) for dp, dn, fn in os.walk(os.path.join(src_root, "CalienteTools", "BodySlide", "SliderSets")) for f in fn if f.lower().endswith(".osp")), None)
    if not osp_src:
        fail("%s archive has no .osp" % kind)
    tree = ET.parse(osp_src)
    root = tree.getroot()
    kept = 0
    label = "%s - %s" % (prof["title"], "HIMBO" if kind == "himbo" else "CBBE 3BA")
    for ss in list(root.findall("SliderSet")):
        name = ss.get("name", "")
        key = name[len(prefix):] if name.startswith(prefix) else None
        if key not in sets:
            root.remove(ss)
            continue
        ours = sets[key]
        new_name = "%s - %s" % (label, ours)
        ss.set("name", new_name)
        df = ss.find("DataFolder")
        sf = ss.find("SourceFile")
        op = ss.find("OutputPath")
        of = ss.find("OutputFile")
        old_folder = df.text
        df.text = new_name
        sf.text = new_name + ".nif"
        # "cuirass (no fur collar)" writes the same output file as "cuirass": the player builds one
        outfile = ours.split(" (")[0]
        if prof.get("sexed_dirs"):
            op.text = prof["mesh_dir"] + ("\\m" if kind == "himbo" else "\\f")
            of.text = outfile
        else:
            op.text = prof["mesh_dir"]
            of.text = outfile + ("M" if kind == "himbo" else "F")
        # shape data folder: renamed, meshes texture-rewritten
        sd_src = os.path.join(src_root, "CalienteTools", "BodySlide", "ShapeData", old_folder)
        sd_dst = os.path.join(out, "CalienteTools", "BodySlide", "ShapeData", new_name)
        os.makedirs(sd_dst, exist_ok=True)
        for f in os.listdir(sd_src):
            s = os.path.join(sd_src, f)
            stem, ext = os.path.splitext(f)
            d = os.path.join(sd_dst, new_name + ext)
            if ext.lower() == ".nif":
                copy_mesh(s, d, prof["new_tex"])
            else:
                shutil.copy2(s, d)
        kept += 1
    if kept != len(sets):
        fail("%s: expected %d slider sets, found %d (names in the archive changed?)" % (kind, len(sets), kept))
    ss_dir = os.path.join(out, "CalienteTools", "BodySlide", "SliderSets")
    os.makedirs(ss_dir, exist_ok=True)
    tree.write(os.path.join(ss_dir, label + ".osp"), encoding="utf-8", xml_declaration=True)
    # a slider group so BodySlide's batch build can pick them up in one go
    grp_dir = os.path.join(out, "CalienteTools", "BodySlide", "SliderGroups")
    os.makedirs(grp_dir, exist_ok=True)
    g = ET.Element("SliderGroups")
    ge = ET.SubElement(g, "Group", name=label)
    for ours in sets.values():
        ET.SubElement(ge, "Member", name="%s - %s" % (label, ours))
    ET.ElementTree(g).write(os.path.join(grp_dir, label + ".xml"), encoding="utf-8", xml_declaration=True)
    return kept


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True, choices=sorted(PROFILES))
    ap.add_argument("--out", required=True, help="package root; the option folders are created inside it")
    ap.add_argument("--refits", default=REFITS_DEFAULT)
    ap.add_argument("--first", type=int, default=30, help="number of the first option folder")
    a = ap.parse_args()
    prof = PROFILES[a.profile]
    for k, v in ARCHIVES.items():
        if not os.path.isfile(os.path.join(a.refits, v)):
            fail("missing %s in %s" % (v, a.refits))
    tmp = tempfile.mkdtemp(prefix="loy-refits-")
    try:
        himbo = os.path.join(tmp, "himbo"); tba = os.path.join(tmp, "3ba")
        extract(os.path.join(a.refits, ARCHIVES["himbo"]), himbo)
        extract(os.path.join(a.refits, ARCHIVES["3ba"]), tba)
        d1 = os.path.join(a.out, "%02d HIMBO meshes" % a.first)
        d2 = os.path.join(a.out, "%02d BodySlide - HIMBO" % (a.first + 1))
        d3 = os.path.join(a.out, "%02d BodySlide - CBBE 3BA" % (a.first + 2))
        for d in (d1, d2, d3):
            if os.path.isdir(d):
                shutil.rmtree(d)
        n1 = build_himbo_meshes(prof, himbo, d1)
        n2 = build_bodyslide(prof, himbo, d2, "himbo")
        n3 = build_bodyslide(prof, tba, d3, "3ba")
        if prof.get("nofur"):
            d4 = os.path.join(a.out, "%02d HIMBO meshes - no fur collar" % (a.first + 3))
            if os.path.isdir(d4):
                shutil.rmtree(d4)
            sub = dict(prof); sub["pieces"] = prof["nofur"]
            n4 = build_himbo_meshes(sub, himbo, d4)
            print("  HIMBO no-fur cuirass .. %d files -> %s" % (n4, os.path.basename(d4)))
        print("  HIMBO meshes .......... %d files -> %s" % (n1, os.path.basename(d1)))
        print("  BodySlide HIMBO ....... %d slider sets -> %s" % (n2, os.path.basename(d2)))
        print("  BodySlide CBBE 3BA .... %d slider sets -> %s" % (n3, os.path.basename(d3)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
