# Nordic Ebony Armor and Weapons Replacer

NordwarUA's wolf ebony armour and weapons from **Legacy of Ysgramor**, in Xtudo's all-black colourway,
replacing the game's ebony armour and weapons - the whole set: the armour, the sword, greatsword, war axe,
battleaxe, dagger and shield, and (since 1.1.0) a matching **mace, warhammer, bow, arrows and quiver**
assembled from pieces of NordwarUA's own Wolf weapons, since Legacy of Ysgramor has none of those.

* **Textures: 2K only**, installed with the core.
* A light plugin (ESPFE) overrides the four vanilla ebony armour addon records; the weapons are loose meshes
  at the vanilla paths, with first-person models.
* Installer choices: the fur-collared or collarless cuirass; HIMBO meshes and BodySlide files; CBBE 3BA
  BodySlide files.

## Credits

* **NordwarUA** - [Legacy of Ysgramor](https://www.nexusmods.com/skyrimspecialedition/mods/109963): every
  mesh, normal and mask, and every piece the new mace, warhammer, bow, arrows and quiver are made from.
  Used and modified under its permissions (modification and asset use with credit; Nexus only; never sold).
* **Xtudo** - [Legacy of Ysgramor - my patches and fixes](https://www.nexusmods.com/skyrimspecialedition/mods/111121):
  the Ebony Black, Wolf Black (one file) and Full Collar Black textures.
* **Trexasle** - [Legacy of Ysgramor - HIMBO Conversion](https://www.nexusmods.com/skyrimspecialedition/mods/110002).
* **Xonek** - [Legacy of Ysgramor - 3BA Bodyslide](https://www.nexusmods.com/skyrimspecialedition/mods/111209).

Details and permissions: [NOTICE.md](NOTICE.md). Changes: [CHANGELOG.md](CHANGELOG.md).

## Building

The repository carries no game or Legacy of Ysgramor art; the build reads it from your own files.

* Python 3 with `numpy`, `scipy`, `lz4` and `Pillow`; 7-Zip; Blender 4.2+ with the PyNifly add-on
  (`BLENDER` names blender.exe if it is not on PATH).
* The Nexus downloads named in `tools/build-fomod.py` (Legacy of Ysgramor main file and Fur Lighting Bug
  patch; Xtudo's Ebony Black 2K, Wolf Black 2K and Full Collar Black; the HIMBO and 3BA refits) in one
  folder - `EWA_DOWNLOADS`, or the `download_directory` of the MO2 instance named by `EWA_MO2`.
* Skyrim Special Edition's `Data` folder (`SKYRIM_DATA`, or the MO2 instance's game path) for the vanilla
  ebony meshes the new weapons are built on.

Then `python tools/build-arma-esl.py` (the plugin) and `python tools/build-fomod.py` (the installer, which
runs `tools/build-missing-weapons.py`).
