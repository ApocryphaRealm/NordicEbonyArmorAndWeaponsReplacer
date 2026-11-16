r"""Prebuilt full-3D body meshes: BodySlide (staging copy) on the 3D projects bodyslide.py wrote.
  py -3 build3d_bodies.py ebony|skyforged
Output: <here>\3d-<set>\{30 BodySlide - CBBE 3BA, 32 CBBE 3BA meshes, 34 BodySlide - HIMBO, 36 HIMBO meshes}
(+ the collarless 31/33/35/37 for Ebony) - option folders shaped like the flat package's, NOT installed anywhere."""
import os, sys, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repo's tools\ (truepbr, niflib, body_fits)
sys.path.insert(0, HERE)   # sets.py and the 3D tools are in this folder
import body_fits as bf
S = sys.argv[1]; os.environ["NSET"] = S
import sets
C = sets.get(S)
title = {"ebony": "Nordic Ebony", "skyforged": "Nordic Skyforged"}[S]   # the BodySlide group names the flat package uses
PLAN = r"D:\Claude output\4. plans\body-fits-20261116"
out = os.environ.get("FULL3D_BODIES_OUT") or os.path.join(PLAN, "3d-" + S)
if os.path.isdir(out): shutil.rmtree(out)
pkg = os.environ.get("FULL3D_PKG") or os.path.join(PLAN, "pkg-" + S)
src = {"30": os.path.join(C.build, "bodyslide", "CalienteTools", "BodySlide"),
       "34": os.path.join(C.build, "bodyslide_34", "CalienteTools", "BodySlide")}
bs = bf.staging(os.path.join(out, "_stage", "s"))
for k, d in src.items():
    name = {"30": "30 BodySlide - CBBE 3BA", "34": "34 BodySlide - HIMBO"}[k]
    dst = os.path.join(out, name, "CalienteTools", "BodySlide")
    shutil.copytree(d, dst, ignore=shutil.ignore_patterns("*.anchors.json"))
    bf.add_project(bs, dst)
for key, label, preset in (("32 CBBE 3BA meshes", title + " - CBBE 3BA", bf.PRESET_3BA), ("36 HIMBO meshes", title + " - HIMBO", bf.PRESET_HIMBO)):
    print(key, len(bf.run_bodyslide(bs, label, preset, os.path.join(out, key))), "files")
if S == "ebony":
    for grp, mesh, label, preset in (("31 BodySlide - CBBE 3BA - no fur collar", "33 CBBE 3BA meshes - no fur collar", title + " - CBBE 3BA", bf.PRESET_3BA),
                                     ("35 BodySlide - HIMBO - no fur collar", "37 HIMBO meshes - no fur collar", title + " - HIMBO", bf.PRESET_HIMBO)):
        shutil.copytree(os.path.join(pkg, grp), os.path.join(out, grp))
        bf.add_project(bs, os.path.join(out, grp, "CalienteTools", "BodySlide"))
        t = os.path.join(out, mesh); bf.run_bodyslide(bs, label, preset, t)
        for dp, _, fs in os.walk(t):
            for f in fs:
                if not f.lower().startswith("cuirass"): os.remove(os.path.join(dp, f))
        print(mesh, "cuirass only")
shutil.rmtree(os.path.join(out, "_stage"))
