# Game-like proof renders of BUILT Truly Nordic NIFs (TruePBR) - an approved piece of the set | the new Nordic piece | the
# new Ebony piece, the same views and the same scale per view. From skyforged-missing-weapons-20261115\render_compare.py
# (its "game" lighting): metal mirrors its surroundings in game, so reflections see a sky-to-ground gradient while the
# camera sees a plain grey backdrop - a metallic material under a flat grey world renders steel black (the 2026-11-15
# sheets before 07:30). TruePBR is a metal workflow: base colour = the albedo, metallic = _rmaos G, roughness = _rmaos R,
# the normal = _n (DirectX, green flipped here). Backface culling on (a wrong-way face shows see-through); blood hidden.
# Two halves:
#   python -I render_game_pbr.py prep <job.json>      decode every DDS the job's NIFs name (texconv) into <out>\tex\
#   blender -b --factory-startup --python-exit-code 1 --python render_game_pbr.py -- <job.json>
#   job: {"out", "samples", "models": [{"tag", "nif", "tex_root"}], "views": [{"name","yaw","pitch","W","H", "yr"?, "persp"?}]}
#   tex_root: the folder the NIF's "textures\..." paths resolve under (a package or stage folder holding textures\).
import os, sys, json, math
if "bpy" not in sys.modules:
    import subprocess, re
    TEXCONV = r"D:\Modlists\Njordlinger\tools\Skyking Toolkit\runtime\texconv.exe"
    JOB = json.load(open(sys.argv[2])); OUT = os.path.join(JOB["out"], "tex"); os.makedirs(OUT, exist_ok=True)
    for m in JOB["models"]:
        raw = open(m["nif"], "rb").read()
        for t in sorted(set(x.decode("latin-1") for x in re.findall(rb"textures\\[\x20-\x7e]+?\.dds", raw, re.I))):
            src = os.path.join(m["tex_root"], t)
            if not os.path.isfile(src): print("MISSING", src); continue
            d = os.path.join(OUT, m["tag"], os.path.dirname(t)); os.makedirs(d, exist_ok=True)
            srgb = not re.search(r"_(n|rmaos|s|g|m)\.dds$", t, re.I)
            subprocess.run([TEXCONV, "-nologo", "-y", "-ft", "png", "-f", "R8G8B8A8_UNORM_SRGB" if srgb else "R8G8B8A8_UNORM", "-o", d, src], capture_output=True)
            print("decoded", m["tag"], t)
    sys.exit(0)

import bpy, addon_utils
from mathutils import Vector, Matrix, Euler
addon_utils.enable("io_scene_nifly", default_set=True)
from io_scene_nifly.pyn.pynifly import NifFile
JOB = json.load(open(sys.argv[sys.argv.index("--") + 1])); OUT = JOB["out"]
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = JOB.get("samples", 32); sc.cycles.use_denoising = True
sc.view_settings.view_transform = "Standard"
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; nt_ = w.node_tree
bg = nt_.nodes["Background"]; bg.inputs["Color"].default_value = (0.32, 0.33, 0.35, 1)
tc = nt_.nodes.new("ShaderNodeTexCoord"); sep = nt_.nodes.new("ShaderNodeSeparateXYZ"); ramp = nt_.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position = 0.35; ramp.color_ramp.elements[0].color = (0.10, 0.10, 0.11, 1)
ramp.color_ramp.elements[1].position = 0.75; ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.02, 1)
mapr = nt_.nodes.new("ShaderNodeMapRange"); mapr.inputs["From Min"].default_value = -1.0; mapr.inputs["From Max"].default_value = 1.0
nt_.links.new(tc.outputs["Generated"], sep.inputs[0]); nt_.links.new(sep.outputs["Z"], mapr.inputs["Value"]); nt_.links.new(mapr.outputs["Result"], ramp.inputs["Fac"])
bg2 = nt_.nodes.new("ShaderNodeBackground"); nt_.links.new(ramp.outputs["Color"], bg2.inputs["Color"]); bg2.inputs["Strength"].default_value = 1.3
lp = nt_.nodes.new("ShaderNodeLightPath"); mx = nt_.nodes.new("ShaderNodeMixShader")
nt_.links.new(lp.outputs["Is Camera Ray"], mx.inputs["Fac"]); nt_.links.new(bg2.outputs[0], mx.inputs[1]); nt_.links.new(bg.outputs[0], mx.inputs[2])
nt_.links.new(mx.outputs[0], nt_.nodes["World Output"].inputs["Surface"])
for nm, rot, e in (("key", (math.radians(40), math.radians(-35), 0), 3.0), ("rim", (math.radians(-55), math.radians(145), 0), 2.0),
                   ("fill", (math.radians(60), math.radians(160), 0), 1.2)):
    l = bpy.data.lights.new(nm, "SUN"); l.energy = e; lo = bpy.data.objects.new(nm, l); lo.rotation_euler = rot; sc.collection.objects.link(lo)

