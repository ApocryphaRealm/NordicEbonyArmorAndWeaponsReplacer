r"""Full-3D build driver for one set (NSET=ebony|skyforged):
  py -3 full3d.py cfg                 per-piece Blender configs -> build\cfg\<piece>.json
  py -3 full3d.py build [piece ...]   Blender (build3d.py) on every piece, JOBS in parallel (default 4) -> build\logs\
  py -3 full3d.py post                TruePBR texture sets + parallax (postfix.fix), splice the unskinned items' added
                                      shapes into the untouched originals, write the package's duplicate paths
  py -3 full3d.py install             copy build\out\meshes + the set's 3D textures into the set's MO2 folder (no
                                      modlist.txt edit: a new folder shows in MO2 disabled); option pieces (no-fur) are
                                      staged in build\out_opt\ only
  py -3 full3d.py stats               Blender read-back counts -> build\stats_full.json
Order for a whole rebuild: prep.py, chainmail.py helm torso, features.py, prep_feat.py, backing.py helm|torso, make_tex.py
(see rebuild_set.sh)."""
import os, sys, json, shutil, subprocess
from concurrent.futures import ThreadPoolExecutor
T = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, T)
import sets
C = sets.get()
CFG = os.path.join(C.build, "cfg"); LOG = os.path.join(C.build, "logs"); ADD = os.path.join(C.build, "added")
RING = dict(col_px=9.0, row_px=6.7, R=0.62, wire=0.13, tilt_deg=35, lift=0.35, M=8, m=4)


def added_of(rel, opt): return os.path.join(ADD, opt or "core", rel)


def cfg():
    os.makedirs(CFG, exist_ok=True); n = 0
    for pc in C.pieces:
        opt = pc.get("opt"); files = []
        for rel in pc["files"]:
            dst = added_of(rel, opt) if pc.get("splice") else C.out_of(rel, opt)
            files.append([C.snap_of(rel, opt), dst])
        c = dict(feat_dir=C.feat, stats=os.path.join(C.build, "stats", pc["name"] + ".json"), ring=RING,
                 pieces=[dict(name=pc["name"], splice=bool(pc.get("splice")), atlases={C.alb(a): a for a in pc["atlases"]}, files=files)])
        json.dump(c, open(os.path.join(CFG, pc["name"] + ".json"), "w"), indent=1); n += 1
    os.makedirs(os.path.join(C.build, "stats"), exist_ok=True); print("cfg", n)


def build(names):
    os.makedirs(LOG, exist_ok=True)
    todo = [pc["name"] for pc in C.pieces if not names or pc["name"] in names]
    def one(nm):
        with open(os.path.join(LOG, nm + ".log"), "w") as f:
            r = subprocess.run([sets.BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "--python", os.path.join(T, "build3d.py"), "--",
                                os.path.join(CFG, nm + ".json")], stdout=f, stderr=subprocess.STDOUT)
        txt = open(os.path.join(LOG, nm + ".log"), errors="replace").read()
        pl = [l for l in txt.splitlines() if l.startswith("PIECE") or l.startswith("NOTHING ADDED")]
        return nm, r.returncode, pl
    bad = []
    with ThreadPoolExecutor(int(os.environ.get("JOBS", "4"))) as ex:
        for nm, rc, pl in ex.map(one, todo):
            print(("OK  " if rc == 0 else "FAIL"), nm, *pl, sep="\n   ")
            if rc: bad.append(nm)
    if bad: sys.exit("BUILD FAILED: " + " ".join(bad))


def post():
    import postfix
    lines = []
    for pc in C.pieces:
        opt = pc.get("opt"); outs = []
        for rel in pc["files"]:
            out = C.out_of(rel, opt); os.makedirs(os.path.dirname(out), exist_ok=True)
            if pc.get("splice"):
                a = added_of(rel, opt)
                if os.path.isfile(a): new = postfix.splice(C.snap_of(rel, opt), a, out); lines.append("splice %s %d shapes" % (rel, len(new)))
                else: shutil.copy2(C.snap_of(rel, opt), out); lines.append("parallax-only %s" % rel)
            lines += ["  " + l for l in postfix.fix(out)]
            outs.append(out)
        for src, crel in zip(outs, pc.get("copies", [])):
            d = C.out_of(crel, opt); os.makedirs(os.path.dirname(d), exist_ok=True); shutil.copy2(src, d)
    open(os.path.join(C.build, "postfix_full.log"), "w").write("\n".join(lines))
    print("post: %d log lines, NOT TRUEPBR %d" % (len(lines), sum("NOT TRUEPBR" in l for l in lines)))


def install():
    M = C.mo2; n = 0
    for dp, _, fs in os.walk(os.path.join(C.bout, "meshes")):
        for f in fs:
            s = os.path.join(dp, f); d = os.path.join(M, os.path.relpath(s, C.bout)); os.makedirs(os.path.dirname(d), exist_ok=True); shutil.copy2(s, d); n += 1
    td = os.path.join(M, C.tex); os.makedirs(td, exist_ok=True)
    for f in os.listdir(C.texout): shutil.copy2(os.path.join(C.texout, f), td); n += 1
    # read back
    bad = [os.path.relpath(os.path.join(dp, f), C.bout) for dp, _, fs in os.walk(C.bout) for f in fs
           if open(os.path.join(dp, f), "rb").read() != open(os.path.join(M, os.path.relpath(os.path.join(dp, f), C.bout)), "rb").read()]
    print("installed", n, "files to", M, "read-back mismatches", len(bad))


def stats():
    r = subprocess.run([sets.BLENDER, "-b", "--factory-startup", "--python", os.path.join(T, "stats_set.py"), "--", C.name], capture_output=True, text=True)
    for l in r.stdout.splitlines():
        if l.startswith("STAT") or l.startswith("TOTAL"): print(l)


if __name__ == "__main__":
    cmd = sys.argv[1]
    {"cfg": cfg, "post": post, "install": install, "stats": stats}.get(cmd, lambda: build(sys.argv[2:]))()
