import matplotlib.pyplot as plt
import numpy as np
import pytest

import cogra


def _bars(heights=(240, 280), yerr=12):
    fig, ax = plt.subplots()
    cogra.bars(ax, range(len(heights)), list(heights), yerr=[yerr] * len(heights))
    return fig, ax


def _bracket_y(line):
    return max(line.get_ydata())


@pytest.mark.parametrize(
    "p, mark",
    [(0.0004, "***"), (0.001, "**"), (0.009, "**"), (0.01, "*"), (0.049, "*"), (0.05, ""), (0.4, "")],
)
def test_stars(p, mark):
    assert cogra.stars(p) == mark


@pytest.mark.parametrize("p, text", [(0.0004, r"$p$ < .001"), (0.0123, r"$p$ = .012"), (0.5, r"$p$ = .500")])
def test_format_p(p, text):
    assert cogra.format_p(p) == text


def test_label_options():
    _fig, ax = _bars()
    assert cogra.signif(ax, 0, 1, p=0.003)[1].get_text() == "**"
    assert cogra.signif(ax, 0, 1, p=0.003, show="p")[1].get_text() == r"$p$ = .003"
    assert cogra.signif(ax, 0, 1, text="d = 0.54")[1].get_text() == "d = 0.54"


def test_not_significant_draws_nothing_unless_asked():
    _fig, ax = _bars()
    n = len(ax.artists)
    assert cogra.signif(ax, 0, 1, p=0.3) is None
    assert len(ax.artists) == n and not ax.texts
    assert cogra.signif(ax, 0, 1, p=0.3, ns=True)[1].get_text() == "n.s."


def test_bracket_clears_bars_and_error_bars():
    _fig, ax = _bars((240, 280), yerr=12)
    line, _ = cogra.signif(ax, 0, 1, p=0.01)
    assert min(line.get_ydata()) > 280 + 12


def test_bracket_clears_bars_in_between():
    _fig, ax = _bars((240, 400, 250), yerr=10)
    line, _ = cogra.signif(ax, 0, 2, p=0.01)
    assert min(line.get_ydata()) > 410


def test_brackets_stack():
    fig, ax = _bars((240, 280, 260), yerr=10)
    inner, t1 = cogra.signif(ax, 0, 1, p=0.01)
    side, t2 = cogra.signif(ax, 1.6, 2.4, p=0.01)  # does not overlap the first: not raised by it
    assert _bracket_y(side) < _bracket_y(inner)
    outer, _ = cogra.signif(ax, 0, 2, p=0.001)  # overlaps both: goes above both labels
    fig.canvas.draw()
    to_data = ax.transData.inverted()
    for t in (t1, t2):
        assert min(outer.get_ydata()) > to_data.transform(t.get_window_extent().get_points())[1, 1]


def test_x_limits_unchanged_and_label_fits():
    fig, ax = _bars((240, 280), yerr=12)
    ax.set_ylim(0, 295)
    xlim = ax.get_xlim()
    _, label = cogra.signif(ax, 0, 1, p=0.0001)
    assert ax.get_xlim() == xlim
    fig.canvas.draw()
    top = ax.transData.inverted().transform(label.get_window_extent().get_points())[1, 1]
    assert ax.get_ylim()[1] >= top


def test_plain_rule_under_the_style_and_after_restyle():
    cogra.use()  # the style's prop cycle would add markers to ax.plot
    fig, ax = plt.subplots()
    ax.bar([0, 1], [240, 280], color=["tab:blue", "tab:orange"])
    line, label = cogra.signif(ax, 0, 1, p=0.01)
    assert line.get_marker() in ("none", "None", "", None) and line.get_linestyle() == "-"
    cogra.restyle(fig)
    assert line.get_marker() in ("none", "None", "", None) and line.get_linestyle() == "-"
    assert label.get_color() == "black"


def test_seaborn_dodged_bars():
    sns = pytest.importorskip("seaborn")
    pd = pytest.importorskip("pandas")
    rng = np.random.default_rng(5)
    df = pd.DataFrame(
        {"x": np.tile(["1", "2"], 40), "cond": np.repeat(["f", "c"], 40), "y": rng.normal(250, 30, 80)}
    )
    _fig, ax = plt.subplots()
    sns.barplot(df, x="x", y="y", hue="cond", palette="deep", ax=ax)
    ci_top = max(
        np.nanmax(ln.get_ydata()) for ln in ax.lines if abs(np.nanmean(ln.get_xdata())) <= 0.25
    )  # the two bars at x = -0.2, 0.2
    line, _ = cogra.signif(ax, -0.2, 0.2, p=0.02)
    assert min(line.get_ydata()) > ci_top


@pytest.mark.parametrize("kw", [dict(p=1.5), dict(), dict(p=0.01, show="exact")])
def test_bad_arguments(kw):
    _fig, ax = _bars()
    with pytest.raises(ValueError):
        cogra.signif(ax, 0, 1, **kw)


def test_same_x_raises():
    _fig, ax = _bars()
    with pytest.raises(ValueError):
        cogra.signif(ax, 1, 1, p=0.01)


def test_demo_example_runs():
    """examples/demo_signif.py draws the README picture: three brackets per panel."""
    pytest.importorskip("seaborn")
    pytest.importorskip("scipy")
    from conftest import load_example

    fig = load_example("demo_signif").make_figure()
    a, b = fig.axes[:2]
    assert [t.get_text() for t in a.texts] == ["*", "n.s.", r"$p$ < .001"]
    assert len(b.texts) == 3 and all(t.get_text() in ("*", "**", "***", "n.s.") for t in b.texts)
