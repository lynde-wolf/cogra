"""Render every geom in cogra_geoms on one sheet, clean and worn.
All data are synthetic. Run: python gallery.py"""

import matplotlib.pyplot as plt
import numpy as np

import cogra
from cogra import geoms as g

cogra.use()
rng = np.random.default_rng(7)
x = rng.normal(0, 1, 150)
y = 0.6 * x + rng.normal(0, 0.8, 150)
grp = np.where(rng.random(150) < 0.5, "a", "b")
xs = np.linspace(0, 10, 25)
ys = np.sin(xs) + 1.5
X, Y = np.meshgrid(np.linspace(-2, 2, 80), np.linspace(-2, 2, 80))
Z = np.exp(-(X**2 + Y**2)) - 0.6 * np.exp(-((X - 1) ** 2 + (Y + 0.8) ** 2) / 0.4)


def map_regions(nx=5, ny=4, seed=3):
    """Non-overlapping synthetic regions: cells of a jittered grid."""
    r = np.random.default_rng(seed)
    gx, gy = np.meshgrid(np.linspace(0, 1, nx + 1), np.linspace(0, 0.8, ny + 1))
    inner = (gx > 0) & (gx < 1) & (gy > 0) & (gy < 0.8)
    gx = gx + inner * r.uniform(-0.06, 0.06, gx.shape)
    gy = gy + inner * r.uniform(-0.05, 0.05, gy.shape)
    return [
        np.array(
            [
                [gx[j, i], gy[j, i]],
                [gx[j, i + 1], gy[j, i + 1]],
                [gx[j + 1, i + 1], gy[j + 1, i + 1]],
                [gx[j + 1, i], gy[j + 1, i]],
            ]
        )
        for j in range(ny)
        for i in range(nx)
    ]


polys = map_regions()

