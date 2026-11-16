#!/usr/bin/env python3
r"""Render the installer pictures from a BUILT package (gate fomod-model-options-have-a-picture: every option that
installs a model shows that model). Each picture is a render of exactly the meshes its option installs, with the
package's own TruePBR textures (tools/render_lib.py: game-like lighting, the gradient world standing in for Community
Shaders' cube-map reflections); the header lines up the whole set.

Usage:  python tools/installer-images.py "<package folder>"   (the FLAT package: <version folder>\Flat)      -> fomod/images/*.png in the repository
Needs Blender with PyNifly (BLENDER, or on PATH, or under Program Files) and Pillow.
"""
import os, sys, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import render_lib  # noqa: E402
IMG = os.path.join(REPO, "fomod", "images")
PREFIXES = ("textures\\pbr\\nordicebony\\",)

# picture -> (meshes relative to the package, a camera yaw)
SHOTS = {
    "fur": (["00 Core/meshes/armor/ebony/m/cuirass_1.nif"], 20),
    "nofur": (["10 Cuirass - No fur collar/meshes/armor/ebony/m/cuirass_1.nif"], 20),
    # every body option shows the set on that body (2026-11-16: every body option a picture): the vanilla sets from the
    # core, CBBE 3BA and HIMBO from the meshes BodySlide prebuilt for those options (the 3BA ShapeData NIFs do not open
    # in PyNifly; the prebuilt game meshes do)
    "vanilla_f": (["00 Core/meshes/NordicEbony/f/%s_1.nif" % p for p in ("cuirass", "boots", "gauntlets")], 20),
    "vanilla_m": (["00 Core/meshes/NordicEbony/m/%s_1.nif" % p for p in ("cuirass", "boots", "gauntlets")], 20),
    "cbbe3ba": (["32 CBBE 3BA meshes/meshes/NordicEbony/f/%s_1.nif" % p for p in ("cuirass", "boots", "gauntlets")], 20),
    "himbo": (["36 HIMBO meshes/meshes/NordicEbony/m/%s_1.nif" % p for p in ("cuirass", "boots", "gauntlets")], 20),
    "w_mace": (["00 Core/meshes/weapons/ebony/ebonymace.nif"], 0), "w_warhammer": (["00 Core/meshes/weapons/ebony/ebonywarhammer.nif"], 0),
    "w_bow": (["00 Core/meshes/weapons/ebony/ebonybowskinned.nif"], 0), "w_quiver": (["00 Core/meshes/weapons/ebony/ebonyarrow.nif"], 0),
    "w_sword": (["00 Core/meshes/weapons/ebony/ebonysword.nif"], 0), "w_greatsword": (["00 Core/meshes/weapons/ebony/ebonygreatsword.nif"], 0),
    "w_waraxe": (["00 Core/meshes/weapons/ebony/ebonywaraxe.nif"], 0), "w_battleaxe": (["00 Core/meshes/weapons/ebony/ebonybattleaxe.nif"], 0),
    "w_dagger": (["00 Core/meshes/weapons/ebony/ebonydagger.nif"], 0), "w_shield": (["00 Core/meshes/weapons/ebony/ebonyshield.nif"], 0),
}


def main(pkg, tex_pkg=None):
    from PIL import Image, ImageDraw
    import tempfile
    work = tempfile.mkdtemp(prefix="installer-images-")     # never inside the package (2026-11-16)
    shots = {k: ([os.path.join(pkg, p) for p in ps], yaw) for k, (ps, yaw) in SHOTS.items()}
    # textures: the package's own core, or (second argument) another built package's core with the same textures
    tex = [os.path.join(tex_pkg or pkg, "00 Core")]
    render_lib.render(shots, tex, work, PREFIXES)
    os.makedirs(IMG, exist_ok=True)
    bg = (38, 39, 42)
    for name in ("fur", "nofur", "vanilla_f", "vanilla_m", "cbbe3ba", "himbo"):
        render_lib.card(os.path.join(work, name + ".png"), (800, 1000)).save(os.path.join(IMG, name + ".png"))
    # header: the armour and the twelve pieces in a row
    order = ["fur", "w_sword", "w_greatsword", "w_waraxe", "w_battleaxe", "w_dagger", "w_shield", "w_mace", "w_warhammer", "w_bow", "w_quiver"]
    H = 520; head = Image.new("RGB", (1800, H + 60), bg); x = 10
    widths = {k: (260 if k == "fur" else 230 if k in ("w_shield", "w_quiver") else 140) for k in order}
    scale = (1780 - 10 * (len(order) - 1)) / sum(widths.values())
    for k in order:
        w = int(widths[k] * scale); head.paste(render_lib.card(os.path.join(work, k + ".png"), (w, H)), (x, 10)); x += w + 10
    d = ImageDraw.Draw(head)
    d.text((14, H + 22), "Truly Nordic Ebony Armor and Weapons - NordwarUA's Wolf ebony set, all black, in TruePBR - the full set", fill=(225, 205, 150))
    head.save(os.path.join(IMG, "header.png"))
    shutil.rmtree(work, ignore_errors=True)
    print("installer images written to", IMG)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
