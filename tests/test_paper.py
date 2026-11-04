import re
import subprocess

import matplotlib.pyplot as plt
import pytest
from conftest import ROOT

from cogra import paper

pytest.importorskip("markdown")
pytest.importorskip("yaml")

EXAMPLE = ROOT / "examples" / "paper" / "example.md"

MINI = """---
title: "a study of fMRI and the stop-signal task"
authors: ["A. One^1", "B. Two^2"]
affiliations: ["^1First University", "^2Second Institute"]
abstract: "An abstract."
author_note: "Supported by nothing."
masthead: |
  Journal of Examples
  1980, Vol. 1, No. 1, 1-2
---

# Introduction

Opening text.[^a]

# Method

## Subjects

### Procedure

Procedure text.

- first item
- second item

# Results

Results text, ANOVA in small capitals.[^b] And again.[^a]

![A caption.](fig:f)

Table: A table title

| a | b |
|---|---|
| 1 | 2 |

# References

Author, A. (1980). A title. *Journal, 1*, 1-2.

[^a]: First note.
[^b]: Second note.
"""


@pytest.fixture
def fig():
    f, ax = plt.subplots(figsize=(3, 2))
    ax.plot([0, 1], [0, 1])
    return f


def test_title_case_keeps_capitalised_words():
    assert (
        paper.title_case("a study of fMRI and the stop-signal task")
        == "A Study of fMRI and the Stop-Signal Task"
    )
    assert paper.title_case("on the ability to inhibit thought") == "On the Ability to Inhibit Thought"


def test_markdown_structure(fig):
    p = paper.Paper.from_markdown(MINI, figures={"f": fig})
    assert p.title == "A Study of fMRI and the Stop-Signal Task"
    assert p.authors == ["A. One<sup>1</sup>", "B. Two<sup>2</sup>"]
    assert p.affiliations == ["<sup>1</sup>First University", "<sup>2</sup>Second Institute"]
    assert p.short_authors == "One and Two"
    assert p.author_note == ["Supported by nothing."]
    body = "\n".join(p.blocks)
    assert "Introduction" not in body  # the introduction carries no heading
    assert '<h2 class="h1">Method</h2>' in body
    assert '<h3 class="h2">Subjects</h3>' in body
    assert '<p class="small"><span class="runin">Procedure.</span> Procedure text.</p>' in body
    assert body.count('class="li small" data-mark="•"') == 2
    # footnotes numbered by first use; a repeated reference keeps its number
    assert re.findall(r'data-n="(\d)"', body) == ["1", "2", "1"]
    assert p.footnotes == {1: "First note.", 2: "Second note."}
    assert '<span class="sc">anova</span>' in body
    assert '<figure data-fig="1">' in body and "Figure 1.</span> A caption." in body
    assert 'class="table" data-fig="t1"' in body and "A table title" in body
    assert '<p class="ref">Author, A. (1980).' in body
    assert p.blocks[-1] == '<p class="endmark">&#9632;</p>'


def test_unknown_figure_name_is_an_error():
    with pytest.raises(KeyError):
        paper.Paper.from_markdown(MINI)


def test_save_writes_page_and_assets(tmp_path, fig):
    p = paper.Paper.from_markdown(
        MINI, figures={"f": fig}, style={"body": "10pt", "page-w": "612pt"}, columns=1
    )
    index = p.save(tmp_path / "site")
    site = index.parent
    for f in (
        "apa1980.css",
        "paginate.js",
        "fonts/texgyreschola-regular.otf",
        "fonts/GUST-FONT-LICENSE.txt",
        "figures/f.png",
        "figures/f-scan.png",
    ):
        assert (site / f).is_file(), f
    h = index.read_text()
    assert 'data-columns="1"' in h
    assert "--body: 10pt;" in h and "--page-w: 612pt;" in h
    assert "@page { size: 612pt 726pt; margin: 0; }" in h
    assert 'src="figures/f.png" style="width:216.0pt"' in h  # 3 in at its own size
    assert 'src="figures/f-scan.png"' in h
    assert '<body class="worn">' in h and 'id="cogra-scan"' in h


def test_clean_paper_has_no_scan_files(tmp_path, fig):
    p = paper.Paper.from_markdown(MINI, figures={"f": fig}, worn=False)
    index = p.save(tmp_path / "site", controls=False)
    assert not (index.parent / "figures" / "f-scan.png").exists()
    h = index.read_text()
    assert '<body class="">' in h and "wornToggle" not in h


def test_image_file_figures(tmp_path):
    f, ax = plt.subplots(figsize=(2, 1.5))
    ax.plot([0, 1], [1, 0])
    f.savefig(tmp_path / "plot.png", dpi=100)
    md = tmp_path / "p.md"
    md.write_text("---\ntitle: t\nauthors: [A]\n---\n\nText.\n\n![Cap.](plot.png)\n")
    p = paper.Paper.from_markdown(md)
    index = p.save(tmp_path / "site")
    assert (index.parent / "figures" / "file1.png").is_file()
    assert (index.parent / "figures" / "file1-scan.png").is_file()
    assert 'style="width:144.0pt"' in index.read_text()


