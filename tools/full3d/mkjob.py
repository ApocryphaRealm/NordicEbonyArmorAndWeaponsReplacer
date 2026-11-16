import json, os, sys, shutil
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = r"D:\Claude output\7. current test builds\Skyrim - Nordic Ebony Armor and Weapons Replacer\Nordic Ebony Armor and Weapons Replacer 1.1.0\00 Core"
# snapshot of the current package files this demo renders (read-only use of the package)
SNAP = os.path.join(HERE, "pkg_snapshot")
def snap():
    for rel in (r"meshes\NordicEbony\m\helmet_1.nif", r"meshes\NordicEbony\m\cuirass_1.nif"):
        d = os.path.join(SNAP, rel); os.makedirs(os.path.dirname(d), exist_ok=True); shutil.copy2(os.path.join(CORE, rel), d)
    src = os.path.join(CORE, r"textures\pbr\NordicEbony"); dst = os.path.join(SNAP, r"textures\pbr\NordicEbony"); os.makedirs(dst, exist_ok=True)
    for f in os.listdir(src):
        if f.split("_")[0].split(".")[0] in ("helmebony", "helm", "torsoebony", "torso", "furcollar", "bgpbebony", "bgpb"): shutil.copy2(os.path.join(src, f), dst)
def model(tag, piece):
    return {"tag": tag, "nif": os.path.join(SNAP, r"meshes\NordicEbony\m\%s_1.nif" % piece), "tex_root": SNAP,
            "hide": ["Scb"], "rot": [-90, 180, 0], "hide_tex": ["actors", "body", "skin"], "alphatest": True}
def job(name, models, views, samples=48, **kw):
    out = os.path.join(HERE, "render", name); os.makedirs(out, exist_ok=True)
    j = dict(dict(fit_each=False, use_ao=True), out=out, samples=samples, models=models, views=views); j.update(kw)
    p = os.path.join(HERE, "render", name + ".json"); json.dump(j, open(p, "w"), indent=1); return p
if __name__ == "__main__":
    snap()
    print(job("orient", [model("helmet", "helmet"), model("cuirass", "cuirass")],
              [dict(name="y%d" % y, yaw=y, pitch=10, W=360, H=360) for y in (0, 90, 180, 270)], samples=12))
