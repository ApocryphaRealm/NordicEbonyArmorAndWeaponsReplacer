#!/bin/bash
# builds the two render jobs (helmet, cuirass) x (current | option 1 | option 1+2) x (close, far) and renders them
set -e
cd "$(dirname "$0")/.."
BL="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
py -3 - <<'PY'
import sys; sys.path.insert(0, "tools"); import mkjob
H = [mkjob.model(t, "helmet") for t in ("hcur", "h1", "h2")]
C = [mkjob.model(t, "cuirass") for t in ("ccur", "c1", "c2")]
mkjob.job("helmet", H, [dict(name="close", yaw=135, pitch=8, W=1300, H=1300), dict(name="far", yaw=135, pitch=8, W=170, H=170)], samples=64, bump_distance=0.22)
mkjob.job("cuirass", C, [dict(name="close", yaw=25, pitch=5, W=1150, H=1610), dict(name="far", yaw=25, pitch=5, W=400, H=560)], samples=64, bump_distance=0.22)
PY
for J in helmet cuirass; do py -3 -I tools/render_chain.py prep render/$J.json > /dev/null; done
py -3 - <<'PY'
import shutil, os
for job, at, tags in (("helmet", "helm", ("h1", "h2")), ("cuirass", "torso", ("c1", "c2"))):
    for tag, opt in zip(tags, ("opt1", "opt2")):
        d = "render/%s/tex/%s/textures/pbr/NordicEbony" % (job, tag)
        for f in os.listdir("out/%s/%s" % (at, opt)):
            if not f.endswith("_n.png"): shutil.copy2("out/%s/%s/%s" % (at, opt, f), os.path.join(d, f)); print("put", tag, f)
PY
for J in helmet cuirass; do "$BL" -b --factory-startup --python-exit-code 1 --python tools/render_chain.py -- render/$J.json > render/$J.log 2>&1; echo "$J done"; done
grep -h "PARALLAX-AS-BUMP\|Error\|MISSING" render/*.log | sort | uniq -c
