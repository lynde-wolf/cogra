"""
style: the cogra figure style for matplotlib, plus wear (1-bit
archival scan, photocopy, or aged print) applied to the rendered figure.

    import cogra                       # registers the fonts and the cogra styles
    plt.style.use("cogra")             # or cogra.use(); stack cogra-serif / -column / -page
    fig, ax = plt.subplots()
    ...
    fig.savefig("clean.pdf")        # clean vector version
    cogra.save_vintage(fig, "worn.png", look="scan")
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.container import BarContainer
    from matplotlib.contour import ContourSet
    from matplotlib.figure import Figure
    from matplotlib.text import Text
    from numpy.typing import ArrayLike, NDArray

import hashlib
import io
import json
import os
import shutil
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.lines import Line2D
from PIL import Image

from . import wear

HERE = Path(__file__).resolve().parent
STYLES = HERE / "styles"
STYLE = STYLES / "cogra.mplstyle"
SIZES = ("column", "page")
_FONT_DIRS = [
    HERE / "fonts",
    Path("/usr/share/texmf/fonts/opentype/public/tex-gyre"),
    Path("/usr/share/texlive/texmf-dist/fonts/opentype/public/tex-gyre"),
]
_fonts_registered = False


def register_fonts() -> None:
    """Add TeX Gyre Heros and Schola to matplotlib's font list (once)."""
    global _fonts_registered
    if _fonts_registered:
        return
    for d in _FONT_DIRS:
        if d.is_dir():
            for f in sorted(d.iterdir()):
                if f.name.startswith(("texgyreheros-", "texgyreschola-")) and f.suffix in (".otf", ".ttf"):
                    font_manager.fontManager.addfont(str(f))
    _fonts_registered = True


def register_styles() -> None:
    """Make the cogra styles available by name to plt.style.use and
    plt.style.context: cogra, cogra-serif, cogra-column, cogra-page.
    Runs on import cogra, as SciencePlots does for its styles."""
    from matplotlib import rc_params_from_file
    from matplotlib import style as mstyle

    for f in sorted(STYLES.glob("*.mplstyle")):
        mstyle.library[f.stem] = rc_params_from_file(f, use_default_template=False)
    mstyle.available[:] = sorted(mstyle.library, key=str.lower)


def use(labels: Literal["sans", "serif"] = "sans", size: str | None = None) -> None:
    """Apply the style; the same as plt.style.use(["cogra", ...]).
    labels: 'sans' (stencil/phototype look, as in 1980s PDP figures) or
    'serif' (the cogra body face). size: None, 'column' (2.65 in, one
    column of a cogra.paper page) or 'page' (5.46 in, across both)."""
    if labels not in ("sans", "serif"):
        raise ValueError("labels must be 'sans' or 'serif'")
    if size not in (None, *SIZES):
        raise ValueError(f"size must be None or one of {SIZES}")
    register_fonts()
    if "cogra" not in plt.style.library:
        register_styles()
    plt.style.use(
        ["cogra"] + (["cogra-serif"] if labels == "serif" else []) + ([f"cogra-{size}"] if size else [])
    )


HATCHES = ["", "////", "....", "xxxx", "\\\\\\\\", "++++"]


def bars(
    ax: Axes, x: ArrayLike, heights: ArrayLike, hatches: Sequence[str] | None = None, **kw: Any
) -> BarContainer:
    """Bar chart in period style: white fill, black outline, hatching to
    tell conditions apart. matplotlib otherwise fills bars with the line
    colour (black), which the style file cannot change separately."""
    n = np.size(heights)
    hatches = hatches or [HATCHES[i % len(HATCHES)] for i in range(n)]
    kw.setdefault("width", 0.55)
    kw.setdefault("linewidth", 0.9)
    kw.setdefault("error_kw", {"elinewidth": 0.9, "capthick": 0.9})
    return ax.bar(x, heights, facecolor="white", edgecolor="black", hatch=hatches, **kw)


