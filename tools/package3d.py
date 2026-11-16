#!/usr/bin/env python3
r"""The full-3D package (the MAIN file since 1.0.0) from the flat package the packager has just built (the owner,
2026-11-16: "The 3D build is the MAIN file, the flat/texture-only build the OPTIONAL file").

WHAT THE 3D PACKAGE IS
    The flat package, file for file, with the full-3D build laid over it:
      00 Core                         <- <work>\build\out\  (the armour and weapon meshes with every mail ring, rivet,
                                         stud, buckle, strap and lamellar scale modelled; the 3D texture sets)
      10 Cuirass - No fur collar      <- <work>\build\out_opt\10 Cuirass - No fur collar\  (Ebony only)
      30..37 body options             <- the 3D BodySlide projects and meshes prebuilt from them (tools\full3d\
                                         build3d_bodies.py), replacing the flat ones folder for folder
    Everything else - the plugin, the SkyPatcher options, the FOMOD, README, NOTICE, CHANGELOG, LICENSE - is the flat
    package's. The installer is the same installer with the same choices.

WHERE THE 3D BUILD COMES FROM
    tools\full3d\ (moved here from 4. plans\nordic-carved-missing-weapons-20261115\chainmail-demo\tools and
    4. plans\body-fits-20261116 on 2026-11-16) builds it with Blender in a work folder outside git (FULL3D_WORK, default
    the plan folder): hundreds of MB of decoded textures, masks and feature maps, and an hour or more of Blender time.
    So the packager does NOT rebuild it every time: by default it takes the last 3D build and REFUSES it when the 3D
    build was made from different meshes than the flat package now ships (every snapshot mesh the 3D build read is
    compared byte for byte with the flat package's file). --rebuild-3d runs the whole 3D build on the flat package
    first (tools\full3d\rebuild_set.sh, then the 3D BodySlide projects and their BodySlide batch build).

Usage (from a packager):  package3d.make(set_name, flat_pkg, out_pkg, rebuild=False)
"""
import filecmp
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FULL3D = os.path.join(HERE, "full3d")
BODY_PLAN = r"D:\Claude output\4. plans\body-fits-20261116"
BASH = os.environ.get("BASH_EXE") or r"C:\Program Files\Git\bin\bash.exe"
BODY_GROUPS = ("30", "31", "32", "33", "34", "35", "36", "37")


def fail(msg):
    raise SystemExit("package3d: " + msg)


def _ctx(set_name, flat_pkg):
    os.environ["NSET"] = set_name
    os.environ["FULL3D_PKG"] = flat_pkg
    if FULL3D not in sys.path:
        sys.path.insert(0, FULL3D)
    import importlib
    import sets
    importlib.reload(sets)
    return sets, sets.get(set_name)


def _run(args, env, what):
    print("  3D: %s ..." % what)
    r = subprocess.run(args, cwd=FULL3D, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        fail("%s failed:\n%s" % (what, (r.stdout + r.stderr).strip()[-3000:]))
    return r.stdout


def rebuild(set_name, flat_pkg):
    """the whole 3D build on <flat_pkg>: Blender on every piece, the 3D BodySlide projects, the prebuilt 3D bodies"""
    sets, C = _ctx(set_name, flat_pkg)
    env = dict(os.environ, NSET=set_name, FULL3D_PKG=flat_pkg)
    _run([BASH, os.path.join(FULL3D, "rebuild_set.sh"), set_name, "noinstall"], env, "rebuild_set.sh " + set_name)
    for opt in ("30 BodySlide - CBBE 3BA", "34 BodySlide - HIMBO"):
        e = dict(env, BSOPT=opt, BSPKG=flat_pkg)
        for step in ("build", "osd", "check"):
            _run([sys.executable, os.path.join(FULL3D, "bodyslide.py"), step], e, "3D BodySlide project %s (%s)" % (opt, step))
    bodies = os.path.join(C.build, "bodies3d")
    _run([sys.executable, os.path.join(FULL3D, "build3d_bodies.py"), set_name], dict(env, FULL3D_BODIES_OUT=bodies),
         "prebuilt 3D bodies (BodySlide batch build)")
    return bodies


def stale(C, flat_pkg):
    """snapshot meshes the 3D build was made from that differ from (or are missing in) the flat package"""
    bad = []
    for pc in C.pieces:
        opt = pc.get("opt")
        for rel in pc["files"]:
            snap = C.snap_of(rel, opt)
            now = os.path.join(flat_pkg, opt or "00 Core", rel)
            if not os.path.isfile(snap):
                bad.append("%s: the 3D build has no snapshot of it" % rel)
            elif not os.path.isfile(now):
                bad.append("%s: the flat package no longer ships it" % rel)
            elif not filecmp.cmp(snap, now, shallow=False):
                bad.append("%s%s: the flat package's file is not the one the 3D build was made from" % (rel, " (%s)" % opt if opt else ""))
    return bad


def _overlay(src, dst):
    n = 0
    for dp, _, fs in os.walk(src):
        for f in fs:
            s = os.path.join(dp, f)
            d = os.path.join(dst, os.path.relpath(s, src))
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)
            n += 1
    return n


