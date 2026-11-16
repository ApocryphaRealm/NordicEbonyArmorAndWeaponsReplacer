#!/usr/bin/env python3
r"""Assemble the FOMOD installer for Nordic Ebony Armor and Weapons Replacer.

WHAT THIS PACKAGES
    NordwarUA's wolf EBONY armour and weapons from Legacy of Ysgramor (Nexus 109963), moved onto
    the vanilla ebony mesh paths so they replace the game's ebony gear, in an all-black look of our
    own: NordwarUA's ORIGINAL diffuses recoloured by tools/recolour_black.py (the owner, 2026-11-15
    21:54 - Xtudo's black colourway needs his permission, so none of his files is read or shipped),
    and since 1.1.0 as Community Shaders TRUEPBR materials (the owner 21:55; tools/truepbr.py):
    albedo + his normal + RMAOS under textures\pbr\NordicEbony\.

    The armour's worn models go through the light plugin's four ADDON overrides (build-arma-esl.py);
    the weapons are loose meshes at the vanilla paths. The four ebony weapons Legacy of Ysgramor has
    no Wolf version of - mace, warhammer, bow, arrow (with the quiver) - are BUILT from the Wolf
    weapons' own pieces by build-missing-weapons.py, which this script runs; first-person copies of
    the Wolf weapons come from it too. (The optional "hide unmatched weapons" plugin, which took those
    four out of the levelled lists and recipes, was retired in 1.1.0 before it was ever posted - build-hide-esp.py and
    verify-hide-esp.py stay in git history.)

    TEXTURES AT 2K ONLY (the owner, 2026-11-14): NordwarUA ships one resolution (2K, some 1K), made
    into PBR maps at that size and installed with the core; the build refuses any DDS larger than 2048.

    BODY OPTIONS: only the CBBE 3BA BodySlide files (Xonek, 111209 - "the same as in original mod",
    the owner 21:54: permission granted). The HIMBO conversion (Trexasle, 110002) is not shipped;
    the page points at it.

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
import struct
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET


def supersede(folder):
    """NEVER DELETE A PACKAGE (2026-10-25): the package folder this build replaces is MOVED to
    <project>/_work/superseded-packages/<date>/ - <project> being the nearest folder above it that has a _work folder
    (SUPERSEDED_PACKAGES_DIR overrides; with neither, a _superseded folder beside it) - and stays there until someone
    clears it by hand. This script used to shutil.rmtree it."""
    import time
    root = os.environ.get("SUPERSEDED_PACKAGES_DIR")
    here = os.path.dirname(os.path.abspath(folder))
    p = here
    while not root:
        if os.path.isdir(os.path.join(p, "_work")):
            root = os.path.join(p, "_work", "superseded-packages")
        elif os.path.dirname(p) == p:
            root = os.path.join(here, "_superseded")
        else:
            p = os.path.dirname(p)
    day = os.path.join(root, time.strftime("%Y-%m-%d"))
    os.makedirs(day, exist_ok=True)
    to = base = os.path.join(day, "%s (replaced %s)" % (os.path.basename(os.path.normpath(folder)), time.strftime("%H%M%S")))
    i = 2
    while os.path.exists(to):
        to, i = "%s %d" % (base, i), i + 1
    shutil.move(folder, to)
    print("the package this build replaces was moved to %s (never deleted)" % to)
    return to

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))
def _mo2_downloads():
    """the MO2 instance's own download_directory (EWA_MO2, default the Njordlinger instance)"""
    ini = os.path.join(os.environ.get("EWA_MO2", r"D:\Modlists\Njordlinger"), "ModOrganizer.ini")
    if os.path.isfile(ini):
        m = re.search(r"^download_directory=(.*)$", open(ini, encoding="utf-8", errors="replace").read(), re.M)
        if m:
            return m.group(1).strip().replace("/", os.sep)
    return r"D:\modlists\Njordlinger\downloads"


DOWNLOADS = os.environ.get("EWA_DOWNLOADS") or _mo2_downloads()
SEVENZIP = [r"C:\Program Files\7-Zip\7z.exe", r"C:\Program Files (x86)\7-Zip\7z.exe", "7z"]

# Source archives, by a fragment of their Nexus file name.
A_BASE = "Main Archive SE-109963"                      # NordwarUA - meshes, diffuses, normals, masks
A_FURFIX = "Patch Fur Lighting Bug-109963"             # NordwarUA - corrected FurCollar_n
MAX_DDS = 2048                                         # the owner: "in 2K and not 4K"
PBR_FOLDER = "NordicEbony"                             # textures\pbr\NordicEbony\
OLD_TEX = ("textures\\nordwar\\companions\\",)          # the set's classic texture folder (converted away)

