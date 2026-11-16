# Whose work this is

**The art is NordwarUA's.** This mod takes his Wolf ebony armour and weapons from Legacy of Ysgramor and puts them
where the game looks for its ebony gear. Since 1.1.0 it also carries **new meshes derived from that art** - the ebony
mace, warhammer, bow, arrows and quiver, which Legacy of Ysgramor does not have, assembled from pieces cut out of his
own Wolf ebony weapons, each piece keeping his UVs - and first-person copies of his Wolf weapons. Since 1.1.0 the
textures are **his own textures recoloured all-black and made into TruePBR materials** by our build scripts. All of it
is modification and asset use of Legacy of Ysgramor under its permissions (below): with credit to NordwarUA as the
original creator, on Nexus only, never sold.

## The armour and weapons - Legacy of Ysgramor

[Nexus 109963](https://www.nexusmods.com/skyrimspecialedition/mods/109963), by **NordwarUA**. Every mesh, and every
diffuse, normal and mask texture the materials are made from, comes from its main archive and its Fur Lighting Bug
patch (the corrected FurCollar_n) - and every piece of the derived mace, warhammer, bow, arrows and quiver is cut from
his Wolf ebony sword, war axe, battleaxe, dagger and shield.

## The textures - our black recolour of his originals, in TruePBR

`tools/recolour_black.py` turns NordwarUA's original diffuses all-black: the red and brown cloth, tabard, leather,
hafts and shield planks and the fur go black-grey, the steel and the ebony plate are left alone, and his gold
knotwork is kept. It is a hue- and saturation-masked recolour tuned by overall numbers only; no other author's texture
is read or shipped. `tools/truepbr.py` then makes each material a Community Shaders **TruePBR** material, the way our
Truly Nordic Carved Weapons Replacer does: an albedo (the recolour, its baked highlights taken out), **his own normal
map unchanged**, and an RMAOS map (roughness, metal, ambient occlusion, specular) worked out from his own environment
mask - metal where his mask says the surface shines, leather, cloth, wood and fur never metal. NordwarUA's own
damascus-look and wear detail stays in the textures as he painted it. The textures sit under `textures\pbr\NordicEbony\`,
so installing Legacy of Ysgramor beside this mod no longer changes the colour of either.

**The repository carries none of his files.** `tools/build-fomod.py` opens the Nexus downloads at build time,
derives the material list from the meshes it is shipping (never from a hand-written list), and
`tools/build-missing-weapons.py` builds the derived weapons on the game's own vanilla ebony meshes, read from the
player's `Skyrim - Meshes0/1.bsa` - so no Bethesda mesh is in the repository either.

## The CBBE 3BA BodySlide files - Legacy of Ysgramor - 3BA Bodyslide

[Nexus 111209](https://www.nexusmods.com/skyrimspecialedition/mods/111209), **Legacy of Ysgramor - 3BA Bodyslide** by
**Xonek**: the CBBE 3BA slider sets and shape data, installed as an optional choice, renamed and repathed to this mod's
folders by `tools/loy-refits.py`, their materials made TruePBR like the rest. Credited to Xonek and to NordwarUA.

## Our own body fits - CBBE 3BA and HIMBO (2026-11-16)

The installer's Body step offers, beside the vanilla bodies (the default), CBBE 3BA for women and HIMBO for men: meshes prebuilt by BodySlide (3BA "- Zeroed Sliders -", "HIMBO Default"), RaceMenu / OBody morphs, and the BodySlide projects for your own preset. The 3BA sets are Xonek's (above) with their slider data now shipped in our own files. The HIMBO fit is ours: NordwarUA's male meshes moved by HIMBO's own "Vanilla to HIMBO" conversion set and given every slider of HIMBO's "Refit: HIMBO Vanilla" reference (Outfit Studio's convert and conform, run by our tools). Credit: HIMBO by Kreiste and Novelyst (Gaztec, Trivutron); CBBE 3BA by Acro; BodySlide and Outfit Studio by ousnius and Caliente.

## Not included - the HIMBO conversion

[Nexus 110002](https://www.nexusmods.com/skyrimspecialedition/mods/110002), **Legacy of Ysgramor - HIMBO Conversion**
by **Trexasle**, asks for his permission before its assets are used, so it is not packaged here (it was an option
before 1.1.0 was posted). The mod page points HIMBO players at his page.

## What IS ours

`tools/` (including the recolour, the TruePBR conversion and the design and build scripts of the derived weapons),
`fomod/ModuleConfig.xml`, the plugin's generator, and the documentation. The derived meshes and the recoloured
textures themselves are NordwarUA's art modified and stay under his permissions, not under our licence.
GPL-3.0-or-later, Copyright (C) 2026 ApocryphaRealm.

---

## The four weapons Legacy of Ysgramor does not have

NordwarUA's wolf ebony line has a sword, greatsword, war axe, battleaxe, dagger and shield. Vanilla ebony also has a
**mace, a warhammer, a bow and arrows** (with the quiver). Up to 1.0.0 they kept the game's look, and an optional
plugin took them out of the levelled lists. Since 1.1.0 they are built from the Wolf weapons' own pieces (see above),
so the set is complete and that plugin is retired.

## What is deliberately NOT replaced

Ebony Mail, the Ebony Blade and the ebony dragon priest masks are distinct artifacts with their own meshes. They are
left alone - except that an optional SkyPatcher patch in the installer (off by default) gives the Ebony Mail the ebony
cuirass's look. A second optional patch does the same for the Ebony Warrior's own set from Ryn's Snazzy Last Vigil
(Nexus 76385, by Ryn and Gutmaw): it names his records only, ships none of his files, and leaves his Vitreous Ebony
set alone.

## Permissions, read per shipped source

Every source the build scripts open, with its Nexus permissions box as read. A source whose box says "You must get
permission" is not shipped until a written permission is recorded here.

| Source (what the build opens) | Nexus | Author | Permissions read | Shipped? |
|---|---|---|---|---|
| Legacy of Ysgramor - Main Archive SE, Patch Fur Lighting Bug | 109963 | NordwarUA | Permissions read 2026-11-12, again 2026-11-15: modification allowed with credit; asset use allowed with credit; conversion allowed with credit; no upload to other sites; no use in sold mods; donation points allowed | Yes - meshes, textures (recoloured), derived weapons |
| Legacy of Ysgramor - 3BA Bodyslide | 111209 | Xonek | Permissions read 2026-11-15: author's instructions "The same as in original mod" (no separate permission lines); file credits NordwarUA; not opted into donation points. The owner (2026-11-15 21:54): "consider it as permission granted" - so under Legacy of Ysgramor's terms, with credit | Yes - optional CBBE 3BA BodySlide files |
| HIMBO - Highly Improved Male Body Overhaul | 46311 | Kreiste and Novelyst | Permissions read 2026-11-16 (author's instructions): body mesh and undies licensed CC-BY-SA-4.0; refits and original armour using the HIMBO body allowed with credit if the files are free | Not shipped - its conversion and reference shapes (read from the instance at build time) drive OUR HIMBO fit; the fitted armour meshes and slider data derived from them ship |
| CBBE 3BA (3BBB) | 30174 | Acro | Permissions read 2026-11-16: modification allowed with credit; asset use allowed without asking, with credit; no use in sold mods; author's notes: everything but the body meshes allowed if not for sale, body meshes too unless vertex order/count is changed | Not shipped - its zeroed body is the target the prebuilt female meshes are built for |
| Legacy of Ysgramor - HIMBO Conversion | 110002 | Trexasle | Permissions read 2026-11-15: asset use needs his permission; some assets belong to other authors | **No** - not read by the build, not shipped; the page points at it |
| Legacy of Ysgramor - My patches and fixes (Ebony Black, Wolf Black, Full Collar Black) | 111121 | Xtudo | Permissions read 2026-11-15: modification and asset use need his permission; no donation points on mods using his assets | **No** - not read by the build, not shipped (up to the unposted 1.1.0 builds of 2026-11-15 his black diffuses were used; replaced by our own recolour of NordwarUA's originals) |

The NordwarUA box in full, read 2026-11-12 (the owner: this mod "has permission for use since this is the mod its
from" - the same permission applies to both of our mods built from that source, Nordic Ebony Armor and Weapons
Replacer and Nordic Skyforged Armor and Weapons):

- Other user's assets: all the assets belong to the author or are free-to-use modder's resources.
- **Modification permission: allowed** - "You are allowed to modify my files and release bug fixes or improve on the
  features so long as you credit me as the original creator".
- **Asset use permission: allowed** - "You are allowed to use the assets in this file without permission as long as you
  credit me".
- Conversion permission: allowed, with credit.
- Upload permission: NOT allowed to upload the file to other sites - so this mod is posted on Nexus only.
- Assets in mods that are being sold: NOT allowed - this mod is never sold or paywalled.
- Assets in mods that earn Donation Points: allowed.

Conditions we keep: credit NordwarUA as the original creator (and Xonek for the 3BA files) on the mod page and in this
file, link back to Legacy of Ysgramor, post on Nexus only, and never sell it.
