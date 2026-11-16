#!/usr/bin/env python3
r"""Our own body fits for the armour: CBBE 3BA (female) and HIMBO (male), built with BodySlide run by us.

The owner, 2026-11-16 02:38: "If you're capable of running body slide to make it compatible on our end, then we should
ship it with CBBE and Himbo compatibility." This module is shared, byte-identical, by the Truly Nordic Ebony and Truly
Nordic Skyforged repos (tools/body_fits.py); loy-refits.py calls it.

CBBE 3BA (female)
  The slider sets and shape data come from Xonek's Legacy of Ysgramor - 3BA Bodyslide (Nexus 111209). Their .osp named
  Xonek's own shape-data folders and .osd files ("Legacy of Ysgramor - Ebony - Armor 3BA" ...), which our package does
  not ship, so the sliders only worked with Xonek's mod installed. fix_3ba() repoints every <Shape> and <Data> at the
  set's own folder and .osd and refuses if any slider entry is missing from the .osd we ship.

HIMBO (male) - our own conform, no third-party refit used
  For each worn male piece, from OUR male weight-0 mesh (the vanilla-male fit NordwarUA made):
    1. conversion: every vertex moves by the inverse-distance blend of HIMBO's own "Vanilla to HIMBO" conversion
       slider (HIMBO's ConversionSets\HIMBO Conversion.osp, the reference Outfit Studio's "Convert: Vanilla to HIMBO"
       template loads) over its 10 nearest reference vertices within 10 units, weighted 1/d^2 - the scripted form
       of Outfit Studio's Load Reference -> conversion slider at 100% -> Conform All (Outfit Studio has no command
       line); HIMBO's author-shipped conversion and reference sets are the data, nothing hand-made;
    2. clearance: a vertex that sat outside the vanilla body but ends up closer to (or inside) the HIMBO body than it
       was is pushed back out along the body normal to its old clearance (capped at 0.5 units);
    3. BodySlide itself writes the converted mesh (a one-slider project built with --groupbuild, so skin partitions
       and the rest of the NIF are written by BodySlide, not by us);
    4. slider data: every HIMBO slider of "HIMBO Ref - Merged Body (Vanilla Flat)" (the "Refit: HIMBO Vanilla"
       template - body, hands and feet) is transferred the same way onto the converted mesh: what Outfit Studio's
       "Conform" does. UV-only sliders are left out. "Weight 0 to 1" (hidden, big 100) carries weight 0 -> 1.
  The project is "<Mod> - HIMBO - <piece>" in group "<Mod> - HIMBO" and in HIMBO's own group "HIMBO", so every HIMBO
  preset is offered for it.

Prebuilt meshes: BodySlide.exe --groupbuild with "- Zeroed Sliders -" (CBBE 3BA, the zeroed body 3BA itself ships)
and "HIMBO Default" (HIMBO), --trimorphs so RaceMenu / OBody morph the armour with the body. BodySlide runs from a
staging copy (no MO2): its program files are copied from the instance's "BodySlide and Outfit Studio" mod, and only
our projects and the two preset files are put beside it.

Read-only inputs from the Njordlinger instance (never shipped): HIMBO's reference shapes and presets, CBBE's preset
file, BodySlide's program files. HIMBO's terms (Kreiste, 2026-11-16 read): refits and original armour using the HIMBO
body are allowed with credit if free. CBBE 3BA's (Acro): asset use allowed with credit, not for sale.
"""
import os
import shutil
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET

import numpy as np

NJ = r"D:\modlists\Njordlinger\mods"
BODYSLIDE_MOD = os.path.join(NJ, "BodySlide and Outfit Studio", "CalienteTools", "BodySlide")
HIMBO_MOD = os.path.join(NJ, "Highly Improved Male Body Overhaul (HIMBO)", "CalienteTools", "BodySlide")
CBBE_PRESETS = os.path.join(NJ, "Caliente's Beautiful Bodies Enhancer -CBBE-", "CalienteTools", "BodySlide", "SliderPresets", "CBBE.xml")
PYNIFLY = os.path.join(os.environ.get("APPDATA", ""), "Blender Foundation", "Blender", "5.2", "scripts", "addons", "io_scene_nifly")
PRESET_3BA = "- Zeroed Sliders -"
PRESET_HIMBO = "HIMBO Default"
K = 10                # nearest reference vertices blended per vertex (Outfit Studio's conform: 10 results...)
RADIUS = 10.0         # ...within a 10-unit search radius; a vertex with none in reach does not move
CLEAR_CAP = 0.5       # clearance kept, at most (game units)


