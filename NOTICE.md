# Whose work this is

**None of the art is ours.** This mod is a mapping job: it takes an existing armour set and puts it
where the game looks for its ebony gear.

## The armour and weapons - Legacy of Ysgramor

[Nexus 109963](https://www.nexusmods.com/skyrimspecialedition/mods/109963), by **NordwarUA**. Every
mesh, and every normal and mask texture, comes from its main archive and its Fur Lighting Bug patch.

## The black colourway - Legacy of Ysgramor, my patches and fixes

[Nexus 111121](https://www.nexusmods.com/skyrimspecialedition/mods/111121), by **Xtudo**. The
diffuse textures come from his Ebony Black download (1K, 2K and 4K) and his Full Collar Black.

One file comes from his **Wolf Black** download instead: `Axe1H.dds`. The wolf ebony war axe's haft
uses the steel axe's diffuse, so without that file an "all black" ebony set has one brown handle in
it. This was found by reading the mesh, not by reasoning about which files belong to which set.

**The repository carries none of these files.** `tools/build-fomod.py` opens the Nexus downloads at
build time. It also derives the texture list from the meshes it is shipping rather than from a
hand-written list, so a texture the art needs cannot be silently left out.

**Permissions.** Per the owner's standing policy for our asset mods, set 2026-09-16, the mod page
names both authors and links back to both mod pages.

## The body refits - HIMBO and CBBE 3BA options

[Nexus 110002](https://www.nexusmods.com/skyrimspecialedition/mods/110002), **Legacy of Ysgramor - HIMBO
Conversion** by **Trexasle**: the prebuilt HIMBO male meshes and the HIMBO BodySlide slider sets and
shape data. [Nexus 111209](https://www.nexusmods.com/skyrimspecialedition/mods/111209), **Legacy of
Ysgramor - 3BA Bodyslide** by **Xonek**: the CBBE 3BA slider sets and shape data. Both are installed
as optional choices, renamed and repathed to this mod's folders by `tools/loy-refits.py`; the mod page
names both authors and links back to both pages.

## What IS ours

`tools/`, `fomod/ModuleConfig.xml`, the optional plugin's generator, and the documentation.
GPL-3.0-or-later, Copyright (C) 2026 ApocryphaRealm.

---

## The four weapons that cannot be replaced

NordwarUA's wolf ebony line has a sword, greatsword, war axe, battleaxe, dagger and shield. Vanilla
ebony also has a **mace, a warhammer, a bow and arrows**, and there is no wolf version of any of
them on either mod page.

A mesh replacer cannot invent them, so they keep the game's own look. The installer offers an
optional light plugin that takes those four out of circulation instead - removed from the 26
levelled lists they appear in, and their forging and tempering recipes deleted - so a playthrough
never hands the player the one piece that does not match.

That plugin edits vanilla levelled lists, which is the one part of this mod with a real conflict
surface. It is optional for that reason, and the page says to load it after levelled-list overhauls.

## What is deliberately NOT replaced

Ebony Mail, the Ebony Blade and the ebony dragon priest masks are distinct artifacts with their own
meshes. They are left alone.

## The interaction with Legacy of Ysgramor itself

The textures here sit at NordwarUA's own `textures\NordWar\Companions\` paths, because that is what
his meshes reference. If Legacy of Ysgramor is also installed, whichever of the two loads later
decides the colour of BOTH sets. For someone who wanted the black colourway that is the point; it is
still worth knowing before wondering why the Companions changed colour.
