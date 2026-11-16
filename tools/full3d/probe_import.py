import bpy, sys, addon_utils
addon_utils.enable("io_scene_nifly", default_set=True)
src = sys.argv[sys.argv.index("--") + 1]
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
bpy.ops.import_scene.pynifly(filepath=src, import_collisions=False)
for o in bpy.data.objects:
    print("OBJ", o.name, o.type, "parent", o.parent.name if o.parent else None, "mods", [(m.type, getattr(m, "object", None) and m.object.name) for m in getattr(o, "modifiers", [])])
    if o.type == "MESH":
        print("  vgroups", [g.name for g in o.vertex_groups][:60])
        print("  mats", [m.name for m in o.data.materials], "props", {k: (str(o[k])[:60]) for k in o.keys()})
        for m in o.data.materials:
            print("  matprops", {k: str(m[k])[:80] for k in m.keys()})
            print("  nodes", [(n.type, n.name, getattr(getattr(n, "image", None), "filepath", None)) for n in m.node_tree.nodes][:20])
        print("  attrs", [a.name for a in o.data.attributes], "uv", [u.name for u in o.data.uv_layers], "verts", len(o.data.vertices))
