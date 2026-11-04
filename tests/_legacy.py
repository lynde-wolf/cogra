"""The pre-0.1 scan look (vintage.py), kept only to check the new one against it."""

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, map_coordinates, zoom


def noise(rng, shape, sigma):
    """Unit-variance smooth noise. Large sigmas are made at low res."""
    if sigma >= 8:
        f = sigma / 4.0
        small = (max(2, int(shape[0] / f)), max(2, int(shape[1] / f)))
        n = gaussian_filter(rng.standard_normal(small), 4.0)
        n = zoom(n, (shape[0] / small[0], shape[1] / small[1]), order=1)
        n = n[: shape[0], : shape[1]]
        if n.shape != shape:
            n = np.pad(n, ((0, shape[0] - n.shape[0]), (0, shape[1] - n.shape[1])), mode="edge")
    else:
        n = gaussian_filter(rng.standard_normal(shape), sigma)
    return (n - n.mean()) / (n.std() + 1e-8)


def degrade_scan(gray, rng, dpi, strength, weight, scan_dpi, skew, specks=True):
    """Bilevel scan. Work at render resolution, then area-average down to
    the scan resolution and threshold, which produces the stair-stepped
    edges. A noise field at roughly letter scale shifts the threshold so
    some glyphs come out heavier or lighter than their neighbours."""
    k = dpi / 300.0
    s = strength
    h, w = gray.shape
    ink = 1.0 - gray.astype(np.float32) / 255.0

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    amp = 0.35 * k * s
    dx = noise(rng, (h, w), 1.8 * k) * amp
    dy = noise(rng, (h, w), 1.8 * k) * amp
    ink = map_coordinates(ink, [yy + dy, xx + dx], order=1, mode="nearest")
    del yy, xx, dx, dy

    # Copy fill-in plus per-glyph weight variation
    blur = gaussian_filter(ink, 0.8 * k)
    thr = (
        0.33
        - 0.06 * weight * noise(rng, (h, w), 7 * k)
        - 0.03 * weight * noise(rng, (h, w), 60 * k)
        + 0.02 * s * noise(rng, (h, w), 0.8 * k)
    )
    thr = np.clip(thr, 0.18, 0.5)
    ink = 1.0 / (1.0 + np.exp(-(blur - thr) / 0.05))
    ink[blur < 0.02] = 0.0

    img = Image.fromarray((255 * (1.0 - ink)).astype(np.uint8), "L")
    if skew:
        img = img.rotate(skew, resample=Image.BICUBIC, fillcolor=255)
    sw, sh = round(w * scan_dpi / dpi), round(h * scan_dpi / dpi)
    small = np.asarray(img.resize((sw, sh), Image.BOX)).astype(np.float32) / 255.0
    bw = small > 0.55  # True = white

    # A few isolated specks, as on a lightly dirty copier glass
    n = rng.poisson(25 * s) if specks else 0
    ys = rng.integers(0, sh, n)
    xs = rng.integers(0, sw, n)
    for y, x in zip(ys, xs):
        r = rng.integers(0, 2)
        bw[y : y + r + 1, x : x + r + 1] = False
    return bw
