"""
geoms: one function per ggplot2 geom, drawn on a matplotlib
Axes in the cogra style (black ink, white paper, no colour).

Naming follows ggplot2 so the vocabulary carries over:

    import cogra
    from cogra import geoms as g
    cogra.use()
    fig, ax = plt.subplots()
    g.geom_point(ax, x, y, group=cond)
    g.geom_smooth(ax, x, y, method="lm")

Period conventions applied throughout:
  * groups are told apart by marker shape, line style and hatching, never colour
  * fills are white with black outlines; filled areas are hatched
  * continuous fills (tile, raster, bin_2d, hex) are drawn as halftone dots,
    because a 1-bit scan turns grey fills into solid white or black
  * filled contours use hatching that gets denser with the level

GEOMS maps every geom exported by ggplot2 (checked against its NAMESPACE)
to the function here, so the coverage test can confirm nothing is missing.
"""

import numpy as np
from matplotlib.collections import LineCollection, PatchCollection
from matplotlib.patches import Circle, FancyArrowPatch, Polygon, Rectangle
from scipy import sparse

from .halftone import halftone

MARKERS = [("o", "white"), ("o", "black"), ("s", "white"), ("^", "black"), ("D", "white"), ("v", "black")]
LINESTYLES = ["-", "--", ":", "-.", (0, (5, 1, 1, 1, 1, 1))]
HATCHES = ["", "////", "....", "xxxx", "\\\\\\\\", "++++"]
INK = "black"


# ---------- helpers ----------


def _groups(x, group):
    """Yield (index, label, mask). One group if group is None."""
    if group is None:
        yield 0, None, np.ones(len(x), bool)
        return
    group = np.asarray(group)
    for i, lab in enumerate(dict.fromkeys(group)):
        yield i, lab, group == lab


def _marker(i):
    m, face = MARKERS[i % len(MARKERS)]
    return dict(marker=m, markerfacecolor=face, markeredgecolor=INK, markeredgewidth=0.9, color=INK)


def _line(i):
    return dict(color=INK, linestyle=LINESTYLES[i % len(LINESTYLES)], marker="none")


def _hatch(i):
    return HATCHES[i % len(HATCHES)]


def _halftone(ax, cx, cy, values, cell_w, cell_h, vmin=None, vmax=None, shape="circle", **kw):
    """Dots whose area is proportional to value, as in a printed halftone
    (sized at draw time, so they stay round on any aspect)."""
    return halftone(ax, cx, cy, values, cell_w, cell_h, vmin, vmax, shape, **kw)


def _level_hatches(n):
    """Hatching that gets denser with level index (0 = lightest)."""
    seq = ["", "/", "//", "///", "////", "xx", "xxx", "xxxx", "XXXX"]
    if n <= len(seq):
        idx = np.round(np.linspace(0, len(seq) - 1, n)).astype(int)
        return [seq[i] for i in idx]
    return [seq[min(i, len(seq) - 1)] for i in range(n)]


def _kde1(x, grid, bw=None):
    from scipy.stats import gaussian_kde

    return gaussian_kde(np.asarray(x, float), bw_method=bw)(grid)


def _kde2(x, y, res=150, pad=0.15, bw=None):
    from scipy.stats import gaussian_kde

    x = np.asarray(x, float)
    y = np.asarray(y, float)
    k = gaussian_kde(np.vstack([x, y]), bw_method=bw)
    gx = np.linspace(x.min() - pad * np.ptp(x), x.max() + pad * np.ptp(x), res)
    gy = np.linspace(y.min() - pad * np.ptp(y), y.max() + pad * np.ptp(y), res)
    X, Y = np.meshgrid(gx, gy)
    return X, Y, k(np.vstack([X.ravel(), Y.ravel()])).reshape(X.shape)


# ---------- points and lines ----------


def geom_point(ax, x, y, group=None, size=5, **kw):
    out = []
    for i, lab, m in _groups(x, group):
        out += ax.plot(
            np.asarray(x)[m],
            np.asarray(y)[m],
            linestyle="none",
            markersize=size,
            label=lab,
            **{**_marker(i), **kw},
        )
    return out


