#!/usr/bin/env python3
r"""Turn a built package's meshes into Community Shaders TruePBR, with textures made from NordwarUA's own maps.

The owner, 2026-11-15 21:55: "make the whole armor and weapon set in PBR with cube maps". The method is our Truly Nordic
set's (TrulyNordicCarvedWeaponsReplacer\tools\assemble.py): every shape of ours gets the PLAIN TruePBR shader block
(BSLightingShaderProperty type 0, SLSF2 bit 23 'TruePBR'; data\truepbr_plain_shader.bin, the same 100 bytes Truly Nordic
ships) and a texture set of three: slot 0 albedo, slot 1 normal, slot 5 RMAOS. Per shape, the original block's SLSF1
Skinned and SLSF2 Double_Sided / Vertex_Colors bits are carried over (a skinned shape without Skinned draws nothing).

CUBE MAPS: the TruePBR shader has no per-material environment cube map - in Community Shaders' Lighting.hlsl the
TRUE_PBR path binds slot 4 as parallax, and every PBR surface's reflection is the specular image-based lighting from the
Dynamic Cubemaps feature (DynamicCubemaps::GetDynamicCubemapSpecularIrradiance, weighted by the material's metalness and
roughness). So "with cube maps" is: real metal in the RMAOS (metal mirrors its surroundings through CS's cube maps), and
the page recommends Community Shaders' Dynamic Cubemaps. NordwarUA's static cube maps (Ebony_e, metalic_e) are not used.

Only shaders whose diffuse is one of OUR set's textures (src_prefixes) are converted; blood decals and anything else stay.
Textures are produced once per diffuse (recolour_black.pbr_maps) and the normal map is NordwarUA's _n, copied unchanged:
    <out_tex_root>\textures\pbr\<folder>\<diffuse stem>.dds         albedo   BC7 sRGB
    <out_tex_root>\textures\pbr\<folder>\<diffuse stem>_rmaos.dds   RMAOS    BC7
    <out_tex_root>\textures\pbr\<folder>\<normal stem>.dds          normal   (his file)

verify() reads every NIF back: each converted shader is type 0 with the TruePBR bit, slots exactly 0/1/5, and the three
files exist in the package; no shader anywhere may still name a texture of the set's old folders.
"""
import os
import re
import shutil
import struct
import subprocess
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import niflib  # noqa: E402
import recolour_black as RB  # noqa: E402
import chainmail  # noqa: E402

TEMPLATE = open(os.path.join(HERE, "data", "truepbr_plain_shader.bin"), "rb").read()
TEXCONV_CANDIDATES = [os.environ.get("TEXCONV", ""), r"D:\Modlists\Njordlinger\tools\Skyking Toolkit\runtime\texconv.exe",
                      shutil.which("texconv") or ""]
_F1, _F2 = struct.unpack_from("<II", TEMPLATE, 16)
assert struct.unpack_from("<I", TEMPLATE, 0)[0] == 0 and _F2 & 0x00800000, "data\\truepbr_plain_shader.bin is not the plain TruePBR block"
KEEP_F1 = 0x00000002            # Skinned
KEEP_F2 = 0x00000010 | 0x00000020   # Double_Sided, Vertex_Colors


def fail(msg):
    raise SystemExit("truepbr: " + msg)


def texconv():
    for c in TEXCONV_CANDIDATES:
        if c and os.path.isfile(c):
            return c
    fail("texconv.exe not found - set TEXCONV")


def _texset(n, sh):
    ts = n.i32(sh, n.ref_offsets(sh)[0][-1])
    if ts < 0:
        return ts, []
    blk = n.blocks[ts]; k = struct.unpack_from("<I", blk, 0)[0]; q = 4; out = []
    for _ in range(k):
        L = struct.unpack_from("<I", blk, q)[0]; out.append(blk[q + 4:q + 4 + L].decode("latin-1")); q += 4 + L
    return ts, out