_mat = {}
def img(p, data):
    i = bpy.data.images.load(p, check_existing=True)
    if data: i.colorspace_settings.name = "Non-Color"
    return i
def material(base, npath=None, legacy=False, clip=None):
    """base: the decoded albedo png path (without .png)"""
    key = (base, npath, legacy, clip)
    if key in _mat: return _mat[key]
    m = bpy.data.materials.new(os.path.basename(base)); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    if os.path.isfile(base + ".png"):
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = img(base + ".png", False); nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
        if clip is not None:
            t.image.alpha_mode = "STRAIGHT"; gt = nt.nodes.new("ShaderNodeMath"); gt.operation = "LESS_THAN"; gt.inputs[1].default_value = clip / 255.0
            nt.links.new(t.outputs["Alpha"], gt.inputs[0]); CLIPN = gt
    else:
        print("MISSING TEXTURE", base); b.inputs["Base Color"].default_value = (1, 0, 1, 1)
    npath = npath if npath and os.path.isfile(npath) else base + "_n.png"
    print("NORMAL", base, npath, os.path.isfile(npath))
    if os.path.isfile(npath):
        tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = img(npath, True)
        sp = nt.nodes.new("ShaderNodeSeparateColor"); inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
        cm = nt.nodes.new("ShaderNodeCombineColor"); nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(tn.outputs["Color"], sp.inputs[0]); nt.links.new(sp.outputs[0], cm.inputs[0]); nt.links.new(sp.outputs[1], inv.inputs[1])
        nt.links.new(inv.outputs[0], cm.inputs[1]); nt.links.new(sp.outputs[2], cm.inputs[2]); nt.links.new(cm.outputs[0], nm.inputs["Color"]); nt.links.new(nm.outputs[0], b.inputs["Normal"])
        # 2026-11-15 chainmail demo, option 2: the _p height (CS TruePBR parallax, NIF slot 3) approximated as a bump on
        # top of the normal map; 0.5 = no displacement
        if os.path.isfile(base + "_p.png"):
            tp = nt.nodes.new("ShaderNodeTexImage"); tp.image = img(base + "_p.png", True); bu = nt.nodes.new("ShaderNodeBump")
            bu.inputs["Strength"].default_value = JOB.get("bump_strength", 1.0); bu.inputs["Distance"].default_value = JOB.get("bump_distance", 0.06)
            nt.links.new(tp.outputs["Color"], bu.inputs["Height"]); nt.links.new(nm.outputs[0], bu.inputs["Normal"]); nt.links.new(bu.outputs[0], b.inputs["Normal"])
            print("PARALLAX-AS-BUMP", base)
    if legacy:
        # vanilla shader as the earlier comparison sheets drew it (sheet_render.py "game"): diffuse kept, no metallic,
        # specular strength from the _m environment mask so reflections see the sky-to-ground world
        b.inputs["Metallic"].default_value = 0.0
        if os.path.isfile(base + "_m.png"):
            tm = nt.nodes.new("ShaderNodeTexImage"); tm.image = img(base + "_m.png", True); sm = nt.nodes.new("ShaderNodeMath"); sm.operation = "MULTIPLY_ADD"
            sm.inputs[1].default_value = 0.9; sm.inputs[2].default_value = 0.3; nt.links.new(tm.outputs["Color"], sm.inputs[0]); nt.links.new(sm.outputs[0], b.inputs["Specular IOR Level"]); b.inputs["Roughness"].default_value = 0.3
        else: b.inputs["Roughness"].default_value = 0.5
    elif os.path.isfile(base + "_rmaos.png"):
        tr_ = nt.nodes.new("ShaderNodeTexImage"); tr_.image = img(base + "_rmaos.png", True); sp2 = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(tr_.outputs["Color"], sp2.inputs[0]); nt.links.new(sp2.outputs[0], b.inputs["Roughness"]); nt.links.new(sp2.outputs[1], b.inputs["Metallic"])
        # 2026-11-15 chainmail demo: the RMAOS AO (B) darkens the base colour (TruePBR applies it to ambient light; here
        # the world light is most of the light, so a base-colour multiply is the closest stand-in) - in every variant
        if JOB.get("use_ao") and "Color" in t.outputs:
            mul = nt.nodes.new("ShaderNodeVectorMath"); mul.operation = "MULTIPLY"
            nt.links.new(t.outputs["Color"], mul.inputs[0]); nt.links.new(sp2.outputs[2], mul.inputs[1]); nt.links.new(mul.outputs[0], b.inputs["Base Color"])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent"); geo = nt.nodes.new("ShaderNodeNewGeometry"); mix = nt.nodes.new("ShaderNodeMixShader")
    if clip is not None and os.path.isfile(base + ".png"):
        mxm = nt.nodes.new("ShaderNodeMath"); mxm.operation = "MAXIMUM"; nt.links.new(geo.outputs["Backfacing"], mxm.inputs[0]); nt.links.new(CLIPN.outputs[0], mxm.inputs[1]); nt.links.new(mxm.outputs[0], mix.inputs["Fac"])
    else: nt.links.new(geo.outputs["Backfacing"], mix.inputs["Fac"])
    nt.links.new(b.outputs[0], mix.inputs[1]); nt.links.new(tr.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], nt.nodes["Material Output"].inputs["Surface"]); m.use_backface_culling = True; _mat[key] = m; return m

