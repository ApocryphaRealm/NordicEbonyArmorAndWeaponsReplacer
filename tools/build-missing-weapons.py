#!/usr/bin/env python3
r"""Build the game meshes of the four ebony weapons Legacy of Ysgramor has no Wolf version of - the MACE, WARHAMMER,
BOW and ARROW (with the QUIVER and its six quiver arrows, and the arrow in flight) - plus first-person copies of the
Wolf weapons, at the vanilla paths under meshes\weapons\ebony\.

WHERE THE ART COMES FROM
    Every piece is cut from NordwarUA's own Wolf ebony weapons (Legacy of Ysgramor, Nexus 109963 - modification and
    asset use allowed with credit) and keeps its own UVs on the Wolf set's Xtudo-black atlases, which this mod already
    ships. No new texture. The approved designs (2026-11-14) are tools/missing_weapons/build_designs.py,
    build_round2.py and build_v1face.py. The repository carries no Legacy of Ysgramor art and no Bethesda art:
      * Legacy of Ysgramor's weapon meshes are read out of its Nexus download at build time (as build-fomod.py does);
      * the vanilla ebony meshes - the node trees, bones, collision and blood shapes the new meshes are built on - are
        read out of the player's own Skyrim - Meshes0/1.bsa.

STEPS
    1. extract the LoY weapon NIFs (Main Archive) and the vanilla ebony NIFs (game BSA) into the work folder
    2. Blender, headless: missing_weapons/build_stage.py runs the three design scripts and exports single shapes
    3. missing_weapons/assemble.py splices them into vanilla's NIFs; first-person copies of the Wolf weapons
    4. missing_weapons/verify.py: node tree, collision node, Skinned flag, texture paths, winding - fails the build

ENVIRONMENT (each optional)
    EWA_DOWNLOADS   the folder holding the Nexus downloads (default: the MO2 instance's download_directory)
    EWA_MO2         an MO2 instance folder (default D:\Modlists\Njordlinger) - its ModOrganizer.ini names the
                    downloads folder and the game folder
    SKYRIM_DATA     the game's Data folder (default: the MO2 instance's gamePath + \Data)
    BLENDER         blender.exe (default: on PATH, else the newest under Program Files\Blender Foundation)

Usage:  python tools/build-missing-weapons.py <output meshes folder> [--work <folder>]
        (build-fomod.py calls it and copies the result into the package's 00 Core)
"""
import glob, json, os, re, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
MW = os.path.join(HERE, "missing_weapons")
sys.path.insert(0, MW)

VANILLA = ["ebonymace.nif", "1stpersonebonymace.nif", "ebonywarhammer.nif", "1stpersonebonywarhammer.nif",
           "ebonybowskinned.nif", "ebonyarrow.nif", "ebonyarrowprojectile.nif",
           "ebonysword.nif", "1stpersonebonysword.nif", "ebonygreatsword.nif", "1stpersonebonygreatsword.nif",
           "ebonywaraxe.nif", "1stpersonebonywaraxe.nif", "ebonybattleaxe.nif", "1stpersonebonybattleaxe.nif",
           "ebonydagger.nif", "1stpersonebonydagger.nif", "ebonyshield.nif"]
# Legacy of Ysgramor's file -> the vanilla name this mod ships it under (as build-fomod.py MAP_WEAPONS)
LOY = {"SwordEbony.nif": "ebonysword.nif", "GreatswordEbony.nif": "ebonygreatsword.nif", "AxeEbony.nif": "ebonywaraxe.nif",
       "BattleAxeEbony.nif": "ebonybattleaxe.nif", "DaggerEbony.nif": "ebonydagger.nif", "ShieldEbony.nif": "ebonyshield.nif"}
OUTPUTS = ["ebonymace.nif", "1stpersonebonymace.nif", "ebonywarhammer.nif", "1stpersonebonywarhammer.nif",
           "ebonybowskinned.nif", "ebonyarrow.nif", "ebonyarrowprojectile.nif",
           "1stpersonebonysword.nif", "1stpersonebonygreatsword.nif", "1stpersonebonywaraxe.nif",
           "1stpersonebonybattleaxe.nif", "1stpersonebonydagger.nif"]


def fail(msg):
    raise SystemExit("build-missing-weapons: " + msg)


def mo2_ini():
    p = os.path.join(os.environ.get("EWA_MO2", r"D:\Modlists\Njordlinger"), "ModOrganizer.ini")
    return open(p, encoding="utf-8", errors="replace").read() if os.path.isfile(p) else ""


def ini_path(key):
    m = re.search(r"^%s=(.*)$" % key, mo2_ini(), re.M)
    if not m:
        return None
    v = m.group(1).strip()
    v = re.sub(r"^@ByteArray\((.*)\)$", r"\1", v).replace("\\\\", "\\")
    return v.replace("/", "\\")


def downloads():
    d = os.environ.get("EWA_DOWNLOADS") or ini_path("download_directory")
    if not d or not os.path.isdir(d):
        fail("no downloads folder - set EWA_DOWNLOADS to the folder holding the Legacy of Ysgramor download")
    return d


def game_data():
    d = os.environ.get("SKYRIM_DATA") or (ini_path("gamePath") and os.path.join(ini_path("gamePath"), "Data"))
    if not d or not os.path.isdir(d):
        fail("no game Data folder - set SKYRIM_DATA")
    return d