def fail(msg):
    raise SystemExit("body_fits: " + msg)


# ---------------------------------------------------------------- files

def read_osd(p):
    b = open(p, "rb").read()
    if b[:4] != b"\x00DSO":
        fail("%s is not an .osd" % p)
    ver, n = struct.unpack_from("<II", b, 4); q = 12; D = {}
    for _ in range(n):
        L = b[q]; name = b[q + 1:q + 1 + L].decode("latin-1"); q += 1 + L
        k = struct.unpack_from("<H", b, q)[0]; q += 2
        arr = np.frombuffer(b, dtype=np.dtype([("i", "<u2"), ("v", "<f4", 3)]), count=k, offset=q); q += 14 * k
        D[name] = (arr["i"].astype(np.int64), arr["v"].astype(np.float64))
    return D


def write_osd(p, D):
    out = bytearray(b"\x00DSO") + struct.pack("<II", 1, len(D))
    for name, (idx, vec) in D.items():
        e = name.encode("latin-1")
        if len(e) > 255 or len(idx) > 65535:
            fail("osd entry %s too large" % name)
        out += bytes([len(e)]) + e + struct.pack("<H", len(idx))
        rec = np.zeros(len(idx), dtype=np.dtype([("i", "<u2"), ("v", "<f4", 3)]))
        rec["i"] = idx; rec["v"] = vec
        out += rec.tobytes()
    open(p, "wb").write(bytes(out))


def dense(entry, n):
    a = np.zeros((n, 3))
    if entry is not None:
        a[entry[0]] = entry[1]
    return a


_nifly = None


def nif_shapes(path):
    """[(name, verts (n,3), tris (m,3))] read with pynifly (Blender's NIF add-on library, loaded without Blender)"""
    global _nifly
    if _nifly is None:
        sys.path.insert(0, PYNIFLY)
        from pyn.pynifly import NifFile
        NifFile.Load(os.path.join(PYNIFLY, "NiflyDLL.dll"))
        _nifly = NifFile
    nf = _nifly(path)
    out = []
    for s in nf.shapes:
        t = s.transform
        if abs(t.scale - 1) > 1e-4 or max(abs(x) for x in t.translation) > 1e-3:
            fail("%s: shape %s has a transform - the fit assumes body space vertices" % (path, s.name))
        out.append((s.name, np.array(s.verts, np.float64), np.array(s.tris, np.int64)))
    return out


def vertex_normals(V, T):
    N = np.zeros_like(V)
    fn = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
    for j in range(3):
        np.add.at(N, T[:, j], fn)
    L = np.linalg.norm(N, axis=1, keepdims=True); L[L == 0] = 1
    return N / L


class Blend:
    """inverse-distance blend of per-vertex values from a reference point set (K nearest)"""

    def __init__(self, ref_pts, q):
        from scipy.spatial import cKDTree
        d, i = cKDTree(ref_pts).query(q, k=K, distance_upper_bound=RADIUS)
        miss = ~np.isfinite(d)
        i = np.where(miss, 0, i); d = np.where(miss, RADIUS, d)
        w = np.where(miss, 0.0, 1.0 / (d * d + 1e-4))
        s = w.sum(axis=1, keepdims=True); s[s == 0] = 1
        self.i = i; self.w = w / s; self.d0 = d[:, 0]; self.n0 = i[:, 0]

    def __call__(self, vals):
        return np.einsum("nk,nkc->nc", self.w, vals[self.i])


# ---------------------------------------------------------------- CBBE 3BA: own slider data

