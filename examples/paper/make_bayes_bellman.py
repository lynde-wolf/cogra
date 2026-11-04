"""Build the second example paper: bayes_bellman.md plus a cogra figure, as a web page and a PDF.

python examples/paper/make_bayes_bellman.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import cogra
from cogra import geoms as g
from cogra import paper

HERE = Path(__file__).parent


def make_figure():
    """The paper's figure, drawn with cogra."""
    cogra.use(labels="serif")
    fig, ax = plt.subplots(figsize=(3.2, 2.4))
    conds = ["High\ninformation", "Low\ninformation", "Reward\ndominant", "Information\nirrelevant"]
    prop = [0.61, 0.36, 0.19, 0.48]  # invented values, as in the paper's Results
    half = [0.04, 0.04, 0.03, 0.04]  # half-widths of the 95% CIs
    g.geom_col(ax, conds, prop, width=0.6)
    g.geom_errorbar(
        ax, range(4), [p - h for p, h in zip(prop, half)], [p + h for p, h in zip(prop, half)], width=0.2
    )
    ax.set(ylabel="Information-seeking choices", ylim=(0, 0.8))
    ax.tick_params(axis="x", labelsize=7)
    fig.tight_layout()
    return fig


def build(site_dir=HERE / "bayes_bellman_site", pdf=HERE / "bayes_bellman.pdf"):
    """Write the paper as a web page in site_dir, and as a PDF unless pdf is None."""
    fig = make_figure()
    fig.savefig(HERE / "infoseek.png", dpi=300)  # for the command-line build, see TUTORIAL.md
    p = paper.Paper.from_markdown(HERE / "bayes_bellman.md", figures={"infoseek": fig})
    print("wrote", p.save(site_dir))
    if pdf is not None:
        try:
            print("wrote", p.pdf(pdf))
        except RuntimeError as e:
            print("no PDF:", e)
    plt.close(fig)


if __name__ == "__main__":
    build()
