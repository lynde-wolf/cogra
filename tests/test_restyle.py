import matplotlib.pyplot as plt
import numpy as np
import pytest

import cogra
from cogra.halftone import HalftoneCollection
from cogra.restyle import HATCHES, MARKERS


def _colour_fig(rng):
    fig, (a, b) = plt.subplots(1, 2)
    for c in ("tab:blue", "tab:orange"):
        a.plot(np.arange(5), rng.random(5), color=c, marker="o", label=c)
        b.bar([0, 1], rng.random(2) + 1, color=c, label=c)
    a.legend()
    return fig, a, b


def test_same_colour_same_encoding_across_panels(rng):
    fig, a, b = _colour_fig(rng)
    cogra.restyle(fig)
    blue, orange = a.lines
    assert blue.get_linestyle() == "-" and orange.get_linestyle() == "--"
    assert (blue.get_marker(), blue.get_markerfacecolor()) == MARKERS[0]
    assert (orange.get_marker(), orange.get_markerfacecolor()) == MARKERS[1]
    assert [p.get_hatch() for p in b.patches] == [HATCHES[0]] * 2 + [HATCHES[1]] * 2
    leg = a.get_legend().legend_handles
    assert [h.get_linestyle() for h in leg] == ["-", "--"]
    assert len(fig.cogra_report["groups"]) == 2


def test_everything_is_black_and_white(rng):
    fig, a, b = _colour_fig(rng)
    cogra.restyle(fig)
    for ln in a.lines:
        assert ln.get_color() == "black"
    for p in b.patches:
        assert tuple(p.get_facecolor()[:3]) == (1, 1, 1) and tuple(p.get_edgecolor()[:3]) == (0, 0, 0)


def test_second_restyle_warns_and_keeps_groups(rng):
    fig, ax = plt.subplots()
    for c in ("tab:blue", "tab:orange", "tab:green"):
        ax.scatter(rng.random(10), rng.random(10), color=c)
    cogra.restyle(fig)
    before = [(len(c.get_paths()[0].vertices), tuple(c.get_facecolors()[0])) for c in ax.collections]
    with pytest.warns(UserWarning, match="already restyled"):
        cogra.restyle(fig)
    after = [(len(c.get_paths()[0].vertices), tuple(c.get_facecolors()[0])) for c in ax.collections]
    assert before == after and len(set(before)) == 3


def test_pipe_syntax(rng):
    fig, *_ = _colour_fig(rng)
    assert (fig | cogra.cogra(labels="serif")) is fig and hasattr(fig, "cogra_report")


def test_continuous_scatter_becomes_terciles(rng):
    fig, ax = plt.subplots()
    ax.scatter(rng.random(90), rng.random(90), c=np.arange(90), cmap="viridis")
    cogra.restyle(fig)
    fills = sorted(l.get_fillstyle() for l in ax.lines)
    assert fills == ["full", "left", "none"]
    assert sum(len(l.get_xdata()) for l in ax.lines) == 90
    assert "terciles" in fig.cogra_report["continuous"][0]


def test_rgba_colormap_scatter_warns(rng):
    fig, ax = plt.subplots()
    ax.scatter(rng.random(300), rng.random(300), c=plt.cm.viridis(rng.random(300)))
    with pytest.warns(UserWarning, match="continuous value"):
        cogra.restyle(fig)


def test_heatmap_and_colorbar_become_halftones(rng):
    fig, ax = plt.subplots()
    im = ax.imshow(rng.random((4, 6)))
    fig.colorbar(im)
    cogra.restyle(fig)
    assert not im.get_visible()
    dots = [c for c in ax.collections if isinstance(c, HalftoneCollection)]
    assert len(dots) == 1 and len(dots[0].get_offsets()) <= 24
    cax = fig.axes[1]
    assert any(isinstance(c, HalftoneCollection) for c in cax.collections)
    fig.canvas.draw()


def test_imshow_orientation_preserved():
    fig, ax = plt.subplots()
    z = np.zeros((3, 3))
    z[0, 0] = 1.0  # top-left with origin="upper"
    ax.imshow(z, vmin=0, vmax=1)
    cogra.restyle(fig)
    ((x, y),) = ax.collections[0].get_offsets()
    assert (x, y) == pytest.approx((0, 0))  # row 0, column 0 in data coordinates


def test_masked_image_cells_get_no_dots():
    fig, ax = plt.subplots()
    z = np.ma.masked_array(np.ones((2, 2)), mask=[[1, 0], [0, 0]])
    ax.imshow(z, vmin=0, vmax=1)
    cogra.restyle(fig)
    assert len(ax.collections[0].get_offsets()) == 3


def test_pcolormesh_becomes_halftone(rng):
    fig, ax = plt.subplots()
    ax.pcolormesh(rng.random((3, 5)))
    cogra.restyle(fig)
    dots = [c for c in ax.collections if isinstance(c, HalftoneCollection)]
    assert len(dots) == 1
    fig.canvas.draw()