def geom_jitter(ax, x, y, group=None, width=0.15, height=0.0, seed=0, size=4, **kw):
    rng = np.random.default_rng(seed)
    x = np.asarray(x, float) + rng.uniform(-width, width, len(x))
    y = np.asarray(y, float) + rng.uniform(-height, height, len(y))
    return geom_point(ax, x, y, group, size=size, **kw)


def geom_count(ax, x, y, max_size=12, **kw):
    """Open circles sized by the number of overlapping observations."""
    pts, n = np.unique(np.column_stack([x, y]), axis=0, return_counts=True)
    s = (np.sqrt(n / n.max()) * max_size) ** 2
    return ax.scatter(pts[:, 0], pts[:, 1], s=s, facecolors="white", edgecolors=INK, linewidths=0.9, **kw)


def geom_line(ax, x, y, group=None, markers=False, **kw):
    out = []
    for i, lab, m in _groups(x, group):
        xs = np.asarray(x)[m]
        o = np.argsort(xs)
        style = {**_line(i), **(_marker(i) if markers else {})}
        if markers:
            style["linestyle"] = LINESTYLES[i % len(LINESTYLES)]
        out += ax.plot(xs[o], np.asarray(y)[m][o], label=lab, **{**style, **kw})
    return out


def geom_path(ax, x, y, group=None, **kw):
    """Like geom_line but joins points in data order."""
    out = []
    for i, lab, m in _groups(x, group):
        out += ax.plot(np.asarray(x)[m], np.asarray(y)[m], label=lab, **{**_line(i), **kw})
    return out


def geom_step(ax, x, y, group=None, where="post", **kw):
    out = []
    for i, lab, m in _groups(x, group):
        xs = np.asarray(x)[m]
        o = np.argsort(xs)
        out += ax.step(xs[o], np.asarray(y)[m][o], where=where, label=lab, **{**_line(i), **kw})
    return out


def geom_abline(ax, intercept=0, slope=1, **kw):
    return ax.axline((0, intercept), slope=slope, **{**_line(0), "linewidth": 0.8, **kw})


def geom_hline(ax, yintercept, **kw):
    return [ax.axhline(v, **{**_line(0), "linewidth": 0.8, **kw}) for v in np.atleast_1d(yintercept)]


def geom_vline(ax, xintercept, **kw):
    return [ax.axvline(v, **{**_line(0), "linewidth": 0.8, **kw}) for v in np.atleast_1d(xintercept)]


def geom_segment(ax, x, y, xend, yend, arrow=False, **kw):
    if arrow:
        props = dict(arrowstyle="-|>", color=INK, lw=kw.pop("linewidth", 0.9), shrinkA=0, shrinkB=0)
        return [
            ax.annotate("", (xe, ye), (xs, ys), arrowprops=props, **kw)
            for xs, ys, xe, ye in zip(x, y, xend, yend)
        ]
    segs = [[(a, b), (c, d)] for a, b, c, d in zip(x, y, xend, yend)]
    lc = LineCollection(segs, colors=INK, linewidths=kw.pop("linewidth", 0.9), **kw)
    ax.add_collection(lc)
    ax.autoscale_view()
    return lc


def geom_curve(ax, x, y, xend, yend, curvature=0.3, arrow=True, **kw):
    out = []
    for xs, ys, xe, ye in zip(x, y, xend, yend):
        p = FancyArrowPatch(
            (xs, ys),
            (xe, ye),
            connectionstyle=f"arc3,rad={curvature}",
            arrowstyle="-|>" if arrow else "-",
            mutation_scale=9,
            color=INK,
            linewidth=0.9,
            **kw,
        )
        ax.add_patch(p)
        out.append(p)
    ax.update_datalim(np.column_stack([np.r_[x, xend], np.r_[y, yend]]))
    ax.autoscale_view()
    return out


def geom_spoke(ax, x, y, angle, radius, **kw):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    return geom_segment(ax, x, y, x + radius * np.cos(angle), y + radius * np.sin(angle), **kw)


def geom_function(ax, fun, xlim=None, n=200, **kw):
    lo, hi = xlim or ax.get_xlim()
    xs = np.linspace(lo, hi, n)
    return ax.plot(xs, fun(xs), **{**_line(0), **kw})