panels = {
    "point": lambda a: g.geom_point(a, x, y, grp, size=3),
    "jitter": lambda a: g.geom_jitter(a, rng.integers(0, 3, 90), rng.normal(0, 1, 90), size=3),
    "count": lambda a: g.geom_count(a, rng.integers(0, 5, 120), rng.integers(0, 5, 120)),
    "line": lambda a: (g.geom_line(a, xs, ys, markers=True), g.geom_line(a, xs, ys * 0.6, markers=False)),
    "path": lambda a: g.geom_path(
        a,
        np.cos(np.linspace(0, 6, 60)) * np.linspace(1, 0.2, 60),
        np.sin(np.linspace(0, 6, 60)) * np.linspace(1, 0.2, 60),
    ),
    "step": lambda a: g.geom_step(a, xs, np.cumsum(rng.random(25))),
    "abline": lambda a: (g.geom_point(a, x, y, size=2.5), g.geom_abline(a, 0, 0.6)),
    "hline/vline": lambda a: (
        g.geom_point(a, x, y, size=2.5),
        g.geom_hline(a, 0),
        g.geom_vline(a, 0, linestyle="--"),
    ),
    "segment": lambda a: g.geom_segment(
        a, rng.random(8), rng.random(8), rng.random(8), rng.random(8), arrow=True
    ),
    "curve": lambda a: g.geom_curve(a, [0, 0.2, 0.5], [0, 0.8, 0.1], [1, 0.9, 0.6], [0.6, 0.2, 1]),
    "spoke": lambda a: g.geom_spoke(
        a, np.tile(np.arange(6), 5), np.repeat(np.arange(5), 6), rng.uniform(0, 2 * np.pi, 30), 0.45
    ),
    "function": lambda a: (a.set_xlim(-3, 3), g.geom_function(a, lambda t: np.exp(-(t**2) / 2), (-3, 3))),
    "rug": lambda a: (g.geom_point(a, x, y, size=2.5), g.geom_rug(a, x, y)),
    "area": lambda a: g.geom_area(a, np.r_[xs, xs], np.r_[ys, ys * 0.5 + 0.3], np.r_[["a"] * 25, ["b"] * 25]),
    "ribbon": lambda a: (g.geom_ribbon(a, xs, ys - 0.4, ys + 0.4), g.geom_line(a, xs, ys)),
    "rect": lambda a: g.geom_rect(
        a, [0, 1.2, 2.4], [1, 2.2, 3.4], [0, 0.5, 0.2], [1, 2, 1.4], ["a", "b", "c"]
    ),
    "polygon": lambda a: g.geom_polygon(a, polys[:6], ["a", "b", "c", "a", "b", "c"]),
    "col": lambda a: g.geom_col(a, ["F", "C", "F", "C"], [4, 6, 3, 5], ["vis", "vis", "aud", "aud"]),
    "bar": lambda a: g.geom_bar(a, rng.choice(["x", "y", "z"], 80)),
    "histogram": lambda a: g.geom_histogram(a, x, bins=18),
    "histogram (grouped)": lambda a: g.geom_histogram(a, x, grp, bins=18),
    "freqpoly": lambda a: g.geom_freqpoly(a, x, grp, bins=15),
    "density": lambda a: g.geom_density(a, x, grp, hatch=True),
    "dotplot": lambda a: g.geom_dotplot(a, rng.normal(0, 1, 60), binwidth=0.25),
    "boxplot": lambda a: g.geom_boxplot(a, [rng.normal(0, 1, 80), rng.normal(0.8, 1.3, 80)]),
    "violin": lambda a: g.geom_violin(a, [rng.normal(0, 1, 80), rng.normal(0.8, 1.3, 80)]),
    "errorbar": lambda a: (
        g.geom_point(a, [0, 1, 2], [2, 3, 2.5]),
        g.geom_errorbar(a, [0, 1, 2], [1.6, 2.5, 2.2], [2.4, 3.5, 2.8]),
    ),
    "errorbar (orientation='y')": lambda a: (
        g.geom_point(a, [2, 3, 2.5], [0, 1, 2]),
        g.geom_errorbar(a, [0, 1, 2], [1.6, 2.5, 2.2], [2.4, 3.5, 2.8], orientation="y"),
    ),
    "linerange": lambda a: g.geom_linerange(a, [0, 1, 2, 3], [1, 2, 1.5, 2.2], [2, 3.2, 2.5, 3]),
    "pointrange": lambda a: g.geom_pointrange(
        a, [0, 1, 2, 3], [1.5, 2.6, 2, 2.6], [1, 2, 1.5, 2.2], [2, 3.2, 2.5, 3]
    ),
    "crossbar": lambda a: g.geom_crossbar(a, [0, 1, 2], [1.5, 2.6, 2], [1, 2, 1.5], [2, 3.2, 2.5]),
    "smooth (lm)": lambda a: (g.geom_point(a, x, y, size=2.5), g.geom_smooth(a, x, y, method="lm")),
    "smooth (loess)": lambda a: (
        g.geom_point(a, x, y, size=2.5),
        g.geom_smooth(a, x, np.sin(x * 1.5) + rng.normal(0, 0.4, 150), method="loess", se=False),
    ),
    "quantile": lambda a: (g.geom_point(a, x, y, size=2.5), g.geom_quantile(a, x, y)),
    "qq + qq_line": lambda a: (g.geom_qq(a, rng.standard_t(4, 80)), g.geom_qq_line(a, rng.standard_t(4, 80))),
    "density_2d": lambda a: (g.geom_point(a, x, y, size=2), g.geom_density_2d(a, x, y)),
    "density_2d_filled": lambda a: g.geom_density_2d_filled(a, x, y),
    "contour": lambda a: g.geom_contour(a, X, Y, Z),
    "contour_filled": lambda a: g.geom_contour_filled(a, X, Y, Z),
    "bin_2d": lambda a: g.geom_bin_2d(a, x, y, bins=14),
    "hex": lambda a: g.geom_hex(a, x, y, gridsize=12),
    "tile": lambda a: g.geom_tile(a, np.tile(np.arange(6), 5), np.repeat(np.arange(5), 6), rng.random(30)),
    "raster": lambda a: g.geom_raster(a, Z[::5, ::5]),
    "text": lambda a: (
        a.set_xlim(-0.5, 3.5),
        a.set_ylim(-0.5, 2.5),
        g.geom_text(a, [0, 1, 2, 3], [0, 2, 1, 2], ["go", "stop", "probe", "cue"]),
    ),
    "label": lambda a: (
        a.set_xlim(-0.5, 3.5),
        a.set_ylim(-0.5, 2.5),
        g.geom_label(a, [0, 1, 2, 3], [0, 2, 1, 2], ["go", "stop", "probe", "cue"]),
    ),
    "map": lambda a: g.geom_map(a, polys, rng.random(len(polys))),
    "sf + sf_label": lambda a: (
        g.geom_sf(a, polys, rng.random(len(polys))),
        g.geom_sf_label(a, polys[:4], ["A", "B", "C", "D"]),
    ),
    "sf + sf_text": lambda a: (g.geom_sf(a, polys), g.geom_sf_text(a, polys[:6], list("abcdef"))),
    "blank": lambda a: g.geom_blank(a),
}


def render(path_clean, path_worn):
    n = len(panels)
    cols = 6
    rows = int(np.ceil(n / cols))
    fig, axs = plt.subplots(rows, cols, figsize=(cols * 2.1, rows * 1.95))
    for ax, (name, f) in zip(axs.ravel(), panels.items()):
        f(ax)
        ax.set_title("geom_" + name, fontsize=7.5, pad=3)
        ax.tick_params(labelsize=6)
    for ax in axs.ravel()[n:]:
        ax.axis("off")
    fig.tight_layout(h_pad=1.2, w_pad=0.6)
    fig.savefig(path_clean, dpi=150)
    cogra.save_vintage(fig, path_worn, look="scan", dpi=450, scan_dpi=200)
    plt.close(fig)
    return n


if __name__ == "__main__":
    print(render("gallery-clean.png", "gallery-scan.png"), "panels")
