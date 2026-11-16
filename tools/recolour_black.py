#!/usr/bin/env python3
r"""Our own all-black recolour of NordwarUA's Legacy of Ysgramor diffuses, and the TruePBR maps made from it.

WHY (the owner, 2026-11-15 21:54): Xtudo's black colourway may not be shipped without his permission, so the black look is
remade here from NordwarUA's ORIGINAL diffuses, whose permissions allow modification with credit. No Xtudo file is an
input or a target: the recolour is a hue/saturation-masked procedure tuned only by overall numbers measured on 2026-11-15
(4. plans\nordic-carved-missing-weapons-20261115\xtudo-diff\xtudo-vs-nordwarua.tsv): the black look leaves grey steel
alone and turns the warm red/brown regions (cloth, tabard, leather straps, hafts, shield planks) and the fur to black-grey,
at about 0.7x their luminance (the fur lifted by a curve, luminance ** 0.6, to a black-grey with its strands); the shield's blue painted panels go the same way.

THE RECOLOUR (recolour())
    * warm  = hue within about -25..38 degrees, saturation above ~0.2      -> black-grey at luminance x GAIN
    * gold  = (ebony atlases only) hue 24..52, bright, saturated and shiny  -> KEPT: the ebony set's gold knotwork
    * blue  = (shield atlases only) hue 200..265, saturated                -> black-grey as well
    * fur   = the fur collar atlas, all of it                              -> black-grey at luminance ** FUR_GAMMA
    Grey (unsaturated) texels - the steel, the ebony plate - are never touched. Every mask is soft, so edges stay clean.

THE TRUEPBR MAPS (pbr_maps(), the owner 21:55 "make the whole armor and weapon set in PBR with cube maps")
    Built from the recoloured diffuse and NordwarUA's own _m environment mask (his shine mask for the metal):
    * metal     = where his mask says shiny, minus the warm/blue/fur regions (leather, cloth, wood, fur are never metal);
                  the ebony set's gold knotwork is metal
    * albedo    = de-lit recolour (the baked highlights pulled down to the local mean); on metal, the metal's own colour
                  (steel grey, dark ebony, or the gold's hue) times the diffuse's detail
    * roughness = metal 0.22..0.55 (shinier where his mask is brighter), leather/cloth 0.78, fur 0.9
    * AO        = the baked shading the de-light took out (the darker-than-local-mean part), 0.6..1
    * specular  = 0.5 (the TruePBR default F0)
    Packed as RMAOS: R roughness, G metallic, B AO, A specular - the Community Shaders TruePBR convention our Truly Nordic
    set uses. The normal map is his _n unchanged.
"""
import os
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

GAIN = 0.70        # warm regions' luminance factor (measured: the black look keeps ~0.5-0.8x, mean ~0.7)
FUR_GAMMA = 0.60   # the fur collar: luminance ** 0.6 (his visible fur median ~21 -> ~55/255, strands kept); 2026-11-15
RESIDUAL = 0.06    # the share of the original hue left in the black-grey (keeps leather from turning flat neutral)
METAL_BASE = {"steel": (0.58, 0.58, 0.60), "ebony": (0.27, 0.27, 0.29)}   # sRGB metal colour per set


def _smooth(x, a, b):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _hue_window(h, lo, hi, soft=8.0):
    """h in degrees; a soft window from lo to hi (lo may be negative, wrapping through 0)"""
    hh = np.where(h > 180 + (lo + hi) / 2, h - 360, h)
    return _smooth(hh, lo - soft, lo) * (1 - _smooth(hh, hi, hi + soft))


def _hsv(rgb):
    mx = rgb.max(-1); mn = rgb.min(-1); d = mx - mn
    s = np.where(mx > 1e-6, d / np.maximum(mx, 1e-6), 0.0)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    dd = np.maximum(d, 1e-6)
    h = np.where(mx == r, ((g - b) / dd) % 6, np.where(mx == g, (b - r) / dd + 2, (r - g) / dd + 4)) * 60.0
    return np.where(d > 1e-6, h, 0.0), s, mx


def _luma(rgb):
    return rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722


