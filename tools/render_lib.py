#!/usr/bin/env python3
r"""Blender renders of built meshes with GAME-LIKE lighting, shared by installer-images.py and the review sheets.

Each shape is textured from ITS OWN texture set, read from the NIF with niflib (no guessing a normal from a diffuse name):
  * a TruePBR shape (texture set slots 0 / 1 / 5): Principled BSDF with base colour = albedo, metallic = RMAOS green,
    roughness = RMAOS red, the normal map from slot 1 - lit by a sky-to-ground gradient world that the reflections see
    (the camera sees the plain backdrop): the stand-in for Community Shaders' cube-map reflections;
  * a classic shape (diffuse, normal, env mask in slot 5): the owner's 2026-11-15 07:26 rule for classic Skyrim shading -
    no metallic, specular strength from the _m mask, the same gradient world.
Shapes whose diffuse does not start with one of `prefixes` (blood decals, vanilla parts) are hidden.

render(shots, tex_roots, out_dir, prefixes, size) -> writes <out_dir>\<shot>.png; shots = {name: ([nif paths], yaw)}.
"""
import glob
import json
import os
import shutil
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import niflib  # noqa: E402

BLENDER_SCRIPT = r'''
import bpy, os, sys, json, math, addon_utils
from mathutils import Vector, Matrix
addon_utils.enable("io_scene_nifly", default_set=True)
job = json.load(open(sys.argv[sys.argv.index("--") + 1]))
sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 48; sc.cycles.use_denoising = True
sc.view_settings.view_transform = "Standard"; sc.render.film_transparent = True
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; bg = w.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.35, 0.36, 0.38, 1)
nt_ = w.node_tree; tc = nt_.nodes.new("ShaderNodeTexCoord"); sep = nt_.nodes.new("ShaderNodeSeparateXYZ")
ramp = nt_.nodes.new("ShaderNodeValToRGB"); ramp.color_ramp.elements[0].position = 0.35; ramp.color_ramp.elements[0].color = (0.10, 0.10, 0.11, 1)
ramp.color_ramp.elements[1].position = 0.75; ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.02, 1)
mapr = nt_.nodes.new("ShaderNodeMapRange"); mapr.inputs["From Min"].default_value = -1.0; mapr.inputs["From Max"].default_value = 1.0
nt_.links.new(tc.outputs["Generated"], sep.inputs[0]); nt_.links.new(sep.outputs["Z"], mapr.inputs["Value"]); nt_.links.new(mapr.outputs["Result"], ramp.inputs["Fac"])
bg2 = nt_.nodes.new("ShaderNodeBackground"); nt_.links.new(ramp.outputs["Color"], bg2.inputs["Color"]); bg2.inputs["Strength"].default_value = 1.3
lp = nt_.nodes.new("ShaderNodeLightPath"); mx = nt_.nodes.new("ShaderNodeMixShader")
nt_.links.new(lp.outputs["Is Camera Ray"], mx.inputs["Fac"]); nt_.links.new(bg2.outputs[0], mx.inputs[1]); nt_.links.new(bg.outputs[0], mx.inputs[2])
nt_.links.new(mx.outputs[0], nt_.nodes["World Output"].inputs["Surface"])
mats = {}
def img(p, data):
    if not p or not os.path.isfile(p): return None
    i = bpy.data.images.load(p, check_existing=True)
    if data: i.colorspace_settings.name = "Non-Color"
    return i
def material(ts):
    key = json.dumps(ts)
    if key in mats: return mats[key]
    m = bpy.data.materials.new("m%d" % len(mats)); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    d = img(ts["d"], False); n = img(ts["n"], True); x = img(ts["x"], True)
    if d:
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = d; nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    if n:
        tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = n
        nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(tn.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    if ts["pbr"] and x:
        tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = x; sp = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(tx.outputs["Color"], sp.inputs[0]); nt.links.new(sp.outputs[0], b.inputs["Roughness"]); nt.links.new(sp.outputs[1], b.inputs["Metallic"])
        b.inputs["Specular IOR Level"].default_value = 0.5
    else:
        b.inputs["Metallic"].default_value = 0.0
        if x:
            tm = nt.nodes.new("ShaderNodeTexImage"); tm.image = x
            sm = nt.nodes.new("ShaderNodeMath"); sm.operation = "MULTIPLY_ADD"; sm.inputs[1].default_value = 0.9; sm.inputs[2].default_value = 0.3
            nt.links.new(tm.outputs["Color"], sm.inputs[0]); nt.links.new(sm.outputs[0], b.inputs["Specular IOR Level"]); b.inputs["Roughness"].default_value = 0.3
        else:
            b.inputs["Roughness"].default_value = 0.5
    if ts.get("alpha") and d:
        nt.links.new(t.outputs["Alpha"], b.inputs["Alpha"])
    mats[key] = m; return m
for name, (paths, yaw) in job["shots"].items():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    objs = []
    for p in paths:
        tex = job["tex"][p]
        before = set(bpy.data.objects)
        bpy.ops.import_scene.pynifly(filepath=p, import_collisions=False)
        for o in [o for o in bpy.data.objects if o not in before]:
            if o.type != "MESH": continue
            nm = o.name if o.name in tex else o.name.split(".")[0]; ts = tex.get(nm)
            if not ts: o.hide_render = True; continue
            o.data.materials.clear(); o.data.materials.append(material(ts)); objs.append(o)
    for L, rot, e in (("key", (math.radians(40), math.radians(-35), 0), 3.0), ("rim", (math.radians(-55), math.radians(145), 0), 2.0), ("fill", (math.radians(60), math.radians(160), 0), 1.0)):
        l = bpy.data.lights.new(L, "SUN"); l.energy = e; lo = bpy.data.objects.new(L, l); lo.rotation_euler = rot; sc.collection.objects.link(lo)
    dg = bpy.context.evaluated_depsgraph_get(); P = []
    for o in objs:
        e = o.evaluated_get(dg); me = e.to_mesh(); P += [e.matrix_world @ v.co for v in me.vertices]; e.to_mesh_clear()
    upv = Vector((0, 0, 1)) if job["armour"].get(name) else Vector((0, 1, 0))
    yw = math.radians(yaw)
    if upv.z: fwd = Vector((math.sin(yw), -math.cos(yw), 0.08)).normalized()
    else: fwd = Vector((math.sin(yw), 0, math.cos(yw)))
    right = upv.cross(fwd).normalized(); up = fwd.cross(right)
    xs = [p.dot(right) for p in P]; ys = [p.dot(up) for p in P]; zs = [p.dot(fwd) for p in P]
    W, H = job["size"]; w_, h_ = max(xs) - min(xs), max(ys) - min(ys)
    cam = bpy.data.cameras.new("c"); cam.type = "ORTHO"; cam.clip_start = 1; cam.clip_end = 5000
    cam.ortho_scale = 1.08 * (max(h_, w_ * H / W) if H >= W else max(w_, h_ * W / H))
    co = bpy.data.objects.new("c", cam); sc.collection.objects.link(co); sc.camera = co
    co.location = right * (max(xs) + min(xs)) / 2 + up * (max(ys) + min(ys)) / 2 + fwd * (max(zs) + 300)
    co.rotation_mode = "QUATERNION"; co.rotation_quaternion = Matrix((right, up, fwd)).transposed().to_quaternion()
    sc.render.resolution_x, sc.render.resolution_y = W, H; sc.render.filepath = os.path.join(job["out"], name + ".png")
    bpy.ops.render.render(write_still=True); print("SHOT", name, len(objs))
'''


