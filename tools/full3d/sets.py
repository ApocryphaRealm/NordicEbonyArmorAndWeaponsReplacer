r"""Full-3D build: one description per armour set, so every tool runs on either set (env NSET=ebony|skyforged, default
ebony). Both sets are NordwarUA's Legacy of Ysgramor meshes: the steel (Skyforged) and ebony meshes are the same geometry
and UVs and share the _n normal maps of the armour atlases (helm, torso, bgpb, shield), so the armour feature finder runs
the same way on both; weapons have their own sculpt per set.

Per set:
  work      folder holding src_png\ (decoded set textures; orig\<at>_m.png = NordwarUA's _m), feat\, masks\, out\, build\,
            pkg_snapshot\, render\   (the Ebony set keeps the original demo folder, so its earlier output stays valid)
  core      the package's 00 Core, opts {name: option folder} (option meshes are built to build\out_opt\<name>\)
  alb(at)   albedo stem of feature atlas <at> (helm -> helmebony | helm); normal stem is always <at>_n
  m_src     NordwarUA _m file in the Legacy of Ysgramor main archive per feature atlas
  gold_from feature atlas gold (ornament) mask source: "self" (the set's own albedo) or another set's name - the steel
            set's knotwork is not gold, but the sculpt is the same as the Ebony set's, so the Ebony gilt marks it
  pieces    [{name, render, files: [rel, ...], atlases: [at, ...], splice, opt, copies: [rel, ...]}]
            files: the weights of one item (first one defines the recipe, the rest evaluate it - same vertex order);
            splice: unskinned NIF - only the added shapes are exported and spliced into the untouched original;
            copies: the same built file also installed at these paths (the package ships byte-identical duplicates)."""
import os, json

T = os.path.dirname(os.path.abspath(__file__))
# The work folder (decoded textures, masks, feature maps, build output - hundreds of MB, not in git): FULL3D_WORK,
# else the plan folder the pipeline was developed in. The Skyforged set's work is <work>\sets\skyforged.
ROOT = os.environ.get("FULL3D_WORK") or r"D:\Claude output\4. plans\nordic-carved-missing-weapons-20261115\chainmail-demo"
# The flat package the 3D build starts from: FULL3D_PKG (the repo packager sets it to the package it just built),
# else the 1.1.0 development build it was first made from.
PKG_ENV = os.environ.get("FULL3D_PKG")
TB = r"D:\Claude output\7. current test builds"
ARCHIVE = r"C:\Modlists\Njordlinger-downloads\Main Archive SE-109963-1-0-1706030620.7z"
TEXCONV = r"D:\Modlists\Njordlinger\tools\Skyking Toolkit\runtime\texconv.exe"
BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
ARMOUR = ("helm", "torso", "bgpb", "shield")
# the torso's lamellar pages (percent of the atlas, x0 y0 x1 y1) - modelled as scales, never as mail
LAMELLAR = {"torso": [(8, 2, 23.5, 31), (27, 2, 47, 31), (68.5, 29, 74.5, 47.5), (89.5, 29, 96.5, 47.5), (72.5, 84, 98.5, 98.5)]}


def _ebony_pieces():
    P = []
    for g in ("m", "f"):
        for it, atl in (("helmet", ["helm"]), ("cuirass", ["torso", "bgpb"]), ("gauntlets", ["bgpb"]), ("boots", ["bgpb"]),
                        ("1stpersoncuirass", ["torso", "bgpb"])):
            files = [r"meshes\NordicEbony\%s\%s_%d.nif" % (g, it, w) for w in (1, 0)]
            P.append(dict(name="%s_%s" % (it, g), render=it if g == "m" else None, atlases=atl, files=files,
                          copies=[r"meshes\armor\ebony\%s\%s_%d.nif" % (g, it, w) for w in (1, 0)]))
            if it == "cuirass":
                P.append(dict(name="cuirass_nofur_%s" % g, render=None, atlases=atl, files=files, opt="10 Cuirass - No fur collar",
                              copies=[r"meshes\armor\ebony\%s\%s_%d.nif" % (g, it, w) for w in (1, 0)]))
    for it, atl in (("helmet", ["helm"]), ("cuirass", ["torso", "bgpb"]), ("gauntlets", ["bgpb"]), ("boots", ["bgpb"])):
        P.append(dict(name=it + "gnd", render=None, atlases=atl, files=[r"meshes\armor\ebony\m\%sgnd.nif" % it], splice=True))
    P.append(dict(name="cuirassgnd_nofur", render=None, atlases=["torso", "bgpb"], files=[r"meshes\armor\ebony\m\cuirassgnd.nif"],
                  splice=True, opt="10 Cuirass - No fur collar"))
    P.append(dict(name="shield", render="shield", atlases=["shield"], files=[r"meshes\weapons\ebony\ebonyshield.nif"], splice=True))
    for w, atl in WEAPONS["ebony"]:
        P.append(dict(name=w, render=w if not w.startswith("1stperson") else None, atlases=atl,
                      files=[r"meshes\weapons\ebony\%s.nif" % w], splice=True, weapon=True))
    return P