def blender():
    b = os.environ.get("BLENDER") or shutil.which("blender")
    if not b:
        c = sorted(glob.glob(r"C:\Program Files\Blender Foundation\Blender *\blender.exe"))
        b = c[-1] if c else None
    if not b or not os.path.isfile(b):
        fail("Blender not found - set BLENDER to blender.exe (with the PyNifly add-on installed)")
    return b


def sevenzip():
    for c in (r"C:\Program Files\7-Zip\7z.exe", r"C:\Program Files (x86)\7-Zip\7z.exe", shutil.which("7z") or ""):
        if c and os.path.isfile(c):
            return c
    fail("7-Zip not found")


def loy_meshes(work):
    dl = downloads()
    arc = [f for f in sorted(os.listdir(dl)) if "main archive se-109963" in f.lower() and f.lower().endswith(".7z")]
    if not arc:
        fail("no 'Main Archive SE-109963' in %s - download Legacy of Ysgramor's main file from Nexus first" % dl)
    tmp = os.path.join(work, "loy_x")
    p = subprocess.run([sevenzip(), "x", "-y", "-o" + tmp, os.path.join(dl, arc[-1]), "-ir!*Weapons\\*Ebony.nif"], capture_output=True, text=True)
    if p.returncode != 0:
        fail("7-Zip failed on %s:\n%s" % (arc[-1], p.stdout + p.stderr))
    found = {}
    for dp, _, fns in os.walk(tmp):
        for fn in fns:
            for src, dst in LOY.items():
                if fn.lower() == src.lower() and "companions" in dp.lower():
                    found[dst] = os.path.join(dp, fn)
    missing = [d for d in LOY.values() if d not in found]
    if missing:
        fail("Legacy of Ysgramor's archive has no %s - its layout has changed" % missing)
    out = os.path.join(work, "loy", "weapons", "ebony"); os.makedirs(out, exist_ok=True)
    for dst, src in found.items():
        shutil.copy2(src, os.path.join(out, dst))
    return os.path.join(work, "loy")


def vanilla_meshes(work):
    import bsa
    data = game_data(); want = ["meshes\\weapons\\ebony\\" + f for f in VANILLA]; got = {}
    for name in ("Skyrim - Meshes0.bsa", "Skyrim - Meshes1.bsa"):
        p = os.path.join(data, name)
        if not os.path.isfile(p):
            continue
        try:
            got.update(bsa.extract(p, [w for w in want if w not in got], strict=False))
        except Exception as e:
            fail("could not read %s: %s" % (p, e))
    missing = [w for w in want if w not in got]
    if missing:
        fail("the game's mesh archives have no %s" % missing)
    root = os.path.join(work, "vanilla")
    for w, b in got.items():
        d = os.path.join(root, w); os.makedirs(os.path.dirname(d), exist_ok=True); open(d, "wb").write(b)
    return root


def main(out_meshes, work=None):
    work = work or os.path.join(os.path.dirname(os.path.abspath(out_meshes)), "_work_missing_weapons")
    if os.path.isdir(work):
        shutil.rmtree(work)
    os.makedirs(work)
    loy = loy_meshes(work); van = vanilla_meshes(work)
    env = dict(os.environ, NEAW_LOY_MESHES=os.path.join(loy), NEAW_VANILLA=van, NEAW_WORK=os.path.join(work, "blender"))
    log = os.path.join(work, "blender.log")
    with open(log, "w", encoding="utf-8") as lf:
        r = subprocess.run([blender(), "--background", "--factory-startup", "--python-exit-code", "1", "--python",
                            os.path.join(MW, "build_stage.py"), "--", "ext=5.0", "art", "chamfer=0.8"],
                           env=env, stdout=lf, stderr=subprocess.STDOUT, cwd=MW)
    if r.returncode != 0:
        tail = open(log, encoding="utf-8", errors="replace").read()[-3000:]
        fail("the Blender stage failed (log %s):\n%s" % (log, tail))
    stage = json.load(open(os.path.join(work, "blender", "stage_report.json")))
    import assemble, verify
    vdir = os.path.join(van, "meshes", "weapons", "ebony"); ldir = os.path.join(loy, "weapons", "ebony")
    rep = assemble.build_all(os.path.join(work, "blender", "shapes"), vdir, ldir, out_meshes, stage)
    out_dir = os.path.join(out_meshes, "weapons", "ebony")
    ver, faults = verify.verify_all(out_dir, vdir)
    report = {"stage": stage, "assemble": rep, "verify": ver, "faults": faults}
    json.dump(report, open(os.path.join(work, "build_report.json"), "w"), indent=1, default=str)
    missing = [f for f in OUTPUTS if not os.path.isfile(os.path.join(out_dir, f))]
    if missing:
        fail("not built: %s" % missing)
    if faults:
        fail("%d verification fault(s) - see %s" % (faults, os.path.join(work, "build_report.json")))
    print("missing weapons built: %d files in %s (report %s)" % (len(OUTPUTS), out_dir, os.path.join(work, "build_report.json")))
    return out_dir, report


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        fail("usage: build-missing-weapons.py <output meshes folder> [--work <folder>]")
    w = a[a.index("--work") + 1] if "--work" in a else None
    main(a[0], w)
