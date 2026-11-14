# Proof renders of the BUILT bow (ebonybowskinned.nif) for the three faults the owner found in game (2026-11-14 07:15):
# string nocks, light through the handle, the arrow rest. Imported from the game NIF (PyNifly), textured with the shipped
# Wolf atlases AND their normal maps (Blender derives the tangents from the exported UVs, as the game does), BACKFACE
# CULLING ON (the game draws one side of a triangle). Cycles.
#   tip_*      the limb tips close up: the notches and the cord looped through them
#   grip_*     the riser from the side and from the front with the arrow shown where it rests: a red rod of an arrow's
#              radius (0.3) lying against vanilla's riser width at Bow_MidBone's height, from the string to past the bow
#   backlit_*  the riser against a bright panel straight behind it, nothing else lighting the back: a hole shows as light
# Run: blender --background --factory-startup --python bow_proof.py -- <bow nif> <textures root> <out folder> [prefix]
import bpy, os, sys, math, addon_utils
from mathutils import Vector, Matrix
addon_utils.enable("io_scene_nifly", default_set=True)
a = sys.argv[sys.argv.index("--") + 1:]
NIF, TEX, OUT = a[:3]; PRE = a[3] if len(a) > 3 else "bow"
os.makedirs(OUT, exist_ok=True)
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 48; sc.cycles.use_denoising = True
sc.view_settings.view_transform = "Standard"
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.32, 0.33, 0.35, 1)

def material(dds):
    m = bpy.data.materials.new(os.path.basename(dds)); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    p = os.path.join(TEX, dds.replace("\\", os.sep))
    if os.path.isfile(p):
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(p, check_existing=True); nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    else:
        b.inputs["Base Color"].default_value = (1, 0, 1, 1)
    pn = p[:-4] + "_n.dds"
    if os.path.isfile(pn):
        tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = bpy.data.images.load(pn, check_existing=True); tn.image.colorspace_settings.name = "Non-Color"
        nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(tn.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Metallic"].default_value = 0.6; b.inputs["Roughness"].default_value = 0.4
    tr = nt.nodes.new("ShaderNodeBsdfTransparent"); geo = nt.nodes.new("ShaderNodeNewGeometry"); mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(geo.outputs["Backfacing"], mix.inputs["Fac"]); nt.links.new(b.outputs[0], mix.inputs[1]); nt.links.new(tr.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], nt.nodes["Material Output"].inputs["Surface"]); m.use_backface_culling = True
    return m

def emit(name, rgb, strength):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    for nd in list(nt.nodes):
        if nd.type != "OUTPUT_MATERIAL": nt.nodes.remove(nd)
    e = nt.nodes.new("ShaderNodeEmission"); e.inputs[0].default_value = (*rgb, 1); e.inputs[1].default_value = strength
    nt.links.new(e.outputs[0], nt.nodes["Material Output"].inputs["Surface"]); return m

from io_scene_nifly.pyn.pynifly import NifFile
nf = NifFile(NIF); tex = {s.name: s.shader.textures.get("Diffuse", "") for s in nf.shapes}
bpy.ops.import_scene.pynifly(filepath=NIF, import_collisions=False)
objs = []
for o in bpy.data.objects:
    if o.type != "MESH": continue
    d = tex.get(o.name, tex.get(o.name.split(".")[0], ""))
    o.data.materials.clear(); o.data.materials.append(material(d)); objs.append(o)
arm = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]
dg = bpy.context.evaluated_depsgraph_get()
def bone_world(name):
    for b in arm.data.bones:
        if b.name == name: return arm.matrix_world @ b.head_local
mid = bone_world("Bow_MidBone"); s1, s2 = bone_world("Bow_StringBone1"), bone_world("Bow_StringBone2")
print("PIVOTS", tuple(s1), tuple(s2), "MID", tuple(mid))

lights = []
def three_suns(on=True):
    global lights
    for l in lights: bpy.data.objects.remove(l)
    lights = []
    if not on: return
    for L, rot, e in (("key", (math.radians(40), math.radians(-35), 0), 3.0), ("rim", (math.radians(-55), math.radians(145), 0), 2.0),
                      ("fill", (math.radians(60), math.radians(160), 0), 1.2)):
        l = bpy.data.lights.new(L, "SUN"); l.energy = e; lo = bpy.data.objects.new(L, l); lo.rotation_euler = rot; sc.collection.objects.link(lo); lights.append(lo)