def test_filled_contours_become_hatching():
    fig, ax = plt.subplots()
    X, Y = np.meshgrid(np.linspace(-2, 2, 40), np.linspace(-2, 2, 40))
    cs = ax.contourf(X, Y, np.exp(-(X**2) - Y**2), levels=5)
    cogra.restyle(fig)
    assert cs.hatches[0] == "" and len(set(cs.hatches)) == len(cs.hatches)
    fig.canvas.draw()


def test_translucent_band_becomes_stipple(rng):
    fig, ax = plt.subplots()
    x = np.arange(10)
    ax.plot(x, x, color="tab:red")
    band = ax.fill_between(x, x - 1, x + 1, color="tab:red", alpha=0.2)
    cogra.restyle(fig)
    assert band.get_hatch() == "...."
    fc = band.get_facecolor()
    assert len(fc) == 0 or fc[0][3] == 0


def test_existing_halftones_left_alone(rng):
    fig, ax = plt.subplots()
    coll = cogra.halftone(ax, [0, 1], [0, 0], [1, 2], 1, 1)
    cogra.restyle(fig)
    assert coll in ax.collections


def test_figure_legends_all_restyled(rng):
    fig, (a, b) = plt.subplots(1, 2)
    (l1,) = a.plot([0, 1], color="tab:blue")
    (l2,) = b.plot([0, 1], color="tab:orange")
    fig.legend([l1], ["one"], loc="upper left")
    fig.legend([l2], ["two"], loc="upper right")
    cogra.restyle(fig)
    styles = [leg.legend_handles[0].get_linestyle() for leg in fig.legends]
    assert styles == ["-", "--"]


def test_seaborn_figure_restyles():
    sns = pytest.importorskip("seaborn")
    pd = pytest.importorskip("pandas")
    rng = np.random.default_rng(3)
    df = pd.DataFrame(
        {"load": np.tile([2, 4, 6], 40), "cond": np.repeat(["f", "c"], 60), "rt": rng.normal(500, 50, 120)}
    )
    fig, axs = plt.subplots(1, 3)
    pal = "deep"  # after cogra.use() seaborn's default palette is the all-black prop cycle
    sns.lineplot(df, x="load", y="rt", hue="cond", marker="o", palette=pal, ax=axs[0])
    sns.barplot(df, x="load", y="rt", hue="cond", palette=pal, ax=axs[1])
    sns.kdeplot(df, x="rt", hue="cond", fill=True, palette=pal, ax=axs[2])
    cogra.restyle(fig)
    assert len(fig.cogra_report["groups"]) == 2
    fig.canvas.draw()


def test_seaborn_error_bars_stay_plain_rules():
    """seaborn draws error bars and violin boxes with ax.plot. Under the cogra
    style those lines pick up the cycle's markers and dashes; restyle must
    turn them back into plain solid rules, but leave axhline styles alone."""
    sns = pytest.importorskip("seaborn")
    pd = pytest.importorskip("pandas")
    rng = np.random.default_rng(4)
    df = pd.DataFrame(
        {"x": np.tile(["1", "2", "3"], 40), "cond": np.repeat(["f", "c"], 60), "y": rng.normal(250, 30, 120)}
    )
    cogra.use()  # the style is active at draw time, as after an earlier restyle
    fig, (a, b) = plt.subplots(1, 2)
    sns.barplot(df, x="x", y="y", hue="cond", palette="deep", capsize=0.2, ax=a)
    sns.violinplot(df, x="cond", y="y", hue="cond", palette="deep", inner="box", ax=b)
    a.axhline(200, linestyle="--")
    cogra.restyle(fig)
    # one-point lines are seaborn's median ticks, drawn on purpose with a "_" marker
    rules = [
        ln for ln in a.lines + b.lines if ln.get_transform() == ln.axes.transData and len(ln.get_xdata()) > 1
    ]
    assert len(rules) == 10  # 6 error bars with caps, 4 violin whiskers/boxes
    for ln in rules:
        assert ln.get_marker() in ("", "None", "none", None)
        assert ln.get_linestyle() == "-"
        assert ln.get_color() == "black"
    ref = [ln for ln in a.lines if ln.get_transform() != a.transData]
    assert [ln.get_linestyle() for ln in ref] == ["--"]


def test_restyled_hatching_is_black():
    """A band drawn in colour comes out with black stipple, not coloured
    stipple (matplotlib >= 3.10 keeps the hatch colour separately)."""
    fig, ax = plt.subplots()
    x = np.arange(5)
    ax.fill_between(x, x, x + 1, color="tab:orange", alpha=0.3)
    ax.bar([0, 1], [1, 2], color=["tab:blue", "tab:green"])
    cogra.restyle(fig)
    from matplotlib.colors import to_rgba

    for artist in [ax.collections[0], *ax.patches]:
        if artist.get_hatch() and hasattr(artist, "get_hatchcolor"):
            hc = artist.get_hatchcolor()
            hc = hc[0] if np.ndim(hc) > 1 else hc
            assert tuple(np.round(to_rgba(hc), 3)) == (0, 0, 0, 1)