def fix_3ba(bs_root):
    """repoint every shape and slider entry of the .osp files under bs_root\\SliderSets at the set's own folder/.osd"""
    n_sets = n_data = 0
    for f in os.listdir(os.path.join(bs_root, "SliderSets")):
        p = os.path.join(bs_root, "SliderSets", f)
        tree = ET.parse(p)
        for ss in tree.getroot().iter("SliderSet"):
            folder = ss.findtext("DataFolder")
            sd = os.path.join(bs_root, "ShapeData", folder)
            osds = [x for x in os.listdir(sd) if x.lower().endswith(".osd")]
            if len(osds) != 1:
                fail("%s: expected one .osd in %s, found %s" % (ss.get("name"), sd, osds))
            entries = set(read_osd(os.path.join(sd, osds[0])))
            for sh in ss.findall("Shape"):
                sh.attrib.pop("DataFolder", None)  # no attribute = the set's own DataFolder
            for d in ss.iter("Data"):
                entry = d.text.split("\\")[-1]
                if entry not in entries:
                    fail("%s: slider entry %s is not in %s" % (ss.get("name"), entry, osds[0]))
                d.text = osds[0] + "\\" + entry
                n_data += 1
            n_sets += 1
        tree.write(p, encoding="utf-8", xml_declaration=True)
    return n_sets, n_data


def write_groups(bs_root, label, members, extra_groups):
    gd = os.path.join(bs_root, "SliderGroups"); os.makedirs(gd, exist_ok=True)
    g = ET.Element("SliderGroups")
    for name in [label] + list(extra_groups):
        ge = ET.SubElement(g, "Group", name=name)
        for m in members:
            ET.SubElement(ge, "Member", name=m)
    ET.indent(g, "    ")
    ET.ElementTree(g).write(os.path.join(gd, label + ".xml"), encoding="utf-8", xml_declaration=True)


# ---------------------------------------------------------------- HIMBO reference

class HimboRef:
    def __init__(self, root=HIMBO_MOD):
        if not os.path.isdir(root):
            fail("HIMBO is not in the instance (%s) - its reference shapes are read, not shipped" % root)
        conv = os.path.join(root, "ShapeData", "HIMBO Conversion")
        (_, self.V, self.VT), = nif_shapes(os.path.join(conv, "HIMBO - VAL.nif"))
        self.VD = dense(read_osd(os.path.join(conv, "HIMBO - VAL.osd"))["HIMBO Conversion - VALVanilla to HIMBO"], len(self.V))
        tree = ET.parse(os.path.join(root, "ConversionSets", "HIMBO Ref.osp"))
        ss = [s for s in tree.getroot().iter("SliderSet") if s.get("name") == "HIMBO Ref - Merged Body (Vanilla Flat)"][0]
        sd = os.path.join(root, "ShapeData", ss.findtext("DataFolder"))
        (_, self.R, self.RT), = nif_shapes(os.path.join(sd, ss.findtext("SourceFile")))
        osd = read_osd(os.path.join(sd, os.path.splitext(ss.findtext("SourceFile"))[0] + ".osd"))
        self.sliders = []  # (attrib, dense diff)
        for sl in ss.findall("Slider"):
            if sl.get("uv") == "true" or sl.get("zap") == "true":
                continue
            d = sl.find("Data")
            self.sliders.append((dict(sl.attrib), dense(osd.get(d.text.split("\\")[-1]), len(self.R))))
        self.VN = vertex_normals(self.V, self.VT)
        self.RN = vertex_normals(self.R, self.RT)

    def body(self, values):
        """the HIMBO reference body with slider values {name: 0..100}"""
        X = self.R.copy()
        for a, D in self.sliders:
            v = values.get(a["name"], 0)
            if v:
                X += D * (v / 100.0)
        return X

    def preset(self, name, big):
        tree = ET.parse(os.path.join(HIMBO_MOD, "SliderPresets", "HIMBO.xml"))
        p = [x for x in tree.getroot().iter("Preset") if x.get("name") == name][0]
        vals = {a["name"]: float(a.get("big" if big else "small", 0)) for a, _ in self.sliders}
        for s in p.iter("SetSlider"):
            if s.get("size") == ("big" if big else "small"):
                vals[s.get("name")] = float(s.get("value"))
        return vals