def geom_rug(ax, x=None, y=None, length=0.03, **kw):
    out = []
    if x is not None:
        out.append(
            ax.vlines(x, 0, length, transform=ax.get_xaxis_transform(), colors=INK, linewidths=0.6, **kw)
        )
    if y is not None:
        out.append(
            ax.hlines(y, 0, length, transform=ax.get_yaxis_transform(), colors=INK, linewidths=0.6, **kw)
        )
    return out


# ---------- areas and shapes ----------


def geom_area(ax, x, y, group=None, stacked=True, **kw):
    """Hatched areas; stacked by default, as in ggplot2."""
    out, base = [], None
    for i, lab, m in _groups(x, group):
        xs = np.asarray(x, float)[m]
        o = np.argsort(xs)
        xs = xs[o]
        ys = np.asarray(y, float)[m][o]
        lo = np.zeros_like(ys) if (base is None or not stacked) else np.interp(xs, *base)
        hi = lo + ys
        out.append(
            ax.fill_between(
                xs,
                lo,
                hi,
                facecolor="white",
                edgecolor=INK,
                hatch=_hatch(i + 1),
                linewidth=0.9,
                label=lab,
                **kw,
            )
        )
        base = (xs, hi)
    return out


def geom_ribbon(ax, x, ymin, ymax, hatch="....", outline=True, **kw):
    o = np.argsort(x)
    x = np.asarray(x)[o]
    lo = np.asarray(ymin)[o]
    hi = np.asarray(ymax)[o]
    out = ax.fill_between(x, lo, hi, facecolor="white", edgecolor="none", hatch=hatch, linewidth=0, **kw)
    if outline:
        ax.plot(x, lo, color=INK, linewidth=0.6, linestyle="--", marker="none")
        ax.plot(x, hi, color=INK, linewidth=0.6, linestyle="--", marker="none")
    return out


def geom_rect(ax, xmin, xmax, ymin, ymax, group=None, **kw):
    out = []
    for i, _lab, m in _groups(xmin, group):
        for a, b, c, d in zip(
            np.asarray(xmin)[m], np.asarray(xmax)[m], np.asarray(ymin)[m], np.asarray(ymax)[m]
        ):
            r = Rectangle(
                (a, c), b - a, d - c, facecolor="white", edgecolor=INK, hatch=_hatch(i), linewidth=0.9, **kw
            )
            ax.add_patch(r)
            out.append(r)
    ax.update_datalim([(np.min(xmin), np.min(ymin)), (np.max(xmax), np.max(ymax))])
    ax.autoscale_view()
    return out


def geom_polygon(ax, polygons, group=None, **kw):
    """polygons: list of (n, 2) arrays."""
    out = []
    labs = [None] * len(polygons) if group is None else list(group)
    order = list(dict.fromkeys(labs))
    for poly, lab in zip(polygons, labs):
        p = Polygon(
            poly,
            closed=True,
            facecolor="white",
            edgecolor=INK,
            hatch=_hatch(order.index(lab)),
            linewidth=0.9,
            **kw,
        )
        ax.add_patch(p)
        out.append(p)
    ax.update_datalim(np.vstack(polygons))
    ax.autoscale_view()
    return out


# ---------- bars and distributions ----------


def geom_col(ax, x, height, group=None, width=0.7, dodge=True, **kw):
    """Bars of given height. With groups, bars are dodged side by side."""
    x = np.asarray(x)
    height = np.asarray(height, float)
    cats = list(dict.fromkeys(x))
    gl = [None] if group is None else list(dict.fromkeys(group))
    w = width / len(gl) if dodge else width
    out = []
    for i, lab, m in _groups(x, group):
        pos = np.array([cats.index(v) for v in x[m]], float)
        if dodge and len(gl) > 1:
            pos = pos - width / 2 + w * (i + 0.5)
        out.append(
            ax.bar(
                pos,
                height[m],
                width=w,
                facecolor="white",
                edgecolor=INK,
                hatch=_hatch(i),
                linewidth=0.9,
                label=lab,
                **kw,
            )
        )
    ax.set_xticks(range(len(cats)), [str(c) for c in cats])
    return out