@pytest.mark.slow
@pytest.mark.skipif(paper.find_chrome() is None, reason="no Chrome-family browser")
def test_example_paginates_and_prints(tmp_path, fig):
    """End to end through a real browser: the example paginates with no
    overflowing column, and prints to pages of the right size with
    searchable text when clean."""
    pymupdf = pytest.importorskip("pymupdf")
    p = paper.Paper.from_markdown(EXAMPLE, figures={"clicks": fig}, worn=False)
    index = p.save(tmp_path / "site", controls=False)
    dom = subprocess.run(
        [
            paper.find_chrome(),
            "--headless=new",
            "--disable-gpu",
            "--virtual-time-budget=20000",
            "--window-size=1200,900",
            f"--user-data-dir={tmp_path / 'profile'}",
            "--dump-dom",
            index.as_uri(),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    ).stdout
    book = re.search(r'<div id="book"[^>]*>', dom).group(0)
    assert 'data-overflow="0"' in book
    assert int(re.search(r'data-pages="(\d+)"', book).group(1)) >= 2
    assert dom.count('class="sheet') >= 2 and "first-foot" in dom
    pdf = p.pdf(tmp_path / "example.pdf", worn=False)
    doc = pymupdf.open(pdf)
    assert len(doc) >= 2
    assert abs(doc[0].rect.width - 531) < 1 and abs(doc[0].rect.height - 726) < 1
    assert "Interpolated Clicks" in doc[0].get_text()


MATH = r"""---
title: "Math"
authors: ["A. One"]
abstract: 'Inline $\alpha$ in the abstract.'
---

# Results

Each subject earned $3.50, and \$5 more for $a_1 * b_2$ and $x^2$.

$$\frac{p(y_t \mid H_1)}{p(y_t \mid H_0)} \tag{1}$$

Last, $q < r$ & done.
"""


def test_markdown_math():
    p = paper.Paper.from_markdown(MATH)
    body = "\n".join(p.blocks)
    assert "$3.50" in body and "&#36;5" in body  # money stays money
    assert r"\(a_1 * b_2\)" in body and "<em>" not in body
    assert r"\(x^2\)" in body and r"\(q &lt; r\)" in body
    display = [b for b in p.blocks if 'class="display' in b]
    assert len(display) == 1 and r"\[\frac{p(y_t \mid H_1)}" in display[0]
    assert r"\(\alpha\)" in p.abstract


def test_mathjax_copied_only_with_math(tmp_path, fig):
    with_math = paper.Paper.from_markdown(MATH).save(tmp_path / "math")
    assert 'src="mathjax/startup.js"' in with_math.read_text()
    assert (with_math.parent / "mathjax" / "startup.js").is_file()
    assert (with_math.parent / "mathjax" / "mathjax-schola" / "svg.js").is_file()
    plain = paper.Paper.from_markdown(MINI, figures={"f": fig}).save(tmp_path / "plain")
    assert "mathjax" not in plain.read_text()
    assert not (plain.parent / "mathjax").exists()


@pytest.mark.slow
@pytest.mark.skipif(paper.find_chrome() is None, reason="no Chrome-family browser")
def test_math_typesets_into_pages(tmp_path):
    """MathJax typesets before pagination: the pages hold SVG math, nothing
    failed to parse, and no column overflows."""
    p = paper.Paper.from_markdown(MATH, worn=False)
    index = p.save(tmp_path / "site", controls=False)
    dom = subprocess.run(
        [
            paper.find_chrome(),
            "--headless=new",
            "--disable-gpu",
            "--virtual-time-budget=20000",
            "--window-size=1200,900",
            f"--user-data-dir={tmp_path / 'profile'}",
            "--dump-dom",
            index.as_uri(),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    ).stdout
    book = dom[dom.index('<div id="book"') : dom.index('<div id="source"')]
    assert 'data-overflow="0"' in book
    assert book.count("<mjx-container") == 5 and 'display="true"' in book
    assert "data-mjx-error" not in book and 'data-mml-node="merror"' not in book


def test_missing_markdown_file_raises(tmp_path):
    """A mistyped file name used to become the paper's text (bug-driven test)."""
    with pytest.raises(FileNotFoundError, match="no such Markdown file"):
        paper.Paper.from_markdown(str(tmp_path / "typo.md"))


def test_pathlike_source_is_read(tmp_path):
    import os

    md = tmp_path / "p.md"
    md.write_text('---\ntitle: "Read from a path"\n---\nBody text.\n')
    assert "Body text." in paper.Paper.from_markdown(os.fspath(md)).html().replace("\n", " ")