def clearance(P, B, BN):
    """signed distance of points P from body B (vertex normals BN) by the nearest body vertex"""
    from scipy.spatial import cKDTree
    _, i = cKDTree(B).query(P)
    return np.einsum("nc,nc->n", P - B[i], BN[i]), i


def convert_offsets(ref, X0):
    """per-vertex move of a vanilla-male-fitted mesh onto HIMBO's zero shape, with the clearance kept"""
    off = Blend(ref.V, X0)(ref.VD)
    X1 = X0 + off
    c0, _ = clearance(X0, ref.V, ref.VN)
    c1, i1 = clearance(X1, ref.R, ref.RN)
    want = np.minimum(c0, CLEAR_CAP)
    push = np.where((c0 > -0.05) & (c1 < want - 0.02), want - c1, 0.0)
    off += ref.RN[i1] * push[:, None]
    return off, int((push > 0).sum())


# ---------------------------------------------------------------- BodySlide (staging copy, no MO2)

def staging(root):
    """a runnable BodySlide beside our projects: program files copied from the instance, empty data folders"""
    bs = os.path.join(root, "CalienteTools", "BodySlide")
    if os.path.isdir(root):
        shutil.rmtree(root)
    os.makedirs(bs)
    for f in ("BodySlide.exe", "Config.xml"):
        shutil.copy2(os.path.join(BODYSLIDE_MOD, f), bs)
    for d in ("res", "lang"):
        shutil.copytree(os.path.join(BODYSLIDE_MOD, d), os.path.join(bs, d))
    for d in ("SliderSets", "ShapeData", "SliderGroups", "SliderPresets", "SliderCategories"):
        os.makedirs(os.path.join(bs, d), exist_ok=True)
    shutil.copy2(CBBE_PRESETS, os.path.join(bs, "SliderPresets", "CBBE.xml"))
    shutil.copy2(os.path.join(HIMBO_MOD, "SliderPresets", "HIMBO.xml"), os.path.join(bs, "SliderPresets", "HIMBO.xml"))
    return bs


def add_project(bs, src_bs):
    """copy a project tree (SliderSets / ShapeData / SliderGroups) into the staging BodySlide"""
    for d in ("SliderSets", "ShapeData", "SliderGroups"):
        s = os.path.join(src_bs, d)
        if os.path.isdir(s):
            shutil.copytree(s, os.path.join(bs, d), dirs_exist_ok=True)


def run_bodyslide(bs, group, preset, target, tri=True):
    if os.path.isdir(target):
        shutil.rmtree(target)
    os.makedirs(target)
    cmd = [os.path.join(bs, "BodySlide.exe"), "--groupbuild", group, "--targetdir", target, "--preset", preset]
    if tri:
        cmd.append("--trimorphs")
    r = subprocess.run(cmd, cwd=bs, timeout=900, capture_output=True, text=True)
    built = [os.path.join(dp, f) for dp, _, fs in os.walk(target) for f in fs]
    if not built:
        log = os.path.join(bs, "Log_BS.txt")
        tail = open(log, errors="replace").read()[-3000:] if os.path.isfile(log) else ""
        fail("BodySlide built nothing for group '%s' preset '%s' (exit %s)\n%s" % (group, preset, r.returncode, tail))
    return built


def _osp(sets_el, name, folder, srcfile, outpath, outfile, genweights, shapes, sliders):
    ss = ET.SubElement(sets_el, "SliderSet", name=name)
    ET.SubElement(ss, "DataFolder").text = folder
    ET.SubElement(ss, "SourceFile").text = srcfile
    ET.SubElement(ss, "OutputPath").text = outpath
    ET.SubElement(ss, "OutputFile", GenWeights="true" if genweights else "false").text = outfile
    for sh in shapes:
        ET.SubElement(ss, "Shape", target=sh).text = sh
    for attrib, datas in sliders:
        sl = ET.SubElement(ss, "Slider", **attrib)
        for nm, tgt, txt in datas:
            ET.SubElement(sl, "Data", name=nm, target=tgt, local="true").text = txt
    return ss


