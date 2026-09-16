#!/usr/bin/env python3
r"""Assemble the FOMOD installer for Ebony Wolf Armor and Weapons.

WHAT THIS PACKAGES
    NordwarUA's wolf EBONY armour and weapons from Legacy of Ysgramor (Nexus 109963), moved onto
    the vanilla ebony mesh paths so they replace the game's ebony gear, in Xtudo's all-black
    colourway from Nexus 111121 (Ebony Black + Full Collar Black).

    No plugin is needed for the replacement itself - it is a mesh swap. The one plugin this mod can
    install is OPTIONAL and does something else entirely; see build-hide-esl.py.

WHY IT READS ARCHIVES INSTEAD OF SHIPPING FILES
    None of the art is ours. The repository carries none of it: this script opens the Nexus
    downloads at build time and takes only what the shipped meshes actually reference.

THE TEXTURE LIST IS DERIVED, NOT WRITTEN DOWN
    Every texture in the package is found by reading the texture paths out of the .nif files that
    are being shipped. Hand-listing them is how a replacer ends up with one shape rendering purple
    in game: the ebony WAR AXE, for instance, uses the STEEL axe's diffuse for its haft, which no
    amount of reasoning about "the ebony set" would have predicted.

WHAT IT REFUSES TO DO
    * ship if a download is missing;
    * ship if any vanilla ebony mesh path this mod claims to replace has no source mesh;
    * ship if a texture a shipped mesh references cannot be found in any source archive;
    * ship if any folder ModuleConfig.xml installs from came out missing or empty;
    * ship if an installer image the XML points at is absent.

Usage:  python tools/build-fomod.py [output folder]
"""
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))
DOWNLOADS = os.environ.get("EWA_DOWNLOADS", r"D:\modlists\Njordlinger\downloads")
SEVENZIP = [r"C:\Program Files\7-Zip\7z.exe", r"C:\Program Files (x86)\7-Zip\7z.exe", "7z"]

# Source archives, by a fragment of their Nexus file name.
A_BASE = "Main Archive SE-109963"                      # NordwarUA - meshes, normals, masks
A_FURFIX = "Patch Fur Lighting Bug-109963"             # NordwarUA - corrected FurCollar_n
A_COLLAR = "Color - Full Collar Black-111121"          # Xtudo - the black fur collar
A_EBONY = {"1K": "Color - Ebony Black 1K-111121",      # Xtudo - the black ebony diffuses
           "2K": "Color - Ebony Black 2K-111121",
           "4K": "Color - Ebony Black 4K-111121"}
A_WOLF = {"1K": "Color - Wolf Black 1K-111121",        # for Axe1H.dds - see AXE_NOTE below
          "2K": "Color - Wolf Black 2K-111121",
          "4K": "Color - Wolf Black 4K-111121"}

# The ebony war axe's haft uses the STEEL axe diffuse, so an "all black" ebony set needs one file
# out of the Wolf Black download as well. Found by reading the mesh, not by guessing.
AXE_NOTE = "textures\\nordwar\\companions\\axe1h.dds"

SRC = "meshes/NordWar/Companions"

# source mesh (under SRC) -> the vanilla path it replaces. _1 entries imply their _0 twin on both
# sides; the build expands them.
MAP_ARMOR = {
    "ArmorEbonyM_1.nif": "armor/ebony/m/cuirass_1.nif",
    "ArmorEbonyF_1.nif": "armor/ebony/f/cuirass_1.nif",
    "1stpersonArmorEbonyM_1.nif": "armor/ebony/m/1stpersoncuirass_1.nif",
    "1stpersonArmorEbonyF_1.nif": "armor/ebony/f/1stpersoncuirass_1.nif",
    "BootsEbonyM_1.nif": "armor/ebony/m/boots_1.nif",
    "BootsEbonyF_1.nif": "armor/ebony/f/boots_1.nif",
    "GauntletsEbonyM_1.nif": "armor/ebony/m/gauntlets_1.nif",
    "GauntletsEbonyF_1.nif": "armor/ebony/f/gauntlets_1.nif",
    "EbonyHelmetM_1.nif": "armor/ebony/m/helmet_1.nif",
    "EbonyHelmetF_1.nif": "armor/ebony/f/helmet_1.nif",
    "ArmorEbony_Gnd.nif": "armor/ebony/m/cuirassgnd.nif",
    "BootsEbony_Gnd.nif": "armor/ebony/m/bootsgnd.nif",
    "GauntletsEbony_Gnd.nif": "armor/ebony/m/gauntletsgnd.nif",
    "EbonyHelmet_Gnd.nif": "armor/ebony/m/helmetgnd.nif",
}

# The fur-collared cuirass is the default; NordwarUA also ships a collarless one, so the installer
# offers it. Only the cuirass has the two versions.
MAP_NOFUR = {
    "ArmorNoFurEbonyM_1.nif": "armor/ebony/m/cuirass_1.nif",
    "ArmorNoFurEbonyF_1.nif": "armor/ebony/f/cuirass_1.nif",
    "ArmorNoFurEbony_Gnd.nif": "armor/ebony/m/cuirassgnd.nif",
}

