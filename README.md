# Nordic Ebony Armor and Weapons Replacer

NordwarUA's wolf ebony armour and weapons from **Legacy of Ysgramor**, all black - his own textures recoloured - in
**TruePBR**, replacing the game's ebony armour and weapons - the whole set: the armour, the sword, greatsword, war axe,
battleaxe, dagger and shield, and (since 1.1.0) a matching **mace, warhammer, bow, arrows and quiver** assembled from
pieces of NordwarUA's own Wolf weapons, since Legacy of Ysgramor has none of those.

* **TruePBR materials** (Community Shaders): albedo, NordwarUA's normal maps, and RMAOS, at his 2K, under
  `textures\pbr\NordicEbony\`. Metal reflects its surroundings through Community Shaders' cube maps (its Dynamic
  Cubemaps feature is recommended).
* A light plugin (ESPFE) overrides the four vanilla ebony armour addon records; the weapons are loose meshes at the
  vanilla paths, with first-person models.
* Installer choices: the fur-collared or collarless cuirass; CBBE 3BA BodySlide files; and optional compatibility
  patches that need SkyPatcher (`skypatcher\`): Ryn's Snazzy Last Vigil's Ebony Warrior set (his Vitreous Ebony set
  is left alone) and the Ebony Mail, in this look.

## Requirements

* Community Shaders with TruePBR support (the materials are TruePBR only - without it the set does not draw right).
  Recommended: its Dynamic Cubemaps feature, for the metal's reflections.
* For HIMBO bodies: [Legacy of Ysgramor - HIMBO Conversion](https://www.nexusmods.com/skyrimspecialedition/mods/110002)
  by Trexasle is not included (its author's permission is needed to package it).

## Credits

* **NordwarUA** - [Legacy of Ysgramor](https://www.nexusmods.com/skyrimspecialedition/mods/109963): every mesh, and
  every texture the materials are recoloured and made from, and every piece the new mace, warhammer, bow, arrows and
  quiver are made from. Used and modified under its permissions (modification and asset use with credit; Nexus only;
  never sold).
* **Xonek** - [Legacy of Ysgramor - 3BA Bodyslide](https://www.nexusmods.com/skyrimspecialedition/mods/111209): the
  CBBE 3BA BodySlide files, under the same terms as Legacy of Ysgramor ("the same as in original mod").

Details and permissions: [NOTICE.md](NOTICE.md). Changes: [CHANGELOG.md](CHANGELOG.md).

## Building

The repository carries no game or Legacy of Ysgramor art; the build reads it from your own files.

* Python 3 with `numpy`, `scipy`, `lz4` and `Pillow`; 7-Zip; texconv (`TEXCONV` names texconv.exe); Blender 4.2+ with
  the PyNifly add-on (`BLENDER` names blender.exe if it is not on PATH).
* The Nexus downloads named in `tools/build-fomod.py` (Legacy of Ysgramor main file and Fur Lighting Bug patch) in one
  folder - `EWA_DOWNLOADS`, or the `download_directory` of the MO2 instance named by `EWA_MO2` - and the 3BA refit
  named in `tools/loy-refits.py`.
* Skyrim Special Edition's `Data` folder (`SKYRIM_DATA`, or the MO2 instance's game path) for the vanilla ebony meshes
  the new weapons are built on.

Then `python tools/build-arma-esl.py` (the plugin) and `python tools/build-fomod.py` (the installer, which runs
`tools/build-missing-weapons.py`, `tools/loy-refits.py`, and `tools/truepbr.py` with `tools/recolour_black.py`).
