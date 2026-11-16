r"""Before/after renders of a set's full-3D build (NSET): shipped (pkg_snapshot) | full 3D (build\exp_root = the snapshot's
textures with the 3D textures over them + the built meshes), same camera and light, per render piece (sets.py "render").
  py -3 render_set.py root                       build exp_root
  py -3 render_set.py job <piece> [yaw] [pitch]  write render\f3d_<piece>.json (SAMPLES env, default 64)
  py -3 render_set.py all                        root + every job + decode + Blender render (render_chain.py)
Views are FRONT views (yaw per item below: the armour is turned to stand upright facing the camera)."""
import os, sys, json, shutil, subprocess
T = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, T)
import sets
C = sets.get(); EXP = os.path.join(C.build, "exp_root")
ARM_ROT = [-90, 180, 0]
# piece -> (yaw, pitch, W, H, rot)
VIEW = {"helmet": (0, 5, 1100, 1100, ARM_ROT), "cuirass": (0, 3, 1100, 1540, ARM_ROT), "gauntlets": (0, 5, 1000, 1000, ARM_ROT),
        "boots": (0, 5, 1000, 1000, ARM_ROT), "1stpersoncuirass": (0, 5, 1100, 1100, ARM_ROT), "shield": (180, 0, 1100, 1100, [0, 0, 0])}
WEAPON = (0, 0, 560, 1800, [0, 0, 0])   # blade up, flat to the camera; the sheath (Scb) hidden


def rels(piece):
    pc = next(p for p in C.pieces if p.get("render") == piece); return pc["files"][0], pc


def root():
    if os.path.isdir(EXP): shutil.rmtree(EXP)
    shutil.copytree(os.path.join(C.snap, "textures"), os.path.join(EXP, "textures"))
    shutil.copytree(os.path.join(C.bout, "meshes"), os.path.join(EXP, "meshes"))
    for f in os.listdir(C.texout): shutil.copy2(os.path.join(C.texout, f), os.path.join(EXP, C.tex, f))
    print("exp_root ok")


def job(piece, yaw=None, pitch=None):
    rel, pc = rels(piece); y, p, W, H, rot = VIEW.get(piece, WEAPON)
    if yaw is not None: y = float(yaw)
    if pitch is not None: p = float(pitch)
    def m(tag, rt):
        return {"tag": tag, "nif": os.path.join(rt, rel), "tex_root": rt, "hide": ["Scb"],
                "hide_tex": ["actors", "body", "skin"], "alphatest": True, "rot": rot}
    out = os.path.join(C.render, "f3d_" + piece); os.makedirs(out, exist_ok=True)
    j = dict(fit_each=False, use_ao=True, out=out, samples=int(os.environ.get("SAMPLES", "64")), models=[m("o1", C.snap), m("x3", EXP)],
             views=[dict(name="v", yaw=y, pitch=p, W=W, H=H)])
    pth = os.path.join(C.render, "f3d_%s.json" % piece); json.dump(j, open(pth, "w"), indent=1); return pth


def render(pieces):
    for pc in pieces:
        j = job(pc)
        subprocess.run([sys.executable, "-I", os.path.join(T, "render_chain.py"), "prep", j], capture_output=True)
        with open(os.path.join(C.render, "f3d_%s.log" % pc), "w") as f:
            r = subprocess.run([sets.BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "--python", os.path.join(T, "render_chain.py"), "--", j],
                               stdout=f, stderr=subprocess.STDOUT)
        print(pc, "rendered" if r.returncode == 0 else "FAILED")


if __name__ == "__main__":
    a = sys.argv[1]
    if a == "root": root()
    elif a == "job": print(job(*sys.argv[2:]))
    elif a == "render": render(sys.argv[2:])
    elif a == "all":
        root(); render(sys.argv[2:] or [p["render"] for p in C.pieces if p.get("render")])
