#!/bin/bash
# Full-3D build of one armour set, end to end (no game): bash rebuild_set.sh <ebony|skyforged> [noinstall]
#   prep (snapshot + decode) -> chain-mail masks -> feature maps + recipes (armour + weapon atlases) -> mail backing ->
#   3D textures + _p maps -> Blender build of every piece -> TruePBR/parallax post + splices -> install to the MO2 folder
#   -> read-back stats. Renders: py -3 render_set.py all ; sheets: py -3 sheet_set.py
# In the repo (since 2026-11-16) the scripts sit in tools\full3d\ and run from there; FULL3D_PKG names the flat package
# the build starts from and FULL3D_WORK the work folder (see sets.py). tools\package3d.py runs this with "noinstall".
set -e
export NSET="$1"; cd "$(dirname "$0")"
WA=$(py -3 -c "import sets; print(' '.join(sets.get().weapon_atlases))")
py -3 prep.py
py -3 chainmail.py helm torso
py -3 features.py helm torso bgpb shield $WA | grep -v candidates
py -3 prep_feat.py helm torso bgpb shield $WA
py -3 backing.py helm; py -3 backing.py torso
py -3 make_tex.py $WA | grep -v "^dds"
py -3 full3d.py cfg
py -3 full3d.py build
py -3 full3d.py post
[ "$2" = "noinstall" ] || py -3 full3d.py install
py -3 full3d.py stats