def geom_bar(ax, x, group=None, **kw):
    """Counts of each category, like geom_bar(stat='count')."""
    x = np.asarray(x)
    if group is None:
        cats, n = np.unique(x, return_counts=True)
        return geom_col(ax, cats, n, **kw)
    group = np.asarray(group)
    cats = list(dict.fromkeys(x))
    gl = list(dict.fromkeys(group))
    cx, ch, cg = [], [], []
    for gv in gl:
        for c in cats:
            cx.append(c)
            cg.append(gv)
            ch.append(np.sum((x == c) & (group == gv)))
    return geom_col(ax, np.array(cx), np.array(ch), np.array(cg), **kw)


def geom_histogram(ax, x, group=None, bins=30, **kw):
    """Outlined bars; overlapping groups are drawn as step outlines with hatching."""
    out = []
    edges = np.histogram_bin_edges(np.asarray(x, float), bins=bins)
    for i, lab, m in _groups(x, group):
        out.append(
            ax.hist(
                np.asarray(x, float)[m],
                bins=edges,
                histtype="bar" if group is None else "step",
                facecolor="white" if group is None else "none",
                edgecolor=INK,
                hatch=_hatch(i) if group is not None else "",
                linewidth=0.9,
                linestyle=LINESTYLES[i % len(LINESTYLES)] if group is not None else "-",
                label=lab,
                **kw,
            )
        )
    return out


def geom_freqpoly(ax, x, group=None, bins=30, **kw):
    edges = np.histogram_bin_edges(np.asarray(x, float), bins=bins)
    mids = (edges[:-1] + edges[1:]) / 2
    out = []
    for i, lab, m in _groups(x, group):
        n, _ = np.histogram(np.asarray(x, float)[m], bins=edges)
        out += ax.plot(mids, n, label=lab, **{**_line(i), **kw})
    return out


def geom_density(ax, x, group=None, hatch=False, bw=None, n=256, **kw):
    x = np.asarray(x, float)
    grid = np.linspace(x.min() - 0.1 * np.ptp(x), x.max() + 0.1 * np.ptp(x), n)
    out = []
    for i, lab, m in _groups(x, group):
        d = _kde1(x[m], grid, bw)
        out += ax.plot(grid, d, label=lab, **{**_line(i), **kw})
        if hatch:
            ax.fill_between(grid, 0, d, facecolor="none", edgecolor=INK, hatch=_hatch(i + 1), linewidth=0)
    ax.set_ylim(bottom=0)
    return out


def geom_dotplot(ax, x, binwidth=None, dot_scale=1.0, **kw):
    """Wilkinson dot plot: values binned and stacked as open circles.
    Dots are drawn in data units, so set the y range to suit."""
    x = np.sort(np.asarray(x, float))
    bw = binwidth or (np.ptp(x) / 30 if np.ptp(x) > 0 else 1.0)
    centers = np.floor((x - x.min()) / bw) * bw + x.min() + bw / 2
    patches = []
    for c in np.unique(centers):
        k = np.sum(centers == c)
        for j in range(k):
            patches.append(Circle((c, bw / 2 + j * bw), bw / 2 * 0.92 * dot_scale))
    pc = PatchCollection(patches, facecolor="white", edgecolor=INK, linewidths=0.8, **kw)
    ax.add_collection(pc)
    top = max(np.unique(centers, return_counts=True)[1]) * bw
    ax.set_xlim(x.min() - bw, x.max() + bw)
    ax.set_ylim(0, top * 1.1)
    ax.set_aspect("equal", adjustable="datalim")
    ax.set_yticks([])
    return pc


def geom_boxplot(ax, datasets, positions=None, width=0.5, hatches=None, outliers=True, **kw):
    """Tukey box plots: whiskers to 1.5 IQR, outliers as open circles."""
    positions = list(range(len(datasets))) if positions is None else positions
    bp = ax.boxplot(
        datasets,
        positions=positions,
        widths=width,
        patch_artist=True,
        showfliers=outliers,
        medianprops=dict(color=INK, linewidth=1.5),
        whiskerprops=dict(color=INK, linewidth=0.9, linestyle="-"),
        capprops=dict(color=INK, linewidth=0.9),
        flierprops=dict(
            marker="o", markerfacecolor="white", markeredgecolor=INK, markersize=3.5, linestyle="none"
        ),
        **kw,
    )
    for i, b in enumerate(bp["boxes"]):
        b.set(facecolor="white", edgecolor=INK, linewidth=0.9, hatch=(hatches[i] if hatches else _hatch(i)))
    return bp