MAP_WEAPONS = {
    "Weapons/SwordEbony.nif": "weapons/ebony/ebonysword.nif",
    "Weapons/GreatswordEbony.nif": "weapons/ebony/ebonygreatsword.nif",
    "Weapons/AxeEbony.nif": "weapons/ebony/ebonywaraxe.nif",
    "Weapons/BattleAxeEbony.nif": "weapons/ebony/ebonybattleaxe.nif",
    "Weapons/DaggerEbony.nif": "weapons/ebony/ebonydagger.nif",
    "Weapons/ShieldEbony.nif": "weapons/ebony/ebonyshield.nif",
}

# Vanilla supplies these; shipping them would override the player's own texture mods for no reason.
VANILLA_TEXTURES = ("textures\\blood\\", "textures\\cubemaps\\eyecubemap.dds")

TEXPAT = re.compile(rb"[Tt]extures.{1,180}?\.dds")
IMAGES = ("header.png", "fur.png", "nofur.png")


def fail(msg):
    raise SystemExit("build-fomod: " + msg)


def sevenzip():
    for c in SEVENZIP:
        if os.path.isfile(c):
            return c
        if shutil.which(c):
            return shutil.which(c)
    fail("7-Zip not found - install it, or put 7z on PATH")


def version():
    """The version lives in fomod/info.xml, which is what version-gate.ps1 stamps for this mod."""
    t = open(os.path.join(REPO, "fomod", "info.xml"), encoding="utf-8").read()
    m = re.search(r"<Version>\s*(\d+\.\d+\.\d+)\s*</Version>", t)
    if not m:
        fail("no <Version>x.y.z</Version> in fomod/info.xml - the version location has moved")
    return m.group(1)


def find_archive(fragment):
    for fn in sorted(os.listdir(DOWNLOADS)):
        if fragment.lower() in fn.lower() and fn.lower().endswith(".7z"):
            return os.path.join(DOWNLOADS, fn)
    fail("no archive matching '%s' in %s - download it from Nexus first" % (fragment, DOWNLOADS))


def extract(fragment, dest):
    os.makedirs(dest, exist_ok=True)
    p = subprocess.run([sevenzip(), "x", "-y", "-o" + dest, find_archive(fragment)],
                       capture_output=True, text=True)
    if p.returncode != 0:
        fail("7-Zip failed on %s:\n%s" % (fragment, p.stdout + p.stderr))
    # Some of these archives wrap everything in a Data\ folder and some do not. Flatten it so the
    # rest of the script only ever deals with one layout.
    data = os.path.join(dest, "Data")
    if os.path.isdir(data):
        for name in os.listdir(data):
            target = os.path.join(dest, name)
            if os.path.isdir(target):
                for dp, _, fns in os.walk(os.path.join(data, name)):
                    for fn in fns:
                        s = os.path.join(dp, fn)
                        d = os.path.join(target, os.path.relpath(s, os.path.join(data, name)))
                        os.makedirs(os.path.dirname(d), exist_ok=True)
                        shutil.move(s, d)
            else:
                shutil.move(os.path.join(data, name), target)
        shutil.rmtree(data, ignore_errors=True)
    return dest


def ci_find(root, rel):
    """Case-insensitive lookup - these archives mix Textures\\ and textures\\ freely."""
    cur = root
    for part in rel.replace("\\", "/").split("/"):
        if not part:
            continue
        entries = os.listdir(cur) if os.path.isdir(cur) else []
        match = next((e for e in entries if e.lower() == part.lower()), None)
        if match is None:
            return None
        cur = os.path.join(cur, match)
    return cur


def expand(mapping):
    """_1 entries imply their _0 twin on both sides."""
    out = {}
    for src, dst in mapping.items():
        out[src] = dst
        if src.endswith("_1.nif"):
            out[src[:-6] + "_0.nif"] = dst[:-6] + "_0.nif"
    return out


