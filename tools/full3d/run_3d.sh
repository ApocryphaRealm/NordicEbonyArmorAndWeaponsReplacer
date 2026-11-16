#!/bin/bash
set -e
cd "$(dirname "$0")/.."
BL="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
py -3 tools/patch3d.py
py -3 tools/backing.py helm
py -3 tools/backing.py torso
py -3 tools/job3d.py jobs
for J in h3d c3d; do py -3 -I tools/render_chain.py prep render/$J.json > /dev/null; done
py -3 tools/job3d.py put
for J in ${JOBS:-h3d c3d}; do "$BL" -b --factory-startup --python-exit-code 1 --python tools/render_chain.py -- render/$J.json > render/$J.log 2>&1 || echo "$J FAILED"; echo "$J done"; done
grep -h "RINGS3D\|aventail triangles\|Error\|Traceback" render/h3d.log render/c3d.log || true