def masks(rgb, name, envmask=None):
    """returns (recolour weight, gold weight, fur?) for an atlas (rgb float 0..1, sRGB). The gold must also be shiny in
    NordwarUA's own _m mask when one is given: pale tan leather has the gold's hue but no shine."""
    stem = name.lower()
    h, s, v = _hsv(rgb)
    if stem.startswith("furcollar"):
        return np.ones(rgb.shape[:2]), np.zeros(rgb.shape[:2]), True
    warm = _hue_window(h, -25.0, 38.0) * _smooth(s, 0.15, 0.30)
    gold = np.zeros_like(warm)
    if stem.endswith("ebony"):
        gold = _hue_window(h, 24.0, 52.0, 6.0) * _smooth(v, 0.32, 0.50) * _smooth(s, 0.30, 0.45)
        if envmask is not None:
            gold = gold * _smooth(envmask, 0.15, 0.35)
    w = warm * (1 - gold)
    if stem.startswith("shield"):
        w = np.maximum(w, _hue_window(h, 200.0, 265.0) * _smooth(s, 0.15, 0.30))
    return w, gold, False


def recolour(rgb, name, envmask=None):
    """rgb float HxWx3 (sRGB 0..1) -> the black recolour, plus the masks used"""
    w, gold, fur = masks(rgb, name, envmask)
    L = _luma(rgb)[..., None]
    if fur:
        # the fur: NordwarUA's own fur is already dark (visible median ~21/255), so a flat gain left a flat black
        # silhouette in game (median 10, max 33 - the owner, 2026-11-15). A curve on HIS luminance lifts it to a
        # black-grey with the strand contrast kept (median ~55); the alpha channel is never touched here.
        target = np.power(np.clip(L, 0, 1), FUR_GAMMA) + (rgb - L) * RESIDUAL
    else:
        target = L * GAIN + (rgb - L) * RESIDUAL
    out = rgb * (1 - w[..., None]) + np.clip(target, 0, 1) * w[..., None]
    return out, w, gold, fur


def pbr_maps(rgb, envmask, name, kind):
    """rgb: NordwarUA's diffuse (float sRGB 0..1); envmask: his _m (float 0..1, HxW) or None; kind 'steel' | 'ebony'.
    returns (albedo HxWx3, rmaos HxWx4), floats 0..1"""
    rec, w, gold, fur = recolour(rgb, name, envmask)
    H, W = rgb.shape[:2]
    m = np.zeros((H, W)) if envmask is None else envmask
    # de-light: the baked highlights pulled toward the local mean; the baked shadows become AO
    L = _luma(rec)
    B = gaussian_filter(L, sigma=max(2.0, 6.0 * W / 2048))
    s = (L + 0.02) / (B + 0.02)
    hi = np.where(s > 1, s ** 0.5, 1.0)
    base = np.clip(rec / hi[..., None], 0, 1)
    ao = np.clip(np.where(s < 1, s ** 0.5, 1.0), 0.6, 1.0)
    # metal
    nonmetal = 1.0 if fur else w
    metal = np.clip(_smooth(m, 0.08, 0.35) * (1 - nonmetal) + gold * _smooth(m, 0.05, 0.30), 0, 1)
    if fur:
        metal = np.zeros((H, W))
    Lm = _luma(base)
    sel = metal > 0.5
    med = float(np.median(Lm[sel])) if sel.sum() > 64 else float(np.median(Lm))
    # NordwarUA's own detail (his damascus-look blades, scratches, rivets) carried in full: the owner 22:05, "the original
    # texture already does the Damascus look where it wants"
    det = np.clip(Lm / max(med, 1e-3), 0.35, 2.0)
    mcol = np.clip(np.broadcast_to(np.array(METAL_BASE[kind]), base.shape) * det[..., None], 0, 1)
    # the gold keeps its own hue, brought to a metal's brightness
    gmax = np.maximum(base.max(-1, keepdims=True), 1e-3)
    gcol = np.clip(base / gmax * 0.74, 0, 1)
    gcol = (gcol * 0.75 + _luma(gcol)[..., None] * 0.25) * np.clip(det, 0.6, 1.3)[..., None]   # a paler, less orange gold
    mcol = mcol * (1 - gold[..., None]) + gcol * gold[..., None]
    albedo = np.clip(base * (1 - metal[..., None]) + mcol * metal[..., None], 0, 1)
    rough_nm = 0.9 if fur else 0.78
    rough = (0.55 - 0.33 * m) * metal + rough_nm * (1 - metal)
    rmaos = np.stack([np.clip(rough, 0.05, 1), metal, ao, np.full((H, W), 0.5)], -1)
    return albedo, rmaos, rec


def load(path):
    im = Image.open(path); im.load()
    return np.asarray(im.convert("RGBA"), np.float32) / 255.0


def save_png(path, arr, mode):
    a = np.clip(np.round(arr * 255), 0, 255).astype(np.uint8)
    Image.fromarray(a, mode).save(path)
