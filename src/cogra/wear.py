"""
wear: give a rendered page or figure the look of a worn mid-century print.

Three looks, each taking a grayscale raster (uint8, 0 = black ink):

  scan    1-bit archival scan of a photocopy, as in the PDFs of 1980s
          PDP-era papers: pure black and white, stair-stepped edges from
          the low scan resolution, some letters heavier than others.
  xerox   photocopied reprint: neutral stock, toner-black type thickened
          by copy generations, toner fog, drum streaks, edge shadow.
  aged    original letterpress page on toned paper (uneven ink, grain,
          toning, foxing).

Speed. Ink effects are computed tile by tile, and tiles with no ink
nearby are skipped (a typical figure is 3 to 10% ink). This is exact,
not an approximation: every noise field is defined over the whole image
and is the same wherever it is sampled (see _Noise), so the result does
not depend on the tile size. All arithmetic is float32.
"""

from __future__ import annotations

import zlib
from collections import OrderedDict
from typing import Literal

import numpy as np
from numpy.typing import NDArray
from PIL import Image
from scipy.ndimage import binary_dilation, gaussian_filter, map_coordinates
from scipy.special import expit

PAPERS = {
    "aged": (236, 227, 204),
    "light": (243, 238, 224),
    "white": (250, 249, 245),
}
INK = np.array((30, 27, 23), dtype=np.float32) / 255.0
TILE = 256  # tile edge in pixels
LOWRES_SIGMA = 3.0  # fields at least this smooth are built at low resolution
F32 = np.float32


def _radius(sigma):
    """Kernel radius gaussian_filter uses (truncate=4)."""
    return int(4.0 * sigma + 0.5)


def _fid(name):
    return zlib.crc32(name.encode())


class _Noise:
    """Smooth, unit-variance noise fields over one image.

    A field is identified by a name and has a smoothing sigma in pixels.
    It is defined for the whole image (and a little beyond), so any window
    of it can be computed on its own and windows agree where they overlap.

    Fields with sigma >= LOWRES_SIGMA are made at low resolution for the
    whole image (blur 2 px, or 4 px from sigma 8, at the matching scale)
    and interpolated bilinearly. Finer fields are blurred
    white noise; the white noise comes in blocks seeded by (seed, field,
    block row, block column), so a window needs only the blocks under it."""

    def __init__(self, seed, shape, block=TILE):
        self.seed, self.shape, self.block = int(seed), shape, block
        self._low = {}
        self._white = OrderedDict()
        self._white_max = 768  # ~200 MB of float32 blocks

    # -- white noise blocks --------------------------------------------
    def _block(self, fid, by, bx):
        key = (fid, by, bx)
        b = self._white.get(key)
        if b is None:
            rng = np.random.default_rng([self.seed, fid, by + (1 << 20), bx + (1 << 20)])
            b = rng.standard_normal((self.block, self.block), dtype=F32)
            self._white[key] = b
            if len(self._white) > self._white_max:
                self._white.popitem(last=False)
        else:
            self._white.move_to_end(key)
        return b

    def _white_window(self, fid, y0, y1, x0, x1):
        B = self.block
        by0, by1 = y0 // B, (y1 - 1) // B
        bx0, bx1 = x0 // B, (x1 - 1) // B
        rows = [
            np.hstack([self._block(fid, by, bx) for bx in range(bx0, bx1 + 1)]) for by in range(by0, by1 + 1)
        ]
        big = np.vstack(rows) if len(rows) > 1 else rows[0]
        oy, ox = y0 - by0 * B, x0 - bx0 * B
        return big[oy : oy + (y1 - y0), ox : ox + (x1 - x0)]

    # -- fields ----------------------------------------------------------
    def field(self, name, sigma, y0, y1, x0, x1):
        """Field `name` over rows y0:y1, columns x0:x1 (may extend past the image)."""
        if sigma >= LOWRES_SIGMA:
            return self._lowres(name, sigma, y0, y1, x0, x1)
        r = _radius(sigma)
        w = self._white_window(_fid(name), y0 - r, y1 + r, x0 - r, x1 + r)
        out = gaussian_filter(w, sigma, mode="constant")[r : r + (y1 - y0), r : r + (x1 - x0)]
        # blurred unit white noise has std = sum of squared 1-D kernel weights
        g = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
        g /= g.sum()
        out *= F32(1.0 / np.sum(g**2))
        return out

    def full(self, name, sigma):
        h, w = self.shape
        return self.field(name, sigma, 0, h, 0, w)

    def _lowres(self, name, sigma, y0, y1, x0, x1):
        h, w = self.shape
        key = (name, sigma)
        small = self._low.get(key)
        if small is None:
            blur = 4.0 if sigma >= 8 else 2.0
            f = sigma / blur
            sh, sw = max(2, int(h / f)), max(2, int(w / f))
            rng = np.random.default_rng([self.seed, _fid(name), 7])
            small = gaussian_filter(rng.standard_normal((sh, sw), dtype=F32), blur)
            small = (small - small.mean()) / (small.std() + 1e-8)
            self._low[key] = small
        sh, sw = small.shape
        ys = np.clip(np.arange(y0, y1) * ((sh - 1) / max(h - 1, 1)), 0, sh - 1)
        xs = np.clip(np.arange(x0, x1) * ((sw - 1) / max(w - 1, 1)), 0, sw - 1)
        iy = np.minimum(ys.astype(int), sh - 2)
        fy = (ys - iy).astype(F32)[:, None]
        ix = np.minimum(xs.astype(int), sw - 2)
        fx = (xs - ix).astype(F32)[None, :]
        c0, c1 = ix[0], ix[-1] + 2  # only the columns under the window
        sub = small[:, c0:c1]
        rows = sub[iy] * (1 - fy) + sub[iy + 1] * fy
        ix = ix - c0
        return rows[:, ix] * (1 - fx) + rows[:, ix + 1] * fx


