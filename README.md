# Truly Nordic Ebony Armor and Weapons

NordwarUA's wolf ebony armour and weapons from **Legacy of Ysgramor**, all black - his own textures recoloured - in
**TruePBR**, replacing the game's ebony armour and weapons. That covers the whole set: the armour, the sword,
greatsword, war axe, battleaxe, dagger and shield, plus a matching **mace, warhammer, bow, arrows and quiver**
assembled from pieces of NordwarUA's own Wolf weapons, because Legacy of Ysgramor has none of those. (Named Nordic
Ebony Armor and Weapons Replacer while in development.)

## Two downloads

* **Main file - full 3D.** The chain mail is modelled ring by ring, each ring linked four-in-one to its neighbours
  (about 3,200 rings on the helmet, 7,500 on the cuirass). The rivets, studs, buckles, straps and lamellar scales are
  raised geometry on the helmet, cuirass, gauntlets, boots, shield and weapons. Measured in one launch, ten NPCs in the
  3D set cost about 0.8-1.1 ms of GPU time more than the same ten in the flat set, and in that CPU-bound scene the
  frame time stayed within noise. First-person mail has no measurable cost.
* **Optional file - flat.** The same armour with the mail as a chain-link TruePBR material, for big battles or older
  PCs.

Both are FOMOD installers with the same choices:

* **Plugin:** the ESP version (recommended) - a light plugin (ESL-flagged, `Truly Nordic Ebony Armor and Weapons.esp`)
  that points vanilla's four ebony armour addon records at this mod's meshes - or **No ESP - SkyPatcher**, which needs
  [SkyPatcher](https://www.nexusmods.com/skyrimspecialedition/mods/106659) and puts the meshes on vanilla's own paths.
* The fur-collared or collarless cuirass.
* **Body:** vanilla, or our own **CBBE 3BA** (female) and **HIMBO** (male) fits, made by running BodySlide ourselves.
  Each fit has prebuilt meshes plus the BodySlide project for your own preset. The body fits go with the ESP version.
* **Compatibility patches (requires SkyPatcher):** Ryn's Snazzy Last Vigil's Ebony Warrior set and the Ebony Mail,
  in this look.

## Requirements

* Community Shaders with TruePBR support. The materials are TruePBR only, so without it the set does not draw right.
  Its Dynamic Cubemaps feature is recommended, for the metal's reflections.
* SkyPatcher, only for the No ESP option and the compatibility patches.

## Credits

* **NordwarUA** - [Legacy of Ysgramor](https://www.nexusmods.com/skyrimspecialedition/mods/109963): every mesh,
  every texture the materials are recoloured and made from, and every piece the new mace, warhammer, bow, arrows and
  quiver are made from. Used and modified under its permissions (modification and asset use with credit; Nexus only;
  never sold).
* **Xonek** - [Legacy of Ysgramor - 3BA Bodyslide](https://www.nexusmods.com/skyrimspecialedition/mods/111209): the
  CBBE 3BA fit starts from his sets, under the same terms as Legacy of Ysgramor.
* CBBE 3BA and HIMBO, whose own conversion references and sliders our fits are conformed to. See NOTICE.md.

Details and permissions: [NOTICE.md](NOTICE.md). Changes: [CHANGELOG.md](CHANGELOG.md).

## Building

The repository carries no game or Legacy of Ysgramor art. The build reads it from your own files.

* Python 3 with `numpy`, `scipy`, `lz4` and `Pillow`; 7-Zip; texconv (`TEXCONV`); Blender with the PyNifly add-on
  (`BLENDER`); BodySlide (for the body fits); Git Bash (for the 3D build).
* The Nexus downloads named in `tools/build-fomod.py` in one folder: `EWA_DOWNLOADS`, or the `download_directory` of
  the MO2 instance named by `EWA_MO2`.
* Skyrim Special Edition's `Data` folder (`SKYRIM_DATA`, or the MO2 instance's game path) for the vanilla ebony meshes
  the new weapons are built on.

Then run `python tools/build-arma-esl.py` for the plugin, and `python tools/build-fomod.py [--rebuild-3d]` for both
installers. The second one builds `Flat\` from the downloads and then `3D\` from it (`tools/package3d.py`). The full-3D
build itself is `tools/full3d/`; its work folder is `FULL3D_WORK`, outside git.