# ---------- significance brackets ----------

STARS = ((0.001, "***"), (0.01, "**"), (0.05, "*"))


def _check_p(p):
    if not 0.0 <= p <= 1.0:  # also catches NaN
        raise ValueError(f"p must be between 0 and 1, got {p!r}")


def stars(p: float, levels: Sequence[tuple[float, str]] = STARS) -> str:
    """'***', '**', '*' or '' for a p value (thresholds are exclusive: p < .05).
    Raises ValueError for a p outside [0, 1] or NaN."""
    _check_p(p)
    for cut, mark in levels:
        if p < cut:
            return mark
    return ""


def format_p(p: float) -> str:
    """APA-style p with an italic p and no leading zero: 'p < .001', 'p = .012'.
    Raises ValueError for a p outside [0, 1] or NaN."""
    _check_p(p)
    if p < 0.001:
        return r"$p$ < .001"
    return r"$p$ = " + f"{p:.3f}".lstrip("0")


def _top_between(ax, lo, hi):
    """Highest data y of anything drawn between x = lo and x = hi: bars and
    other patches, error bars, lines, points, filled areas, and earlier
    brackets (including their labels). None if nothing is there."""
    tops = []
    eps = 1e-9 * max(1.0, abs(lo), abs(hi))  # seaborn puts dodged bars at 0.20000000000000007
    lo, hi = lo - eps, hi + eps
    to_data = ax.transData.inverted()
    for p in ax.patches:
        bb = p.get_window_extent().transformed(to_data)
        if np.isfinite([bb.x0, bb.x1, bb.y1]).all() and bb.x1 >= lo and bb.x0 <= hi:
            tops.append(max(bb.y0, bb.y1))
    for ln in ax.lines:
        if ln.get_transform() != ax.transData:
            continue  # axhline, axvline
        xs, ys = np.asarray(ln.get_xdata(), float), np.asarray(ln.get_ydata(), float)
        keep = np.isfinite(xs) & np.isfinite(ys) & (xs >= lo) & (xs <= hi)
        if keep.any():
            tops.append(ys[keep].max())
    for c in ax.collections:
        if c.get_transform() != ax.transData:
            pts = np.asarray(c.get_offsets(), float).reshape(-1, 2)  # scatter points
        else:
            paths = c.get_paths()
            pts = np.concatenate([pa.vertices for pa in paths]) if len(paths) else np.empty((0, 2))
        if len(pts):
            keep = np.isfinite(pts).all(axis=1) & (pts[:, 0] >= lo) & (pts[:, 0] <= hi)
            if keep.any():
                tops.append(pts[keep, 1].max())
    for blo, bhi, btop in getattr(ax, "_cogra_brackets", []):
        if bhi >= lo and blo <= hi:
            tops.append(btop)
    return max(tops) if tops else None


