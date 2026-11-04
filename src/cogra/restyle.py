"""
restyle: apply the cogra look to a figure that is
already finished, made with plain matplotlib, pandas or seaborn.

    fig = make_my_plot()                 # however you normally do it
    fig = cogra.restyle(fig)                # or:  fig | cogra.cogra()
    cogra.save_vintage(fig, "fig.png")      # optional wear

What it inherits and how it translates it:
  * Each distinct colour is treated as a group. Groups get a consistent
    encoding across every panel: marker shape, line style, hatching.
    The legend follows, because its handles are restyled the same way.
  * Neutral greys and black stay black (lines) or white (fills).
  * Translucent fills (confidence bands) become stippling.
  * Continuous colour (scatter with a colormap) becomes three marker
    fills: open, half, filled, by tercile of the mapped value.
  * Heatmaps (imshow, pcolormesh, seaborn.heatmap) become halftone dots;
    their colorbars become halftone scales.
  * Filled contours become hatching that gets denser with level.
  * Fonts, spines, ticks and backgrounds take the period style.

Returns a dict-like report (fig.cogra_report) of what was mapped, so
a user can check that, say, "tab:blue -> group 0 (open circle, solid)".

restyle changes the figure in place and works once: a second call on the
same figure warns and returns it unchanged, because after the first pass
the group colours are gone and could not be told apart again.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from matplotlib.figure import Figure

import colorsys
import warnings

import matplotlib as mpl
import numpy as np
from matplotlib.collections import LineCollection, PathCollection, PolyCollection, QuadMesh
from matplotlib.colors import to_rgba
from matplotlib.contour import ContourSet
from matplotlib.lines import Line2D
from matplotlib.markers import MarkerStyle
from matplotlib.patches import Patch
from matplotlib.text import Text

from .halftone import HalftoneCollection, halftone

MARKERS = [
    ("o", "white"),
    ("o", "black"),
    ("s", "white"),
    ("^", "black"),
    ("D", "white"),
    ("v", "black"),
    ("s", "black"),
    ("^", "white"),
]
LINESTYLES = ["-", "--", ":", "-.", (0, (5, 1, 1, 1, 1, 1)), (0, (8, 2)), (0, (1, 3)), (0, (3, 1, 1, 1))]
HATCHES = ["", "////", "....", "xxxx", "\\\\\\\\", "++++", "oo", "--"]
BAND_HATCHES = ["....", "|||", "---", "++", "xx"]
INK = "black"


def _key(c):
    r, g, b, _a = to_rgba(c)
    return (round(r, 3), round(g, 3), round(b, 3))


def _neutral(c, tol=0.04):
    r, g, b, _a = to_rgba(c)
    return max(r, g, b) - min(r, g, b) < tol


class _Groups:
    """Assigns group indices to colours in order of first appearance.

    Near-identical colours are merged: seaborn draws bars and violins with
    a desaturated copy of the palette colour, which is the same group.
    Two colours merge when their hues are within `hue_tol` and their RGB
    distance is under `rgb_tol`. Steps of a sequential palette (one hue,
    different lightness) are usually further apart than rgb_tol and stay
    separate; check fig.cogra_report if in doubt."""

    def __init__(self, hue_tol=0.03, rgb_tol=0.16):
        self.order = {}
        self.hue_tol, self.rgb_tol = hue_tol, rgb_tol

    def idx(self, c):
        if c is None or _neutral(c):
            return None
        k = _key(c)
        if k in self.order:
            return self.order[k]
        h = colorsys.rgb_to_hsv(*k)[0]
        for k2, i in self.order.items():
            h2 = colorsys.rgb_to_hsv(*k2)[0]
            dh = min(abs(h - h2), 1 - abs(h - h2))
            if dh < self.hue_tol and np.linalg.norm(np.subtract(k, k2)) < self.rgb_tol:
                self.order[k] = i
                return i
        self.order[k] = len(set(self.order.values()))
        return self.order[k]


def _halftone(ax, cx, cy, vals, cell_w, cell_h, vmin, vmax, zorder=2):
    return halftone(ax, cx, cy, vals, cell_w, cell_h, vmin, vmax, zorder=zorder)


def _level_hatches(n):
    seq = ["", "/", "//", "///", "////", "xx", "xxx", "xxxx", "XXXX"]
    idx = np.round(np.linspace(0, len(seq) - 1, max(n, 1))).astype(int)
    return [seq[i] for i in idx]


def _is_rule(line):
    """An unlabelled line in data coordinates made only of 2-point vertical or
    horizontal segments: how seaborn draws error bars, caps and violin boxes.
    Under the cogra style these pick up the cycle's markers and dashes, so
    they are drawn as plain solid rules. axhline/axvline use a blended
    transform and are left alone."""
    if not line.get_label().startswith("_") or line.get_transform() != line.axes.transData:
        return False
    xy = np.column_stack([np.asarray(line.get_xdata(), float), np.asarray(line.get_ydata(), float)])
    runs = np.split(xy, np.flatnonzero(np.isnan(xy).any(axis=1)))
    runs = [r[~np.isnan(r).any(axis=1)] for r in runs]
    runs = [r for r in runs if len(r)]
    return bool(runs) and all(len(r) == 2 and (r[0, 0] == r[1, 0] or r[0, 1] == r[1, 1]) for r in runs)


def _style_line(line, i):
    line.set_color(INK)
    if line.axes is not None and _is_rule(line):
        line.set_marker("")
        line.set_linestyle("-")
        return
    if i is None:
        return
    had_marker = line.get_marker() not in (None, "None", "none", "", " ")
    had_line = line.get_linestyle() not in ("None", "none", "", " ")
    if had_line:
        line.set_linestyle(LINESTYLES[i % len(LINESTYLES)])
    if had_marker:
        m, face = MARKERS[i % len(MARKERS)]
        line.set_marker(m)
        line.set_markerfacecolor(face)
        line.set_markeredgecolor(INK)
        line.set_markeredgewidth(0.9)


def _hatch(artist, pattern):
    """Set a hatch in black ink. Matplotlib >= 3.10 keeps a separate hatch
    colour, set from the artist's original colour, which set_edgecolor does
    not change; without this, restyled hatching stays orange or blue."""
    artist.set_hatch(pattern)
    if hasattr(artist, "set_hatchcolor"):
        artist.set_hatchcolor(INK)


def _style_patch(p, i):
    fc = p.get_facecolor()
    alpha = fc[3] * (p.get_alpha() if p.get_alpha() is not None else 1)
    translucent = 0 < alpha < 0.6
    p.set_alpha(None)
    p.set_facecolor("white" if alpha > 0 else "none")
    p.set_edgecolor(INK)
    if p.get_linewidth() == 0:
        p.set_linewidth(0.8)
    if translucent:  # same rule as translucent fills, so legends match
        _hatch(p, BAND_HATCHES[(i or 0) % len(BAND_HATCHES)])
    elif i is not None:
        _hatch(p, HATCHES[i % len(HATCHES)])


def _restyle_scatter(ax, coll, groups, report):
    offs = coll.get_offsets()
    if len(offs) == 0:
        return
    sizes = coll.get_sizes()
    sizes = np.resize(sizes, len(offs)) if len(sizes) else np.full(len(offs), 20.0)
    z = coll.get_zorder()
    arr = coll.get_array()
    if arr is not None and len(arr) == len(offs) and np.issubdtype(np.asarray(arr).dtype, np.number):
        # continuous colour -> open / half / filled by tercile
        a = np.asarray(arr, float)
        t = np.nanpercentile(a, [33.33, 66.67])
        cls = np.digitize(a, t)
        ms = np.sqrt(np.median(sizes))
        for k, fill in enumerate(["none", "left", "full"]):
            m = cls == k
            if m.any():
                ax.plot(
                    offs[m, 0],
                    offs[m, 1],
                    linestyle="none",
                    marker="o",
                    markersize=ms,
                    fillstyle=fill,
                    markerfacecolor=INK,
                    markeredgecolor=INK,
                    markerfacecoloralt="white",
                    markeredgewidth=0.8,
                    zorder=z,
                )
        report.setdefault("continuous", []).append(
            f"scatter colour -> open/half/filled terciles (cuts at {t[0]:.3g}, {t[1]:.3g})"
        )
        coll.remove()
        return
    fcs = coll.get_facecolors()
    fcs = np.resize(fcs, (len(offs), 4)) if len(fcs) else np.tile(to_rgba(INK), (len(offs), 1))
    keys = [groups.idx(tuple(c)) for c in fcs]
    distinct = set(keys) - {None}
    if len(distinct) > len(MARKERS):
        warnings.warn(
            f"one scatter has {len(distinct)} colour groups; if its colours encode a "
            "continuous value, pass the values with c=... and a cmap instead of RGBA "
            "colours, so restyle can map them to open/half/filled markers",
            stacklevel=3,
        )
    for gi in dict.fromkeys(keys):
        m = np.array([k == gi for k in keys])
        mk, face = MARKERS[(gi or 0) % len(MARKERS)]
        ax.scatter(
            offs[m, 0],
            offs[m, 1],
            s=sizes[m],
            marker=mk,
            facecolors=face,
            edgecolors=INK,
            linewidths=0.8,
            zorder=z,
            label=coll.get_label() if gi is None else None,
        )
    coll.remove()


def _restyle_polycoll(coll, groups):
    fcs = coll.get_facecolors()
    if len(fcs) == 0:
        coll.set_edgecolor(INK)
        return
    c = fcs[0]
    alpha = c[3] * (coll.get_alpha() if coll.get_alpha() is not None else 1)
    i = groups.idx(tuple(c))
    ecs = coll.get_edgecolors()
    lws = coll.get_linewidths()
    outlined = len(ecs) and len(lws) and lws[0] > 0 and ecs[0][3] > 0.5
    if alpha < 0.6:  # translucent fill: light per-group hatch
        coll.set_facecolor("none")
        coll.set_edgecolor(INK)
        coll.set_linewidth(0.9 if outlined else 0)  # density fills keep an outline; CI bands do not
        _hatch(coll, BAND_HATCHES[(i or 0) % len(BAND_HATCHES)])
        coll.set_alpha(None)
    else:
        coll.set_facecolor("white")
        coll.set_edgecolor(INK)
        coll.set_linewidth(0.9)
        coll.set_alpha(None)
        if i is not None:
            _hatch(coll, HATCHES[i % len(HATCHES)])


def _restyle_mesh(ax, mesh, report):
    arr = np.ma.filled(np.asarray(mesh.get_array(), float).astype(float), np.nan)
    coords = mesh.get_coordinates()  # (ny+1, nx+1, 2)
    cx = (coords[:-1, :-1, 0] + coords[1:, 1:, 0]) / 2
    cy = (coords[:-1, :-1, 1] + coords[1:, 1:, 1]) / 2
    arr = arr.reshape(cx.shape)
    cw = np.abs(coords[0, 1, 0] - coords[0, 0, 0])
    ch = np.abs(coords[1, 0, 1] - coords[0, 0, 1])
    vmin, vmax = mesh.norm.vmin, mesh.norm.vmax
    mesh.set_visible(False)
    _halftone(ax, cx, cy, arr, cw, ch, vmin, vmax, zorder=mesh.get_zorder())
    report.setdefault("continuous", []).append(f"heatmap -> halftone ({vmin:.3g} to {vmax:.3g})")


def _restyle_image(ax, im, report):
    arr = np.ma.filled(np.ma.asarray(im.get_array()).astype(float), np.nan)
    if arr.ndim != 2:
        return  # RGB photographs are left alone
    x0, x1, y0, y1 = im.get_extent()
    ny, nx = arr.shape
    cw, ch = (x1 - x0) / nx, (y1 - y0) / ny
    xs = x0 + cw * (np.arange(nx) + 0.5)
    ys = y0 + ch * (np.arange(ny) + 0.5)
    cx, cy = np.meshgrid(xs, ys)
    if im.origin == "upper":  # row 0 is drawn at the top edge of the extent
        arr = arr[::-1]
    vmin, vmax = im.norm.vmin, im.norm.vmax
    im.set_visible(False)
    _halftone(ax, cx, cy, arr, abs(cw), abs(ch), vmin, vmax, zorder=im.get_zorder())
    report.setdefault("continuous", []).append(f"image -> halftone ({vmin:.3g} to {vmax:.3g})")


def _restyle_colorbar(cax):
    cb = getattr(cax, "_colorbar", None)
    if cb is None:
        return False
    if getattr(cb, "solids", None) is not None:
        cb.solids.set_visible(False)
    vmin, vmax = cb.vmin, cb.vmax
    n = 9
    vertical = cb.orientation == "vertical"
    step = (vmax - vmin) / n
    pos = vmin + step * (np.arange(n) + 0.5)
    if vertical:
        _halftone(cax, np.full(n, 0.5), pos, pos, 1.0, step, vmin, vmax, zorder=3)
    else:
        _halftone(cax, pos, np.full(n, 0.5), pos, step, 1.0, vmin, vmax, zorder=3)
    cb.outline.set_edgecolor(INK)
    cax.set_facecolor("white")
    cax.tick_params(direction="in", colors=INK)
    return True


def _restyle_contours(cs, report):
    n = len(cs.levels)
    if getattr(cs, "filled", False):
        hs = _level_hatches(n - 1)
        cs.set_facecolor("none")
        cs.set_edgecolor(INK)
        cs.hatches = hs
        cs.set_linewidth(0)
        report.setdefault("continuous", []).append(f"filled contours -> {n - 1} hatch levels")
    else:
        cs.set_color(INK)


def _restyle_legend(leg, groups):
    if leg is None:
        return
    leg.set_frame_on(False)
    for h in leg.legend_handles:
        if isinstance(h, Line2D):
            c = h.get_color() if h.get_linestyle() not in ("None", "none") else h.get_markerfacecolor()
            _style_line(h, groups.idx(c))
            if h.get_linestyle() in ("None", "none") and h.get_marker() in (None, "None", "none", ""):
                h.set_marker("o")
        elif isinstance(h, Patch):
            _style_patch(h, groups.idx(h.get_facecolor()))
        elif isinstance(h, PathCollection):
            fc = h.get_facecolors()
            gi = groups.idx(tuple(fc[0])) if len(fc) else None
            mk, face = MARKERS[(gi or 0) % len(MARKERS)]
            ms = MarkerStyle(mk)
            h.set_paths([ms.get_path().transformed(ms.get_transform())])
            h.set_facecolor(face)
            h.set_edgecolor(INK)
            h.set_linewidth(0.8)
    for t in leg.get_texts():
        t.set_color(INK)


def restyle(fig: Figure, labels: Literal["sans", "serif"] = "sans", despine: bool = True) -> Figure:
    """Restyle a finished figure in place and return it. Also applies the
    cogra rcParams globally (via use), so later figures match."""
    from .style import use

    if getattr(fig, "cogra_report", None) is not None:
        warnings.warn("figure was already restyled; returning it unchanged", stacklevel=2)
        return fig
    use(labels=labels)  # registers fonts, sets rcParams
    family = mpl.rcParams["font.family"]
    groups = _Groups()
    report: dict[str, Any] = {}
    fig.set_facecolor("white")

    data_axes = [ax for ax in fig.axes if getattr(ax, "_colorbar", None) is None]
    # pass 1: register colours in a stable order (lines, then fills) so the
    # same colour gets the same encoding in every panel and in the legend
    for ax in data_axes:
        for ln in ax.lines:
            groups.idx(ln.get_color())
        for c in ax.collections:
            if isinstance(c, HalftoneCollection):
                continue
            if isinstance(c, (PathCollection, PolyCollection)) and not isinstance(c, QuadMesh):
                fc = np.atleast_2d(np.asarray(c.get_facecolor()))
                if len(fc) and c.get_array() is None:
                    for col in fc[: min(len(fc), 500)]:
                        groups.idx(tuple(col))
        for p in ax.patches:
            groups.idx(p.get_facecolor())

    for ax in fig.axes:
        if _restyle_colorbar(ax):
            continue
        ax.set_facecolor("white")
        ax.grid(False)
        for ln in list(ax.lines):
            _style_line(ln, groups.idx(ln.get_color()))
        for c in list(ax.collections):
            if isinstance(c, HalftoneCollection):
                continue
            if isinstance(c, ContourSet):
                _restyle_contours(c, report)
            elif isinstance(c, QuadMesh):
                _restyle_mesh(ax, c, report)
            elif isinstance(c, PathCollection):
                _restyle_scatter(ax, c, groups, report)
            elif isinstance(c, PolyCollection):
                _restyle_polycoll(c, groups)
            elif isinstance(c, LineCollection):
                c.set_color(INK)
        for im in list(ax.images):
            _restyle_image(ax, im, report)
        for p in ax.patches:
            _style_patch(p, groups.idx(p.get_facecolor()))
        for name, sp in ax.spines.items():
            sp.set_color(INK)
            sp.set_linewidth(0.9)
            if despine and name in ("top", "right"):
                sp.set_visible(False)
        ax.tick_params(direction="in", colors=INK, which="both")
        _restyle_legend(ax.get_legend(), groups)
    for leg in fig.legends:
        _restyle_legend(leg, groups)
    for t in fig.findobj(Text):
        t.set_color(INK)
        t.set_fontfamily(family)

    # report the mapping in human terms
    report["groups"] = []
    for i in sorted(set(groups.order.values())):
        hexc = ", ".join(
            "#{:02x}{:02x}{:02x}".format(*tuple(round(v * 255) for v in k))
            for k, j in groups.order.items()
            if j == i
        )
        mk, face = MARKERS[i % len(MARKERS)]
        shape = {"o": "circle", "s": "square", "^": "triangle", "D": "diamond", "v": "down-triangle"}[mk]
        ls = LINESTYLES[i % len(LINESTYLES)]
        report["groups"].append(
            f"{hexc} -> group {i}: {'open' if face == 'white' else 'filled'} {shape}, "
            f"line {ls!r}, hatch {HATCHES[i % len(HATCHES)]!r}"
        )
    fig.cogra_report = report  # type: ignore[attr-defined]
    return fig


class cogra:
    """Pipe-style application:  fig | cogra()   (mirrors  p + cogra()  in R)."""

    def __init__(self, **kw):
        self.kw = kw

    def __ror__(self, fig):
        return restyle(fig, **self.kw)