def make(set_name, flat_pkg, out_pkg, rebuild_3d=False):
    if not os.path.isdir(os.path.join(flat_pkg, "00 Core")):
        fail("no flat package at %s" % flat_pkg)
    bodies = rebuild(set_name, flat_pkg) if rebuild_3d else None
    sets, C = _ctx(set_name, flat_pkg)
    if bodies is None:
        bodies = os.path.join(C.build, "bodies3d")
        if not os.path.isdir(bodies):
            bodies = os.path.join(BODY_PLAN, "3d-" + set_name)     # where the first prebuilt 3D bodies were made
    bad = stale(C, flat_pkg)
    if bad:
        fail("the last 3D build was made from other meshes than this flat package ships - rebuild it (--rebuild-3d):\n  "
             + "\n  ".join(bad[:20]) + ("\n  ... %d more" % (len(bad) - 20) if len(bad) > 20 else ""))
    if not os.path.isdir(os.path.join(C.bout, "meshes")):
        fail("no 3D build output in %s - run with --rebuild-3d" % C.bout)

    if os.path.isdir(out_pkg):
        fail("%s already exists - the packager moves an old version folder aside before building" % out_pkg)
    shutil.copytree(flat_pkg, out_pkg)
    n_core = _overlay(C.bout, os.path.join(out_pkg, "00 Core"))
    n_opt = 0
    opt_root = os.path.join(C.build, "out_opt")
    if os.path.isdir(opt_root):
        for opt in os.listdir(opt_root):
            if not os.path.isdir(os.path.join(out_pkg, opt)):
                fail("the 3D build has an option '%s' the flat package does not" % opt)
            n_opt += _overlay(os.path.join(opt_root, opt), os.path.join(out_pkg, opt))

    # body options: the 3D projects and prebuilt meshes replace the flat ones, folder for folder
    flat_groups = sorted(d for d in os.listdir(flat_pkg) if d[:2] in BODY_GROUPS and os.path.isdir(os.path.join(flat_pkg, d)))
    have = sorted(d for d in os.listdir(bodies) if os.path.isdir(os.path.join(bodies, d)) and d[:2] in BODY_GROUPS) if os.path.isdir(bodies) else []
    if flat_groups != have:
        fail("the 3D body folders (%s) are not the flat package's body options (%s) - rebuild them (--rebuild-3d)"
             % (", ".join(have) or "none", ", ".join(flat_groups)))
    n_body = 0
    for g in flat_groups:
        shutil.rmtree(os.path.join(out_pkg, g))
        n_body += _overlay(os.path.join(bodies, g), os.path.join(out_pkg, g))

    # the 3D textures the 3D meshes name must all be in the 3D package
    tex = os.path.join(out_pkg, "00 Core", C.tex)
    missing = [f for f in os.listdir(os.path.join(C.bout, C.tex)) if not os.path.isfile(os.path.join(tex, f))]
    if missing:
        fail("3D textures missing from the package: %s" % ", ".join(missing))
    print("  3D package ............ %s" % out_pkg)
    print("  3D core files laid over %d, option files %d, body-option files %d (from %s)" % (n_core, n_opt, n_body, bodies))
    return out_pkg