# The ebony war axe's haft uses the STEEL axe diffuse (Axe1H), so it is recoloured and made PBR along
# with the ebony atlases. Found by reading the mesh, not by guessing.

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
IMAGES = ("header.png", "fur.png", "nofur.png", "cbbe3ba.png")   # tools/installer-images.py


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
            "Nordic Ebony Armor and Weapons Replacer %s" % ver))
    if os.path.isdir(out_root):
        supersede(out_root)
    work = os.path.join(out_root, "_work")

    base = extract(A_BASE, os.path.join(work, "base"))
    furfix = extract(A_FURFIX, os.path.join(work, "furfix"))

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

    # the shield to the Truly Nordic Carved "Shield - Clean" face size (the owner, 2026-11-15) - scaled about its grip
    # in place, before build-missing-weapons.py verifies the weapons folder; see missing_weapons/shield_size.py
    sys.path.insert(0, os.path.join(HERE, "missing_weapons"))
    import shield_size
    sh = shield_size.resize(os.path.join(core, "meshes", "weapons", "ebony", "ebonyshield.nif"))
    print("  shield ................ rim %.2f -> %.2f (x%.4f about %s)" % (
        sh["rim_diameter_before"], sh["rim_diameter_after"], sh["scale"], sh["pivot"]))

    # the mace, warhammer, bow, arrow / quiver / arrow in flight, and first-person copies of the Wolf
    # weapons - built from the Wolf weapons' own pieces (build-missing-weapons.py)
    import importlib.util
    spec = importlib.util.spec_from_file_location("bmw", os.path.join(HERE, "build-missing-weapons.py"))
    bmw = importlib.util.module_from_spec(spec); spec.loader.exec_module(bmw)
    mw_dir, mw_report = bmw.main(os.path.join(core, "meshes"), os.path.join(work, "missing-weapons"))
    for fn in bmw.OUTPUTS:
        shipped.append(os.path.join(mw_dir, fn))
    n_built = len(bmw.OUTPUTS)
    n_nofur = place(MAP_NOFUR, os.path.join(out_root, "10 Cuirass - No fur collar"))

    # The worn armour again under our own folder, which is where the light plugin points vanilla's
    # four ebony armour ADDON records. Both copies are wanted: the plugin governs the armour as it
    # is worn, while ground models and the weapons - which have no addon record and name their
    # meshes directly - still read the vanilla paths. Meshes are megabytes against a package of 2K
    # textures, so the duplication is not worth engineering away.
    n_ours = 0
    for sex in ("m", "f"):
        src = os.path.join(core, "meshes", "armor", "ebony", sex)
        if not os.path.isdir(src):
            continue
        dest = os.path.join(core, "meshes", "NordicEbony", sex)
        os.makedirs(dest, exist_ok=True)
        for fn in os.listdir(src):
            if fn.lower().endswith(".nif") and "gnd" not in fn.lower():
                shutil.copy2(os.path.join(src, fn), os.path.join(dest, fn))
                n_ours += 1

    # The collarless option must ALSO ship its worn cuirass under our folder: the plugin points the worn cuirass at
    # NordicEbony\<sex>\Cuirass_*.nif, so a copy on the vanilla path alone changed only the ground model (found
    # 2026-11-15 before posting). The option's files overwrite the core's (FOMOD install order).
    nofur = os.path.join(out_root, "10 Cuirass - No fur collar", "meshes")
    for sex in ("m", "f"):
        src = os.path.join(nofur, "armor", "ebony", sex)
        if not os.path.isdir(src):
            continue
        dest = os.path.join(nofur, "NordicEbony", sex)
        os.makedirs(dest, exist_ok=True)
        for fn in os.listdir(src):
            if fn.lower().endswith(".nif") and "gnd" not in fn.lower():
                shutil.copy2(os.path.join(src, fn), os.path.join(dest, fn))
    if not os.path.isfile(os.path.join(nofur, "NordicEbony", "m", "cuirass_1.nif")):
        fail("the collarless option has no worn cuirass under meshes\\NordicEbony - the option would change nothing worn")

    main_esl = os.path.join(REPO, "plugin", "Nordic Ebony Armor and Weapons Replacer.esp")
    if not os.path.isfile(main_esl):
        fail("the light plugin is missing - run tools/build-arma-esl.py first, or the worn armour "
             "would keep pointing at vanilla's own meshes")
    # The plugin is one side of the installer's required "Plugin" choice (the owner, 2026-11-16 02:43: an ESP and a
    # no-ESP version using SkyPatcher). The other side, "02 Plugin - SkyPatcher", is the repo's skypatcher\ INIs:
    # the worn meshes are on the vanilla paths already (above), so without the plugin they need only the helmet's
    # body-slot fix, plus the Ebony Mail and Ryn's Snazzy Last Vigil swaps. Neither folder may hold what the other does.
    esp_dir = os.path.join(out_root, "01 Plugin - ESP")
    os.makedirs(esp_dir, exist_ok=True)
    shutil.copy2(main_esl, esp_dir)
    sp_src = os.path.join(REPO, "skypatcher")
    sp_dir = os.path.join(out_root, "02 Plugin - SkyPatcher", "SKSE", "Plugins", "SkyPatcher")
    n_sp = 0
    for dp, _, fs in os.walk(sp_src):
        for f in fs:
            if not f.lower().endswith(".ini"):
                fail("skypatcher\\ holds '%s' - only .ini files go there" % f)
            d = os.path.join(sp_dir, os.path.relpath(os.path.join(dp, f), sp_src))
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(os.path.join(dp, f), d)
            n_sp += 1
    if not os.path.isfile(os.path.join(sp_dir, "armor", "TrulyNordicEbony", "TrulyNordicEbony.ini")):
        fail("the no-ESP option has no helmet slot fix - the open helm would show an invisible head")
    for dp, _, fs in os.walk(os.path.join(out_root, "02 Plugin - SkyPatcher")):
        if any(f.lower().endswith((".esp", ".esm", ".esl")) for f in fs):
            fail("the no-ESP option holds a plugin")

    # ---- body option: CBBE 3BA BodySlide files (Xonek, Nexus 111209); see tools/loy-refits.py. Built before the
    # textures, because its shape data names the same materials and is converted to TruePBR with the rest.
    r = subprocess.run([sys.executable, os.path.join(HERE, "loy-refits.py"), "--profile", "ebony",
                        "--out", out_root, "--first", "30"], capture_output=True, text=True)
    if r.returncode != 0:
        fail("body options failed:\n" + (r.stdout + r.stderr).strip())
    for line in r.stdout.strip().splitlines():
        print(line)

    # ---- textures: every material the shipped meshes use, found by reading them (never a hand list), made into our
    # black recolour as TruePBR maps from NordwarUA's own files; then every shader of ours is converted (tools/truepbr.py)
    import truepbr
    mesh_roots = [os.path.join(out_root, d) for d in sorted(os.listdir(out_root))
                  if os.path.isdir(os.path.join(out_root, d)) and d[:2].isdigit()]
    mats = truepbr.scan(mesh_roots, OLD_TEX)
    if not mats:
        fail("no shipped mesh names a texture of the set - the scan is looking in the wrong place")

    def find_src(stem):
        """NordwarUA's file by name: the Fur Lighting Bug patch's FurCollar_n wins over the main archive's"""
        for root in (furfix, base):
            p = ci_find(root, "textures/NordWar/Companions/%s.dds" % stem)
            if p:
                return p
        return None
    truepbr.build_textures(mats, find_src, "ebony", PBR_FOLDER, core, os.path.join(work, "pbr"))
    n_files, n_shaders = truepbr.convert(mesh_roots, OLD_TEX, PBR_FOLDER)
    n_ok = truepbr.verify(mesh_roots, OLD_TEX, PBR_FOLDER, [core])
    found = 0; biggest = 0
    for dp, _, fs in os.walk(os.path.join(core, "textures")):
        for f in fs:
            hdr = open(os.path.join(dp, f), "rb").read(20)
            h, w = struct.unpack_from("<II", hdr, 12)
            if hdr[:4] != b"DDS " or max(w, h) > MAX_DDS:
                fail("'%s' is %dx%d - this mod ships 2K textures only" % (f, w, h))
            biggest = max(biggest, w, h); found += 1

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

    for name in ("README.md", "NOTICE.md", "CHANGELOG.md", "LICENSE"):
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
    print("  mirrored under ours ... %d" % n_ours)
    print("  light plugin .......... %s (option 01; option 02 is %d SkyPatcher INIs)" % (os.path.basename(main_esl), n_sp))
    print("  built weapon meshes ... %d (mace, warhammer, bow, arrow + quiver, flight, 1st-person copies)" % n_built)
    print("  TruePBR ............... %d materials, %d shaders in %d meshes converted, %d verified" % (len(mats), n_shaders, n_files, n_ok))
    print("  textures, 2K only ..... %d (largest %d px), under textures\\pbr\\%s" % (found, biggest, PBR_FOLDER))
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
