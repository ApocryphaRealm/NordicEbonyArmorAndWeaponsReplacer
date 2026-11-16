r"""Full-3D BodySlide (CBBE 3BA) projects for a set (NSET): the package's slider sets with the 3D parts added and conformed.
  1. every slider set's ShapeData NIF gets the same 3D parts (build3d.py on it - the recipe is in UV space, so it lands on
     the 3BA-fitted shapes as on the shipped ones) and its anchors: each added vertex = (source shape, triangle, barycentric)
  2. slider data for each added shape = the barycentric blend of its anchor triangle's three vertex offsets in the
     package's .osd, per slider (a ring or a stud has one anchor for all its vertices, so a slider moves it rigidly with
     the surface under it - no stretched rings), written to "<slider set> 3D.osd" beside the original
  3. the .osp gets a <Shape> and a <Data> per slider for every added shape; TruePBR texture sets + parallax as in game
Output: <work>\build\bodyslide\CalienteTools\BodySlide\... (a copy of the package's BodySlide folder with the 3D added)
  py -3 bodyslide.py build | osd | check"""
import os, sys, json, re, shutil, struct, subprocess
import xml.etree.ElementTree as ET
import numpy as np
T = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, T)
import sets
C = sets.get()
# 2026-11-16: any body's project - env BSOPT names the package option folder (default the CBBE 3BA one; "34 BodySlide -
# HIMBO" for our HIMBO fit), env BSPKG an other package root (default the set's test build)
BSOPT = os.environ.get("BSOPT", "30 BodySlide - CBBE 3BA")
SRC = os.path.join(os.environ.get("BSPKG", C.pkg), BSOPT, "CalienteTools", "BodySlide")
OUT = os.path.join(C.build, "bodyslide" if BSOPT.startswith("30 ") else "bodyslide_" + BSOPT[:2], "CalienteTools", "BodySlide")
RING = dict(col_px=9.0, row_px=6.7, R=0.62, wire=0.13, tilt_deg=35, lift=0.35, M=8, m=4)


def read_osd(p):
    b = open(p, "rb").read(); assert b[:4] == b"\x00DSO", p
    ver, n = struct.unpack_from("<II", b, 4); q = 12; D = {}
    for _ in range(n):
        L = b[q]; name = b[q + 1:q + 1 + L].decode("latin-1"); q += 1 + L
        k = struct.unpack_from("<H", b, q)[0]; q += 2
        arr = np.frombuffer(b, dtype=np.dtype([("i", "<u2"), ("v", "<f4", 3)]), count=k, offset=q); q += 14 * k
        D[name] = {int(i): np.array(v, np.float64) for i, v in zip(arr["i"], arr["v"])}
    return D


def write_osd(p, D):
    out = bytearray(b"\x00DSO") + struct.pack("<II", 1, len(D))
    for name, dd in D.items():
        e = name.encode("latin-1"); assert len(e) < 256 and len(dd) < 65536
        out += bytes([len(e)]) + e + struct.pack("<H", len(dd))
        for i, v in sorted(dd.items()): out += struct.pack("<H3f", i, *v)
    open(p, "wb").write(out)


def projects():
    for f in os.listdir(os.path.join(SRC, "SliderSets")):
        tree = ET.parse(os.path.join(SRC, "SliderSets", f))
        for ss in tree.getroot().iter("SliderSet"):
            yield f, ss.get("name"), ss.findtext("DataFolder"), ss.findtext("SourceFile")


def build():
    if os.path.isdir(OUT): shutil.rmtree(OUT)
    shutil.copytree(SRC, OUT)
    cfgs = []
    for osp, name, folder, srcnif in projects():
        nif = os.path.join(SRC, "ShapeData", folder, srcnif); raw = open(nif, "rb").read().lower()
        atl = [a for a in sets.ARMOUR if (C.alb(a) + ".dds").encode() in raw]
        # Blender works on short copies: the package's ShapeData paths pass Windows' 260-character limit (pynifly then
        # cannot open them - the 1stperson and gauntlet projects)
        sw = os.path.join(C.build, "bs", str(len(cfgs))); os.makedirs(sw, exist_ok=True)
        shutil.copy2(nif, os.path.join(sw, "src.nif")); nif = os.path.join(sw, "src.nif"); dst = os.path.join(sw, "out.nif")
        c = dict(feat_dir=C.feat, stats=os.path.join(C.build, "stats", "bs_" + folder + ".json"), ring=RING, anchors=True,
                 pieces=[dict(name="bs " + folder, atlases={C.alb(a): a for a in atl}, files=[[nif, dst]])])
        p = os.path.join(C.build, "cfg", "bs_" + folder + ".json"); json.dump(c, open(p, "w"), indent=1); cfgs.append((folder, p))
    from concurrent.futures import ThreadPoolExecutor
    def one(fp):
        folder, p = fp; lg = os.path.join(C.build, "logs", "bs_" + folder + ".log")
        with open(lg, "w") as f:
            r = subprocess.run([sets.BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "--python", os.path.join(T, "build3d.py"), "--", p], stdout=f, stderr=subprocess.STDOUT)
        sw = os.path.dirname(json.load(open(p))["pieces"][0]["files"][0][1]); srcnif = next(x[3] for x in projects() if x[2] == folder)
        sd = os.path.join(OUT, "ShapeData", folder)
        if r.returncode == 0:
            shutil.copy2(os.path.join(sw, "out.nif"), os.path.join(sd, srcnif))
            shutil.copy2(os.path.join(sw, "out.anchors.json"), os.path.join(sd, os.path.splitext(srcnif)[0] + ".anchors.json"))
        return folder, r.returncode, [l for l in open(lg, errors="replace").read().splitlines() if l.startswith("PIECE")]
    with ThreadPoolExecutor(4) as ex:
        for folder, rc, pl in ex.map(one, cfgs): print("OK " if rc == 0 else "FAIL", folder, pl)
    import postfix
    for osp, name, folder, srcnif in projects():
        log = postfix.fix(os.path.join(OUT, "ShapeData", folder, srcnif)); print(folder, "NOT TRUEPBR", sum("NOT TRUEPBR" in l for l in log))
    osd()


