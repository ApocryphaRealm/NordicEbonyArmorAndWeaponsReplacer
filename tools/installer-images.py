#!/usr/bin/env python3
r"""Render the installer pictures from a BUILT package (gate fomod-model-options-have-a-picture: every option that
installs a model shows that model). Each picture is a render of exactly the meshes its option installs, textured from the
package's own 2K textures; the header lines up the whole set.

Usage:  python tools/installer-images.py "<package folder>"      -> fomod/images/*.png in the repository
Needs Blender with PyNifly (BLENDER, or on PATH, or under Program Files) and Pillow.
"""
import json, os, subprocess, sys, glob, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
IMG = os.path.join(REPO, "fomod", "images")

# picture -> (meshes relative to the package, a camera yaw)
SHOTS = {
    "fur": (["00 Core/meshes/armor/ebony/m/cuirass_1.nif"], 20),
    "nofur": (["10 Cuirass - No fur collar/meshes/armor/ebony/m/cuirass_1.nif"], 20),
    "himbo": (["30 HIMBO meshes/meshes/NordicEbony/m/%s_1.nif" % p for p in ("cuirass", "boots", "gauntlets", "helmet")], 20),
    "himbo_nofur": (["33 HIMBO meshes - no fur collar/meshes/NordicEbony/m/cuirass_1.nif"], 20),
    # the 3BA ShapeData NIFs do not open in PyNifly; the female set (the same outfit, before BodySlide) stands in
    "cbbe3ba": (["00 Core/meshes/NordicEbony/f/%s_1.nif" % p for p in ("cuirass", "boots", "gauntlets")], 20),
    "w_mace": (["00 Core/meshes/weapons/ebony/ebonymace.nif"], 0), "w_warhammer": (["00 Core/meshes/weapons/ebony/ebonywarhammer.nif"], 0),
    "w_bow": (["00 Core/meshes/weapons/ebony/ebonybowskinned.nif"], 0), "w_quiver": (["00 Core/meshes/weapons/ebony/ebonyarrow.nif"], 0),
    "w_sword": (["00 Core/meshes/weapons/ebony/ebonysword.nif"], 0), "w_greatsword": (["00 Core/meshes/weapons/ebony/ebonygreatsword.nif"], 0),
    "w_waraxe": (["00 Core/meshes/weapons/ebony/ebonywaraxe.nif"], 0), "w_battleaxe": (["00 Core/meshes/weapons/ebony/ebonybattleaxe.nif"], 0),
    "w_dagger": (["00 Core/meshes/weapons/ebony/ebonydagger.nif"], 0), "w_shield": (["00 Core/meshes/weapons/ebony/ebonyshield.nif"], 0),
}