def load(model):
    nf = NifFile(model["nif"]); tex = {}; ntex = {}; clipthr = {}
    for s in nf.shapes:
        try: tex[s.name] = s.shader.textures.get("Diffuse", ""); ntex[s.name] = s.shader.textures.get("Normal", "")
        except Exception: tex[s.name] = ""
        if model.get("alphatest"):
            thr = None
            try:
                if s.has_alpha_property:
                    ap = s.alpha_property.properties; thr = int(ap.threshold); print("ALPHA", model["tag"], s.name, "flags", ap.flags, "threshold", thr)
            except Exception as ex: print("ALPHA read failed", s.name, ex)
            if thr is not None: clipthr[s.name] = thr
    before = set(bpy.data.objects)
    for x in bpy.context.scene.objects: x.select_set(False)
    bpy.context.view_layer.objects.active = None
    bpy.ops.import_scene.pynifly(filepath=model["nif"], import_collisions=False)
    objs = []
    for o in [o for o in bpy.data.objects if o not in before]:
        if o.type != "MESH": continue
        nm = o.name if o.name in tex else o.name.split(".")[0]; d = tex.get(nm, "")
        if model.get("mats"):
            # 2026-11-15 (katana / rapier design options): a DESIGN work NIF names no textures - "mats" maps a shape-name
            # substring to the painter's texture base (<work>\tex\<stem>, no .png); key "" is the default
            key = next((k for k in model["mats"] if k and k.lower() in nm.lower()), "")
            if key not in model["mats"]: o.hide_render = True; continue
            o.data.materials.clear(); o.data.materials.append(material(model["mats"][key])); objs.append(o); continue
        # "hide_tex": [substring] hides shapes whose diffuse path holds one (e.g. the approved sword's sheath)
        if "blood" in (nm + d).lower() or not d or nm in model.get("hide", []) or any(h.lower() in nm.lower() for h in model.get("hide_sub", [])) or (model.get("only_sub") and not any(h.lower() in nm.lower() for h in model["only_sub"])) or any(h in d.lower() for h in model.get("hide_tex", [])): o.hide_render = True; continue
        rel = d if d.lower().startswith("textures") else os.path.join("textures", d)
        base = os.path.join(OUT, "tex", model["tag"], rel)[:-4]
        nn = ntex.get(nm, ""); npath = None
        if nn: npath = os.path.join(OUT, "tex", model["tag"], nn if nn.lower().startswith("textures") else os.path.join("textures", nn))[:-4] + ".png"
        o.data.materials.clear(); o.data.materials.append(material(base, npath, model.get("legacy", False), clipthr.get(nm))); objs.append(o)
    if model.get("drop_islands_y_over") is not None:
        # 2026-11-15 (saber A5j design): drop a shape's connected pieces reaching above this world y - the shipped saber's
        # BLADE pieces (to y 67) leave, its guard (to y 9.7), ferrule and pommel stay, so a new design blade can be shown
        # on the shipped hilt
        import bmesh
        thr = float(model["drop_islands_y_over"]); dropped = 0
        for o in objs:
            bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table(); Mw = o.matrix_world; seen = set(); kill = []
            for v in bm.verts:
                if v.index in seen: continue
                st, isl = [v], []; seen.add(v.index)
                while st:
                    a_ = st.pop(); isl.append(a_)
                    for e_ in a_.link_edges:
                        b_ = e_.other_vert(a_)
                        if b_.index not in seen: seen.add(b_.index); st.append(b_)
                if max((Mw @ x.co).y for x in isl) > thr: kill += isl; dropped += 1
            if kill: bmesh.ops.delete(bm, geom=kill, context="VERTS")
            bm.to_mesh(o.data); bm.free()
        print("DROPPED ISLANDS", model["tag"], dropped)
    if model.get("xf_like"):
        # 2026-11-15 (saber A5j design): a design NIF built in a shipped NIF's shape-local frame takes that NIF's shape
        # transform (the shipped saber's shapes sit tilted 4 degrees and offset), so the two line up exactly
        before2 = set(bpy.data.objects)
        for x in bpy.context.scene.objects: x.select_set(False)
        bpy.ops.import_scene.pynifly(filepath=model["xf_like"], import_collisions=False)
        new = [o for o in bpy.data.objects if o not in before2]; bpy.context.view_layer.update()
        ref = next(o for o in new if o.type == "MESH" and "blood" not in o.name.lower()).matrix_world.copy()
        for o in new: bpy.data.objects.remove(o)
        for o in objs: o.matrix_world = ref @ o.matrix_world
        bpy.context.view_layer.update()
    if model.get("rot"):
        # 2026-11-15 (claws): "rot" [x, y, z] degrees (XYZ euler) turns a model about the origin for DISPLAY only - a claw's
        # blades leave the fist along -x with their flats facing y, so (90, 0, -90) stands it blade-up, flats to the camera,
        # like the dagger and sword it is compared with
        R = Euler([math.radians(a) for a in model["rot"]], "XYZ").to_matrix().to_4x4()
        bpy.context.view_layer.update()
        for o in objs: o.matrix_world = R @ o.matrix_world
        bpy.context.view_layer.update()
    if model.get("rings3d"):
        # 2026-11-15 chainmail 3D demo: modelled 4-in-1 rings over the UV-mapped mail region (tools/rings3d.py)
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import rings3d
        bpy.context.view_layer.update(); objs.append(rings3d.make(objs, model["rings3d"]))
    print("MODEL", model["tag"], [(o.name, o.data.materials[0].name) for o in objs]); return objs