def signif(
    ax: Axes,
    x1: float,
    x2: float,
    p: float | None = None,
    text: str | None = None,
    show: Literal["stars", "p"] = "stars",
    ns: bool = False,
    y: float | None = None,
    pad: float = 0.04,
    tick: float = 0.02,
    fontsize: float | None = None,
    linewidth: float = 0.8,
    levels: Sequence[tuple[float, str]] = STARS,
) -> tuple[Line2D, Text] | None:
    """A significance bracket from x1 to x2 with stars above it.

    p: the p value, labelled with stars (show="stars", the default) or as
    'p = .012' (show="p"). text: your own label instead ("n.s.", "d = 0.54").
    ns: with stars, a p that is not significant draws nothing unless ns=True,
    which writes "n.s.". y: where the bracket sits; by default just above the
    highest thing between x1 and x2 (bars, error bars, points, earlier
    brackets), so several brackets stack. pad and tick are fractions of the
    y range. Call it after the data are drawn. Returns (line, text), or None
    when nothing is drawn.

    The bracket never changes the x limits; the y limit grows if the label
    would otherwise be cut off."""
    if x1 == x2:
        raise ValueError("x1 and x2 must differ")
    if show not in ("stars", "p"):
        raise ValueError("show must be 'stars' or 'p'")
    if text is None:
        if p is None:
            raise ValueError("give p or text")
        if not 0 <= p <= 1:
            raise ValueError("p must be between 0 and 1")
        text = format_p(p) if show == "p" else (stars(p, levels) or ("n.s." if ns else ""))
    if not text:
        return None
    lo, hi = sorted((x1, x2))
    ylo, yhi = ax.get_ylim()
    span = yhi - ylo
    if y is None:
        top = _top_between(ax, lo, hi)
        y = (top if top is not None else ylo) + pad * span
    t = tick * span
    line = Line2D(
        [x1, x1, x2, x2],
        [y - t, y, y, y - t],
        color="black",
        linewidth=linewidth,
        marker="none",
        linestyle="-",
        solid_joinstyle="miter",
        clip_on=False,
        label="_cogra_signif",
    )
    ax.add_artist(line)  # unlike ax.plot, leaves the axis limits alone
    label = ax.text(
        (x1 + x2) / 2,
        y,
        text,
        ha="center",
        va="bottom",
        clip_on=False,
        fontsize=fontsize if fontsize is not None else mpl.rcParams["font.size"],
    )
    # height of the label in data units, so the next bracket clears it
    px = float(label.get_fontsize()) * 1.25 * ax.figure.dpi / 72
    to_data = ax.transData.inverted()
    h = abs(to_data.transform((0, px))[1] - to_data.transform((0, 0))[1])
    brackets = [*getattr(ax, "_cogra_brackets", []), (lo, hi, y + h)]
    ax._cogra_brackets = brackets  # type: ignore[attr-defined]
    if y + h > yhi:
        ax.set_ylim(ylo, y + h + 0.01 * span)
    return line, label


# ---------- wear ----------

WEAR_VERSION = 3  # bump when wear output changes, to invalidate the cache


def cache_dir() -> Path:
    """Where save_vintage keeps worn images: $COGRA_CACHE, else
    $XDG_CACHE_HOME/cogra, else ~/.cache/cogra."""
    d = os.environ.get("COGRA_CACHE")
    if d:
        return Path(d)
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "cogra"


def clear_cache() -> None:
    shutil.rmtree(cache_dir(), ignore_errors=True)


def render_gray(fig: Figure, dpi: float) -> NDArray[np.uint8]:
    """The figure as a grayscale uint8 array at `dpi` (honours savefig.bbox)."""
    b = io.BytesIO()
    fig.savefig(b, format="png", dpi=dpi, pil_kwargs={"compress_level": 1})
    b.seek(0)
    return np.asarray(Image.open(b).convert("L"))


def save_vintage(
    fig: Figure,
    path: str | os.PathLike[str],
    look: Literal["scan", "xerox", "aged"] = "scan",
    dpi: int = 600,
    scan_dpi: int = 300,
    strength: float = 1.0,
    weight: float = 1.0,
    fade: float | None = None,
    generations: int = 2,
    seed: int = 1956,
    specks: bool = False,
    cache: bool = True,
) -> Path:
    """Render fig at `dpi`, apply wear, save as PNG (or anything PIL
    writes). The scan look writes a 1-bit image at scan_dpi.

    specks defaults to False for figures: random dust specks are
    indistinguishable from data points in a scatter plot.

    cache: True keeps worn images in cache_dir(), keyed by the rendered
    figure and every setting, so re-running an unchanged figure skips the
    wear. False turns it off; a path uses that folder."""
    path = Path(path)
    gray = render_gray(fig, dpi)
    params = dict(
        look=look,
        dpi=dpi,
        scan_dpi=scan_dpi,
        strength=strength,
        weight=weight,
        fade=fade,
        generations=generations,
        seed=seed,
        specks=specks,
        suffix=path.suffix.lower(),
        version=WEAR_VERSION,
    )
    cached = None
    if cache:
        h = hashlib.blake2b(json.dumps(params, sort_keys=True).encode(), digest_size=20)
        h.update(np.asarray(gray.shape, np.int64).tobytes())
        h.update(gray.tobytes())
        root = cache_dir() if cache is True else Path(cache)
        cached = root / (h.hexdigest() + path.suffix.lower())
        if cached.is_file():
            shutil.copyfile(cached, path)
            return path
    img, out_dpi = wear.apply(
        gray,
        look=look,
        dpi=dpi,
        scan_dpi=scan_dpi,
        strength=strength,
        weight=weight,
        fade=fade,
        generations=generations,
        specks=specks,
        seed=seed,
    )
    img.save(path, dpi=(out_dpi, out_dpi))
    if cached is not None:
        cached.parent.mkdir(parents=True, exist_ok=True)
        tmp = cached.with_suffix(cached.suffix + ".tmp")
        shutil.copyfile(path, tmp)
        os.replace(tmp, cached)
    return path


