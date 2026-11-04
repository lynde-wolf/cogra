"""The documentation site builds, covers the public API, and has no broken links."""

import sys

import pytest
from conftest import ROOT

pytest.importorskip("markdown")
sys.path.insert(0, str(ROOT / "docs"))
import build
import check_links


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("site")
    old, build.OUT = build.OUT, out
    try:
        build.build(quick=True)
    finally:
        build.OUT = old
    return out


def test_every_page_is_built(site):
    for name, _ in build.NAV:
        assert (site / name).is_file(), name
    assert (site / "web" / "cogra.css").is_file()


def test_no_broken_links(site):
    assert check_links.broken_links(site) == []


def test_api_page_lists_every_geom(site):
    from cogra import geoms

    text = (site / "api.html").read_text()
    for name in dir(geoms):
        if name.startswith("geom_"):
            assert f'id="cogra.geoms.{name}"' in text, name


def test_gallery_shows_code_for_each_panel(site):
    text = (site / "gallery.html").read_text()
    setup, code = build.gallery_code((ROOT / "examples" / "gallery.py").read_text())
    assert "rng = np.random.default_rng" in setup
    assert len(code) == text.count('<figure class="geom"')
    assert all("ax" in c for c in code.values() if c != "g.geom_blank(ax)")


@pytest.mark.parametrize(
    "path, expected",
    [
        ("src/cogra/style.py", True),
        ("examples/paper/example.pdf", False),  # listed in .gitignore
        ("examples/paper/regret_value_of_computation_site/index.html", False),
        ("missing.txt", False),
    ],
)
def test_in_repo_follows_gitignore(path, expected):
    assert build._in_repo(ROOT / path) is expected


def test_worn_printing_parts(site):
    """Every page carries the scan filter and the worn switch; the specks and
    the worn copies the switch shows exist."""
    for name, _ in build.NAV:
        text = (site / name).read_text()
        assert 'id="cogra-scan"' in text, name
        assert "worn-toggle" in text, name
    for tile in ("cogra-specks-a.png", "cogra-specks-b.png"):
        assert (site / "web" / tile).stat().st_size > 1000
    for name in build.WORN_FIGURES:
        assert (site / "figures" / name.replace(".png", "-scan.png")).is_file()
    gallery = (site / "gallery.html").read_text()
    assert gallery.count('class="worn-only') == gallery.count('class="clean-only')


def test_images_never_sit_inside_paragraphs(site):
    """The text filter goes on paragraphs; an image inside one would be greyed."""
    import re

    for page in site.glob("*.html"):
        assert not re.search(r"<p>[^<]*<img", page.read_text()), page.name


def test_controls_are_drawn_in_ink():
    """No page styling leaves form controls to the system accent colour."""
    for path in (
        "extras/web/cogra.css",
        "extras/web/cogra-specimen.html",
        "src/cogra/paper/apa1980.css",
        "extras/scanfont/specimen.html",
        "docs/site.css",
    ):
        text = (ROOT / path).read_text()
        assert "accent-color" not in text, path
    css = (ROOT / "extras" / "web" / "cogra.css").read_text()
    assert ':is(.cogra-page, .cogra-controls) input[type="checkbox"]:checked' in css


def test_wrap_code_keeps_the_code():
    """Code blocks get one span per line, so long lines can wrap, and copying
    the block still gives the original text, blank lines included."""
    import html
    import re

    code = "import cogra\n\nfig, ax = plt.subplots()  # a comment &lt;here&gt;\n    indented()\n"
    out = build.wrap_code(f"<p>x</p><pre><code>{code}</code></pre>")
    assert out.count('<span class="ln">') == 4
    text = html.unescape(re.sub(r"<[^>]+>", "", out.removeprefix("<p>x</p>")))
    assert text == html.unescape(code)


def test_no_system_highlight_colour():
    for path in ("extras/web/cogra.css", "src/cogra/paper/apa1980.css", "docs/site.css"):
        assert "::selection" in (ROOT / path).read_text(), path
