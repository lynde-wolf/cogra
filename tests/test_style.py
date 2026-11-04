import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib import font_manager

import cogra


def test_fonts_registered_once():
    cogra.use()
    n = len(font_manager.fontManager.ttflist)
    cogra.use()
    cogra.use(labels="serif")
    cogra.restyle(plt.subplots()[0])
    assert len(font_manager.fontManager.ttflist) == n


def test_packaged_fonts_resolve():
    cogra.use()
    for family in ("TeX Gyre Heros", "TeX Gyre Schola"):
        path = font_manager.findfont(font_manager.FontProperties(family=family), fallback_to_default=False)
        assert "texgyre" in path.lower()


def test_use_sets_period_style():
    cogra.use()
    assert mpl.rcParams["axes.spines.top"] is False
    assert mpl.rcParams["xtick.direction"] == "in"
    assert mpl.rcParams["pdf.fonttype"] == 42
    assert mpl.rcParams["font.family"] == ["sans-serif"]
    cogra.use(labels="serif")
    assert mpl.rcParams["font.family"] == ["serif"]
    cogra.use(labels="sans")  # switching back resets the serif settings
    assert mpl.rcParams["mathtext.rm"] == "TeX Gyre Heros"


def test_use_rejects_unknown_labels():
    with pytest.raises(ValueError):
        cogra.use(labels="script")


def test_bars_are_white_hatched_and_outlined():
    cogra.use()
    bars = cogra.bars(plt.subplots()[1], [0, 1, 2], [1, 2, 3], yerr=[0.1, 0.2, 0.1])
    assert [b.get_hatch() for b in bars] == cogra.HATCHES[:3]
    assert all(b.get_facecolor()[:3] == (1, 1, 1) and b.get_edgecolor()[:3] == (0, 0, 0) for b in bars)


def test_violin_constant_and_short_data_do_not_crash():
    cogra.use()
    ax = plt.subplots()[1]
    cogra.violin(ax, [np.ones(10), [3.0], np.random.default_rng(0).normal(size=50)])
    assert len(ax.collections) == 1  # only the real distribution gets a body
    assert any(np.allclose(l.get_ydata(), 1.0) for l in ax.lines)


def test_raincloud_draws_cloud_box_and_rain():
    cogra.use()
    ax = plt.subplots()[1]
    d = [np.random.default_rng(1).normal(size=40), np.random.default_rng(2).normal(1, 1, 40)]
    cogra.raincloud(ax, d)
    assert len(ax.collections) == 2 and len(ax.patches) == 2
    rain = [l for l in ax.lines if l.get_marker() == "o"]
    assert [len(l.get_ydata()) for l in rain] == [40, 40]


def test_topoplot_signs_and_flat_map(rng):
    cogra.use()
    xy = rng.uniform(-0.7, 0.7, (20, 2))
    vals = 3 * xy[:, 0]  # positive right, negative left
    cs = cogra.topoplot(plt.subplots()[1], xy, vals)
    assert min(cs.levels) < 0 < max(cs.levels) and 0 not in cs.levels
    assert cogra.topoplot(plt.subplots()[1], xy, np.zeros(20)) is None


def test_density_topo_levels_enclose_mass(rng):
    cogra.use()
    x, y = rng.normal(size=(2, 600))
    cs = cogra.density_topo(plt.subplots()[1], x, y, res=120)
    assert np.all(np.diff(cs.levels) > 0)
    assert len(cs.levels) == 9  # 10% ... 90%


def test_density_topo_duplicate_thresholds_are_merged(rng):
    cogra.use()
    x, y = rng.normal(size=(2, 200))
    cs = cogra.density_topo(plt.subplots()[1], x, y, masses=np.linspace(0.1, 0.9, 80), res=20)
    assert np.all(np.diff(cs.levels) > 0)


def test_named_styles_registered_on_import():
    for name in ("cogra", "cogra-serif", "cogra-column", "cogra-page"):
        assert name in plt.style.available


def test_named_styles_stack():
    plt.style.use(["cogra", "cogra-serif", "cogra-column"])
    assert mpl.rcParams["xtick.direction"] == "in"
    assert mpl.rcParams["font.family"] == ["serif"]
    assert list(mpl.rcParams["figure.figsize"]) == [2.65, 2.0]
    assert mpl.rcParams["font.size"] == 8
    with plt.style.context("cogra-page"):
        assert list(mpl.rcParams["figure.figsize"]) == [5.46, 3.0]
    assert list(mpl.rcParams["figure.figsize"]) == [2.65, 2.0]


def test_size_presets_match_the_paper_layout():
    """cogra-column and cogra-page are one column and the full measure of
    the default cogra.paper page (191 pt and 393 pt)."""
    cogra.use(size="column")
    assert mpl.rcParams["figure.figsize"][0] * 72 == pytest.approx(191, abs=0.5)
    cogra.use(size="page")
    assert mpl.rcParams["figure.figsize"][0] * 72 == pytest.approx(393, abs=0.5)
    with pytest.raises(ValueError):
        cogra.use(size="poster")


def test_use_matches_named_style():
    cogra.use(labels="serif", size="column")
    via_use = {k: mpl.rcParams[k] for k in ("font.family", "figure.figsize", "font.size", "axes.prop_cycle")}
    mpl.rcdefaults()
    plt.style.use(["cogra", "cogra-serif", "cogra-column"])
    assert via_use == {k: mpl.rcParams[k] for k in via_use}


def test_import_needs_no_seaborn_or_pandas():
    """The base install is numpy, SciPy, matplotlib and Pillow: importing cogra
    must not pull in the plotting libraries that only the tests use."""
    import subprocess
    import sys

    code = "import sys, cogra; print(sorted(m for m in ('seaborn', 'pandas') if m in sys.modules))"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "[]"