def _skyforged_pieces():
    A = r"meshes\NordicSkyforge\armor" + "\\"
    P = []
    for g in ("M", "F"):
        for it, atl in (("Helmet", ["helm"]), ("Armor", ["torso", "bgpb"]), ("Gauntlets", ["bgpb"]), ("Boots", ["bgpb"]),
                        ("1stpersonArmor", ["torso", "bgpb"])):
            nm = {"Helmet": "helmet", "Armor": "cuirass", "Gauntlets": "gauntlets", "Boots": "boots", "1stpersonArmor": "1stpersoncuirass"}[it]
            P.append(dict(name="%s_%s" % (nm, g.lower()), render=nm if g == "M" else None, atlases=atl,
                          files=[A + "%s%s_%d.nif" % (it, g, w) for w in (1, 0)]))
    # helmet variants for the beast races / orcs (one weight each): F/M x Argonian, Khajiit, Orc
    for v in ("Helmet_FA", "Helmet_FK", "Helmet_MA", "Helmet_MK", "Helmet_MO", "HelmetFO"):
        P.append(dict(name=v.lower(), render=None, atlases=["helm"], files=[A + v + ".nif"]))
    for it, atl in (("Helmet", ["helm"]), ("Armor", ["torso", "bgpb"]), ("Gauntlets", ["bgpb"]), ("Boots", ["bgpb"])):
        P.append(dict(name=it.lower() + "_gnd", render=None, atlases=atl, files=[A + it + "_Gnd.nif"], splice=True))
    P.append(dict(name="shield", render="shield", atlases=["shield"], files=[r"meshes\NordicSkyforge\weapons\ShieldSteel.nif"], splice=True))
    for w, atl in WEAPONS["skyforged"]:
        P.append(dict(name=w.lower(), render=w.lower() if not w.lower().startswith("1stperson") else None, atlases=atl,
                      files=[r"meshes\NordicSkyforge\weapons\%s.nif" % w], splice=True, weapon=True))
    return P


# weapons with raised detail (filled in from the feature survey; bows and arrows stay out - the bow is skinned to its
# string bones and an unskinned splice would not bend with it)
WEAPONS = {"ebony": [], "skyforged": []}
_wp = os.path.join(T, "weapons3d.json")
if os.path.isfile(_wp): WEAPONS.update(json.load(open(_wp)))

