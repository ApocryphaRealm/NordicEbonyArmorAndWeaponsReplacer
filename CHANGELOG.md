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
* An optional light plugin, `Nordic Ebony - Hide Unmatched Weapons.esp`, that takes the ebony
  mace, warhammer, bow and arrow - which have no wolf counterpart and would otherwise be the only
  vanilla-looking pieces left in the set - out of the game's levelled lists and crafting. 113
  levelled lists overridden (45 of them emptied outright, and dropped from the lists above them),
  7 recipes gated behind a condition that is never true; every enchanted variant is caught because
  the targets are found by model path. Nothing is deleted or made non-playable, so a weapon
  already in a save keeps working. (Promised in the first draft of this changelog, but not built
  until 2026-09-17 - the owner asked to "confirm that the missing ebony weapons are deactivated",
  and they were not.)
* The texture list is derived by reading the shipped meshes, not written by hand, which is how the
  ebony war axe's use of the STEEL axe diffuse was caught.
* **HIMBO and CBBE 3BA options in the installer.** Prebuilt HIMBO male meshes (zeroed sliders,
  collared and collarless cuirass) and HIMBO BodySlide files from Trexasle's Legacy of Ysgramor -
  HIMBO Conversion (Nexus 110002), and CBBE 3BA BodySlide files from Xonek's Legacy of Ysgramor -
  3BA Bodyslide (Nexus 111209), the Ebony variants, renamed to this mod's mesh names by
  `tools/loy-refits.py`. The 3BA set is BodySlide-only: build it once.