# ---------- Anachronisms, drawn as a 1960s draftsman might have ----------


def _plain(ax, x, y, **kw):
    """A line with the prop cycle's markers and dashes switched off."""
    return ax.plot(x, y, **{"color": "black", "marker": "none", "linestyle": "-", **kw})


def violin(
    ax: Axes,
    datasets: Sequence[ArrayLike],
    positions: ArrayLike | None = None,
    hatches: Sequence[str] | None = None,
    width: float = 0.7,
    bw: float | None = None,
    median: bool = True,
    side: Literal["both", "left", "right"] = "both",
) -> Axes:
    """Outlined violins with hatching instead of fill colour.
    side: 'both', 'left' or 'right' (half violins, used by raincloud).
    A dataset with no spread is drawn as a single horizontal rule."""
    from scipy.stats import gaussian_kde

    positions = np.arange(len(datasets)) if positions is None else np.asarray(positions, float)
    hatches = hatches or [HATCHES[i % len(HATCHES)] for i in range(len(datasets))]
    for d, x, h in zip(datasets, positions, hatches):
        d = np.asarray(d, float)
        d = d[np.isfinite(d)]
        lo_x = x - width / 2 if side in ("both", "left") else x
        hi_x = x + width / 2 if side in ("both", "right") else x
        if len(d) < 2 or np.ptp(d) == 0:
            if len(d):
                _plain(ax, [lo_x, hi_x], [d[0], d[0]], linewidth=1.4)
            continue
        kde = gaussian_kde(d, bw_method=bw)
        y = np.linspace(d.min(), d.max(), 200)
        w = kde(y)
        w = w / w.max() * width / 2
        left = x - w if side in ("both", "left") else np.full_like(w, x)
        right = x + w if side in ("both", "right") else np.full_like(w, x)
        ax.fill_betweenx(y, left, right, facecolor="white", edgecolor="black", hatch=h, linewidth=0.9)
        if median:
            m = np.median(d)
            wm = np.interp(m, y, w)
            l = x - wm if side in ("both", "left") else x
            r = x + wm if side in ("both", "right") else x
            _plain(ax, [l, r], [m, m], linewidth=1.4)
    ax.set_xticks(positions)
    return ax