class _Window:
    """What an ink function sees: the source ink over one tile plus margin,
    and noise fields over the same window."""

    def __init__(self, noise, y0, y1, x0, x1):
        self.noise, self.y0, self.y1, self.x0, self.x1 = noise, y0, y1, x0, x1

    def field(self, name, sigma):
        return self.noise.field(name, sigma, self.y0, self.y1, self.x0, self.x1)

    def grid(self):
        return np.mgrid[0 : self.y1 - self.y0, 0 : self.x1 - self.x0].astype(F32)


def _tiled(ink, ink_fn, noise, margin, tile=TILE):
    """Apply ink_fn to every tile that has ink within `margin` pixels,
    leaving the rest at zero ink."""
    h, w = ink.shape
    tile = max(tile, 2 * margin)
    nty, ntx = -(-h // tile), -(-w // tile)
    # which tiles have ink within `margin`: test 32-px blocks, grow by the
    # margin in blocks, then reduce to tiles
    b = 32 if tile % 32 == 0 else tile
    nby, nbx = nty * (tile // b), ntx * (tile // b)
    has = np.zeros((nby * b, nbx * b), bool)
    has[:h, :w] = ink > 0
    has = has.reshape(nby, b, nbx, b).any(axis=(1, 3))
    reach = -(-margin // b)
    if reach:
        has = binary_dilation(has, structure=np.ones((3, 3), bool), iterations=reach)
    active = has.reshape(nty, tile // b, ntx, tile // b).any(axis=(1, 3))
    out = np.zeros((h, w), F32)
    for ty, tx in zip(*np.nonzero(active)):
        y0, x0 = ty * tile, tx * tile
        y1, x1 = min(y0 + tile, h), min(x0 + tile, w)
        wy0, wy1, wx0, wx1 = y0 - margin, y1 + margin, x0 - margin, x1 + margin
        src = ink[np.clip(np.arange(wy0, wy1), 0, h - 1)][:, np.clip(np.arange(wx0, wx1), 0, w - 1)]
        res = ink_fn(src, _Window(noise, wy0, wy1, wx0, wx1))
        out[y0:y1, x0:x1] = res[margin : margin + y1 - y0, margin : margin + x1 - x0]
    return out


def _wobble(src, win, name, sigma, amp):
    """Tiny smooth displacement so edges are not machine-straight."""
    yy, xx = win.grid()
    yy += win.field(name + ".dy", sigma) * F32(amp)
    xx += win.field(name + ".dx", sigma) * F32(amp)
    return map_coordinates(src, [yy, xx], order=1, mode="nearest")


def _spread(ink, sigma, thr, soft):
    """Blur then soft-threshold: fattens strokes and roughens outlines."""
    blur = gaussian_filter(ink, sigma)
    out = expit((blur - thr) / F32(soft))
    out[blur < 0.02] = 0.0
    return out


def _margin(amp, *sigmas):
    """Pixels of context a tile needs: displacement reach plus blur radii."""
    return int(np.ceil(6 * amp)) + sum(_radius(s) for s in sigmas) + 2


def _to_ink(gray):
    return F32(1.0) - np.asarray(gray, F32) / F32(255.0)


def _specks(rng, shape, rate, size):
    """Random positions for dust specks: (rows, cols, half-width)."""
    h, w = shape
    n = rng.binomial(h * w, min(rate, 1.0))
    return rng.integers(0, h, n), rng.integers(0, w, n), size


def _blob(rng, d):
    """Coverage (0..1) of one dust speck d pixels across: an ellipse up to
    twice as long as it is wide, randomly turned, with a wavy edge and one
    pixel of soft edge. Real dust is irregular; a square stamp looks made."""
    r = max(d, 0.3) / 2
    m = int(np.ceil(r * 3.2)) + 2
    yy, xx = np.mgrid[-m : m + 1, -m : m + 1].astype(F32)
    th, ratio = rng.uniform(0, np.pi), rng.uniform(1.0, 2.0)
    u = (xx * np.cos(th) + yy * np.sin(th)) / (r * np.sqrt(ratio))
    v = (-xx * np.sin(th) + yy * np.cos(th)) * np.sqrt(ratio) / r
    rho, ang = np.hypot(u, v), np.arctan2(v, u)
    edge = 1 + sum(rng.uniform(0, 0.22) * np.cos(k * ang + rng.uniform(0, 2 * np.pi)) for k in (2, 3, 4))
    return np.clip((edge - rho) * r + 0.5, 0, 1).astype(F32)


def _dust(arr, ys, xs, diam, values, rng):
    """Add dust specks to an ink array (1 = ink): one blob of about diam
    pixels at each (y, x), at its own darkness (values), sometimes with a
    fainter fleck beside it."""
    h, w = arr.shape
    for y, x, v in zip(ys, xs, np.broadcast_to(values, ys.shape)):
        d = diam * float(np.clip(rng.lognormal(0.0, 0.3), 0.6, 1.7))
        flecks = [(0.0, 0.0, d, v)]
        if rng.random() < 0.35:
            off, ang = rng.uniform(1.2, 2.5) * d, rng.uniform(0, 2 * np.pi)
            flecks.append((off * np.sin(ang), off * np.cos(ang), 0.45 * d, 0.5 * v))
        for dy, dx, dd, vv in flecks:
            cov = _blob(rng, dd) * F32(vv)
            m = cov.shape[0] // 2
            cy, cx = int(y + dy), int(x + dx)
            y0, y1, x0, x1 = max(0, cy - m), min(h, cy + m + 1), max(0, cx - m), min(w, cx + m + 1)
            if y0 >= y1 or x0 >= x1:
                continue
            c = cov[y0 - (cy - m) : y1 - (cy - m), x0 - (cx - m) : x1 - (cx - m)]
            np.maximum(arr[y0:y1, x0:x1], c, out=arr[y0:y1, x0:x1])


# ---------- looks ----------


def scan(
    gray: NDArray[np.uint8],
    dpi: int = 600,
    scan_dpi: int = 200,
    strength: float = 1.0,
    weight: float = 1.0,
    skew: float = 0.0,
    specks: bool = True,
    seed: int = 1956,
    tile: int = TILE,
) -> NDArray[np.bool_]:
    """Bilevel scan. Work at render resolution, then area-average down to
    scan_dpi and threshold, which gives the stair-stepped edges. A noise
    field at roughly letter scale shifts the threshold so some glyphs come
    out heavier than their neighbours. Returns a bool array, True = white."""
    k, s = dpi / 300.0, strength
    ink = _to_ink(gray)
    noise = _Noise(seed, ink.shape)
    amp = 0.35 * k * s

    def fn(src, win):
        src = _wobble(src, win, "scan.wobble", 1.8 * k, amp)
        thr = (
            0.33
            - 0.06 * weight * win.field("scan.weight", 7 * k)
            - 0.03 * weight * win.field("scan.weight_broad", 60 * k)
            + 0.02 * s * win.field("scan.edge", 0.8 * k)
        )
        np.clip(thr, 0.18, 0.5, out=thr)
        return _spread(src, 0.8 * k, thr, 0.05)

    ink = _tiled(ink, fn, noise, _margin(amp, 0.8 * k), tile)
    if specks:  # a few isolated specks, as on a lightly dirty copier glass:
        # laid on at render resolution, so the scan's threshold leaves them ragged
        rng = np.random.default_rng([seed, _fid("scan.specks")])
        n = rng.poisson(25 * s)
        h, w = ink.shape
        _dust(ink, rng.integers(0, h, n), rng.integers(0, w, n), 1.5 * dpi / scan_dpi, np.ones(n, F32), rng)
    img = Image.fromarray((255 * (1 - ink)).astype(np.uint8), "L")
    if skew:
        img = img.rotate(skew, resample=Image.Resampling.BICUBIC, fillcolor=255)
    h, w = ink.shape
    sw, sh = max(1, round(w * scan_dpi / dpi)), max(1, round(h * scan_dpi / dpi))
    return np.asarray(img.resize((sw, sh), Image.Resampling.BOX)) > 140  # True = white


def xerox(
    gray: NDArray[np.uint8],
    dpi: int = 600,
    strength: float = 1.0,
    fade: float = 0.25,
    generations: int = 2,
    skew: float = 0.0,
    specks: bool = True,
    seed: int = 1956,
    tile: int = TILE,
) -> NDArray[np.uint8]:
    """Photocopy look. Each generation re-thresholds a slightly blurred
    copy, which thickens strokes and fills in counters the way repeated
    copying does. Returns uint8 grayscale."""
    k, s = dpi / 300.0, strength
    ink = _to_ink(gray)
    h, w = ink.shape
    noise = _Noise(seed, ink.shape)
    amp = 0.5 * k * s
    gens = max(1, generations)
    blurs = [(0.75 + 0.15 * g) * k for g in range(gens)]

    def fn(src, win):
        src = _wobble(src, win, "xerox.wobble", 1.8 * k, amp)
        for g, sig in enumerate(blurs):
            thr = 0.44 + 0.07 * s * win.field(f"xerox.gen{g}", 0.8 * k)
            src = _spread(src, sig, thr, 0.035)
        # toner density: mostly solid, with faint lighter patches
        density = (
            1.0
            - fade * (0.18 + 0.14 * win.field("xerox.patch", 120 * k))
            - 0.05 * s * np.clip(win.field("xerox.mottle", 1.2 * k), 0, None)
        )
        src *= np.clip(density, 0.55, 1.0)
        src *= np.where(win.field("xerox.drop", 0.9 * k) > 3.0 - 0.3 * s, F32(0.3), F32(1.0))
        return src

    ink = _tiled(ink, fn, noise, _margin(amp, *blurs), tile)

    rng = np.random.default_rng([seed, _fid("xerox.paper")])
    # neutral stock: faint grey mottling and toner fog, no colour cast
    paper = (
        0.965
        + 0.010 * noise.full("xerox.stock", 2.5 * k)
        - 0.018 * np.abs(noise.full("xerox.stock_broad", 160 * k))
    )
    fog = np.zeros((h, w), F32)
    ys, xs, _ = _specks(rng, (h, w), 0.004 * s / (k * k), 0)
    fog[ys, xs] = 1.0
    fog = gaussian_filter(fog, 0.6 * k) * F32(0.9)
    # drum streaks (faint full-height lines) and soft horizontal banding
    cols = np.zeros(w, F32)
    for x in rng.integers(0, w, rng.poisson(3 * s)):
        cols[max(0, x - int(k)) : x + int(k) + 1] += rng.uniform(0.03, 0.09)
    band = gaussian_filter(rng.standard_normal(h).astype(F32), 40 * k)
    band = 0.012 * band / (band.std() + 1e-8)
    paper -= cols[None, :]
    paper += band[:, None]
    # copier edge shadow on one side (lid not closed on the book)
    side = rng.integers(0, 4)
    width = max(1, min(int(rng.uniform(0.15, 0.35) * dpi), h, w))
    ramp = np.clip(1 - np.arange(width) / width, 0, 1) ** 2 * rng.uniform(0.25, 0.5)
    ramp = (ramp * (1 + 0.3 * gaussian_filter(rng.standard_normal(width), 3))).astype(F32)
    if side == 0:
        paper[:, :width] -= ramp[None, :]
    elif side == 1:
        paper[:, -width:] -= ramp[::-1][None, :]
    elif side == 2:
        paper[:width, :] -= ramp[:, None]
    else:
        paper[-width:, :] -= ramp[::-1][:, None]

    if specks:
        ys, xs, half = _specks(rng, (h, w), 2.5e-5 * s / (k * k), max(1, round(1.2 * k)))
        _dust(ink, ys, xs, 2 * half + 1, rng.uniform(0.5, 1.0, len(ys)).astype(F32), rng)
        np.maximum(ink, fog, out=ink)

    out = paper * (1.0 - ink) + F32(0.07) * ink
    out = gaussian_filter(out, 0.4 * k)
    img = Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8), "L")
    if skew:
        img = img.rotate(skew, resample=Image.Resampling.BICUBIC, fillcolor=int(0.965 * 255))
    return np.asarray(img)


def aged(
    gray: NDArray[np.uint8],
    dpi: int = 600,
    strength: float = 1.0,
    fade: float = 0.35,
    paper: str = "aged",
    specks: bool = True,
    seed: int = 1956,
    tile: int = TILE,
) -> NDArray[np.uint8]:
    """Original letterpress page on toned paper. Returns uint8 RGB."""
    k, s = dpi / 300.0, strength
    ink = _to_ink(gray)
    h, w = ink.shape
    noise = _Noise(seed, ink.shape)
    amp = 0.75 * k * s

    def fn(src, win):
        src = _wobble(src, win, "aged.wobble", 1.6 * k, amp)
        # ink spread with a noisy threshold (impression squeeze, ragged outline)
        src = _spread(src, 0.95 * k, 0.42 + 0.10 * s * win.field("aged.edge", 0.7 * k), 0.07)
        # uneven inking: broad patches and fine mottle inside strokes
        density = (
            1.0
            - fade * (0.30 + 0.20 * win.field("aged.broad", 90 * k) + 0.12 * win.field("aged.mid", 14 * k))
            - 0.10 * s * np.clip(win.field("aged.mottle", 1.1 * k), 0, None)
        )
        src *= np.clip(density, 0.35, 1.0)
        # breaks in thin strokes where the ink did not take
        src *= np.where(win.field("aged.drop", 0.9 * k) > 2.6 - 0.35 * s, F32(0.25), F32(1.0))
        return src

    ink = _tiled(ink, fn, noise, _margin(amp, 0.95 * k), tile)

    rng = np.random.default_rng([seed, _fid("aged.paper")])
    base = np.array(PAPERS[paper] if isinstance(paper, str) else paper, F32) / 255.0
    grain = 0.018 * noise.full("aged.grain", 0.6 * k) + 0.010 * noise.full("aged.grain2", 3 * k)
    tone = np.abs(0.035 * noise.full("aged.tone", 220 * k))
    ey = np.linspace(-1, 1, h, dtype=F32)[:, None] ** 2
    ex = np.linspace(-1, 1, w, dtype=F32)[None, :] ** 2
    edge = np.clip((np.maximum(ey, ex) - 0.75) / 0.25, 0, 1) ** 2 * F32(0.07)
    shade = 1.0 + grain - tone - edge
    out = base[None, None, :] * shade[:, :, None]
    out[:, :, 2] -= (tone + edge) * F32(0.6)  # yellow toward stains and edges
    n_fox = rng.poisson(6 * s)
    if n_fox:
        fox = np.zeros((h, w), F32)
        fox[rng.integers(0, h, n_fox), rng.integers(0, w, n_fox)] = 1.0
        fox = gaussian_filter(fox, 9 * k)
        fox = np.clip(fox / (fox.max() + 1e-8), 0, 1) * F32(0.10)
        out -= fox[:, :, None] * np.array((0.25, 0.55, 0.9), F32)[None, None, :]

    if specks:
        ys, xs, half = _specks(rng, (h, w), 1.2e-5 * s / (k * k), max(1, round(k)))
        _dust(ink, ys, xs, 2 * half + 1, rng.uniform(0.4, 0.9, len(ys)).astype(F32), rng)

    out = out * (1.0 - ink[:, :, None]) + INK[None, None, :] * ink[:, :, None]
    for c in range(3):  # scan softness
        out[:, :, c] = gaussian_filter(out[:, :, c], 0.45 * k)
    return (np.clip(out, 0, 1) * 255).astype(np.uint8)


LOOKS = ("scan", "xerox", "aged")


def apply(
    gray: NDArray[np.uint8],
    look: Literal["scan", "xerox", "aged"] = "scan",
    dpi: int = 600,
    scan_dpi: int = 200,
    strength: float = 1.0,
    weight: float = 1.0,
    fade: float | None = None,
    generations: int = 2,
    skew: float = 0.0,
    paper: str = "aged",
    specks: bool = True,
    seed: int = 1956,
) -> tuple[Image.Image, int]:
    """Run one look and return (PIL image, output dpi)."""
    if look == "scan":
        bw = scan(gray, dpi, scan_dpi, strength, weight, skew, specks, seed)
        return Image.fromarray(bw).convert("1"), scan_dpi
    if look == "xerox":
        arr = xerox(gray, dpi, strength, 0.25 if fade is None else fade, generations, skew, specks, seed)
        return Image.fromarray(arr, "L"), dpi
    if look == "aged":
        arr = aged(gray, dpi, strength, 0.35 if fade is None else fade, paper, specks, seed)
        return Image.fromarray(arr, "RGB"), dpi
    raise ValueError(f"look must be one of {LOOKS}, not {look!r}")