def geom_violin(ax, datasets, positions=None, **kw):
    from .style import violin

    return violin(ax, datasets, positions, **kw)


# ---------- intervals ----------


def geom_errorbar(ax, x, ymin, ymax, width=0.15, orientation="x", **kw):
    """orientation='y' gives horizontal bars (the replacement for
    geom_errorbarh, deprecated in ggplot2 4.0.0)."""
    x = np.asarray(x, float)
    lo = np.asarray(ymin, float)
    hi = np.asarray(ymax, float)
    lw = kw.pop("linewidth", 0.9)
    if orientation == "x":
        segs = [[(a, b), (a, c)] for a, b, c in zip(x, lo, hi)]
        segs += [[(a - width / 2, v), (a + width / 2, v)] for a, b, c in zip(x, lo, hi) for v in (b, c)]
    else:
        segs = [[(b, a), (c, a)] for a, b, c in zip(x, lo, hi)]
        segs += [[(v, a - width / 2), (v, a + width / 2)] for a, b, c in zip(x, lo, hi) for v in (b, c)]
    lc = LineCollection(segs, colors=INK, linewidths=lw, **kw)
    ax.add_collection(lc)
    ax.autoscale_view()
    return lc


def geom_errorbarh(ax, y, xmin, xmax, height=0.15, **kw):
    """Deprecated in ggplot2 4.0.0; kept as an alias for orientation='y'."""
    return geom_errorbar(ax, y, xmin, xmax, width=height, orientation="y", **kw)


def geom_linerange(ax, x, ymin, ymax, **kw):
    return ax.vlines(x, ymin, ymax, colors=INK, linewidths=kw.pop("linewidth", 0.9), **kw)


def geom_pointrange(ax, x, y, ymin, ymax, group=None, **kw):
    geom_linerange(ax, x, ymin, ymax)
    return geom_point(ax, x, y, group, **kw)


def geom_crossbar(ax, x, y, ymin, ymax, width=0.4, group=None, **kw):
    out = []
    for i, _lab, m in _groups(x, group):
        for a, b, c, d in zip(np.asarray(x)[m], np.asarray(y)[m], np.asarray(ymin)[m], np.asarray(ymax)[m]):
            r = Rectangle(
                (a - width / 2, c),
                width,
                d - c,
                facecolor="white",
                edgecolor=INK,
                hatch=_hatch(i),
                linewidth=0.9,
            )
            ax.add_patch(r)
            out.append(r)
            ax.plot(
                [a - width / 2, a + width / 2], [b, b], color=INK, linewidth=1.6, marker="none", linestyle="-"
            )
    ax.autoscale_view()
    return out


# ---------- statistical summaries ----------


def _local_linear(x, y, grid, span=0.75):
    """Local linear regression with tricube weights (loess, degree 1),
    solved in closed form for every grid point at once. As in loess, the
    neighbourhood is the nearest span*n points; span > 1 widens it."""
    n = len(x)
    k = min(n, max(3, int(np.ceil(span * n))))
    dx = x[None, :] - grid[:, None]  # (grid, n)
    d = np.abs(dx)
    h = np.partition(d, k - 1, axis=1)[:, k - 1 : k] * max(1.0, span) + 1e-12
    w = np.clip(1 - (d / h) ** 3, 0, None) ** 3
    s0 = w.sum(1)
    s1 = (w * dx).sum(1)
    s2 = (w * dx * dx).sum(1)
    t0 = w @ y
    t1 = (w * dx) @ y
    det = s0 * s2 - s1**2
    ok = det > 1e-12 * np.maximum(s0 * s2, 1e-300)
    # where all the weight sits on one x value the slope is undefined: use the weighted mean
    return np.where(ok, (s2 * t0 - s1 * t1) / np.where(ok, det, 1), t0 / np.maximum(s0, 1e-300))