def raincloud(
    ax: Axes,
    datasets: Sequence[ArrayLike],
    positions: ArrayLike | None = None,
    hatches: Sequence[str] | None = None,
    seed: int = 0,
    width: float = 0.6,
) -> Axes:
    """Half violin (cloud), slim box plot, and jittered open circles (rain)."""
    rng = np.random.default_rng(seed)
    positions = np.arange(len(datasets)) if positions is None else np.asarray(positions, float)
    violin(ax, datasets, positions + 0.06, hatches, width=width, median=False, side="right")
    for d, x in zip(datasets, positions):
        d = np.asarray(d, float)
        q1, m, q3 = np.percentile(d, [25, 50, 75])
        lo, hi = np.percentile(d, [2.5, 97.5])
        ax.add_patch(
            mpl.patches.Rectangle(
                (x - 0.035, q1), 0.07, q3 - q1, facecolor="white", edgecolor="black", linewidth=0.9, zorder=3
            )
        )
        _plain(ax, [x - 0.035, x + 0.035], [m, m], linewidth=1.4, zorder=4)
        _plain(ax, [x, x], [lo, q1], linewidth=0.8)
        _plain(ax, [x, x], [q3, hi], linewidth=0.8)
        jit = x - 0.12 - rng.uniform(0, 0.16, len(d))
        ax.plot(
            jit,
            d,
            linestyle="none",
            marker="o",
            markersize=2.6,
            markerfacecolor="white",
            markeredgewidth=0.6,
            color="black",
        )
    ax.set_xticks(positions)
    return ax


def _nice_step(x):
    e = 10 ** np.floor(np.log10(x))
    f = x / e
    return e * (1 if f < 1.5 else 2 if f < 3.5 else 5 if f < 7.5 else 10)


def topoplot(
    ax: Axes,
    xy: ArrayLike,
    values: ArrayLike,
    levels: int | ArrayLike | None = None,
    hatch: bool = True,
    labels: bool = True,
    electrodes: bool = True,
    res: int = 200,
    fmt: str = "%g",
) -> ContourSet | None:
    """Scalp map in contour-and-hatching form.
    xy: (n, 2) electrode positions scaled so the head is the unit circle
    (nose at +y). values: n values. Negative contours are dashed.
    Returns the ContourSet, or None if the map is flat (no contours)."""
    from scipy.interpolate import RBFInterpolator

    xy = np.asarray(xy, float)
    values = np.asarray(values, float)
    g = np.linspace(-1, 1, res)
    X, Y = np.meshgrid(g, g)
    Z = RBFInterpolator(xy, values, kernel="thin_plate_spline", smoothing=1e-3)(
        np.column_stack([X.ravel(), Y.ravel()])
    ).reshape(X.shape)
    Z[X**2 + Y**2 > 1] = np.nan
    if levels is None:
        m = np.nanmax(np.abs(Z))
        if m > 0:
            step = _nice_step(m / 3)
            levels = np.arange(-np.ceil(m / step) * step, np.ceil(m / step) * step + step / 2, step)
            levels = levels[levels != 0]
        else:
            levels = []
    lv = np.asarray(levels, float)
    cs = None
    if len(lv):
        if hatch:
            # One band per interval between levels. No hatching around zero;
            # denser hatching for larger magnitudes; "\\" negative, "/" positive.
            neg = np.sort(lv[lv < 0])
            pos = np.sort(lv[lv > 0])
            edges = np.concatenate([[-1e9], neg, pos, [1e9]])
            fill: list[str | None] = [
                "\\" * (len(neg) - i + 1) for i in range(len(neg))
            ]  # most negative first
            fill += [None]
            fill += ["/" * (i + 2) for i in range(len(pos))]
            ax.contourf(X, Y, Z, levels=edges, colors="none", hatches=fill)
        cs = ax.contour(X, Y, Z, levels=lv, colors="black", linewidths=0.8)
        if np.nanmin(Z) < 0 < np.nanmax(Z):
            ax.contour(X, Y, Z, levels=[0], colors="black", linewidths=0.5, linestyles=":")
        if labels:
            for lbl in ax.clabel(cs, fmt=fmt, fontsize=8, inline=True, inline_spacing=3):
                # white patch behind each label so hatching does not run through it
                lbl.set_bbox(dict(facecolor="white", edgecolor="none", pad=0.6))
    # head, nose, ears
    t = np.linspace(0, 2 * np.pi, 400)
    _plain(ax, np.cos(t), np.sin(t), linewidth=1.1)
    _plain(ax, [-0.09, 0, 0.09], [0.995, 1.11, 0.995], linewidth=1.1)
    for s in (-1, 1):
        ey = np.linspace(-0.18, 0.18, 50)
        _plain(ax, s * (1 + 0.07 * np.cos(ey / 0.18 * np.pi / 2)), ey, linewidth=1.1)
    if electrodes:
        ax.plot(
            xy[:, 0],
            xy[:, 1],
            linestyle="none",
            marker="o",
            markersize=1.8,
            markerfacecolor="black",
            markeredgewidth=0,
            color="black",
        )
    ax.set_aspect("equal")
    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-1.12, 1.2)
    ax.axis("off")
    return cs


