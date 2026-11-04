import matplotlib.pyplot as plt
import numpy as np
import pytest
from conftest import ROOT, load_example
from scipy.optimize import linprog

import cogra
from cogra import geoms as g


def test_every_ggplot2_geom_is_mapped():
    names = (ROOT / "tests" / "ggplot2_geoms.txt").read_text().split()
    assert names, "geom list is empty"
    assert not [n for n in names if n not in g.GEOMS]
    assert all(callable(f) for f in g.GEOMS.values())


gallery = load_example("gallery")


@pytest.mark.parametrize("name", list(gallery.panels))
def test_gallery_panel_draws(name):
    fig, ax = plt.subplots(figsize=(2.2, 2))
    gallery.panels[name](ax)
    fig.canvas.draw()


def test_gallery_covers_every_geom_function():
    src = (ROOT / "examples" / "gallery.py").read_text()
    used = {f.__name__ for f in g.GEOMS.values() if f"g.{f.__name__}(" in src}
    assert used == {f.__name__ for f in g.GEOMS.values()} - {"geom_errorbarh"}


def test_groups_get_distinct_markers(rng):
    cogra.use()
    ax = plt.subplots()[1]
    lines = g.geom_point(ax, rng.random(30), rng.random(30), np.repeat(["a", "b", "c"], 10))
    assert [l.get_label() for l in lines] == ["a", "b", "c"]
    assert len({(l.get_marker(), l.get_markerfacecolor()) for l in lines}) == 3
    assert all(l.get_color() == "black" for l in lines)


def _local_linear_reference(x, y, grid, span):
    """The original loop implementation, for checking the vectorised one."""
    n = len(x)
    k = max(3, int(np.ceil(span * n)))
    out = np.empty_like(grid)
    for j, gg in enumerate(grid):
        d = np.abs(x - gg)
        h = np.partition(d, k - 1)[k - 1] + 1e-12
        w = np.clip(1 - (d / h) ** 3, 0, None) ** 3
        W = np.sqrt(w)
        A = np.column_stack([np.ones(n), x - gg]) * W[:, None]
        out[j] = np.linalg.lstsq(A, y * W, rcond=None)[0][0]
    return out


@pytest.mark.parametrize("span", [0.2, 0.75, 1.0])
def test_loess_matches_reference(rng, span):
    x = rng.uniform(0, 10, 120)
    y = np.sin(x) + rng.normal(0, 0.3, 120)
    grid = np.linspace(0, 10, 40)
    np.testing.assert_allclose(
        g._local_linear(x, y, grid, span), _local_linear_reference(x, y, grid, span), rtol=1e-7, atol=1e-9
    )


def test_loess_handles_span_above_one_and_ties(rng):
    x = np.repeat([1.0, 2.0, 3.0], 5)
    y = x * 2
    out = g._local_linear(x, y, np.array([1.0, 2.0, 3.0]), span=0.2)
    np.testing.assert_allclose(out, [2, 4, 6])
    assert np.all(np.isfinite(g._local_linear(rng.random(20), rng.random(20), np.linspace(0, 1, 5), 1.5)))


def test_smooth_lm_matches_polyfit(rng):
    cogra.use()
    x = rng.normal(size=80)
    y = 2 + 0.5 * x + rng.normal(0, 0.3, 80)
    (line,) = g.geom_smooth(plt.subplots()[1], x, y, method="lm")
    b1, b0 = np.polyfit(x, y, 1)
    np.testing.assert_allclose(line.get_ydata(), b0 + b1 * line.get_xdata())


def test_quantile_matches_dense_lp(rng):
    cogra.use()
    x = rng.normal(size=60)
    y = x + rng.standard_t(3, 60)
    lines = g.geom_quantile(plt.subplots()[1], x, y, quantiles=(0.25, 0.5))
    n = len(x)
    X = np.column_stack([np.ones(n), x])
    for line, q in zip(lines, (0.25, 0.5)):
        c = np.r_[0, 0, np.full(n, q), np.full(n, 1 - q)]
        r = linprog(
            c,
            A_eq=np.hstack([X, np.eye(n), -np.eye(n)]),
            b_eq=y,
            bounds=[(None, None)] * 2 + [(0, None)] * (2 * n),
            method="highs",
        )
        gx = line.get_xdata()

        def resid(yy, q=q):
            return np.sum(np.where(y - yy >= 0, q, q - 1) * (y - yy))

        fit = np.interp(x, gx, line.get_ydata())
        assert resid(fit) == pytest.approx(r.fun, rel=1e-6)


def test_dotplot_constant_data():
    with np.errstate(all="raise"):
        pc = g.geom_dotplot(plt.subplots()[1], np.ones(7))
    assert len(pc.get_paths()) == 7


def test_halftone_geoms_accept_artist_keywords(rng):
    ax = plt.subplots()[1]
    for coll in (
        g.geom_tile(ax, [0, 1], [0, 1], [1, 2], zorder=5),
        g.geom_raster(ax, rng.random((3, 3)), zorder=5),
        g.geom_bin_2d(ax, rng.random(50), rng.random(50), bins=4, zorder=5),
        g.geom_hex(ax, rng.random(50), rng.random(50), gridsize=4, zorder=5),
    ):
        assert coll.get_zorder() == 5


def test_segment_arrows_take_keywords():
    anns = g.geom_segment(plt.subplots()[1], [0], [0], [1], [1], arrow=True, linewidth=2, zorder=4)
    assert anns[0].arrow_patch.get_linewidth() == pytest.approx(2) and anns[0].get_zorder() == 4