def osd():
    for f in os.listdir(os.path.join(SRC, "SliderSets")):
        p = os.path.join(OUT, "SliderSets", f); tree = ET.parse(os.path.join(SRC, "SliderSets", f)); root = tree.getroot()
        for ss in root.iter("SliderSet"):
            folder = ss.findtext("DataFolder"); srcnif = ss.findtext("SourceFile"); sd = os.path.join(OUT, "ShapeData", folder)
            anch = json.load(open(os.path.join(sd, os.path.splitext(srcnif)[0] + ".anchors.json")))
            base = {}
            for fn in os.listdir(os.path.join(SRC, "ShapeData", folder)):
                if fn.lower().endswith(".osd"): base.update(read_osd(os.path.join(SRC, "ShapeData", folder, fn)))
            newosd = ss.get("name") + " 3D.osd"; ND = {}; nshape = 0; ndata = 0; missing = 0
            shapes = ss.findall("Shape"); last = list(ss).index(shapes[-1])
            for k, sh in enumerate(sorted(anch)):
                el = ET.Element("Shape", target=sh); el.text = sh; el.tail = shapes[-1].tail; ss.insert(last + 1 + k, el); nshape += 1
            for sl in ss.findall("Slider"):
                datas = {d.get("target"): d for d in sl.findall("Data")}
                for sh, A in sorted(anch.items()):
                    srcs = {a[0] for a in A}
                    dd = {}
                    for vi, (s_, idx, b) in enumerate(A):
                        d = datas.get(s_)
                        if d is None: continue
                        key = d.get("name")
                        if key not in base: missing += 1; continue
                        D = base[key]; v = sum(w * D.get(i, 0.0) for i, w in zip(idx, b))
                        if isinstance(v, np.ndarray) and np.abs(v).max() > 1e-7: dd[vi] = v
                    if not dd: continue
                    nm = sh + sl.get("name"); ND[nm] = dd
                    e = ET.SubElement(sl, "Data", name=nm, target=sh, local="true"); e.text = newosd + "\\" + nm; ndata += 1
            write_osd(os.path.join(sd, newosd), ND)
            print(ss.get("name"), "added shapes", nshape, "slider data", ndata, "missing base data", missing)
        ET.indent(tree, "    "); tree.write(p, encoding="utf-8", xml_declaration=True)


def check():
    """read the written .osd back and compare a blend by hand for one vertex per shape and slider"""
    for osp, name, folder, srcnif in projects():
        sd = os.path.join(OUT, "ShapeData", folder); D = read_osd(os.path.join(sd, name + " 3D.osd"))
        print(name, "3D.osd entries", len(D), "max offset %.3f" % max((max(np.abs(v).max() for v in dd.values()) for dd in D.values()), default=0))


def install():
    """the 3D projects into the set's MO2 folder under CalienteTools/BodySlide - the same project names as the package's
    3BA option, so with the 3D folder enabled after it BodySlide builds the 3D version; the anchors files stay out"""
    n = 0
    for dp, _, fs in os.walk(OUT):
        for f in fs:
            if f.endswith(".anchors.json"): continue
            s_ = os.path.join(dp, f); d = os.path.join(C.mo2, "CalienteTools", "BodySlide", os.path.relpath(s_, OUT))
            os.makedirs(os.path.dirname(d), exist_ok=True); shutil.copy2(s_, d); n += 1
    print("BodySlide files installed", n)


if __name__ == "__main__":
    {"build": build, "osd": osd, "check": check, "install": install}[sys.argv[1]]()