def main(out_root=None, test=False):
    """test=True is for a build meant only for the owner's own MO2, before the pictures exist.

    It skips the installer-image check and nothing else. A package built this way is NOT
    shippable - the installer would show empty panes - and the script says so loudly.
    """
    ver = version()
    if out_root is None:
        out_root = os.path.normpath(os.path.join(
            REPO, "..", "..", "7. current test builds",
            "Ebony Wolf Armor and Weapons %s" % ver))
    if os.path.isdir(out_root):
        shutil.rmtree(out_root)
    work = os.path.join(out_root, "_work")

    base = extract(A_BASE, os.path.join(work, "base"))
    furfix = extract(A_FURFIX, os.path.join(work, "furfix"))
    collar = extract(A_COLLAR, os.path.join(work, "collar"))
    ebony = {k: extract(v, os.path.join(work, "ebony" + k)) for k, v in A_EBONY.items()}
    wolf = {k: extract(v, os.path.join(work, "wolf" + k)) for k, v in A_WOLF.items()}

    # ---- meshes, onto the vanilla paths
    core = os.path.join(out_root, "00 Core")
    shipped = []

    def place(mapping, dest_root):
        n = 0
        for src, dst in expand(mapping).items():
            s = ci_find(base, SRC + "/" + src)
            if s is None:
                fail("Legacy of Ysgramor has no '%s' - its layout has changed, and the vanilla "
                     "path '%s' would be left showing the old ebony armour" % (src, dst))
            d = os.path.join(dest_root, "meshes", dst.replace("/", os.sep))
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)
            shipped.append(s)
            n += 1
        return n

    n_core = place(MAP_ARMOR, core) + place(MAP_WEAPONS, core)
    n_nofur = place(MAP_NOFUR, os.path.join(out_root, "10 Cuirass - No fur collar"))

    # ---- textures, derived from the meshes rather than listed by hand
    wanted = set()
    for s in shipped:
        for m in TEXPAT.findall(open(s, "rb").read()):
            p = m.decode("latin-1").replace("/", "\\").lower()
            if not any(p.startswith(v) or p == v for v in VANILLA_TEXTURES):
                wanted.add(p)

    # Which of them the colour downloads replace, and which come from the base mod as-is.
    def sources_for(res):
        """Search order matters: the colour packs win over the base mod's own textures."""
        return [collar, ebony[res], wolf[res], furfix, base]

    n_tex = {}
    for res in ("1K", "2K", "4K"):
        dest = os.path.join(out_root, "0%d Textures - %s" % (1 + ("1K", "2K", "4K").index(res), res))
        found = 0
        for rel in sorted(wanted):
            src = None
            for root in sources_for(res):
                src = ci_find(root, rel)
                if src:
                    break
            if src is None:
                fail("a shipped mesh asks for '%s' and no source archive has it - in game that "
                     "shape renders purple" % rel)
            d = os.path.join(dest, rel.replace("\\", os.sep))
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(src, d)
            found += 1
        n_tex[res] = found

    # ---- the optional plugin
    esl = os.path.join(REPO, "plugin", "Ebony Wolf - Hide Unmatched Weapons.esp")
    if os.path.isfile(esl):
        d = os.path.join(out_root, "20 Hide unmatched ebony weapons")
        os.makedirs(d, exist_ok=True)
        shutil.copy2(esl, d)

    # ---- fomod
    fomod = os.path.join(out_root, "fomod")
    os.makedirs(os.path.join(fomod, "images"), exist_ok=True)
    shutil.copy2(os.path.join(REPO, "fomod", "ModuleConfig.xml"), fomod)
    shutil.copy2(os.path.join(REPO, "fomod", "info.xml"), fomod)
    for img in IMAGES:
        s = os.path.join(REPO, "fomod", "images", img)
        if not os.path.isfile(s):
            if not test:
                fail("installer image '%s' is missing - the FOMOD is supposed to show the player "
                     "what he is choosing between. Pass --test to build anyway for local testing."
                     % img)
            continue
        shutil.copy2(s, os.path.join(fomod, "images", img))

    for name in ("NOTICE.md", "CHANGELOG.md", "LICENSE"):
        shutil.copy2(os.path.join(REPO, name), os.path.join(out_root, name))

    # ---- every folder the installer names must exist and hold files
    root = ET.parse(os.path.join(fomod, "ModuleConfig.xml")).getroot()
    sources = sorted({e.get("source") for e in root.iter("folder") if e.get("source")})
    for s in sources:
        p = os.path.join(out_root, s.replace("\\", os.sep).replace("/", os.sep))
        if not os.path.isdir(p) or not any(
                os.path.isfile(os.path.join(dp, f)) for dp, _, fs in os.walk(p) for f in fs):
            if not test:
                fail("ModuleConfig.xml installs from '%s', but the package has nothing there" % s)
            print("  !! --test: nothing in '%s'" % s)
    for e in list(root.iter("image")) + list(root.iter("moduleImage")):
        if not os.path.isfile(os.path.join(out_root, e.get("path").replace("\\", os.sep))):
            if not test:
                fail("ModuleConfig.xml shows '%s', which is not in the package" % e.get("path"))

    shutil.rmtree(work, ignore_errors=True)
    total = sum(len(fs) for _, _, fs in os.walk(out_root))
    print("built %s" % out_root)
    print("  version ............... %s" % ver)
    print("  meshes on vanilla paths %d, plus %d for the collarless cuirass" % (n_core, n_nofur))
    print("  textures per resolution %d  (1K/2K/4K)" % n_tex["2K"])
    print("  optional plugin ....... %s" % ("yes" if os.path.isfile(esl) else "NOT BUILT"))
    print("  installer sources ..... %d, every one present" % len(sources))
    print("  files ................. %d" % total)
    return out_root


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--test"]
    is_test = "--test" in sys.argv[1:]
    out = main(args[0] if args else None, test=is_test)
    if is_test:
        print()
        print("  *** --test: built WITHOUT the installer images. Not shippable. ***")
