import os
T = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(T, "backing.py"); s = open(p).read()
if "AT = sys.argv" not in s:
    s = s.replace('S = os.path.join(H, "src_png"); O = os.path.join(H, "out", "helm", "opt3"); os.makedirs(O, exist_ok=True)',
                  'import sys\nAT = sys.argv[1] if len(sys.argv) > 1 else "helm"\nS = os.path.join(H, "src_png"); O = os.path.join(H, "out", AT, "opt3"); os.makedirs(O, exist_ok=True)')
    s = s.replace('"helm_mail.png"', 'AT + "_mail.png"').replace('"helmebony.png"', 'AT + "ebony.png"').replace('"helmebony_rmaos.png"', 'AT + "ebony_rmaos.png"').replace('"helm_n.png"', 'AT + "_n.png"')
    s = s.replace('(("helmebony", a), ("helmebony_rmaos", r), ("helm_n", n))', '((AT + "ebony", a), (AT + "ebony_rmaos", r), (AT + "_n", n))')
    open(p, "w").write(s)
p = os.path.join(T, "render_chain.py"); s = open(p).read()
old = '    print("MODEL", model["tag"], [(o.name, o.data.materials[0].name) for o in objs]); return objs'
new = '''    if model.get("rings3d"):
        # 2026-11-15 chainmail 3D demo: modelled 4-in-1 rings over the UV-mapped mail region (tools/rings3d.py)
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import rings3d
        bpy.context.view_layer.update(); objs.append(rings3d.make(objs, model["rings3d"]))
''' + old
if "rings3d" not in s:
    assert old in s; s = s.replace(old, new); open(p, "w").write(s)
print("patched")
