import json, os, sys, shutil
T = os.path.dirname(os.path.abspath(__file__)); H = os.path.dirname(T); sys.path.insert(0, T); os.chdir(H)
import mkjob
SNAP = os.path.join(H, "pkg_snapshot"); EXP = os.path.join(H, "build", "exp_root"); OUT = os.path.join(H, "build", "out")
def exp_root():
    if os.path.isdir(EXP): shutil.rmtree(EXP)
    shutil.copytree(os.path.join(SNAP, "textures"), os.path.join(EXP, "textures"))
    shutil.copytree(os.path.join(OUT, "meshes"), os.path.join(EXP, "meshes"))
    for f in os.listdir(os.path.join(OUT, "textures", "pbr", "NordicEbony")):
        shutil.copy2(os.path.join(OUT, "textures", "pbr", "NordicEbony", f), os.path.join(EXP, "textures", "pbr", "NordicEbony", f))
REL = {"helmet": r"meshes\NordicEbony\m\helmet_1.nif", "cuirass": r"meshes\NordicEbony\m\cuirass_1.nif",
       "gauntlets": r"meshes\NordicEbony\m\gauntlets_1.nif", "boots": r"meshes\NordicEbony\m\boots_1.nif",
       "shield": r"meshes\weapons\ebony\ebonyshield.nif"}
def m(tag, piece, root, rot=None):
    d = {"tag": tag, "nif": os.path.join(root, REL[piece]), "tex_root": root, "hide": ["Scb"], "hide_tex": ["actors", "body", "skin"], "alphatest": True,
         "rot": rot if rot is not None else [-90, 180, 0]}
    return d
if __name__ == "__main__":
    if sys.argv[1] == "root": exp_root(); print("exp_root ok")
    elif sys.argv[1] == "orient":
        ms = [m("g", "gauntlets", EXP), m("b", "boots", EXP), m("s", "shield", EXP), m("s2", "shield", EXP, [0, 0, 0])]
        print(mkjob.job("orient2", ms, [dict(name="y%d" % y, yaw=y, pitch=10, W=320, H=320) for y in (0, 90, 180, 270)], samples=8, fit_each=True))
    else:
        piece = sys.argv[1]; view = json.loads(sys.argv[2]); rot = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None
        print(mkjob.job("f3d_" + piece, [m("o1", piece, SNAP, rot), m("x3", piece, EXP, rot)], [dict(view, name="v")], samples=int(os.environ.get("SAMPLES", "64"))))
