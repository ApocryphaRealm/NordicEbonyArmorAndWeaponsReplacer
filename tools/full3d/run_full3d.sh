#!/bin/bash
# per-piece side-by-side renders: shipped option 1 (o1) | experimental full 3D + parallax (x3)
cd "$(dirname "$0")/.."
BL="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
declare -A V R
V[helmet]='{"yaw":135,"pitch":8,"W":1200,"H":1200}'
V[cuirass]='{"yaw":25,"pitch":5,"W":1100,"H":1540}'
V[gauntlets]='{"yaw":90,"pitch":8,"W":1000,"H":1000}'
V[boots]='{"yaw":160,"pitch":8,"W":1000,"H":1000}'
V[shield]='{"yaw":180,"pitch":0,"W":1100,"H":1100}'
R[shield]='[0,0,0]'
for P in ${PIECES:-helmet cuirass gauntlets boots shield}; do
  py -3 tools/job_full3d.py $P "${V[$P]}" ${R[$P]} > /dev/null
  py -3 -I tools/render_chain.py prep render/f3d_$P.json > /dev/null
  for at in helm torso; do
    d="render/f3d_$P/tex/o1/textures/pbr/NordicEbony"
    if [ -f "$d/${at}ebony.png" ]; then cp out/$at/opt1/${at}ebony.png out/$at/opt1/${at}ebony_rmaos.png "$d/"; fi
  done
  "$BL" -b --factory-startup --python-exit-code 1 --python tools/render_chain.py -- render/f3d_$P.json > render/f3d_$P.log 2>&1 || echo "$P FAILED"
  echo "$P rendered"
done