def geom_smooth(ax, x, y, method="loess", se=True, level=0.95, span=0.75, n=100, **kw):
    """method='lm': OLS line with a confidence band (dashed bounds over
    stippling). method='loess': local linear fit (degree 1, tricube
    weights). For loess, se=True gives a bootstrap band (200 resamples),
    which differs from ggplot2's analytic loess interval."""
    from scipy import stats

    x = np.asarray(x, float)
    y = np.asarray(y, float)
    grid = np.linspace(x.min(), x.max(), n)
    if method == "lm":
        X = np.column_stack([np.ones_like(x), x])
        beta, _res, *_ = np.linalg.lstsq(X, y, rcond=None)
        fit = beta[0] + beta[1] * grid
        dof = len(x) - 2
        s2 = np.sum((y - X @ beta) ** 2) / dof
        XtXi = np.linalg.inv(X.T @ X)
        G = np.column_stack([np.ones_like(grid), grid])
        se_fit = np.sqrt(s2 * np.einsum("ij,jk,ik->i", G, XtXi, G))
        t = stats.t.ppf(0.5 + level / 2, dof)
        lo, hi = fit - t * se_fit, fit + t * se_fit
    else:
        fit = _local_linear(x, y, grid, span)
        lo = hi = None
        if se:
            rng = np.random.default_rng(0)
            boots = np.array(
                [
                    _local_linear(x[i], y[i], grid, span)
                    for i in (rng.integers(0, len(x), len(x)) for _ in range(200))
                ]
            )
            lo, hi = np.percentile(boots, [50 - level * 50, 50 + level * 50], axis=0)
    if se and lo is not None:
        geom_ribbon(ax, grid, lo, hi)
    return ax.plot(grid, fit, **{**_line(0), "linewidth": 1.3, **kw})


def geom_quantile(ax, x, y, quantiles=(0.25, 0.5, 0.75), **kw):
    """Linear quantile regression, solved exactly as a linear program."""
    from scipy.optimize import linprog

    x = np.asarray(x, float)
    y = np.asarray(y, float)
    n = len(x)
    X = np.column_stack([np.ones(n), x])
    grid = np.linspace(x.min(), x.max(), 50)
    out = []
    for j, q in enumerate(quantiles):
        # min q*u + (1-q)*v  s.t.  X b + u - v = y, u, v >= 0
        c = np.r_[0, 0, np.full(n, q), np.full(n, 1 - q)]
        I = sparse.identity(n, format="csr")
        A = sparse.hstack([sparse.csr_matrix(X), I, -I], format="csr")
        bounds = [(None, None)] * 2 + [(0, None)] * (2 * n)
        r = linprog(c, A_eq=A, b_eq=y, bounds=bounds, method="highs")
        b0, b1 = r.x[:2]
        out += ax.plot(
            grid,
            b0 + b1 * grid,
            **{**_line(j if q != 0.5 else 0), "linewidth": 1.2 if q == 0.5 else 0.8, **kw},
        )
    return out


def geom_qq(ax, sample, dist="norm", **kw):
    from scipy import stats

    (osm, osr), _ = stats.probplot(np.asarray(sample, float), dist=dist)
    return ax.plot(osm, osr, linestyle="none", markersize=4, **{**_marker(0), **kw})


def geom_qq_line(ax, sample, dist="norm", **kw):
    """Line through the first and third quartiles, as in ggplot2."""
    from scipy import stats

    s = np.asarray(sample, float)
    q = np.percentile(s, [25, 75])
    t = getattr(stats, dist).ppf([0.25, 0.75])
    slope = (q[1] - q[0]) / (t[1] - t[0])
    icpt = q[0] - slope * t[0]
    return ax.axline((0, icpt), slope=slope, color=INK, linewidth=0.8, linestyle="--")


# ---------- 2-D densities, contours, bins ----------


def geom_density_2d(ax, x, y, levels=8, bw=None, **kw):
    X, Y, Z = _kde2(x, y, bw=bw)
    return ax.contour(X, Y, Z, levels=levels, colors=INK, linewidths=0.7, **kw)


def geom_density_2d_filled(ax, x, y, levels=6, bw=None, **kw):
    X, Y, Z = _kde2(x, y, bw=bw)
    return geom_contour_filled(ax, X, Y, Z, levels=levels, **kw)


