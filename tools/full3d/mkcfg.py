import json, os, shutil, sys
T = os.path.dirname(os.path.abspath(__file__)); H = os.path.dirname(T)
CORE = r"D:\Claude output\7. current test builds\Skyrim - Nordic Ebony Armor and Weapons Replacer\Nordic Ebony Armor and Weapons Replacer 1.1.0\00 Core"
SNAP = os.path.join(H, "pkg_snapshot"); B = os.path.join(H, "build")
def snap():
    for rel in [r"meshes\NordicEbony\m\%s_%d.nif" % (p, w) for p in ("helmet", "cuirass", "gauntlets", "boots") for w in (0, 1)] + [r"meshes\weapons\ebony\ebonyshield.nif"]:
        d = os.path.join(SNAP, rel); os.makedirs(os.path.dirname(d), exist_ok=True); shutil.copy2(os.path.join(CORE, rel), d)
    src = os.path.join(CORE, r"textures\pbr\NordicEbony"); dst = os.path.join(SNAP, r"textures\pbr\NordicEbony")
    for f in os.listdir(src): shutil.copy2(os.path.join(src, f), dst)
ATL = {"helmet": {"helmebony": "helm"}, "cuirass": {"torsoebony": "torso", "bgpbebony": "bgpb"},
       "gauntlets": {"bgpbebony": "bgpb"}, "boots": {"bgpbebony": "bgpb"}}
def cfg(names, tag):
    pcs = []
    for n in names:
        pcs.append(dict(name=n, atlases=ATL[n], files=[[os.path.join(SNAP, r"meshes\NordicEbony\m\%s_%d.nif" % (n, w)), os.path.join(B, "out", r"meshes\NordicEbony\m\%s_%d.nif" % (n, w))] for w in (1, 0)]))
    c = dict(feat_dir=os.path.join(H, "feat"), stats=os.path.join(B, "stats_%s.json" % tag),
             ring=dict(col_px=9.0, row_px=6.7, R=0.62, wire=0.13, tilt_deg=35, lift=0.35, M=8, m=4), pieces=pcs)
    p = os.path.join(B, "cfg_%s.json" % tag); os.makedirs(B, exist_ok=True); json.dump(c, open(p, "w"), indent=1); print(p)
if __name__ == "__main__":
    if sys.argv[1] == "snap": snap(); print("snap ok")
    elif sys.argv[1] == "shield":
        c = dict(feat_dir=os.path.join(H, "feat"), stats=os.path.join(B, "stats_shield.json"),
                 ring=dict(col_px=9.0, row_px=6.7, R=0.62, wire=0.13, tilt_deg=35, lift=0.35, M=8, m=4),
                 pieces=[dict(name="shield", splice=True, atlases={"shieldebony": "shield"},
                              files=[[os.path.join(SNAP, r"meshes\weapons\ebony\ebonyshield.nif"), os.path.join(B, "added_shield.nif")]])])
        json.dump(c, open(os.path.join(B, "cfg_shield.json"), "w"), indent=1); print("cfg shield")
    else: cfg(sys.argv[2:], sys.argv[1])