def shoot(png, centre, look, up, size, W=900, H=900):
    look = Vector(look).normalized(); up = Vector(up); right = look.cross(up).normalized(); up = right.cross(look).normalized()
    cam = bpy.data.cameras.new("c"); cam.type = "ORTHO"; cam.ortho_scale = size; cam.clip_start = 0.1; cam.clip_end = 2000
    co = bpy.data.objects.new("c", cam); sc.collection.objects.link(co); sc.camera = co
    co.location = Vector(centre) - look * 300
    co.rotation_mode = "QUATERNION"; co.rotation_quaternion = Matrix((right, up, -look)).transposed().to_quaternion()
    sc.render.resolution_x, sc.render.resolution_y = W, H; sc.render.filepath = os.path.join(OUT, "%s_%s.png" % (PRE, png))
    bpy.ops.render.render(write_still=True); bpy.data.objects.remove(co)

three_suns()
# 1. the tips: string side three-quarter, edge-on (the notches in profile), and from the back (the loop over the back)
for nm, p in (("upper", s2), ("lower", s1)):
    sg = 1 if p.y > 0 else -1; c = p + Vector((0.4, sg * 0.6, 0))
    shoot("tip_%s_tq" % nm, c, (0.75, -0.25 * sg, -0.6), (0, 1, 0), 5.5)
    shoot("tip_%s_edge" % nm, c, (1, 0, 0), (0, 1, 0), 5.5)         # looking at the belly: the limb's width, notched
    shoot("tip_%s_back" % nm, c, (-1, 0, 0.0001), (0, 1, 0), 5.5)    # from the back: the cord over the limb
# 2. the grip with the arrow where it rests
ZR = 1.99 + 0.3                                                    # vanilla's riser half-width at Bow_MidBone + the arrow
rods = []
for sg in (1, -1):
    bpy.ops.mesh.primitive_cylinder_add(radius=0.3, depth=26, location=(-5.0, mid.y, sg * ZR), rotation=(0, math.radians(90), 0))
    r = bpy.context.active_object; r.data.materials.append(emit("arrow", (0.9, 0.05, 0.05), 2.0)); rods.append(r)
gc = Vector((-1.0, 0.0, 0.0))
shoot("grip_side", gc, (0, 0, -1), (0, 1, 0), 22, 900, 1100)        # from the +z side: the arrow passes beside
shoot("grip_front", gc + Vector((0, 2.5, 0)), (1, 0, 0), (0, 1, 0), 12, 900, 1100)   # from the string: arrow rods end-on
shoot("grip_top", Vector((-4, mid.y, 0)), (0, -1, 0.0001), (1, 0, 0), 22, 1100, 700)  # from above, along the bow
for r in rods: bpy.data.objects.remove(r)
# 3. backlit: a bright panel behind the riser, the suns off, a dim front fill only
three_suns(False); bg.inputs["Color"].default_value = (0.02, 0.02, 0.02, 1)
for view, look in (("side", (0, 0, -1)), ("front", (1, 0, 0)), ("tq", (0.6, 0, -0.8))):
    L = Vector(look).normalized()
    bpy.ops.mesh.primitive_plane_add(size=80, location=tuple(Vector((0, 0, 0)) + L * 40))
    pl = bpy.context.active_object; pl.rotation_mode = "QUATERNION"; pl.rotation_quaternion = (-L).to_track_quat("Z", "Y")
    pl.data.materials.append(emit("panel", (1, 1, 1), 6.0))
    fl = bpy.data.lights.new("front", "SUN"); fl.energy = 0.6; fo = bpy.data.objects.new("front", fl); sc.collection.objects.link(fo)
    fo.rotation_mode = "QUATERNION"; fo.rotation_quaternion = L.to_track_quat("-Z", "Y")
    shoot("backlit_%s" % view, Vector((0.5, 0, 0)), look, (0, 1, 0), 20, 900, 1100)
    bpy.data.objects.remove(pl); bpy.data.objects.remove(fo)
print("BOW PROOF DONE")