def pts(objs):
    dg = bpy.context.evaluated_depsgraph_get(); P = []
    for o in objs:
        e = o.evaluated_get(dg); me = e.to_mesh(); P += [e.matrix_world @ v.co for v in me.vertices]; e.to_mesh_clear()
    return P
def basis(yaw, pitch):
    yaw, pitch = math.radians(yaw), math.radians(pitch)
    fwd = Vector((math.sin(yaw) * math.cos(pitch), math.sin(pitch), math.cos(yaw) * math.cos(pitch)))
    right = Vector((0, 1, 0)).cross(fwd).normalized() if abs(fwd.y) < 0.999 else Vector((1, 0, 0)); up = fwd.cross(right)
    return fwd, right, up
def extent(P, v):
    fwd, right, up = basis(v["yaw"], v["pitch"])
    if v.get("yr"): P = [p for p in P if v["yr"][0] <= p.y <= v["yr"][1]]
    xs = [p.dot(right) for p in P]; ys = [p.dot(up) for p in P]; zs = [p.dot(fwd) for p in P]
    return (min(xs), max(xs), min(ys), max(ys), max(zs))
def shoot(png, v, scale, ext):
    fwd, right, up = basis(v["yaw"], v["pitch"]); x0, x1, y0, y1, z1 = ext; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    cam = bpy.data.cameras.new("c"); cam.clip_start = 0.5; cam.clip_end = 5000
    if v.get("persp"): cam.type = "PERSP"; cam.lens = 35; loc = right * cx + up * cy + fwd * v["persp"]
    else: cam.type = "ORTHO"; cam.ortho_scale = scale; loc = right * cx + up * cy + fwd * (z1 + 300)
    co = bpy.data.objects.new("c", cam); sc.collection.objects.link(co); sc.camera = co; co.location = loc
    co.rotation_mode = "QUATERNION"; co.rotation_quaternion = Matrix((right, up, fwd)).transposed().to_quaternion()
    sc.render.resolution_x, sc.render.resolution_y = v["W"], v["H"]; sc.render.filepath = png
    bpy.ops.render.render(write_still=True); bpy.data.objects.remove(co)

