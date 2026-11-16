import sys, os, shutil
T = os.path.dirname(os.path.abspath(__file__)); H = os.path.dirname(T); sys.path.insert(0, T); os.chdir(H)
import mkjob
if sys.argv[1] == "jobs":
    def rc(at): return dict(mask=os.path.join(H, "masks", at + "_mail.png"), col_px=9.0, row_px=6.7, R=0.62, wire=0.13, tilt_deg=35, lift=0.35, M=24, m=8, mat=at + "ebony")
    h1 = mkjob.model("h1", "helmet"); h3 = dict(mkjob.model("h3", "helmet"), rings3d=rc("helm"))
    c1 = mkjob.model("c1", "cuirass"); c3 = dict(mkjob.model("c3", "cuirass"), rings3d=rc("torso"))
    mkjob.job("h3d", [h1, h3], [dict(name="close", yaw=135, pitch=8, W=1300, H=1300)], samples=64)
    mkjob.job("c3d", [c1, c3], [dict(name="close", yaw=25, pitch=5, W=1150, H=1610)], samples=64)
else:
    for job, at, pairs in (("h3d", "helm", (("h1", "opt1"), ("h3", "opt3"))), ("c3d", "torso", (("c1", "opt1"), ("c3", "opt3")))):
        for tag, opt in pairs:
            d = os.path.join("render", job, "tex", tag, "textures", "pbr", "NordicEbony")
            for f in os.listdir(os.path.join("out", at, opt)):
                if opt == "opt1" and f.endswith("_n.png"): continue
                shutil.copy2(os.path.join("out", at, opt, f), os.path.join(d, f)); print("put", tag, f)