def blender():
    b = os.environ.get("BLENDER") or shutil.which("blender")
    if not b:
        c = sorted(glob.glob(r"C:\Program Files\Blender Foundation\Blender *\blender.exe")); b = c[-1] if c else None
    if not b:
        raise SystemExit("render_lib: Blender not found - set BLENDER")
    return b


def _texsets(path, tex_roots, prefixes):
    """shape name -> {d, n, x, pbr, alpha} for the shapes of ours in one NIF"""
    n = niflib.Nif(path); out = {}
    for b, t in enumerate(n.btypes):
        if t not in ("BSTriShape", "BSDynamicTriShape", "BSSubIndexTriShape", "NiTriShape"):
            continue
        try:
            o = n.av_end(b, 0, [], [])
            sh = struct.unpack_from("<i", n.blocks[b], o + 16 + 4)[0]
        except Exception:
            continue
        if sh < 0 or n.btypes[sh] != "BSLightingShaderProperty":
            continue
        ts = n.i32(sh, n.ref_offsets(sh)[0][-1])
        if ts < 0:
            continue
        blk = n.blocks[ts]; k = struct.unpack_from("<I", blk, 0)[0]; q = 4; paths = []
        for _ in range(k):
            L = struct.unpack_from("<I", blk, q)[0]; paths.append(blk[q + 4:q + 4 + L].decode("latin-1")); q += 4 + L
        if not paths or not paths[0].lower().replace("/", "\\").startswith(tuple(prefixes)):
            continue
        f2 = struct.unpack_from("<I", n.blocks[sh], n.net_end(sh, 4, [], []) + 4)[0]

        def find(rel):
            if not rel:
                return ""
            for r in tex_roots:
                p = os.path.join(r, rel.replace("\\", os.sep))
                if os.path.isfile(p):
                    return p
            return ""
        alpha = any(n.btypes[x] == "NiAlphaProperty" for x in [struct.unpack_from("<i", n.blocks[b], o + 16 + 8)[0]] if x >= 0)
        out[n.name(b)] = {"d": find(paths[0]), "n": find(paths[1] if len(paths) > 1 else ""),
                          "x": find(paths[5] if len(paths) > 5 else ""), "pbr": bool(f2 & 0x00800000), "alpha": alpha}
    return out


def render(shots, tex_roots, out_dir, prefixes, size=(900, 1200)):
    os.makedirs(out_dir, exist_ok=True)
    for k, (ps, _) in shots.items():
        for p in ps:
            if not os.path.isfile(p):
                raise SystemExit("render_lib: no %s" % p)
    tex = {p: _texsets(p, tex_roots, [x.lower() for x in prefixes]) for ps, _ in shots.values() for p in ps}
    job = {"shots": shots, "tex": tex, "out": out_dir, "size": list(size), "armour": {k: not k.startswith("w_") for k in shots}}
    jp = os.path.join(out_dir, "job.json"); json.dump(job, open(jp, "w"))
    sp = os.path.join(out_dir, "render.py"); open(sp, "w", encoding="utf-8").write(BLENDER_SCRIPT)
    r = subprocess.run([blender(), "--background", "--factory-startup", "--python-exit-code", "1", "--python", sp, "--", jp],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("render_lib: Blender failed\n" + (r.stdout + r.stderr)[-3000:])
    return out_dir


def card(path, size, bg=(38, 39, 42), rotate=0):
    from PIL import Image
    im = Image.open(path).convert("RGBA")
    if rotate:
        im = im.rotate(rotate)
    box = im.getbbox(); im = im.crop(box) if box else im
    im.thumbnail(size); c = Image.new("RGB", size, bg); c.paste(im, ((size[0] - im.width) // 2, (size[1] - im.height) // 2), im)
    return c
