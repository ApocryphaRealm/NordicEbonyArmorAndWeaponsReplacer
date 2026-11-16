r"""Full-3D build, step 0 for a set (NSET=ebony|skyforged): snapshot the package files the build reads, decode the set's
textures to src_png\, and NordwarUA's _m maps from the Legacy of Ysgramor main archive to src_png\orig\.
Existing src_png files are kept (the Ebony demo's armour PNGs predate its chain-link texture and its 3D build is made
from them); --force re-decodes."""
import os, sys, shutil, subprocess, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sets
C = sets.get(); FORCE = "--force" in sys.argv
SEVENZIP = r"C:\Program Files\7-Zip\7z.exe"


def decode(src, dst_dir, srgb):
    os.makedirs(dst_dir, exist_ok=True)
    r = subprocess.run([sets.TEXCONV, "-nologo", "-y", "-ft", "png", "-f", "R8G8B8A8_UNORM_SRGB" if srgb else "R8G8B8A8_UNORM", "-o", dst_dir, src],
                       capture_output=True, text=True)
    out = os.path.join(dst_dir, os.path.splitext(os.path.basename(src))[0] + ".png")
    assert r.returncode == 0 and os.path.isfile(out), r.stdout + r.stderr
    return out


def snap():
    n = 0
    for pc in C.pieces:
        for rel in pc["files"]:
            s = C.src_of(rel, pc.get("opt")); d = C.snap_of(rel, pc.get("opt"))
            if not os.path.isfile(s): print("MISSING", s); continue
            os.makedirs(os.path.dirname(d), exist_ok=True); shutil.copy2(s, d); n += 1
    td = os.path.join(C.core, C.tex); sd = os.path.join(C.snap, C.tex); os.makedirs(sd, exist_ok=True)
    for f in os.listdir(td): shutil.copy2(os.path.join(td, f), sd)
    print("snapshot", n, "meshes +", len(os.listdir(td)), "textures")


def textures():
    td = os.path.join(C.core, C.tex)
    ats = list(sets.ARMOUR) + C.weapon_atlases
    for at in ats:
        for stem, srgb in ((C.alb(at), True), (C.alb(at) + "_rmaos", False), (C.nrm(at), False)):
            d = os.path.join(C.src, stem + ".png")
            if os.path.isfile(d) and not FORCE: continue
            s = os.path.join(td, stem + ".dds")
            if not os.path.isfile(s): print("NO TEXTURE", s); continue
            decode(s, C.src, srgb); print("decoded", stem)
    # NordwarUA's _m (environment masks: bright = shiny metal; chain rings bright, gaps black)
    tmp = tempfile.mkdtemp(prefix="loy_m_")
    want = {at: f for at, f in C.m_src.items() if FORCE or not os.path.isfile(C.mfile(at))}
    if want:
        r = subprocess.run([SEVENZIP, "e", "-y", "-r", "-o" + tmp, sets.ARCHIVE] + list(want.values()), capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        for at, f in want.items():
            p = os.path.join(tmp, f)
            if not os.path.isfile(p): print("NOT IN ARCHIVE", f); continue
            png = decode(p, tmp, False); os.makedirs(C.orig, exist_ok=True); shutil.move(png, C.mfile(at)); print("m", at, "<-", f)
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    snap(); textures()
