"""
halftone: dots whose area is proportional to a value, as in a printed
halftone. Used for continuous fills (tiles, rasters, 2-D bins, heatmaps,
colorbars), because a 1-bit scan turns grey fills into solid white or black.

Dot sizes are recomputed every time the figure is drawn, from the size of
a data cell on screen at that moment. Dots therefore stay round on axes
with unequal aspect, and still fill their cells after tight_layout,
constrained layout or a resize.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.collections import Collection
    from numpy.typing import ArrayLike

import numpy as np
from matplotlib.collections import PathCollection
from matplotlib.markers import MarkerStyle
from matplotlib.transforms import IdentityTransform

INK = "black"
FILL = 0.92  # dot diameter at the maximum value, as a fraction of the cell


def _marker_path(marker):
    ms = MarkerStyle(marker)
    return ms.get_path().transformed(ms.get_transform())


class HalftoneCollection(PathCollection):
    """Round or square dots at cell centres, sized by value at draw time."""

    def __init__(self, ax, cx, cy, frac, cell_w, cell_h, shape="circle", **kw):
        self._sqrt_frac = np.sqrt(frac)
        self._cell = (float(cell_w), float(cell_h))
        kw.setdefault("facecolors", INK)
        kw.setdefault("edgecolors", "none")
        kw.setdefault("linewidths", 0)
        # Dot outlines are in points (set_sizes scales them at draw time), as
        # in scatter; say so explicitly, or matplotlib >= 3.11 gives the
        # collection the data transform and draws them in data units.
        kw.setdefault("transform", IdentityTransform())
        super().__init__(
            [_marker_path("s" if shape == "square" else "o")],
            sizes=np.ones(len(frac)),
            offsets=np.column_stack([cx, cy]),
            offset_transform=ax.transData,
            **kw,
        )

    def _cell_points(self):
        ax = self.axes
        p0 = ax.transData.transform((0, 0))
        p1 = ax.transData.transform(self._cell)
        return np.abs(p1 - p0) * 72.0 / self.figure.dpi

    def draw(self, renderer):
        w_pt, h_pt = self._cell_points()
        self.set_sizes((self._sqrt_frac * min(w_pt, h_pt) * FILL) ** 2)
        super().draw(renderer)


def halftone(
    ax: Axes,
    cx: ArrayLike,
    cy: ArrayLike,
    values: ArrayLike,
    cell_w: float,
    cell_h: float,
    vmin: float | None = None,
    vmax: float | None = None,
    shape: Literal["circle", "square"] = "circle",
    **kw: Any,
) -> Collection:
    """Add a HalftoneCollection to ax. cx, cy: cell centres (any shape);
    values: one per cell (NaN = no dot); cell_w, cell_h: cell size in data
    units. Extra keywords (zorder, label, ...) go to the collection."""
    v = np.ravel(np.asarray(values, float))
    vmin = np.nanmin(v) if vmin is None else vmin
    vmax = np.nanmax(v) if vmax is None else vmax
    frac = np.clip((v - vmin) / (vmax - vmin + 1e-12), 0, 1)
    ok = np.isfinite(frac) & (frac > 0)
    x, y = np.ravel(np.asarray(cx, float)), np.ravel(np.asarray(cy, float))
    coll = HalftoneCollection(ax, x[ok], y[ok], frac[ok], abs(cell_w), abs(cell_h), shape, **kw)
    # Data limits from the cell edges (whole cells, not only their centres).
    ax.add_collection(coll, autolim=False)
    fin = np.isfinite(x) & np.isfinite(y)
    if fin.any():
        hw, hh = abs(cell_w) / 2, abs(cell_h) / 2
        ax.update_datalim([(x[fin].min() - hw, y[fin].min() - hh), (x[fin].max() + hw, y[fin].max() + hh)])
    ax.autoscale_view()
    return coll
