# Changelog - Nordic Ebony Armor and Weapons Replacer

## 1.0.0

First release.

* NordwarUA's wolf ebony armour and weapons from Legacy of Ysgramor, replacing the game's ebony gear.
* A light plugin - a `.esp` with the light flag, an ESPFE - overriding the four vanilla ebony armour
  ADDON records so the worn armour points at this mod's own meshes and is settled by load order.
  Four records, not the 430 that reference those meshes, because every pre-enchanted variant reaches
  its worn model through the shared addon. Ground models and the weapons keep their vanilla paths.
* Xtudo's all-black colourway throughout - Ebony Black for the plate, cloth and weapons, Full
  Collar Black for the fur - at a choice of 1K, 2K or 4K in the installer.
* A choice of the fur-collared cuirass or NordwarUA's collarless one.
* **Fixed before release: the helmet hid the head** (the owner, 2026-09-16: *"ebony armor helmet
  caused invisible head"*). Vanilla's ebony helmet is a closed helm whose addon sits in slot 30
  (Head) - the head is hidden and the vanilla mesh covers it. NordwarUA's wolf ebony helm is open,
  and its own mod gives the addon slots 31/41/43 (hair, long hair, ears). The addon record kept
  vanilla's slot word, so the head vanished under an open helm. `EbonyHelmetAA` now carries Legacy
  of Ysgramor's slot word (0x2802), declared in the build script as a slot override and checked by
  the verifier, which otherwise still refuses any difference beyond a model path.
* An optional light plugin that hides the ebony mace, warhammer, bow and arrows, which have no
  wolf counterpart and would otherwise be the only vanilla-looking pieces left in the set.
* The texture list is derived by reading the shipped meshes, not written by hand, which is how the
  ebony war axe's use of the STEEL axe diffuse was caught.
