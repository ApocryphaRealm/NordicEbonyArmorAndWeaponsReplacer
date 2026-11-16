# blender -b --factory-startup --python inspect_nif.py -- <nif> [<nif> ...]   (pynifly read-back)
import bpy, sys, addon_utils
addon_utils.enable("io_scene_nifly", default_set=True)
from io_scene_nifly.pyn.pynifly import NifFile
for p in sys.argv[sys.argv.index("--") + 1:]:
    nf = NifFile(p); print("FILE", p, "shapes", len(nf.shapes))
    for s in nf.shapes:
        try: part = [pp.id for pp in s.partitions]
        except Exception: part = None
        try: tx = s.shader.textures.get("Diffuse", "")
        except Exception: tx = ""
        print("  SHAPE %-28s v=%6d t=%6d bones=%d skinned=%s part=%s f1=%s f2=%s diff=%s" % (s.name, len(s.verts), len(s.tris), len(s.bone_names),
              s.has_skin_instance if hasattr(s, "has_skin_instance") else "?", part, hex(s.shader.properties.Shader_Flags_1), hex(s.shader.properties.Shader_Flags_2), tx))
