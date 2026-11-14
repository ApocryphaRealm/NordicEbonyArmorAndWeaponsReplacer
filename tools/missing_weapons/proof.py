# Proof renders of the BUILT game NIFs with BACKFACE CULLING ON - the game draws one side of a triangle, and the design
# sheets draw both, so a face wound the wrong way only shows here (past mistakes: Truly Nordic shield 1.0.0).
# Each piece is imported from its game NIF (PyNifly), textured from the shipped diffuse atlases, and shot from the front,
# the back and a three-quarter view; a back face renders as see-through.
# Run: blender --background --factory-startup --python proof.py -- <meshes\weapons\ebony folder> <textures root> <out folder>
import bpy, os, sys, math, addon_utils
from mathutils import Vector, Matrix
addon_utils.enable("io_scene_nifly", default_set=True)
SRC, TEX, OUT = sys.argv[sys.argv.index("--") + 1:][:3]
ONLY = (sys.argv[sys.argv.index("--") + 4:] or [""])[0].split(",")      # optional 4th: a comma list of pieces (e.g. warhammer)
os.makedirs(OUT, exist_ok=True)
PIECES = [("mace", "ebonymace.nif", None), ("warhammer", "ebonywarhammer.nif", None), ("bow", "ebonybowskinned.nif", None),
          ("arrow", "ebonyarrowprojectile.nif", None), ("quiver", "ebonyarrow.nif", "ArrowQuiver"),
          ("mace_1st", "1stpersonebonymace.nif", None)]

def clear():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)

sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 24; sc.cycles.use_denoising = True
sc.view_settings.view_transform = "Standard"; sc.render.film_transparent = False
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.32, 0.33, 0.35, 1)
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0