BLENDER_SCRIPT = r'''
import bpy, os, sys, json, math, addon_utils
from mathutils import Vector, Matrix
addon_utils.enable("io_scene_nifly", default_set=True)
from io_scene_nifly.pyn.pynifly import NifFile
job = json.load(open(sys.argv[sys.argv.index("--") + 1]))
sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 48; sc.cycles.use_denoising = True
sc.view_settings.view_transform = "Standard"; sc.render.film_transparent = True
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.35, 0.36, 0.38, 1)
mats = {}
def material(d):
    if d in mats: return mats[d]
    m = bpy.data.materials.new(d); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    p = os.path.join(job["tex"], d.replace("\\", os.sep))
    if os.path.isfile(p):
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(p, check_existing=True); nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Metallic"].default_value = 0.55; b.inputs["Roughness"].default_value = 0.42
    mats[d] = m; return m
for name, (paths, yaw) in job["shots"].items():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    objs = []
    for p in paths:
        tex = {}
        for s in NifFile(p).shapes:
            try: tex[s.name] = s.shader.textures.get("Diffuse", "")
            except Exception: tex[s.name] = ""
        before = set(bpy.data.objects)
        bpy.ops.import_scene.pynifly(filepath=p, import_collisions=False)
        for o in [o for o in bpy.data.objects if o not in before]:
            if o.type != "MESH": continue
            nm = o.name if o.name in tex else o.name.split(".")[0]; d = tex.get(nm, "")
            if "blood" in (nm + d).lower() or not d.lower().startswith("textures\\nordwar"): o.hide_render = True; continue
            o.data.materials.clear(); o.data.materials.append(material(d)); objs.append(o)
    for L, rot, e in (("key", (math.radians(40), math.radians(-35), 0), 3.0), ("rim", (math.radians(-55), math.radians(145), 0), 2.0), ("fill", (math.radians(60), math.radians(160), 0), 1.0)):
        l = bpy.data.lights.new(L, "SUN"); l.energy = e; lo = bpy.data.objects.new(L, l); lo.rotation_euler = rot; sc.collection.objects.link(lo)
    dg = bpy.context.evaluated_depsgraph_get(); P = []
    for o in objs:
        e = o.evaluated_get(dg); me = e.to_mesh(); P += [e.matrix_world @ v.co for v in me.vertices]; e.to_mesh_clear()
    # armour stands up along z, weapons along y
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
    if not b: raise SystemExit("installer-images: Blender not found - set BLENDER")
    return b


def main(pkg):
    from PIL import Image, ImageDraw
    work = os.path.join(pkg, "_images_work"); os.makedirs(work, exist_ok=True)
    shots = {k: ([os.path.join(pkg, p) for p in ps], yaw) for k, (ps, yaw) in SHOTS.items()}
    for k, (ps, _) in shots.items():
        for p in ps:
            if not os.path.isfile(p): raise SystemExit("installer-images: the package has no %s" % p)
    job = {"shots": shots, "tex": os.path.join(pkg, "00 Core"), "out": work, "size": [900, 1200],
           "armour": {k: not k.startswith("w_") for k in shots}}
    jp = os.path.join(work, "job.json"); json.dump(job, open(jp, "w"))
    sp = os.path.join(work, "render.py"); open(sp, "w", encoding="utf-8").write(BLENDER_SCRIPT)
    r = subprocess.run([blender(), "--background", "--factory-startup", "--python-exit-code", "1", "--python", sp, "--", jp], capture_output=True, text=True)
    if r.returncode != 0: raise SystemExit("installer-images: Blender failed\n" + (r.stdout + r.stderr)[-3000:])
    os.makedirs(IMG, exist_ok=True)
    bg = (38, 39, 42)
    def card(name, size):
        im = Image.open(os.path.join(work, name + ".png")).convert("RGBA"); box = im.getbbox(); im = im.crop(box) if box else im
        im.thumbnail(size); c = Image.new("RGB", size, bg); c.paste(im, ((size[0] - im.width) // 2, (size[1] - im.height) // 2), im); return c
    for name in ("fur", "nofur", "himbo", "himbo_nofur", "cbbe3ba"):
        card(name, (800, 1000)).save(os.path.join(IMG, name + ".png"))
    # header: the armour and the twelve pieces in a row
    order = ["fur", "w_sword", "w_greatsword", "w_waraxe", "w_battleaxe", "w_dagger", "w_shield", "w_mace", "w_warhammer", "w_bow", "w_quiver"]
    H = 520; head = Image.new("RGB", (1800, H + 60), bg); x = 10
    widths = {k: (260 if k == "fur" else 230 if k in ("w_shield", "w_quiver") else 140) for k in order}
    scale = (1780 - 10 * (len(order) - 1)) / sum(widths.values())
    for k in order:
        w = int(widths[k] * scale); head.paste(card(k, (w, H)), (x, 10)); x += w + 10
    d = ImageDraw.Draw(head); d.text((14, H + 22), "Nordic Ebony Armor and Weapons Replacer - NordwarUA's Wolf ebony set in Xtudo's black, the full set", fill=(225, 205, 150))
    head.save(os.path.join(IMG, "header.png"))
    shutil.rmtree(work, ignore_errors=True)
    print("installer images written to", IMG)


if __name__ == "__main__":
    main(sys.argv[1])
