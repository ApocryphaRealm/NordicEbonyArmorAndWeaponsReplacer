# Changelog - Nordic Ebony Armor and Weapons Replacer

## 1.1.0 - 2026-11-14 - untested

### Added
- Installer pictures for every option that installs a model, and a header showing the whole set (tools/installer-images.py renders them from the built package).
- First-person models for the Wolf sword, greatsword, war axe, battleaxe and dagger. The vanilla first-person records point at 1stpersonebony*.nif, which 1.0.0 did not ship, so in first person those five showed the vanilla ebony art. The new mace and warhammer ship first-person files too; the bow's first-person record uses the same file as third person.
- The four ebony weapons Legacy of Ysgramor has no Wolf version of - the mace, the warhammer, the bow and the arrows, with the quiver and its six quiver arrows and the arrow in flight - now replace the vanilla ebony ones, so the whole ebony set matches. Every piece is cut from NordwarUA's own Wolf ebony weapons and keeps its own UVs on the set's Xtudo-black atlases; there is no new texture. The mace is the war axe's haft and grip with six knotwork flanges and a spiked crown; the warhammer is the battle axe with a round paw-cap hammer, a gold lip and a gnarled striking face; the bow is the sword's blades bent into recurved limbs with fang spurs; the arrows carry the war axe's spike, fangs as vanes and a paw nock; the quiver is the dagger's scabbard with a gold collar and fang plate. Built by tools/build-missing-weapons.py from the Legacy of Ysgramor download and the game's own meshes at build time - the repository carries no art.

### Changed
- The bow is fitted to the vanilla bow rig: its string ends sit on the two string bones the draw animation turns (the bow 4 to 5 percent shorter, the limb tips 3.2 units further back than the design sheet), every shape skinned with vanilla bone weights, the string on Bow_StringBone1 and 2.
- Textures are 2K only (the owner, 2026-11-14): the 1K and 4K choices are gone and Xtudo's 2K textures install with the core; the build refuses any texture over 2048.
- The arrows' shaft uses the war axe's wrapped grip (the same leather wrap as the approved design's battle-axe haft): the game hides the quiver arrows one by one by shape name, so each quiver arrow has to be one shape on one atlas.

### Removed
- The optional Hide Unmatched Weapons plugin and its installer page: the mace, warhammer, bow and arrows now match, so its 113 levelled-list and 7 recipe overrides are gone and those lists and recipes are vanilla again. It was never posted.
- The vanilla ebony mace's belt hook (Scb) is not carried over - no Wolf piece forms a hook; the mace hangs at the hip like the war axe.

### Known
- Untested in game: the quiver on the back (which side faces out), the bow draw and the six quiver arrows disappearing as arrows are used.

### Fixed
- Build check (tools/missing_weapons/verify.py): the bow and arrow now fail the build if light can pass through them, if the riser has a gap, if the riser is wider than vanilla's where the arrow rests, or if a string end has no nock.
- Bow: the string met the bare metal at the tips. Each limb tip now has a notch cut into both edges, with a loop of the same wrapped cord through the notches, and the string ends in it on the vanilla string-bone pivot; the tips stand 2.6 units past the string as vanilla's do, so the bow is no longer shortened to fit the rig.
- Bow: the upper guard's arms stood where the arrow rests. The upper guard, the top of the grip and the base of the upper limb are drawn in to the vanilla bow's riser width, an arrow shelf on both sides; the lower guard keeps its arms.
- Bow: light shone through the handle in game. The grip ended short of its guard bands and the limbs started above them, and the spurs and limb bases were open shells; the grip and limbs now meet inside each guard band and every opening is closed. The arrow's head and vanes were open the same way and are closed (the arrows look the same from outside).
- Quiver: turned 180 degrees about its long axis so the decorated side faces out and the steel ring (still pointing up) sits against the wearer's back. The six quiver arrows turn with it. Arrows: the pommel-shaped end is now a slotted black-steel nock with a gold collar, the slot across the arrow square to the cock vane, and the vanes moved back to meet the nock.
- Warhammer: the toothed striking face drew in game as a flat tan disc with a diagonal smear. Its texture window held a ridge in the normal map, and the teeth shared vertices so their lighting averaged flat. The face now uses flat-normal blade steel and every tooth facet has its own vertices. A build check now fails any shape with a hard edge smoothed over.
- The warhammer's round extension, gold lip and toothed striking face drew black and flat in game: their UVs were lost when the head's pieces were joined into one shape (the new pieces' UV layer had another name), so they sampled one corner texel with no tangent frame. Every piece now carries one UV layer under one name before the join, and the build fails if a shape has faces with no UV area or a broken tangent frame.

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