def geom_contour(ax, X, Y, Z, levels=8, labels=True, **kw):
    cs = ax.contour(X, Y, Z, levels=levels, colors=INK, linewidths=0.7, **kw)
    if labels:
        for t in ax.clabel(cs, fontsize=7, inline=True, fmt="%g"):
            t.set_bbox(dict(facecolor="white", edgecolor="none", pad=0.4))
    return cs


def geom_contour_filled(ax, X, Y, Z, levels=6, lines=True, **kw):
    """Bands hatched more densely at higher levels; the lowest band is left white."""
    lv = np.linspace(np.nanmin(Z), np.nanmax(Z), levels + 1) if np.isscalar(levels) else np.asarray(levels)
    cf = ax.contourf(X, Y, Z, levels=lv, colors="none", hatches=_level_hatches(len(lv) - 1), **kw)
    if lines:
        ax.contour(X, Y, Z, levels=lv[1:-1], colors=INK, linewidths=0.6)
    return cf


def geom_bin_2d(ax, x, y, bins=20, **kw):
    """Rectangular bins drawn as halftone squares."""
    H, xe, ye = np.histogram2d(x, y, bins=bins)
    cx, cy = np.meshgrid((xe[:-1] + xe[1:]) / 2, (ye[:-1] + ye[1:]) / 2, indexing="ij")
    H = np.where(H > 0, H, np.nan)
    pc = _halftone(ax, cx, cy, H, np.diff(xe)[0], np.diff(ye)[0], vmin=0, shape="square", **kw)
    ax.set_xlim(xe[0], xe[-1])
    ax.set_ylim(ye[0], ye[-1])
    return pc


def geom_hex(ax, x, y, gridsize=18, **kw):
    """Hexagonal bins drawn as halftone dots at the hexagon centres."""
    hb = ax.hexbin(x, y, gridsize=gridsize, mincnt=1)
    off, cnt = hb.get_offsets(), hb.get_array()
    hb.remove()
    xr = np.ptp(x) / gridsize
    yr = np.ptp(y) / gridsize * np.sqrt(3)
    pc = _halftone(ax, off[:, 0], off[:, 1], cnt, xr, yr, vmin=0, **kw)
    ax.set_xlim(np.min(x) - xr, np.max(x) + xr)
    ax.set_ylim(np.min(y) - yr, np.max(y) + yr)
    return pc


def geom_tile(ax, x, y, value, width=1.0, height=1.0, **kw):
    """Tiles at (x, y) with halftone dots sized by value, plus a light grid."""
    for a, b in zip(x, y):
        ax.add_patch(
            Rectangle(
                (a - width / 2, b - height / 2), width, height, facecolor="none", edgecolor=INK, linewidth=0.3
            )
        )
    return _halftone(ax, x, y, value, width, height, **kw)


def geom_raster(ax, Z, extent=None, **kw):
    """Regular grid of values as halftone dots, no cell outlines."""
    Z = np.asarray(Z, float)
    ny, nx = Z.shape
    x0, x1, y0, y1 = extent or (0, nx, 0, ny)
    cw, ch = (x1 - x0) / nx, (y1 - y0) / ny
    cx, cy = np.meshgrid(x0 + cw * (np.arange(nx) + 0.5), y0 + ch * (np.arange(ny) + 0.5))
    pc = _halftone(ax, cx, cy, Z, cw, ch, **kw)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    return pc


# ---------- text ----------


def geom_text(ax, x, y, labels, **kw):
    kw.setdefault("fontsize", 8)
    return [ax.text(a, b, str(t), ha="center", va="center", color=INK, **kw) for a, b, t in zip(x, y, labels)]


def geom_label(ax, x, y, labels, **kw):
    kw.setdefault("fontsize", 8)
    return [
        ax.text(
            a,
            b,
            str(t),
            ha="center",
            va="center",
            color=INK,
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor=INK, linewidth=0.7),
            **kw,
        )
        for a, b, t in zip(x, y, labels)
    ]


# ---------- maps ----------


