# blender -b --factory-startup --python roundtrip_test.py -- <in.nif> <out.nif>
import bpy, sys, addon_utils
addon_utils.enable("io_scene_nifly", default_set=True)
from io_scene_nifly.pyn.pynifly import NifFile
a = sys.argv[sys.argv.index("--") + 1:]
src, dst = a[0], a[1]
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
bpy.ops.import_scene.pynifly(filepath=src, import_collisions=False)
for o in bpy.data.objects: o.select_set(True)
bpy.context.view_layer.objects.active = [o for o in bpy.data.objects if o.type == "MESH"][0]
r = bpy.ops.export_scene.pynifly(filepath=dst, target_game="SKYRIMSE")
print("EXPORT", r)
def info(p):
    nf = NifFile(p); out = []
    for s in nf.shapes:
        sh = s.shader
        try: tx = dict(s.shader.textures)
        except Exception: tx = {}
        part = None
        try: part = [pp.id for pp in s.partitions]
        except Exception: pass
        out.append((s.name, len(s.verts), len(s.tris), s.blockname, getattr(sh.properties, "Shader_Flags_1", None), getattr(sh.properties, "Shader_Flags_2", None), part, len(s.bone_names), sorted(tx.items())))
    return out
for p in (src, dst):
    print("FILE", p)
    for x in info(p): print("  ", x)
