#!/usr/bin/env python3
r"""Build the CBBE 3BA body option for a mod made from NordwarUA's Legacy of Ysgramor art (the HIMBO option was
dropped on 2026-11-15 - see main(); the text below describes how both were built).

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
        "title": "Nordic Skyforged",          # the shape-data folder names (kept: built meshes and paths unchanged)
        "display": "Truly Nordic Skyforged",  # the set and group names BodySlide shows (2026-11-16)
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
        "display": "Truly Nordic Ebony",
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


# Our own HIMBO fit (body_fits.py), per profile: (piece, our male weight-0 mesh under 00 Core, output path, output file)
HIMBO_PIECES = {
    "skyforged": [(p, "meshes\\NordicSkyforge\\armor\\%sM_0.nif" % b, "meshes\\NordicSkyforge\\armor", b + "M")
                  for p, b in (("Armor", "Armor"), ("Boots", "Boots"), ("Gauntlets", "Gauntlets"), ("1stpersonArmor", "1stpersonArmor"))],
    "ebony": [(p, "meshes\\NordicEbony\\m\\%s_0.nif" % p, "meshes\\NordicEbony\\m", p)
              for p in ("cuirass", "boots", "gauntlets", "1stpersoncuirass")],
}
NOFUR_SRC = "10 Cuirass - No fur collar"   # the Ebony collarless cuirass option (its male mesh is the HIMBO source)

# Option folders, numbered from --first (30). The "no fur collar" ones (Ebony) only change the group file / the cuirass.
OPT = {"3ba_bs": 0, "3ba_bs_nofur": 1, "3ba_mesh": 2, "3ba_mesh_nofur": 3,
       "himbo_bs": 4, "himbo_bs_nofur": 5, "himbo_mesh": 6, "himbo_mesh_nofur": 7}
OPT_NAMES = {"3ba_bs": "BodySlide - CBBE 3BA", "3ba_bs_nofur": "BodySlide - CBBE 3BA - no fur collar",
             "3ba_mesh": "CBBE 3BA meshes", "3ba_mesh_nofur": "CBBE 3BA meshes - no fur collar",
             "himbo_bs": "BodySlide - HIMBO", "himbo_bs_nofur": "BodySlide - HIMBO - no fur collar",
             "himbo_mesh": "HIMBO meshes", "himbo_mesh_nofur": "HIMBO meshes - no fur collar"}


def opt_dir(out, first, key):
    return os.path.join(out, "%02d %s" % (first + OPT[key], OPT_NAMES[key]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True, choices=sorted(PROFILES))
    ap.add_argument("--out", required=True, help="package root; the option folders are created inside it")
    ap.add_argument("--refits", default=REFITS_DEFAULT)
    ap.add_argument("--first", type=int, default=30, help="number of the first option folder")
    a = ap.parse_args()
    prof = PROFILES[a.profile]
    import body_fits as bf
    # SINCE 2026-11-15 (the owner, 21:42/21:54): Trexasle's HIMBO Conversion asks for his permission for asset use, so
    # nothing of it is packaged or read. Xonek's 3BA page says its permissions are "the same as in original mod"
    # (NordwarUA's: asset use and modification with credit), which the owner took as permission granted.
    # SINCE 2026-11-16 (the owner, 02:38): we ship our OWN HIMBO fit and prebuilt meshes for both bodies, built by
    # running BodySlide ourselves (body_fits.py). The HIMBO functions above (Trexasle's files) stay unused.
    v = ARCHIVES["3ba"]
    if not os.path.isfile(os.path.join(a.refits, v)):
        fail("missing %s in %s" % (v, a.refits))
    for k in OPT:
        if os.path.isdir(opt_dir(a.out, a.first, k)):
            shutil.rmtree(opt_dir(a.out, a.first, k))
    nofur = "nofur" in prof
    tmp = tempfile.mkdtemp(prefix="loy-refits-")
    try:
        # ---- CBBE 3BA: Xonek's sets, renamed, pointed at our own shape-data folders and .osd files
        tba = os.path.join(tmp, "3ba")
        extract(os.path.join(a.refits, ARCHIVES["3ba"]), tba)
        d3 = opt_dir(a.out, a.first, "3ba_bs")
        n3 = build_bodyslide(prof, tba, d3, "3ba")
        bs3 = os.path.join(d3, "CalienteTools", "BodySlide")
        n_sets, n_data = bf.fix_3ba(bs3)
        label3 = "%s - CBBE 3BA" % prof["title"]
        main3 = ["%s - %s" % (label3, o) for o in prof["tba_sets"].values() if " (" not in o]
        # one cuirass per group: the collarless set writes the same file, and BodySlide stops to ask which to build
        bf.write_groups(bs3, label3, main3, ["CBBE", "3BA"])
        print("  BodySlide CBBE 3BA .... %d slider sets, %d slider entries on our own .osd -> %s" % (n3, n_data, os.path.basename(d3)))
        if nofur:
            alt = [m if not m.endswith(" - cuirass") else m + " (no fur collar)" for m in main3]
            bf.write_groups(os.path.join(opt_dir(a.out, a.first, "3ba_bs_nofur"), "CalienteTools", "BodySlide"), label3, alt, ["CBBE", "3BA"])

        # ---- HIMBO: our own conversion and conform (body_fits.himbo_project)
        core = os.path.join(a.out, "00 Core")
        labelh = "%s - HIMBO" % prof["title"]
        pieces = [(p, os.path.join(core, src), op, of) for p, src, op, of in HIMBO_PIECES[a.profile]]
        if nofur:
            pieces.append(("cuirass (no fur collar)", os.path.join(a.out, NOFUR_SRC, "meshes", "NordicEbony", "m", "cuirass_0.nif"),
                           "meshes\\NordicEbony\\m", "cuirass"))
        for p in pieces:
            if not os.path.isfile(p[1]):
                fail("HIMBO source mesh missing: %s" % p[1])
        dh = opt_dir(a.out, a.first, "himbo_bs")
        bsh = os.path.join(dh, "CalienteTools", "BodySlide")
        names, rep = bf.himbo_project(labelh, pieces, bsh, os.path.join(tmp, "himbo"))
        mainh = [n for n in names if " (" not in n.split(" - ")[-1]]
        bf.write_groups(bsh, labelh, mainh, ["HIMBO"])
        print("  BodySlide HIMBO ....... %d slider sets (our conversion; vertices pushed out for clearance: %s) -> %s"
              % (len(names), ", ".join("%s %d" % r for r in rep), os.path.basename(dh)))
        if nofur:
            alt = [m if not m.endswith(" - cuirass") else m + " (no fur collar)" for m in mainh]
            bf.write_groups(os.path.join(opt_dir(a.out, a.first, "himbo_bs_nofur"), "CalienteTools", "BodySlide"), labelh, alt, ["HIMBO"])

        # ---- prebuilt meshes, BodySlide run from a staging copy (no MO2)
        bs = bf.staging(os.path.join(tmp, "stage"))
        bf.add_project(bs, bs3); bf.add_project(bs, bsh)
        jobs = [("3ba_mesh", label3, bf.PRESET_3BA), ("himbo_mesh", labelh, bf.PRESET_HIMBO)]
        for key, group, preset in jobs:
            built = bf.run_bodyslide(bs, group, preset, opt_dir(a.out, a.first, key))
            print("  %-22s %d files (BodySlide, preset '%s') -> %s" % (OPT_NAMES[key], len(built), preset, os.path.basename(opt_dir(a.out, a.first, key))))
        if nofur:
            for key, bskey, group, preset in (("3ba_mesh_nofur", "3ba_bs_nofur", label3, bf.PRESET_3BA),
                                              ("himbo_mesh_nofur", "himbo_bs_nofur", labelh, bf.PRESET_HIMBO)):
                bf.add_project(bs, os.path.join(opt_dir(a.out, a.first, bskey), "CalienteTools", "BodySlide"))
                tgt = opt_dir(a.out, a.first, key)
                bf.run_bodyslide(bs, group, preset, tgt)
                # keep only the cuirass: the rest is the same as the main option's
                for dp, _, fs in os.walk(tgt):
                    for f in fs:
                        if not f.lower().startswith("cuirass"):
                            os.remove(os.path.join(dp, f))
                print("  %-22s cuirass only -> %s" % (OPT_NAMES[key], os.path.basename(tgt)))
        # the names BodySlide shows -> the Truly Nordic names, now that every prebuilt mesh is built (bf.rename_display)
        for key in ("3ba_bs", "3ba_bs_nofur", "himbo_bs", "himbo_bs_nofur"):
            d = os.path.join(opt_dir(a.out, a.first, key), "CalienteTools", "BodySlide")
            if os.path.isdir(d):
                bf.rename_display(d, prof["title"], prof["display"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
