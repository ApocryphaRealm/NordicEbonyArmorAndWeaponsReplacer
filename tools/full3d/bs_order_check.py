# blender -b --factory-startup --python bs_order_check.py -- <nif> : the imported Blender mesh keeps the NIF's vertex order
# (the BodySlide slider data of the added shapes is indexed by the source shape's NIF vertex index through the anchors)
import bpy, sys, addon_utils, numpy as np
addon_utils.enable("io_scene_nifly", default_set=True)
from io_scene_nifly.pyn.pynifly import NifFile
p = sys.argv[sys.argv.index("--") + 1]
nf = NifFile(p); bpy.ops.import_scene.pynifly(filepath=p, import_collisions=False)
for s in nf.shapes:
    o = next((o for o in bpy.data.objects if o.type == "MESH" and o.get("pynNodeName", o.name) == s.name), None)
    if o is None: print("ORDER", s.name, "no object"); continue
    a = np.array(s.verts); b = np.array([tuple(v.co) for v in o.data.vertices])
    print("ORDER", s.name, len(a), len(b), "max diff %.6f" % (np.abs(a - b).max() if a.shape == b.shape else -1))