def geom_map(ax, polygons, values=None, classes=4, **kw):
    """Choropleth: polygons hatched by value class (denser = higher).
    polygons: list of (n, 2) coordinate arrays, one per region."""
    if values is None:
        return geom_polygon(ax, polygons, **kw)
    v = np.asarray(values, float)
    edges = np.quantile(v, np.linspace(0, 1, classes + 1))
    cls = np.clip(np.searchsorted(edges, v, side="right") - 1, 0, classes - 1)
    hs = _level_hatches(classes)
    out = []
    for poly, c in zip(polygons, cls):
        p = Polygon(poly, closed=True, facecolor="white", edgecolor=INK, hatch=hs[c], linewidth=0.7, **kw)
        ax.add_patch(p)
        out.append(p)
    ax.update_datalim(np.vstack(polygons))
    ax.autoscale_view()
    ax.set_aspect("equal")
    return out


def geom_sf(ax, geometries, values=None, classes=4, **kw):
    """Simple-features layer. Accepts shapely Polygon/MultiPolygon objects
    (or a GeoSeries) and draws them like geom_map. shapely is only needed
    if you pass shapely objects."""
    polys = []
    for gm in geometries:
        if hasattr(gm, "geoms"):
            polys += [np.asarray(p.exterior.coords) for p in gm.geoms]
        elif hasattr(gm, "exterior"):
            polys.append(np.asarray(gm.exterior.coords))
        else:
            polys.append(np.asarray(gm))
    return geom_map(ax, polys, values, classes, **kw)


def _centroids(polygons):
    return [np.asarray(p).mean(axis=0) for p in polygons]


def geom_sf_text(ax, polygons, labels, **kw):
    c = np.array(_centroids(polygons))
    return geom_text(ax, c[:, 0], c[:, 1], labels, **kw)


def geom_sf_label(ax, polygons, labels, **kw):
    c = np.array(_centroids(polygons))
    return geom_label(ax, c[:, 0], c[:, 1], labels, **kw)


def geom_blank(ax, *args, **kw):
    """Draws nothing, as in ggplot2 (useful for setting limits)."""
    return None


# ---------- coverage ----------

# Every geom exported by ggplot2 4.0.x (from its NAMESPACE), mapped to a function here.
GEOMS = {
    "geom_abline": geom_abline,
    "geom_area": geom_area,
    "geom_bar": geom_bar,
    "geom_bin2d": geom_bin_2d,
    "geom_bin_2d": geom_bin_2d,
    "geom_blank": geom_blank,
    "geom_boxplot": geom_boxplot,
    "geom_col": geom_col,
    "geom_contour": geom_contour,
    "geom_contour_filled": geom_contour_filled,
    "geom_count": geom_count,
    "geom_crossbar": geom_crossbar,
    "geom_curve": geom_curve,
    "geom_density": geom_density,
    "geom_density2d": geom_density_2d,
    "geom_density2d_filled": geom_density_2d_filled,
    "geom_density_2d": geom_density_2d,
    "geom_density_2d_filled": geom_density_2d_filled,
    "geom_dotplot": geom_dotplot,
    "geom_errorbar": geom_errorbar,
    "geom_errorbarh": geom_errorbarh,
    "geom_freqpoly": geom_freqpoly,
    "geom_function": geom_function,
    "geom_hex": geom_hex,
    "geom_histogram": geom_histogram,
    "geom_hline": geom_hline,
    "geom_jitter": geom_jitter,
    "geom_label": geom_label,
    "geom_line": geom_line,
    "geom_linerange": geom_linerange,
    "geom_map": geom_map,
    "geom_path": geom_path,
    "geom_point": geom_point,
    "geom_pointrange": geom_pointrange,
    "geom_polygon": geom_polygon,
    "geom_qq": geom_qq,
    "geom_qq_line": geom_qq_line,
    "geom_quantile": geom_quantile,
    "geom_raster": geom_raster,
    "geom_rect": geom_rect,
    "geom_ribbon": geom_ribbon,
    "geom_rug": geom_rug,
    "geom_segment": geom_segment,
    "geom_sf": geom_sf,
    "geom_sf_label": geom_sf_label,
    "geom_sf_text": geom_sf_text,
    "geom_smooth": geom_smooth,
    "geom_spoke": geom_spoke,
    "geom_step": geom_step,
    "geom_text": geom_text,
    "geom_tile": geom_tile,
    "geom_violin": geom_violin,
    "geom_vline": geom_vline,
}