SETS = {
    "ebony": dict(
        label="Nordic Ebony", work=ROOT,
        core=os.path.join(PKG_ENV, "00 Core") if PKG_ENV else TB + r"\Skyrim - Nordic Ebony Armor and Weapons Replacer\Nordic Ebony Armor and Weapons Replacer 1.1.0\00 Core",
        pkg=PKG_ENV or TB + r"\Skyrim - Nordic Ebony Armor and Weapons Replacer\Nordic Ebony Armor and Weapons Replacer 1.1.0",
        tex=r"textures\pbr\NordicEbony", folder="NordicEbony", suffix="ebony",
        m_src={"helm": "HelmEbony_m.dds", "torso": "TorsoEbony_m.dds", "bgpb": "BGPBEbony_m.dds", "shield": "ShieldEbony_m.dds",
               "axe1hebony": "Axe1HEbony_m.dds", "axe2hebony": "Axe2HEbony_m.dds", "daggerebony": "DaggerEbony_m.dds",
               "sword1hebony": "Sword1HEbony_m.dds", "sword2hebony": "Sword2HEbony_m.dds", "axe1h": "Axe1H_m.dds"},
        weapon_atlases=["axe1hebony", "axe2hebony", "daggerebony", "sword1hebony", "sword2hebony"],
        gold_from="self", mo2=r"D:\modlists\Njordlinger\mods\EXPERIMENTAL Nordic Ebony 3D"),
    "skyforged": dict(
        label="Nordic Skyforged", work=os.path.join(ROOT, "sets", "skyforged"),
        core=os.path.join(PKG_ENV, "00 Core") if PKG_ENV else TB + r"\Skyrim - Nordic Skyforged Armor and Weapons\Nordic Skyforged Armor and Weapons 1.1.0\00 Core",
        pkg=PKG_ENV or TB + r"\Skyrim - Nordic Skyforged Armor and Weapons\Nordic Skyforged Armor and Weapons 1.1.0",
        tex=r"textures\pbr\NordicSkyforge", folder="NordicSkyforge", suffix="",
        m_src={"helm": "Helm_m.dds", "torso": "Torso_m.dds", "bgpb": "BGPB_m.dds", "shield": "Shield_m.dds",
               "axe1h": "Axe1H_m.dds", "axe2h": "Axe2H_m.dds", "dagger": "Dagger_m.dds", "sword1h": "Sword1H_m.dds", "sword2h": "Sword2H_m.dds"},
        weapon_atlases=["axe1h", "axe2h", "dagger", "sword1h", "sword2h"],
        gold_from="ebony", mail_from="ebony", mo2=r"D:\modlists\Njordlinger\mods\EXPERIMENTAL Nordic Skyforged 3D"),
}


class Ctx:
    def __init__(self, name):
        self.name = name; d = SETS[name]; self.__dict__.update(d)
        W = self.work
        self.src = os.path.join(W, "src_png"); self.orig = os.path.join(self.src, "orig"); self.feat = os.path.join(W, "feat")
        self.masks = os.path.join(W, "masks"); self.out = os.path.join(W, "out"); self.build = os.path.join(W, "build")
        self.snap = os.path.join(W, "pkg_snapshot"); self.render = os.path.join(W, "render")
        self.bout = os.path.join(self.build, "out"); self.texout = os.path.join(self.bout, self.tex)
        self.pre = self.tex + "\\"
        self.pieces = _ebony_pieces() if name == "ebony" else _skyforged_pieces()
    def alb(self, at):
        """albedo stem of a feature atlas (armour atlases carry the set suffix; weapon atlases are named in full)"""
        return at + self.suffix if at in ARMOUR else at
    def nrm(self, at):
        return at + "_n" if at in ARMOUR else at + "_n"
    def mfile(self, at):
        r"""NordwarUA _m decoded under src_png\orig (the Ebony demo's own names kept)"""
        return os.path.join(self.orig, (at + "ebony_m.png") if (self.name == "ebony" and at in ARMOUR) else (at + "_m.png"))
    def mail(self, at):
        """the modelled-mail mask: the same UVs and sculpt, so a set may take another set's in-game-tested mask (the steel
        _m read as mail a little wider on the torso strips beside the lamellar, and rings stood past the flap edges)"""
        src = SETS[self.name].get("mail_from"); d = Ctx(src).masks if src else self.masks
        p = os.path.join(d, at + "_mail.png"); q = os.path.join(d, at + "_mail3d.png")
        if at in LAMELLAR and os.path.isfile(p) and (not os.path.isfile(q) or os.path.getmtime(q) < os.path.getmtime(p)):
            # 2026-11-16: the mail finder also read the outer columns of the lamellar pages as mail, and the rings modelled
            # there stood out of the flaps' inner edges - the 3D build's mask leaves the lamellar pages out
            import numpy as np
            from PIL import Image
            m = np.asarray(Image.open(p).convert("L")).copy(); H, W = m.shape
            for x0, y0, x1, y1 in LAMELLAR[at]: m[int(y0 * H / 100):int(y1 * H / 100), int(x0 * W / 100):int(x1 * W / 100)] = 0
            Image.fromarray(m, "L").save(q)
        return q if os.path.isfile(q) else p
    def src_of(self, rel, opt=None):
        if opt: return os.path.join(self.pkg, opt, rel)
        return os.path.join(self.core, rel)
    def snap_of(self, rel, opt=None):
        return os.path.join(self.snap if not opt else os.path.join(self.build, "snap_opt", opt), rel)
    def out_of(self, rel, opt=None):
        return os.path.join(self.bout if not opt else os.path.join(self.build, "out_opt", opt), rel)


def get(name=None):
    return Ctx(name or os.environ.get("NSET", "ebony"))