_mat = {}
def material(dds):
    if dds in _mat: return _mat[dds]
    m = bpy.data.materials.new(os.path.basename(dds)); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    p = os.path.join(TEX, dds.replace("\\", os.sep))
    if os.path.isfile(p):
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(p, check_existing=True); nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    else:
        b.inputs["Base Color"].default_value = (1, 0, 1, 1)            # a missing texture shows magenta
    pn = p[:-4] + "_n.dds"            # the game's tangent-space normal map, as the game shader uses it: Blender derives the
    if os.path.isfile(pn):            # tangents from the UVs, so a piece whose UVs were lost renders flat here too (warhammer 1.1.0)
        tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = bpy.data.images.load(pn, check_existing=True); tn.image.colorspace_settings.name = "Non-Color"
        nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(tn.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Metallic"].default_value = 0.6; b.inputs["Roughness"].default_value = 0.4
    tr = nt.nodes.new("ShaderNodeBsdfTransparent"); geo = nt.nodes.new("ShaderNodeNewGeometry"); mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(geo.outputs["Backfacing"], mix.inputs["Fac"]); nt.links.new(b.outputs[0], mix.inputs[1]); nt.links.new(tr.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    m.use_backface_culling = True; _mat[dds] = m; return m

from io_scene_nifly.pyn.pynifly import NifFile
def load(path, only_under=None):
    clear()
    nf = NifFile(path); tex = {}
    for s in nf.shapes:
        try: tex[s.name] = s.shader.textures.get("Diffuse", "")
        except Exception: tex[s.name] = ""
    bpy.ops.import_scene.pynifly(filepath=path, import_collisions=False)
    objs = []
    for o in bpy.data.objects:
        if o.type != "MESH": continue
        nm = o.name if o.name in tex else o.name.split(".")[0]
        d = tex.get(nm, "")
        if "blood" in (nm + d).lower() or not d.lower().startswith("textures\\nordwar"):
            o.hide_render = True; continue
        o.data.materials.clear(); o.data.materials.append(material(d)); objs.append(o)
    for L, rot, e in (("key", (math.radians(40), math.radians(-35), 0), 3.0), ("rim", (math.radians(-55), math.radians(145), 0), 2.0), ("fill", (math.radians(60), math.radians(160), 0), 1.2)):
        l = bpy.data.lights.new(L, "SUN"); l.energy = e; lo = bpy.data.objects.new(L, l); lo.rotation_euler = rot; sc.collection.objects.link(lo)
    return objs

def shoot(objs, png, yaw, pitch, W=700, H=1100, region=None, flip=False):
    dg = bpy.context.evaluated_depsgraph_get(); P = []
    for o in objs:
        e = o.evaluated_get(dg); me = e.to_mesh(); P += [e.matrix_world @ v.co for v in me.vertices]; e.to_mesh_clear()
    if region:                                     # (axis, "min"|"max", depth): frame only the points that far from that end
        ax, end, depth = region; lo, hi = min(p[ax] for p in P), max(p[ax] for p in P)
        P = [p for p in P if (p[ax] <= lo + depth if end == "min" else p[ax] >= hi - depth)]
    yaw, pitch = math.radians(yaw), math.radians(pitch)
    fwd = Vector((math.sin(yaw) * math.cos(pitch), math.sin(pitch), math.cos(yaw) * math.cos(pitch)))   # camera sits along +fwd
    right = Vector((0, 1, 0)).cross(fwd).normalized() if abs(fwd.y) < 0.999 else Vector((1, 0, 0)); up = fwd.cross(right)
    if flip: right, up = -right, -up
    xs = [p.dot(right) for p in P]; ys = [p.dot(up) for p in P]; zs = [p.dot(fwd) for p in P]
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    cam = bpy.data.cameras.new("c"); cam.type = "ORTHO"; cam.clip_start = 1; cam.clip_end = 5000
    w_, h_ = max(xs) - min(xs), max(ys) - min(ys)
    cam.ortho_scale = 1.1 * (max(h_, w_ * H / W) if H >= W else max(w_, h_ * W / H))   # along the longer side
    co = bpy.data.objects.new("c", cam); sc.collection.objects.link(co); sc.camera = co
    co.location = right * cx + up * cy + fwd * (max(zs) + 300)
    co.rotation_mode = "QUATERNION"; co.rotation_quaternion = Matrix((right, up, fwd)).transposed().to_quaternion()
    sc.render.resolution_x, sc.render.resolution_y = W, H; sc.render.filepath = png
    bpy.ops.render.render(write_still=True); bpy.data.objects.remove(co)

def rake(d):
    """one grazing sun travelling along d, the ambient turned down: relief shows, a flat-lit surface reads flat"""
    for o in [o for o in bpy.data.objects if o.type == "LIGHT"]: o.hide_render = True
    l = bpy.data.lights.new("rake", "SUN"); l.energy = 5.0; lo = bpy.data.objects.new("rake", l); sc.collection.objects.link(lo)
    lo.rotation_mode = "QUATERNION"; lo.rotation_quaternion = Vector(d).normalized().to_track_quat("-Z", "Y")
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.12
    return lo

def unrake(lo):
    bpy.data.objects.remove(lo); w.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
    for o in [o for o in bpy.data.objects if o.type == "LIGHT"]: o.hide_render = False

# close-ups (2026-11-14 06:48 fixes): name, yaw, pitch, region, raking light travel direction (None = the three suns), flip
CLOSE = {"warhammer": [("face_rake", -90, 0, (0, "min", 3.0), (0.2, -0.7, 0.7), False),
                       ("face_profile", 0, 0, (0, "min", 6.0), (0.2, -0.7, -0.7), False),
                       ("face_tq", -55, 20, (0, "min", 6.0), (0.25, -0.6, 0.75), False)],
         "arrow": [("nock", 30, 18, (1, "min", 6.0), None, False), ("nock_end", 0, -89, (1, "min", 1.0), None, False),
                   ("nock_side", 90, 0, (1, "min", 6.0), None, False)],
         # ebonyarrow.nif's ArrowQuiver frame on the vanilla skeleton's QUIVER node: local -z points INTO the wearer's back,
         # -y is up (the mouth). "worn_out" is what is seen from behind the wearer; "worn_body" the side against his back
         "quiver": [("worn_out", 0, 0, None, None, True), ("worn_body", 180, 0, None, None, True), ("worn_side", 90, 0, None, None, True)]}

for name, fn, _ in PIECES:
    if ONLY != [""] and name not in ONLY: continue
    objs = load(os.path.join(SRC, fn))
    if name == "quiver":                           # the quiver as worn: its body and six arrows, not the loose arrow beside it
        for o in [o for o in objs if o.name.split(".")[0] == "Arrow:0"]: o.hide_render = True; objs.remove(o)
    print("PIECE", name, [o.name for o in objs])
    for view, yaw, pitch in (("front", 0, 0), ("back", 180, 0), ("tq", 40, 20)):
        shoot(objs, os.path.join(OUT, "%s_%s.png" % (name, view)), yaw, pitch)
    for view, yaw, pitch, region, d, flip in CLOSE.get(name, []):
        lo = rake(d) if d else None
        shoot(objs, os.path.join(OUT, "%s_%s.png" % (name, view)), yaw, pitch, W=900, H=900, region=region, flip=flip)
        if lo: unrake(lo)
print("PROOF DONE")
