import matplotlib.pyplot as plt
import numpy as np
import pytest

from cogra import geoms as g
from cogra.halftone import FILL, HalftoneCollection, halftone


def _dot_extents(fig, coll):
    """Width and height of each drawn dot, in pixels."""
    fig.canvas.draw()
    path = coll.get_paths()[0]
    out = []
    for t in coll.get_transforms():
        v = path.vertices @ t[:2, :2].T
        out.append(np.ptp(v, axis=0))  # set_sizes already scales to pixels
    return np.array(out)


def test_dots_are_round_on_unequal_aspect(rng):
    fig, ax = plt.subplots(figsize=(8, 2))
    coll = g.geom_raster(ax, rng.random((4, 4)) + 0.1)
    wh = _dot_extents(fig, coll)
    np.testing.assert_allclose(wh[:, 0], wh[:, 1], rtol=1e-6)


def test_largest_dot_fills_cell_after_layout_change():
    fig, ax = plt.subplots(layout="constrained")
    ax.set_xlim(0, 4)
    ax.set_ylim(0, 4)
    coll = halftone(ax, [0.5, 1.5], [0.5, 0.5], [0, 1], 1.0, 1.0)
    fig.colorbar(plt.cm.ScalarMappable(), ax=ax)  # shrinks the axes at draw time
    wh = _dot_extents(fig, coll)
    bb = ax.get_window_extent()
    cell = min(bb.width, bb.height) / 4
    assert wh.max() == pytest.approx(FILL * cell, rel=0.02)


def test_area_proportional_to_value():
    fig, ax = plt.subplots()
    ax.set_xlim(0, 3)
    ax.set_ylim(0, 1)
    coll = halftone(ax, [0.5, 1.5, 2.5], [0.5] * 3, [0.25, 0.5, 1.0], 1, 1, vmin=0, vmax=1)
    d = _dot_extents(fig, coll)[:, 0]
    np.testing.assert_allclose((d / d[-1]) ** 2, [0.25, 0.5, 1.0], rtol=1e-6)


def test_nan_and_minimum_cells_get_no_dot():
    ax = plt.subplots()[1]
    coll = halftone(ax, [0, 1, 2], [0, 0, 0], [np.nan, 0.0, 3.0], 1, 1)
    assert isinstance(coll, HalftoneCollection) and len(coll.get_offsets()) == 1


def test_dots_survive_savefig_at_other_dpi(tmp_path, rng):
    fig, ax = plt.subplots(figsize=(3, 2))
    g.geom_tile(ax, np.arange(4), np.zeros(4), [1, 2, 3, 4])
    for dpi in (72, 300):
        fig.savefig(tmp_path / f"t{dpi}.png", dpi=dpi)


def test_autoscaled_limits_cover_the_cells():
    """Without explicit limits, the axes span the cells in data units."""
    _fig, ax = plt.subplots()
    xs, ys = np.meshgrid(range(5), range(4))
    halftone(ax, xs, ys, np.arange(20.0), 1.0, 1.0)
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    assert -0.8 <= x0 <= -0.5 and 4.5 <= x1 <= 4.8
    assert -0.8 <= y0 <= -0.5 and 3.5 <= y1 <= 3.8


def test_dots_stay_inside_their_cells_when_saved(tmp_path):
    """Dots are sized in points and drawn in display space; with matplotlib
    3.11 a collection without its own transform is drawn in data units,
    which turned a tile plot into one black block."""
    from PIL import Image

    fig, ax = plt.subplots(figsize=(3, 3))
    g.geom_tile(ax, np.tile(np.arange(6), 5), np.repeat(np.arange(5), 6), np.linspace(0.05, 1, 30))
    fig.savefig(tmp_path / "t.png", dpi=100)
    a = np.asarray(Image.open(tmp_path / "t.png").convert("L"))
    bb = ax.get_window_extent()
    inner = a[int(a.shape[0] - bb.y1) + 2 : int(a.shape[0] - bb.y0) - 2, int(bb.x0) + 2 : int(bb.x1) - 2]
    ink = (inner < 128).mean()
    assert 0.15 < ink < 0.7  # dots and paper, not one black block
