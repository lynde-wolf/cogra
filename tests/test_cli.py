"""cogra-paper, the command-line front end to cogra.paper."""

import pytest

from cogra.paper import cli

PAPER = """---
title: "A short paper"
authors: ["A. Author^1"]
affiliations: ["^1Somewhere College"]
abstract: "An abstract."
---
# Method

Some text, and a figure.

![A caption.](fig:one)
"""


@pytest.fixture
def paper_md(tmp_path):
    md = tmp_path / "short.md"
    md.write_text(PAPER)
    return md


@pytest.fixture
def figure_png(tmp_path):
    import numpy as np
    from PIL import Image

    path = tmp_path / "one.png"
    Image.fromarray(np.full((60, 90), 255, np.uint8)).save(path, dpi=(300, 300))
    return path


def test_writes_site_to_default_folder(paper_md, figure_png, capsys):
    cli.main([str(paper_md), "--figure", f"one={figure_png}", "--clean"])
    site = paper_md.with_name("short_site")
    assert (site / "index.html").is_file()
    assert (site / "figures" / "one.png").is_file()
    assert "wrote" in capsys.readouterr().out


def test_out_and_columns(paper_md, figure_png, tmp_path):
    out = tmp_path / "elsewhere"
    cli.main([str(paper_md), "-o", str(out), "--columns", "1", "--figure", f"one={figure_png}"])
    html = (out / "index.html").read_text()
    assert "a short paper" in html.lower()
    assert 'data-columns="1"' in html
    assert (out / "figures" / "one-scan.png").is_file()  # worn by default


@pytest.mark.parametrize(
    "args, message",
    [
        (["--no-site"], "--no-site needs --pdf"),
        (["--figure", "oops"], "NAME=IMAGE"),
        (["--figure", "one=missing.png"], "no such image"),
    ],
)
def test_bad_arguments_exit_before_building(paper_md, args, message, capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main([str(paper_md), *args])
    assert exc.value.code == 2
    assert message in capsys.readouterr().err
    assert not paper_md.with_name("short_site").exists()


def test_missing_markdown(tmp_path, capsys):
    with pytest.raises(SystemExit):
        cli.main([str(tmp_path / "nope.md")])
    assert "no such file" in capsys.readouterr().err