def himbo_project(label, pieces, out_bs, work, bs_program=None):
    """pieces: [(piece, src_nif_weight0, output_path, output_file)] -> HIMBO project under out_bs (SliderSets /
    ShapeData / SliderGroups); work: scratch folder. Returns the slider-set names."""
    ref = HimboRef()
    # 1+2: conversion offsets, written as a one-slider project BodySlide applies (hidden slider, 100 at both weights)
    conv_root = os.path.join(work, "conv-stage")
    bs = staging(conv_root)
    sets_el = ET.Element("SliderSetInfo", version="1")
    report = []
    for piece, src, outpath, outfile in pieces:
        nm = "NBF Convert - " + piece
        sd = os.path.join(bs, "ShapeData", nm); os.makedirs(sd)
        shutil.copy2(src, os.path.join(sd, "src.nif"))
        D = {}; shapes = []; datas = []; pushed = 0
        for sname, X0, _ in nif_shapes(src):
            off, n_push = convert_offsets(ref, X0); pushed += n_push
            nz = np.where(np.abs(off).max(axis=1) > 1e-6)[0]
            D[sname + "Convert"] = (nz, off[nz]); shapes.append(sname)
            datas.append((sname + "Convert", sname, "conv.osd\\" + sname + "Convert"))
        write_osd(os.path.join(sd, "conv.osd"), D)
        # GenWeights: with it off, BodySlide left the hidden slider at 0 (2026-11-16 test); with it on, both weights take 100
        _osp(sets_el, nm, nm, "src.nif", "conv", piece, True, shapes,
             [(dict(name="Convert", invert="false", small="100", big="100", hidden="true"), datas)])
        report.append((piece, pushed))
    ET.indent(sets_el, "    ")
    ET.ElementTree(sets_el).write(os.path.join(bs, "SliderSets", "NBF Convert.osp"), encoding="utf-8", xml_declaration=True)
    write_groups(bs, "NBF Convert", ["NBF Convert - " + p[0] for p in pieces], [])
    run_bodyslide(bs, "NBF Convert", PRESET_HIMBO, os.path.join(work, "conv-out"), tri=False)
    # 3+4: the HIMBO project on the converted meshes
    sets_el = ET.Element("SliderSetInfo", version="1")
    names = []
    for piece, src, outpath, outfile in pieces:
        conv = os.path.join(work, "conv-out", "conv", piece + "_0.nif")
        if not os.path.isfile(conv):
            fail("BodySlide did not write the converted %s" % piece)
        a = [s for s in nif_shapes(src)]; b = [s for s in nif_shapes(conv)]
        if [len(x[1]) for x in a] != [len(x[1]) for x in b]:
            fail("%s: the converted mesh's vertex counts differ from the source" % piece)
        moved = max(np.abs(x[1] - y[1]).max() for x, y in zip(a, b))
        if moved < 0.05:
            fail("%s: BodySlide did not apply the conversion (largest move %.3f)" % (piece, moved))
        nm = "%s - %s" % (label, piece); names.append(nm)
        sd = os.path.join(out_bs, "ShapeData", nm); os.makedirs(sd, exist_ok=True)
        shutil.copy2(conv, os.path.join(sd, nm + ".nif"))
        D = {}; slider_datas = {a_["name"]: [] for a_, _ in ref.sliders}; shapes = []
        for sname, X1, _ in b:
            bl = Blend(ref.R, X1); shapes.append(sname)
            for attrib, RD in ref.sliders:
                dd = bl(RD)
                nz = np.where(np.abs(dd).max(axis=1) > 1e-5)[0]
                if len(nz) == 0:
                    continue
                key = sname + attrib["name"]
                D[key] = (nz, dd[nz])
                slider_datas[attrib["name"]].append((key, sname, nm + ".osd\\" + key))
        write_osd(os.path.join(sd, nm + ".osd"), D)
        _osp(sets_el, nm, nm, nm + ".nif", outpath, outfile, True, shapes,
             [(attrib, slider_datas[attrib["name"]]) for attrib, _ in ref.sliders if slider_datas[attrib["name"]]])
    ssd = os.path.join(out_bs, "SliderSets"); os.makedirs(ssd, exist_ok=True)
    ET.indent(sets_el, "    ")
    ET.ElementTree(sets_el).write(os.path.join(ssd, label + ".osp"), encoding="utf-8", xml_declaration=True)
    return names, report