models = []; WH = {}; FW = {}; OBJ = {}
for m in JOB["models"]:
    objs = load(m)
    for o in objs: o.hide_render = True
    # 2026-11-15 (claws): "with": [{"nif", "mats", "views": [view names]}] - extra NIFs (a proxy hand) shown with this model
    # only in the views named, turned by the model's "rot"
    extra = []
    for i, w_ in enumerate(m.get("with", [])):
        eo = load(dict(w_, tag="%s_with%d" % (m["tag"], i), rot=m.get("rot")))
        for o in eo: o.hide_render = True
        extra.append((set(w_["views"]), eo))
    models.append((m["tag"], objs, extra)); WH[m["tag"]] = m.get("WH"); FW[m["tag"]] = m.get("frame_with"); OBJ[m["tag"]] = objs
for v in JOB["views"]:
    vobjs = [objs + [o for vw, eo in extra if v["name"] in vw for o in eo] for _, objs, extra in models]
    exts = [extent(pts(objs), v) for objs in vobjs]; W, H = v["W"], v["H"]
    scale = max(1.1 * max((e[3] - e[2]), (e[1] - e[0]) * H / W) if H >= W else 1.1 * max((e[1] - e[0]), (e[3] - e[2]) * W / H) for e in exts)
    for (tag, _, _), objs, e in zip(models, vobjs, exts):
        if FW.get(tag): e = extent(pts(objs + OBJ[FW[tag]]), v)
        if WH.get(tag): W, H = WH[tag]
        else: W, H = v["W"], v["H"]
        if JOB.get("fit_each"): scale = (1.06 * max((e[3] - e[2]), (e[1] - e[0]) * H / W) if H >= W else 1.06 * max((e[1] - e[0]), (e[3] - e[2]) * W / H))
        for o in objs: o.hide_render = False
        shoot(os.path.join(OUT, "%s_%s.png" % (tag, v["name"])), dict(v, W=W, H=H), scale, e)
        for o in objs: o.hide_render = True
print("RENDER DONE")
