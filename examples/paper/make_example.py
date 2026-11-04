"""Build the example paper: a cogra figure plus example.md, as a web page and a PDF.

python examples/paper/make_example.py
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
    clicks = [0, 4, 8] * 2
    msec = [1042, 1096, 1148, 1071, 1127, 1180]  # invented values, as in the paper's Table 1
    pitch = ["500 Hz"] * 3 + ["2,000 Hz"] * 3
    g.geom_line(ax, clicks, msec, group=pitch, markers=True)
    g.geom_errorbar(ax, clicks, [m - 14 for m in msec], [m + 14 for m in msec], width=0.4)
    ax.set(
        xlabel="Number of clicks", ylabel="Reproduced duration (msec)", xticks=[0, 4, 8], ylim=(1000, 1220)
    )
    ax.legend(frameon=False)
    fig.tight_layout()
    return fig


def build(site_dir=HERE / "example_site", pdf=HERE / "example.pdf"):
    """Write the paper as a web page in site_dir, and as a PDF unless pdf is None."""
    fig = make_figure()
    fig.savefig(HERE / "clicks.png", dpi=300)  # for the command-line build, see TUTORIAL.md
    p = paper.Paper.from_markdown(HERE / "example.md", figures={"clicks": fig})
    print("wrote", p.save(site_dir))
    if pdf is not None:
        try:
            print("wrote", p.pdf(pdf))
        except RuntimeError as e:
            print("no PDF:", e)
    plt.close(fig)


if __name__ == "__main__":
    build()
