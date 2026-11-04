"""cogra-paper: set a Markdown paper as an APA journal article of about 1980.

cogra-paper paper.md                     # writes paper_site/index.html
cogra-paper paper.md --pdf paper.pdf     # and a PDF
cogra-paper paper.md --pdf paper.pdf --clean --columns 1
cogra-paper paper.md --figure ssrt=plots/ssrt.png    # for ![caption](fig:ssrt)
"""

import argparse
from pathlib import Path

from . import Paper


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(
        prog="cogra-paper", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("markdown", type=Path, help="the paper, Markdown with YAML front matter")
    ap.add_argument("-o", "--out", type=Path, help="folder for the web page (default: <name>_site)")
    ap.add_argument("--pdf", type=Path, help="also write a PDF here")
    ap.add_argument("--clean", action="store_true", help="clean type instead of the archival-scan look")
    ap.add_argument("--columns", type=int, choices=(1, 2), help="override the number of columns")
    ap.add_argument(
        "--figure",
        action="append",
        default=[],
        metavar="NAME=IMAGE",
        help="image for ![caption](fig:NAME); repeat for several",
    )
    ap.add_argument("--no-site", action="store_true", help="only write the PDF")
    a = ap.parse_args(argv)
    if a.no_site and not a.pdf:
        ap.error("--no-site needs --pdf")
    if not a.markdown.is_file():
        ap.error(f"no such file: {a.markdown}")
    for spec in a.figure:
        if not Path(spec.partition("=")[2]).is_file() and "=" in spec:
            ap.error(f"--figure {spec}: no such image")

    overrides = {"columns": a.columns} if a.columns else {}
    if a.clean:
        overrides["worn"] = False
    figures = {}
    for spec in a.figure:
        name, sep, img = spec.partition("=")
        if not sep:
            ap.error(f"--figure needs NAME=IMAGE, got {spec!r}")
        figures[name] = Path(img)
    paper = Paper.from_markdown(a.markdown, figures=figures, **overrides)
    if not a.no_site:
        out = a.out or a.markdown.with_name(a.markdown.stem + "_site")
        print("wrote", paper.save(out))
    if a.pdf:
        print("wrote", paper.pdf(a.pdf))


if __name__ == "__main__":
    main()