def _texset_block(paths):
    b = struct.pack("<I", len(paths))
    for p in paths:
        e = p.encode("latin-1"); b += struct.pack("<I", len(e)) + e
    return bytearray(b)


def _flags(n, sh):
    o = n.net_end(sh, 4, [], [])
    return struct.unpack_from("<II", n.blocks[sh], o)


def _stem(p):
    return os.path.splitext(p.replace("/", "\\").split("\\")[-1])[0].lower()


def nifs(roots):
    for r in roots:
        for dp, _, fs in os.walk(r):
            for f in fs:
                if f.lower().endswith(".nif"):
                    yield os.path.join(dp, f)


def ours(path, src_prefixes):
    p = path.lower().replace("/", "\\")
    return any(p.startswith(s) for s in src_prefixes)


def scan(roots, src_prefixes):
    """every material of ours: diffuse stem -> (normal stem, envmask stem or None)"""
    mats = {}
    for p in nifs(roots):
        n = niflib.Nif(p)
        for b, t in enumerate(n.btypes):
            if t != "BSLightingShaderProperty":
                continue
            _, paths = _texset(n, b)
            if not paths or not ours(paths[0], src_prefixes):
                continue
            d = _stem(paths[0]); nm = _stem(paths[1]) if len(paths) > 1 and paths[1] else None
            em = _stem(paths[5]) if len(paths) > 5 and paths[5] else None
            if nm is None:
                fail("%s: a shape on %s has no normal map" % (p, d))
            prev = mats.setdefault(d, (nm, em))
            if prev != (nm, em):
                fail("%s is used with two different normal/mask pairs: %s and %s" % (d, prev, (nm, em)))
    return mats


def build_textures(mats, find_src, kind, folder, out_root, work, report=print):
    """find_src(stem) -> path of NordwarUA's .dds (or None). Writes the PBR maps under out_root\\textures\\pbr\\<folder>."""
    tc = texconv(); os.makedirs(work, exist_ok=True)
    dest = os.path.join(out_root, "textures", "pbr", folder); os.makedirs(dest, exist_ok=True)
    normals = set(); stats = []
    for d, (nm, em) in sorted(mats.items()):
        sp = find_src(d)
        if sp is None:
            fail("NordwarUA's download has no %s.dds" % d)
        rgba = RB.load(sp); rgb = rgba[..., :3]
        m = None
        if em:
            mp = find_src(em)
            if mp is None:
                fail("NordwarUA's download has no %s.dds (the mask of %s)" % (em, d))
            m = RB.load(mp)[..., 0]
            if m.shape != rgb.shape[:2]:
                m = np.asarray(Image.fromarray(np.round(m * 255).astype(np.uint8)).resize(rgb.shape[1::-1], Image.BILINEAR), np.float32) / 255
        alb, rm, rec = RB.pbr_maps(rgb, m, d, kind)
        # chain-link material on the helmet aventail and the cuirass mail (the owner, 2026-11-15: option 1, material only)
        ca = chainmail.atlas_of(d) if kind == "ebony" else None
        if ca:
            if m is None:
                fail("chainmail: %s has no _m mask to find the mail in" % d)
            np_ = find_src(nm)
            if np_ is None:
                fail("NordwarUA's download has no %s.dds" % nm)
            N = RB.load(np_)[..., :3]
            if N.shape[:2] != rgb.shape[:2]:
                N = np.asarray(Image.fromarray(np.round(N * 255).astype(np.uint8)).resize(rgb.shape[1::-1], Image.BILINEAR), np.float32) / 255
            alb, rm, cstats = chainmail.apply(ca, alb, rm, m, N)
            report("  chainmail %-9s %s" % (d, cstats))
        a = np.concatenate([alb, rgba[..., 3:4]], -1)     # his alpha (the fur's cut-out) kept
        RB.save_png(os.path.join(work, d + ".png"), a, "RGBA")
        RB.save_png(os.path.join(work, d + "_rmaos.png"), rm, "RGBA")
        for name, fmt, srgb in ((d, "BC7_UNORM_SRGB", True), (d + "_rmaos", "BC7_UNORM", False)):
            args = [tc, "-nologo", "-y", "-f", fmt, "-m", "0", "-o", dest] + (["-srgb"] if srgb else []) + [os.path.join(work, name + ".png")]
            r = subprocess.run(args, capture_output=True, text=True)
            if r.returncode or not os.path.isfile(os.path.join(dest, name + ".dds")):
                fail("texconv failed on %s: %s %s" % (name, r.stdout[-500:], r.stderr[-500:]))
        if nm not in normals:
            np_ = find_src(nm)
            if np_ is None:
                fail("NordwarUA's download has no %s.dds" % nm)
            shutil.copy2(np_, os.path.join(dest, nm + ".dds")); normals.add(nm)
        stats.append((d, rgb.shape[1], float((rm[..., 1] > 0.5).mean()), float(RB.masks(rgb, d, m)[0].mean())))
    for d, w, metal, rec in stats:
        report("  pbr %-14s %4dpx  metal %4.1f%%  recoloured %4.1f%%" % (d, w, 100 * metal, 100 * rec))
    return dest


