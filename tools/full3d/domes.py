"""rivet / stud finder: a dome in a DirectX normal map tilts outward in BOTH axes around its centre, a groove or a wood
grain line only in one. Score = min(x-tilt match, y-tilt match) / local tilt energy, peaks above a threshold, on metal."""
import numpy as np
from scipy.signal import fftconvolve
from scipy.ndimage import gaussian_filter as G
from skimage.feature import peak_local_max

def find(nx, ny_down, metal, cover, exclude, k, thr=0.42, radii=(2.5, 3.5, 5.0), sign=None):
    best = np.zeros(nx.shape, np.float32); rbest = np.zeros(nx.shape, np.float32)
    for r0 in radii:
        r = r0 * k; R = int(np.ceil(r * 1.6)); yy, xx = np.mgrid[-R:R + 1, -R:R + 1].astype(np.float32); d = np.sqrt(xx ** 2 + yy ** 2)
        w = np.where(d <= r * 1.15, 1.0, 0.0) * np.exp(-0.5 * (d / (0.8 * r)) ** 2)
        kx = xx / r * w; ky = yy / r * w; kx /= np.abs(kx).sum(); ky /= np.abs(ky).sum()
        cx = fftconvolve(nx, kx[::-1, ::-1], mode="same"); cy = fftconvolve(ny_down, ky[::-1, ::-1], mode="same")
        E = np.sqrt(G(nx ** 2 + ny_down ** 2, r)) + 0.02
        s = 1.0 if sign is None else sign
        sc = np.minimum(s * cx, s * cy) / E
        upd = sc > best; best[upd] = sc[upd]; rbest[upd] = r
    best[~(metal & cover) | exclude] = 0
    pk = peak_local_max(best, min_distance=max(2, int(2.5 * k)), threshold_abs=thr)
    return [(y, x, rbest[y, x], best[y, x]) for y, x in pk], best