def density_topo(
    ax: Axes,
    x: ArrayLike,
    y: ArrayLike,
    masses: Sequence[float] | None = None,
    index: Sequence[float] = (0.5, 0.9),
    points: bool | Literal["outside"] = True,
    bw: float | None = None,
    res: int = 220,
    pad: float = 0.15,
    point_size: float = 1.5,
    label_fmt: str = "{:.0%}",
) -> ContourSet:
    """Scatter with kernel density contours drawn like a topographic map.

    Contours enclose fixed fractions of the probability mass (highest-
    density regions): the 50% line encloses the densest half of the
    distribution. Lines in `index` are drawn heavier and labelled, like
    index contours on a survey map; the rest are thin and unlabelled.
    Note these are fractions of the estimated density, not exact
    fractions of the plotted points.

    points: True (all points), False (none), or "outside" (only points
    beyond the outermost contour, which keeps large samples readable).
    """
    from scipy.stats import gaussian_kde

    x = np.asarray(x, float)
    y = np.asarray(y, float)
    base = np.round(np.arange(0.1, 0.96, 0.1), 2) if masses is None else np.asarray(masses, float)
    mass_levels = np.unique(np.round(np.concatenate([base, index]), 6))
    kde = gaussian_kde(np.vstack([x, y]), bw_method=bw)
    xr, yr = np.ptp(x), np.ptp(y)
    gx = np.linspace(x.min() - pad * xr, x.max() + pad * xr, res)
    gy = np.linspace(y.min() - pad * yr, y.max() + pad * yr, res)
    X, Y = np.meshgrid(gx, gy)
    Z = kde(np.vstack([X.ravel(), Y.ravel()])).reshape(X.shape)

    # density threshold enclosing each mass fraction
    z = np.sort(Z.ravel())[::-1]
    cum = np.cumsum(z)
    cum /= cum[-1]
    thr = {m: z[min(np.searchsorted(cum, m), len(z) - 1)] for m in mass_levels}
    # contour needs strictly increasing levels; on a coarse grid two masses
    # can share a threshold, in which case the larger mass is kept
    order: list[float] = []
    for m in sorted(mass_levels, key=lambda m: (thr[m], -m)):
        if not order or thr[m] > thr[order[-1]]:
            order.append(m)
    lv = [thr[m] for m in order]

    if points:
        if points == "outside":
            keep = kde(np.vstack([x, y])) < min(lv)
            px, py = x[keep], y[keep]
        else:
            px, py = x, y
        ax.plot(
            px,
            py,
            linestyle="none",
            marker="o",
            markersize=point_size,
            markerfacecolor="black",
            markeredgewidth=0,
            color="black",
            zorder=1,
        )
    is_index = [any(np.isclose(m, i) for i in index) for m in order]
    widths = [1.15 if k else 0.45 for k in is_index]
    cs = ax.contour(X, Y, Z, levels=lv, colors="black", linewidths=widths, linestyles="solid", zorder=2)
    idx_levels = [l for l, k in zip(lv, is_index) if k]
    names = {thr[m]: label_fmt.format(m) for m in order}
    for t in ax.clabel(
        cs, levels=idx_levels, fmt=lambda v: names.get(v, ""), fontsize=7.5, inline=True, inline_spacing=3
    ):
        t.set_bbox(dict(facecolor="white", edgecolor="none", pad=0.5))
    return cs
