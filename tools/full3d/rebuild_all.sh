#!/bin/bash
# EXPERIMENTAL Nordic Ebony 3D: full rebuild -> post-fix -> shield splice -> install to the MO2 folder -> stats -> renders
set -e
cd "$(dirname "$0")/.."
BL="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"; W="$(cygpath -w "$PWD")"
for C in helmet body shield; do
  "$BL" -b --factory-startup --python-exit-code 1 --python tools/build3d.py -- "$W/build/cfg_$C.json" > build/$C.log 2>&1 || { echo "BUILD $C FAILED"; exit 1; }
  grep -E "PIECE" build/$C.log
done
py -3 tools/postfix.py build/out/meshes/NordicEbony/m/*.nif > build/postfix.log
py -3 tools/postfix.py --splice pkg_snapshot/meshes/weapons/ebony/ebonyshield.nif build/added_shield.nif build/out/meshes/weapons/ebony/ebonyshield.nif >> build/postfix.log
grep -c "NOT TRUEPBR" build/postfix.log || true
powershell -NoProfile -Command '$B="'"$W"'\build\out"; $M="D:\modlists\Njordlinger\mods\EXPERIMENTAL Nordic Ebony 3D"; New-Item -ItemType Directory -Force "$M\meshes\NordicEbony\m","$M\meshes\armor\ebony\m","$M\meshes\weapons\ebony","$M\textures\pbr\NordicEbony" | Out-Null; Copy-Item "$B\meshes\NordicEbony\m\*.nif" "$M\meshes\NordicEbony\m\" -Force; Copy-Item "$B\meshes\NordicEbony\m\*.nif" "$M\meshes\armor\ebony\m\" -Force; Copy-Item "$B\meshes\weapons\ebony\ebonyshield.nif" "$M\meshes\weapons\ebony\" -Force; Copy-Item "$B\textures\pbr\NordicEbony\*.dds" "$M\textures\pbr\NordicEbony\" -Force; "installed"'
"$BL" -b --factory-startup --python tools/stats3d_bl.py -- "$W" 2>&1 | grep STAT
py -3 tools/job_full3d.py root
bash tools/run_full3d.sh
py -3 tools/sheet_full3d.py
