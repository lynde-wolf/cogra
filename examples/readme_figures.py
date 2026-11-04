"""Draw the pictures in the README into examples/figures/.

    python examples/readme_figures.py      # the paper page needs a Chrome-family browser

All values are illustrative, not data.
"""

import sys
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

import cogra
from cogra import geoms as g
from cogra import paper

HERE = Path(__file__).resolve().parent
OUT = HERE / "figures"
sys.path.insert(0, str(HERE))
import demo_restyle  # noqa: E402
import demo_signif  # noqa: E402
import gallery  # noqa: E402

GAP, BG = 24, (255, 255, 255)


def png(fig, dpi=200):
    """The figure as a PIL image, then closed."""
    path = Path(tempfile.mkstemp(suffix=".png")[1])
    fig.savefig(path, dpi=dpi)
    plt.close(fig)
    im = Image.open(path).convert("RGB")  # keep colour: the "before" pictures have it
    path.unlink()
    return im


def strip(images, height=None, out=None, width=1000):
    """Images side by side on white, scaled to a common height, then to width."""
    height = height or min(i.height for i in images)
    images = [
        i.convert("RGB").resize((round(i.width * height / i.height), height), Image.LANCZOS) for i in images
    ]
    w = sum(i.width for i in images) + GAP * (len(images) - 1)
    sheet = Image.new("RGB", (w, height), BG)
    x = 0
    for i in images:
        sheet.paste(i, (x, 0))
        x += i.width + GAP
    if sheet.width > width:
        sheet = sheet.resize((width, round(sheet.height * width / sheet.width)), Image.LANCZOS)
    sheet.save(OUT / out, optimize=True)
    return sheet


def rt_plot(title):
    fig, ax = plt.subplots(figsize=(3.0, 2.4))
    s = np.arange(1, 7)
    ax.plot(s, 392 + 38 * s, label="Positive")
    ax.plot(s, 397 + 38 * s + 6 * np.sin(s), label="Negative")
    ax.set(xlabel="Size of positive set", ylabel="Mean RT (msec)", xticks=s, title=title)
    ax.legend(loc="upper left")
    fig.tight_layout()
    return fig


def styles():
    out = []
    for style, title in (
        (["default"], "matplotlib default"),
        (["cogra"], '"cogra"'),
        (["cogra", "cogra-serif"], '+ "cogra-serif"'),
    ):
        with plt.style.context(style):
            out.append(png(rt_plot(title)))
    strip(out, out="styles.png")


def restyle():
    before = png(demo_restyle.make_figure(), dpi=110)
    after = png(demo_restyle.make_figure() | cogra.cogra(), dpi=110)
    strip([before, after], out="restyle.png", width=1100)


def wear():
    cogra.use(size="column")
    fig, ax = plt.subplots()
    load = [1, 3, 5] * 2
    ssrt = [212, 219, 224, 228, 247, 268]
    g.geom_line(ax, load, ssrt, group=["Feature"] * 3 + ["Relational"] * 3, markers=True)
    ax.set(xlabel="Items held", ylabel="SSRT (msec)", xticks=[1, 3, 5])
    ax.legend()
    fig.tight_layout()
    clean = png(fig, dpi=300)
    looks = [clean]
    with tempfile.TemporaryDirectory() as tmp:
        for look in ("scan", "xerox", "aged"):
            cogra.use(size="column")
            fig, ax = plt.subplots()
            g.geom_line(ax, load, ssrt, group=["Feature"] * 3 + ["Relational"] * 3, markers=True)
            ax.set(xlabel="Items held", ylabel="SSRT (msec)", xticks=[1, 3, 5])
            ax.legend()
            fig.tight_layout()
            p = Path(tmp) / f"{look}.png"
            cogra.save_vintage(fig, p, look=look, cache=False)
            plt.close(fig)
            looks.append(Image.open(p).convert("L"))
    strip(looks, height=clean.height, out="wear.png", width=1100)


def signif():
    strip([png(demo_signif.make_figure(), dpi=200)], out="signif.png", width=1000)


def geoms():
    cogra.use()
    names = ["point", "smooth (loess)", "col", "violin", "density_2d", "tile"]
    fig, axs = plt.subplots(2, 3, figsize=(8.4, 4.8))
    for ax, name in zip(axs.flat, names):
        gallery.panels[name](ax)
        ax.set_title(f"geom_{name.split(' ')[0]}", loc="left", fontsize=9)
    fig.tight_layout()
    im = png(fig, dpi=130)
    im.save(OUT / "geoms.png", optimize=True)


def paper_pages():
    p = paper.Paper.from_markdown(HERE / "paper" / "example.md", figures={"clicks": _paper_figure()})
    with tempfile.TemporaryDirectory() as tmp:
        pdf = p.pdf(Path(tmp) / "example.pdf")
        import pymupdf

        doc = pymupdf.open(pdf)
        pages = []
        for i in range(min(2, len(doc))):
            pix = doc[i].get_pixmap(dpi=110, colorspace=pymupdf.csGRAY)
            pages.append(Image.frombytes("L", (pix.width, pix.height), pix.samples))
    # a thin rule around each page, so white pages show on a white README
    framed = []
    for im in pages:
        f = Image.new("L", (im.width + 2, im.height + 2), 150)
        f.paste(im, (1, 1))
        framed.append(f)
    strip(framed, out="paper.png", width=900)


def _paper_figure():
    cogra.use(labels="serif", size="column")
    fig, ax = plt.subplots()
    clicks = [0, 4, 8] * 2
    msec = [1042, 1096, 1148, 1071, 1127, 1180]  # the example paper's invented Table 1
    g.geom_line(ax, clicks, msec, group=["500 Hz"] * 3 + ["2,000 Hz"] * 3, markers=True)
    g.geom_errorbar(ax, clicks, [m - 14 for m in msec], [m + 14 for m in msec], width=0.4)
    ax.set(
        xlabel="Number of clicks", ylabel="Reproduced duration (msec)", xticks=[0, 4, 8], ylim=(1000, 1220)
    )
    ax.legend()
    fig.tight_layout()
    return fig


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for step in (styles, restyle, wear, signif, geoms, paper_pages):
        step()
        print("drew", step.__name__)