def convert(roots, src_prefixes, folder):
    """rewrite every shader of ours in every NIF under roots to TruePBR; returns (files changed, shaders converted)"""
    pre = "textures\\pbr\\%s\\" % folder
    files = shaders = 0
    for p in nifs(roots):
        n = niflib.Nif(p); changed = False
        for b, t in enumerate(n.btypes):
            if t != "BSLightingShaderProperty":
                continue
            ts, paths = _texset(n, b)
            if not paths or not ours(paths[0], src_prefixes):
                continue
            f1, f2 = _flags(n, b)
            name_idx = n.i32(b, 4)
            blk = bytearray(TEMPLATE)
            struct.pack_into("<i", blk, 4, name_idx)
            struct.pack_into("<II", blk, 16, _F1 | (f1 & KEEP_F1), _F2 | (f2 & KEEP_F2))
            n.blocks[b] = blk
            struct.pack_into("<i", n.blocks[b], n.ref_offsets(b)[0][-1], ts)
            d = _stem(paths[0]); nm = _stem(paths[1])
            n.blocks[ts] = _texset_block([pre + d + ".dds", pre + nm + ".dds", "", "", "", pre + d + "_rmaos.dds", "", "", ""])
            changed = True; shaders += 1
        if changed:
            n.save(p); files += 1
    return files, shaders


def verify(roots, old_prefixes, folder, tex_roots):
    """refuses: a converted shader that is not plain TruePBR with slots 0/1/5, a missing texture, or any shader still on
    an old texture folder of the set"""
    pre = "textures\\pbr\\%s\\" % folder.lower()
    bad = []; n_ok = 0
    for p in nifs(roots):
        n = niflib.Nif(p)
        for b, t in enumerate(n.btypes):
            if t != "BSLightingShaderProperty":
                continue
            _, paths = _texset(n, b)
            if not paths:
                continue
            lp = [x.lower() for x in paths]
            if ours(lp[0], old_prefixes):
                bad.append("%s: still on %s" % (p, paths[0])); continue
            if not lp[0].startswith(pre):
                continue
            typ = struct.unpack_from("<I", n.blocks[b], 0)[0]; f1, f2 = _flags(n, b)
            used = [i for i, x in enumerate(paths) if x]
            if typ != 0 or not f2 & 0x00800000 or used != [0, 1, 5]:
                bad.append("%s: shader type %d TruePBR %s slots %s" % (p, typ, bool(f2 & 0x00800000), used)); continue
            for x in (paths[0], paths[1], paths[5]):
                if not any(os.path.isfile(os.path.join(r, x)) for r in tex_roots):
                    bad.append("%s: %s is not in the package" % (p, x))
            n_ok += 1
    if bad:
        fail("verify refused %d shader(s):\n  " % len(bad) + "\n  ".join(bad[:40]))
    return n_ok
