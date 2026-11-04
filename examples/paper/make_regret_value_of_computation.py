"""Build the third example paper: regret_value_of_computation.md plus a cogra figure, as a web page and a PDF.

python examples/paper/make_regret_value_of_computation.py

An invented 2026 theory paper (regret as the value of computation) with a
theorem, a stopping rule, footnotes, tables and a line figure with error bars
and a reference rule.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import cogra
from cogra import geoms as g
from cogra import paper

HERE = Path(__file__).parent

SLOPE = 1.42  # the logistic slope in the paper's Table 1
THRESHOLDS = {"Low arousal": 0.21, "High arousal": 1.08}  # Table 1, in points
CI_HALF_WIDTH = 0.06  # half-width of the drawn 95% intervals

margin = np.arange(-3.0, 3.5, 1.0)  # expected regret minus cost, in points
rng = np.random.default_rng(11)


def paid_to_look(threshold, slope=SLOPE):
    """Invented binned proportions: a logistic curve plus 2% jitter."""
    p = 1 / (1 + np.exp(-slope * (margin - threshold)))
    return np.clip(p + rng.normal(0, 0.02, margin.size), 0.01, 0.99)


curves = {cond: paid_to_look(t) for cond, t in THRESHOLDS.items()}


def make_figure():
    """The paper's figure, drawn with cogra."""
    cogra.use(labels="serif")
    fig, ax = plt.subplots(figsize=(3.2, 2.5))
    x = np.concatenate([margin] * len(curves))
    y = np.concatenate(list(curves.values()))
    cond = [c for c in curves for _ in margin]
    g.geom_vline(ax, 0.0, linestyle="--", linewidth=0.8)
    g.geom_errorbar(ax, x, np.clip(y - CI_HALF_WIDTH, 0, 1), np.clip(y + CI_HALF_WIDTH, 0, 1), width=0.18)
    g.geom_line(ax, x, y, group=cond, markers=True)
    ax.set(
        xlabel="Expected regret minus cost (points)",
        ylabel="Paid to look",
        xticks=[-3, -2, -1, 0, 1, 2, 3],
        ylim=(0, 1.05),
    )
    ax.legend(frameon=False, fontsize=7, loc="upper left")
    fig.tight_layout()
    return fig


def build(site_dir=HERE / "regret_value_of_computation_site", pdf=HERE / "regret_value_of_computation.pdf"):
    """Write the paper as a web page in site_dir, and as a PDF unless pdf is None."""
    fig = make_figure()
    p = paper.Paper.from_markdown(HERE / "regret_value_of_computation.md", figures={"looking": fig})
    print("wrote", p.save(site_dir))
    if pdf is not None:
        try:
            print("wrote", p.pdf(pdf))
        except RuntimeError as e:
            print("no PDF:", e)
    plt.close(fig)


if __name__ == "__main__":
    build()
