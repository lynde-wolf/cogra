"""Build the cogra documentation site into docs/_site.

    uv run --extra docs python docs/build.py            # the whole site
    uv run --extra docs python docs/build.py --quick    # without the worn gallery images
    python3 -m http.server 8000 --directory docs/_site

The site is styled with extras/web/cogra.css itself, so every page is also a
specimen of the web styling. The pages come from the repository's own
sources, so nothing here needs keeping in step by hand:

- the tutorial, changes and contributing pages from the Markdown files at the root;
- the geom gallery from examples/gallery.py (one figure per geom, with its code);
- the API reference from the package's signatures and docstrings;
- the example papers from examples/paper/make_*.py (as live paginated pages).
"""

from __future__ import annotations

import argparse
import ast
import html
import importlib.util
import inspect
import re
import shutil
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import markdown
import matplotlib.pyplot as plt
import numpy as np

import cogra
from cogra import geoms, paper, wear

DOCS = Path(__file__).resolve().parent
ROOT = DOCS.parent
OUT = DOCS / "_site"
REPO = "https://github.com/lynde-wolf/cogra"
BLOB = f"{REPO}/blob/main/"

NAV = [
    ("index.html", "Home"),
    ("tutorial.html", "Tutorial"),
    ("gallery.html", "Geoms"),
    ("api.html", "API"),
    ("web.html", "Web pages"),
    ("papers.html", "Papers"),
    ("fonts.html", "Fonts"),
    ("about.html", "About"),
]
# Markdown files that are pages of this site; links to anything else in the
# repository go to GitHub
SITE_PAGES = {
    "README.md": "index.html",
    "TUTORIAL.md": "tutorial.html",
    "CHANGES.md": "changes.html",
    "CONTRIBUTING.md": "contributing.html",
    "extras/scanfont/README.md": "fonts.html",
    "docs/about.md": "about.html",
}


# the SVG filters behind worn printing, pasted into every page (browsers
# ignore filters referenced from another file)
FILTERS = re.sub(
    r"\A<!--.*?-->\s*", "", (ROOT / "extras" / "web" / "cogra-filters.html").read_text(), flags=re.S
)

# ---------------------------------------------------------------- pages


def sidebar_from_headings(body: str) -> list[tuple[str, str, int]]:
    """(id, text, level) for each h2 and h3 with an id, for the sidebar."""
    return [
        (hid, re.sub(r"<[^>]+>", "", text).strip(), int(level))
        for level, hid, text in re.findall(r'<h([23]) id="([^"]+)"[^>]*>(.*?)</h\1>', body, re.S)
    ]


def sidebar_html(items: list[tuple[str, str, int]], label: str = "On this page") -> str:
    """The left sidebar: level 2 entries flush, level 3 indented, and level 1
    as group headings (used by the API page)."""
    if not items:
        return ""
    rows = "".join(
        f'<li class="{ {1: "head", 2: "top", 3: "sub"}[level] }"><a href="#{hid}">{text}</a></li>'
        for hid, text, level in items
    )
    return f"""<aside class="sidebar"><details open><summary>{label}</summary>
<nav aria-label="{label}"><ul>{rows}</ul></nav></details></aside>"""


def wrap_code(body: str) -> str:
    """Put each line of every code block in its own span, so a long line can
    wrap with a hanging indent (see .ln in site.css) instead of running off
    the side. Each span keeps its newline, so copied code is unchanged."""

    def lines(m):
        code = m.group(2).rstrip("\n").split("\n")
        return m.group(1) + "".join(f'<span class="ln">{ln}\n</span>' for ln in code) + "</code></pre>"

    return re.sub(r"(<pre[^>]*><code[^>]*>)(.*?)</code></pre>", lines, body, flags=re.S)


def page(title: str, body: str, current: str, sidebar=None, wide: bool = False, home: bool = False) -> str:
    """A complete page: the top bar, then either the home layout or the
    sidebar of links on the left with the content beside it. sidebar: a list
    of (id, text, level); None takes the page's h2 and h3 headings."""
    nav = "\n".join(
        f'<a href="{href}"{" aria-current=page" if href == current else ""}>{label}</a>'
        for href, label in NAV
    )
    name = "cogra: the Cognitive Revolution Aesthetic" if home else f"{title} · cogra"
    body = wrap_code(body)
    # Lynde's notes for anyone reading the home page's source
    note_head = "\n// why are you reading the html? no judgement just a suprise" if home else ""
    note_foot = (
        '\n// you might be suprised to learn that while a some of the package is "vibe coded" I still read my code :P -lwg'
        if home
        else ""
    )
    if home:
        main = f'<main class="home">{body}</main>'
    else:
        side = sidebar_html(sidebar_from_headings(body) if sidebar is None else sidebar)
        main = f'<div class="layout">{side}<main class="content{" wide" if wide else ""}">{body}</main></div>'
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(name)}</title>
<meta name="description" content="cogra (Cognitive Revolution Aesthetic): the look of mid-century psychology journals for figures, papers and web pages.">
<link rel="icon" href="assets/favicon-32.png">
<link rel="stylesheet" href="web/cogra.css">
<link rel="stylesheet" href="site.css">
<script>
// before the first paint: theme, and worn printing (on unless the reader
// turned it off here, or their system asks for more contrast){note_head}
(function () {{
  const r = document.documentElement;
  let theme = null, worn = null;
  try {{ theme = localStorage.getItem("cogra-theme"); worn = localStorage.getItem("cogra-worn"); }} catch (e) {{}}
  if (theme) r.dataset.theme = theme;
  if (worn === null) worn = matchMedia("(prefers-contrast: more)").matches ? "0" : "1";
  if (worn === "1") r.classList.add("worn");
}})();
</script>
</head>
<body>
{FILTERS}
<header class="site-head"><div class="site-head-inner">
<a class="site-title" href="index.html"><img class="ink-img" src="assets/cogra-icon-scan-512.png" alt=""><span>cogra</span></a>
<nav class="site-nav" aria-label="Site">{nav}</nav>
<div class="site-tools cogra-controls"><a href="{REPO}">GitHub</a>
<label class="worn-toggle" title="Text through the archival-scan filter, worn figures and dust specks"><input type="checkbox"> toggle worn</label>
<button class="theme-toggle" type="button" aria-label="Switch light and dark">theme: auto</button></div>
</div></header>
{main}
<footer class="site-foot"><div class="site-foot-inner">
<span>© 2026 Lynde Wolf Gorneault · MIT licence · fonts under the GUST Font License ·
<a href="changes.html">changes</a> · <a href="contributing.html">contributing</a></span>
<span>v{cogra.__version__}</span></div></footer>
<script>
(function () {{
  const root = document.documentElement, btn = document.querySelector(".theme-toggle");
  const order = ["auto", "light", "dark"];
  const show = () => {{ btn.textContent = "theme: " + (root.dataset.theme || "auto"); }};
  btn.addEventListener("click", () => {{
    const next = order[(order.indexOf(root.dataset.theme || "auto") + 1) % order.length];
    if (next === "auto") delete root.dataset.theme; else root.dataset.theme = next;
    try {{ if (next === "auto") localStorage.removeItem("cogra-theme"); else localStorage.setItem("cogra-theme", next); }} catch (e) {{}}
    show();
  }});
  show();
  const worn = document.querySelector(".worn-toggle input");
  worn.checked = root.classList.contains("worn");
  worn.addEventListener("change", () => {{
    root.classList.toggle("worn", worn.checked);
    try {{ localStorage.setItem("cogra-worn", worn.checked ? "1" : "0"); }} catch (e) {{}}
  }});
  // the sidebar: highlight the section in view; start closed on a phone
  const side = document.querySelector(".sidebar details");
  const phone = window.matchMedia("(max-width: 52rem)");
  const fit = () => {{ if (side) side.open = !phone.matches; }};
  fit(); phone.addEventListener("change", fit);
  const links = [...document.querySelectorAll(".sidebar a[href^='#']")];
  const targets = links.map(a => document.getElementById(decodeURIComponent(a.hash.slice(1)))).filter(Boolean);
  if (targets.length && "IntersectionObserver" in window) {{
    const seen = new Set();
    const mark = () => {{
      const first = targets.find(t => seen.has(t));
      links.forEach(a => a.classList.toggle("active", first && a.hash.slice(1) === first.id));
    }};
    const io = new IntersectionObserver(es => {{
      es.forEach(e => e.isIntersecting ? seen.add(e.target) : seen.delete(e.target)); mark();
    }}, {{ rootMargin: "-10% 0px -70% 0px" }});
    targets.forEach(t => io.observe(t));
  }}
}})();{note_foot}
</script>
</body>
</html>
"""


def md(text: str, source: str) -> str:
    """Markdown to HTML, with links rewritten for the site (see links())."""
    out = markdown.Markdown(extensions=["fenced_code", "tables", "toc", "sane_lists"]).convert(text)
    # wide tables scroll on their own instead of widening the page on a phone
    out = out.replace("<table>", '<div class="cogra-tablewrap"><table>').replace("</table>", "</table></div>")
    return links(out, source)


def links(page_html: str, source: str) -> str:
    """Point relative links at the site's pages or copied figures, and
    everything else in the repository at GitHub. source: the repository
    path of the file the HTML came from."""
    base = Path(source).parent

    def fix(m):
        attr, url = m.group(1), m.group(2)
        if re.match(r"^(https?:|mailto:|#|data:)", url):
            return m.group(0)
        path, _, frag = url.partition("#")
        repo_path = (base / path).as_posix() if path else source
        repo_path = re.sub(r"(^|/)\./", r"\1", repo_path)
        if repo_path in SITE_PAGES:
            new = SITE_PAGES[repo_path]
        elif repo_path.startswith("examples/figures/"):
            new = "figures/" + Path(repo_path).name
        else:
            new = BLOB + repo_path
        return f'{attr}="{new}{"#" + frag if frag else ""}"'

    page_html = re.sub(r'(href|src)="([^"]+)"', fix, page_html)
    # figures are black ink on white paper (a negative in dark mode); those
    # with a worn copy get both, and the worn printing switch picks one
    page_html = re.sub(r'<img ([^>]*?)src="figures/([^"]+)"([^>]*)>', _figure_pair, page_html)
    # an image alone in its paragraph becomes a figure, so the worn printing's
    # text filter (which greys anything that is not ink) never reaches it
    return re.sub(r"<p>((?:\s*<img [^>]*>)+)\s*</p>", r'<figure class="site-figure">\1</figure>', page_html)


def _figure_pair(m) -> str:
    before, name, after = m.groups()
    if name not in WORN_FIGURES:
        return f'<img class="ink-img" {before}src="figures/{name}"{after}>'
    worn = name.replace(".png", "-scan.png")
    return (
        f'<img class="ink-img clean-only" {before}src="figures/{name}"{after}>'
        f'<img class="ink-img worn-only" {before}src="figures/{worn}"{after}>'
    )


def markdown_page(source: str, title: str, out_name: str, current: str = "", drop_h1: bool = True) -> None:
    text = (ROOT / source).read_text()
    if drop_h1:
        text = re.sub(r"\A# .*\n", "", text)
    body = f"<h1>{html.escape(title)}</h1>\n" + md(text, source)
    (OUT / out_name).write_text(page(title, body, current or out_name))


# README figures that get a worn copy. The others compare clean with worn
# (wear.png, paper.png) or a colour figure with its cogra version (styles.png,
# restyle.png), which a 1-bit scan would erase.
WORN_FIGURES = {"geoms.png", "signif.png"}


def wear_png(src: Path, dst: Path) -> None:
    """A worn (archival-scan) copy of a finished PNG, the same size: worn at
    twice its resolution, so the scan's stair-steps fall at the original's."""
    from PIL import Image

    with Image.open(src) as im:
        big = im.convert("L").resize((im.width * 2, im.height * 2), Image.Resampling.LANCZOS)
    import numpy as np

    img, _ = wear.apply(np.asarray(big), look="scan", dpi=400, scan_dpi=200, specks=False)
    img.convert("L").save(dst)


# ---------------------------------------------------------------- home


# the strip of figures across the top of the home page: gallery panels,
# each linking to its place in the gallery
# The home page's strip of figures: the plots people make most often, each
# drawn square and unlabelled, linking to its geom in the gallery.
# (gallery anchor, description, drawing function on an Axes)
def _strip_box(ax, rng):
    geoms.geom_boxplot(ax, [rng.normal(0, 1, 80), rng.normal(0.9, 1.3, 80), rng.normal(0.4, 0.8, 80)])


def _strip_histogram(ax, rng):
    x = np.r_[rng.normal(0, 1, 150), rng.normal(1.6, 0.8, 150)]
    geoms.geom_histogram(ax, x, np.repeat(["a", "b"], 150), bins=16)


def _strip_bars(ax, rng):
    cogra.bars(ax, [0, 1, 2], [3.1, 4.4, 4.9], yerr=[0.3, 0.35, 0.4])
    ax.set_ylim(0, 6)
    cogra.signif(ax, 0, 1, p=0.03)
    cogra.signif(ax, 1, 2, p=0.21, ns=True)
    cogra.signif(ax, 0, 2, p=0.0004)


def _strip_smooth(ax, rng):
    x = rng.normal(0, 1, 120)
    y = 0.6 * x + rng.normal(0, 0.7, 120)
    geoms.geom_point(ax, x, y, size=2.5)
    geoms.geom_smooth(ax, x, y, method="lm")


def _strip_density(ax, rng):
    x = np.r_[rng.normal(0, 1, 200), rng.normal(1.4, 0.7, 200)]
    geoms.geom_density(ax, x, np.repeat(["a", "b"], 200), hatch=True)


def _strip_line(ax, rng):
    t = np.arange(1, 6)
    for k, (base, slope) in enumerate([(1.0, 0.45), (1.4, 0.2)]):
        y = base + slope * t + rng.normal(0, 0.08, t.size)
        geoms.geom_line(ax, t, y, group=[f"g{k}"] * t.size, markers=True)
        geoms.geom_errorbar(ax, t, y - 0.18, y + 0.18, width=0.15)


STRIP = [
    ("boxplot", "geom_boxplot", _strip_box),
    ("histogram-grouped", "geom_histogram", _strip_histogram),
    ("col", "cogra.bars with significance brackets", _strip_bars),
    ("smooth-lm", "geom_point and geom_smooth", _strip_smooth),
    ("density", "geom_density", _strip_density),
    ("line", "geom_line with geom_errorbar", _strip_line),
]


def strip_thumbnails(figdir: Path, quick: bool) -> None:
    """Draw the home page's strip, clean and as an archival scan."""
    cogra.use()
    for i, (stem, _, draw) in enumerate(STRIP):
        fig, ax = plt.subplots(figsize=(2.2, 2.2))
        draw(ax, np.random.default_rng(100 + i))
        ax.set(xticks=[], yticks=[], xlabel="", ylabel="")
        ax.set_xticklabels([])
        fig.subplots_adjust(0.04, 0.04, 0.96, 0.96)
        clean, worn = figdir / f"thumb-{stem}.png", figdir / f"thumb-{stem}-scan.png"
        fig.savefig(clean, dpi=150)
        if quick:
            shutil.copyfile(clean, worn)
        else:
            cogra.save_vintage(fig, worn, look="scan", dpi=450, scan_dpi=150)
        plt.close(fig)


FEATURES = [
    ("Styles", [("API", "api.html#styles"), ("Tutorial", "tutorial.html#your-first-figure")]),
    ("ggplot2-style geoms", [("API", "api.html#ggplot2-style-geoms"), ("Gallery", "gallery.html")]),
    (
        "Bars, violins and rainclouds",
        [("API", "api.html#period-plots"), ("Tutorial", "tutorial.html#bars-violins-and-rainclouds")],
    ),
    (
        "Significance brackets",
        [("API", "api.html#significance"), ("Tutorial", "tutorial.html#significance-brackets")],
    ),
    (
        "Restyling finished figures",
        [
            ("API", "api.html#restyling-finished-figures"),
            ("Tutorial", "tutorial.html#restyling-a-figure-you-already-have"),
        ],
    ),
    ("Worn copies", [("API", "api.html#worn-copies"), ("Tutorial", "tutorial.html#worn-copies")]),
    (
        "seaborn, pandas, plotly, Altair",
        [("Tutorial", "tutorial.html#3-seaborn-pandas-and-other-plotting-libraries")],
    ),
    (
        "Papers in the 1980 layout",
        [
            ("API", "api.html#papers"),
            ("Examples", "papers.html"),
            ("Tutorial", "tutorial.html#4-papers-in-the-1980-journal-layout"),
        ],
    ),
    ("R and ggplot2", [("Tutorial", "tutorial.html#5-r-and-ggplot2")]),
    ("Web pages", [("Demo", "web.html"), ("Tutorial", "tutorial.html#6-web-pages")]),
    ("LaTeX", [("Tutorial", "tutorial.html#7-latex-documents")]),
    ("Fonts", [("Specimen", "fonts.html"), ("Tutorial", "tutorial.html#8-the-fonts-in-other-apps")]),
]


def _stem(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def home() -> None:
    strip = "".join(
        f'<a href="gallery.html#{stem}" title="{html.escape(alt)}">'
        f'<img class="ink-img clean-only" src="gallery/thumb-{stem}.png" alt="{html.escape(alt)}">'
        f'<img class="ink-img worn-only" src="gallery/thumb-{stem}-scan.png" alt="{html.escape(alt)}"></a>'
        for stem, alt, _ in STRIP
    )
    contents = "".join(f'<li><a href="{href}">{label}</a></li>' for href, label in NAV[1:])
    contents += (
        '<li><a href="changes.html">Changes</a></li><li><a href="contributing.html">Contributing</a></li>'
    )
    features = "".join(
        f"<li>{name}: "
        + '<span class="sep">|</span>'.join(f'<a href="{h}">{t}</a>' for t, h in targets)
        + "</li>"
        for name, targets in FEATURES
    )
    body = f"""<h1>CogRA: the Cognitive Revolution's Aesthetics</h1>
<div class="home-strip">{strip}</div>
<div class="home-row">
<div class="home-intro">
<p class="lede">The look of experimental psychology papers published around 1980
but adapted for matplotlib figures, ggplot2, papers, LaTeX and web pages.
<a href="about.html">Why?</a></p>
<pre><code>pip install "cogra @ git+{REPO}"</code></pre>
<p>Not sure what to do? Start with the <a href="tutorial.html">tutorial</a>.</p>
</div>
<div class="home-box"><h2>Contents</h2><ul>{contents}</ul></div>
<div class="home-box features"><h2>Features</h2><ul>{features}</ul></div>
</div>"""
    (OUT / "index.html").write_text(page("cogra", body, "index.html", home=True))


# ---------------------------------------------------------------- gallery


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class _RenameAxes(ast.NodeTransformer):
    def __init__(self, old):
        self.old = old

    def visit_Name(self, node):
        if node.id == self.old:
            node.id = "ax"
        return node


def gallery_code(source: str) -> tuple[str, dict[str, str]]:
    """From examples/gallery.py: the shared setup code, and for each panel
    the statements its lambda runs, written as code on an Axes `ax`."""
    tree = ast.parse(source)
    panels_node = next(
        n for n in tree.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "panels"
    )
    start = next(n for n in tree.body if not isinstance(n, (ast.Import, ast.ImportFrom, ast.Expr))).lineno
    setup = "\n".join(source.splitlines()[start - 1 : panels_node.lineno - 1]).strip()
    code = {}
    for key, fn in zip(panels_node.value.keys, panels_node.value.values):
        body = _RenameAxes(fn.args.args[0].arg).visit(fn.body)
        stmts = body.elts if isinstance(body, ast.Tuple) else [body]
        code[key.value] = "\n".join(ast.unparse(s) for s in stmts)
    return setup, code


def gallery(quick: bool) -> None:
    src_path = ROOT / "examples" / "gallery.py"
    setup, code = gallery_code(src_path.read_text())
    gal = _load(src_path, "cogra_gallery")  # runs the setup: cogra.use() and the data
    figdir = OUT / "gallery"
    figdir.mkdir()
    strip_thumbnails(figdir, quick)
    cogra.use()  # the gallery's own style, as examples/gallery.py sets it
    items = []
    for name, draw in gal.panels.items():
        stem = _stem(name)
        fig, ax = plt.subplots(figsize=(2.6, 2.05))
        draw(ax)
        ax.tick_params(labelsize=6.5)
        fig.tight_layout(pad=0.5)
        fig.savefig(figdir / f"{stem}.png", dpi=160)
        if quick:  # the worn switch still has an image to show
            shutil.copyfile(figdir / f"{stem}.png", figdir / f"{stem}-scan.png")
        else:
            cogra.save_vintage(fig, figdir / f"{stem}-scan.png", look="scan", dpi=480, scan_dpi=220)
        plt.close(fig)
        called = sorted(set(re.findall(r"\bg\.(geom_\w+)", code[name])), key=code[name].index)
        refs = ", ".join(f'<a href="api.html#cogra.geoms.{c}"><code>{c}</code></a>' for c in called)
        items.append(
            f'<figure class="geom" id="{stem}"><h3><code>geom_{html.escape(name)}</code></h3>'
            f'<img class="clean-only ink-img" src="gallery/{stem}.png" alt="geom_{html.escape(name)} drawn in the cogra style" loading="lazy">'
            f'<img class="worn-only ink-img" src="gallery/{stem}-scan.png" alt="geom_{html.escape(name)}, as an archival scan" loading="lazy">'
            f"<pre><code>{html.escape(code[name])}</code></pre>"
            f'<span class="api">API: {refs}</span></figure>'
        )
    body = f"""<h1>Every geom</h1>
<p class="lede">One function for each ggplot2 4.0 geom, drawn in black ink.
Each takes a matplotlib <code>Axes</code> first; extra keywords go to matplotlib.
All data are synthetic.</p>
<div class="controls cogra-controls"><span>{len(items)} panels, from <a href="{BLOB}examples/gallery.py"><code>examples/gallery.py</code></a>.
With <i>toggle worn</i> on (top right) each is shown as <code>save_vintage</code> saves it.</span></div>
<details class="setup"><summary>The shared setup code (data used by the panels below)</summary>
<pre><code>{html.escape(setup)}</code></pre></details>
<div class="gallery" id="gallery">
{chr(10).join(items)}
</div>"""
    side = [(_stem(n), f"geom_{html.escape(n)}", 2) for n in gal.panels]
    (OUT / "gallery.html").write_text(page("Geoms", body, "gallery.html", sidebar=side, wide=True))


# ---------------------------------------------------------------- API


def _api_groups():
    geom_fns = [
        f
        for n, f in inspect.getmembers(geoms, inspect.isfunction)
        if n.startswith("geom_") and f.__module__ == geoms.__name__
    ]
    geom_fns.sort(key=lambda f: inspect.getsourcelines(f)[1])
    return [
        ("Styles", "cogra", [cogra.use, cogra.register_fonts, cogra.register_styles]),
        ("Restyling finished figures", "cogra", [cogra.restyle, cogra.cogra]),
        (
            "Period plots",
            "cogra",
            [cogra.bars, cogra.violin, cogra.raincloud, cogra.topoplot, cogra.density_topo, cogra.halftone],
        ),
        ("Significance", "cogra", [cogra.signif, cogra.stars, cogra.format_p]),
        ("Worn copies", "cogra", [cogra.save_vintage, cogra.cache_dir, cogra.clear_cache]),
        ("The wear looks", "cogra.wear", [wear.apply, wear.scan, wear.xerox, wear.aged]),
        ("ggplot2-style geoms", "cogra.geoms", geom_fns),
        ("Papers", "cogra.paper", [paper.Paper, paper.find_chrome, paper.title_case]),
    ]


def _signature(obj) -> str:
    """The signature with annotations shown as written (they are strings
    under `from __future__ import annotations`)."""
    try:
        sig = str(inspect.signature(obj))
    except (TypeError, ValueError):
        return "(...)"
    sig = re.sub(r""": (?:'([^']*)'|"([^"]*)")""", lambda m: ": " + (m.group(1) or m.group(2)), sig)
    return re.sub(r"""-> (?:'([^']*)'|"([^"]*)")$""", lambda m: "-> " + (m.group(1) or m.group(2)), sig)


def _entry(qual: str, obj, methods=()) -> str:
    try:
        src = Path(inspect.getsourcefile(obj)).resolve().relative_to(ROOT).as_posix()
        line = inspect.getsourcelines(obj)[1]
        source = f'<p class="api-src"><a href="{BLOB}{src}#L{line}">source</a></p>'
    except (TypeError, OSError, ValueError):
        source = ""
    kind = "class " if inspect.isclass(obj) else ""
    target = obj.__init__ if inspect.isclass(obj) else obj
    sig = _signature(target).replace("(self, ", "(").replace("(self)", "()")
    doc = html.escape(inspect.getdoc(obj) or "")
    out = (
        f'<div class="api-entry" id="{qual}"><pre class="api-sig"><code>{kind}<span class="name">{qual}</span>'
        f"{html.escape(sig)}</code></pre>"
        f'<div class="api-doc">{doc}</div>{source}'
    )
    if methods:
        out += (
            '<div class="api-methods">'
            + "".join(_entry(f"{qual}.{m}", getattr(obj, m)) for m in methods)
            + "</div>"
        )
    return out + "</div>"


def api() -> None:
    groups = _api_groups()
    documented = {f.__name__ for _, _, fns in groups for f in fns}
    missing = [
        n
        for n in cogra.__all__
        if callable(getattr(cogra, n)) and not inspect.ismodule(getattr(cogra, n)) and n not in documented
    ]
    if missing:
        raise SystemExit(f"public names missing from the API page: {missing}")
    side, sections = [], []
    for title, mod, fns in groups:
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        side.append((slug, title, 1))
        side += [(f"{mod}.{f.__name__}", f.__name__, 3) for f in fns]
        entries = []
        for f in fns:
            methods = ("from_markdown", "save", "pdf", "html") if f is paper.Paper else ()
            entries.append(_entry(f"{mod}.{f.__name__}", f, methods))
        sections.append(
            f'<section class="api-group"><h2 id="{slug}">{title}</h2>{"".join(entries)}</section>'
        )
    body = f"""<h1>API reference</h1>
<p class="lede">Every public function, from its signature and docstring.
<code>import cogra</code> registers the fonts and styles; the geoms are in
<code>cogra.geoms</code>, the wear looks in <code>cogra.wear</code>, and papers in
<code>cogra.paper</code>.</p>
{"".join(sections)}"""
    (OUT / "api.html").write_text(page("API", body, "api.html", sidebar=side))


# ---------------------------------------------------------------- web pages


DEMO = """<article class="cogra-page cogra-worn" id="demo">
<div class="cogra-ink">
<div class="cogra-runhead"><span>Fenwick Quarterly of Perception</span><span>1958, 4, 211–213</span></div>
<h1>Judged Loudness of a Tone Heard Through a Partition</h1>
<p class="cogra-author">Ruth A. Pellam</p>
<p class="cogra-affil">Halvorsen College</p>
<div class="cogra-summary"><p>Twelve listeners judged the loudness of a 1,000-cps tone
heard directly and through a plaster partition. The partition lowered judged loudness by
less than its measured attenuation would predict.</p></div>
<h2>Method</h2>
<p><span class="cogra-runin">Apparatus.</span> The tone was produced by a beat-frequency
oscillator and presented for 1.5 sec. through a loudspeaker 2 m. from the listener, who sat
either in the same room or behind the partition.</p>
<p>Each listener gave a magnitude estimate on each of 40 trials, the first 8 of which were
discarded as practice.<sup>1</sup></p>
<div class="cogra-notes"><p><sup>1</sup> This page is invented, to show cogra.css.</p></div>
</div>
</article>"""


def web() -> None:
    shutil.copytree(ROOT / "extras" / "web", OUT / "web")
    snippet = html.escape(
        "<!-- beside cogra.css: fonts/ and cogra-specks-*.png -->\n"
        '<link rel="stylesheet" href="cogra.css">\n'
        "<!-- once, in <body>: the <svg> block from cogra-filters.html -->\n\n"
        '<article class="cogra-page cogra-worn">\n  <div class="cogra-ink">\n'
        "    <h1>Judged Loudness of a Tone ...</h1>\n"
        '    <p class="cogra-author">Ruth A. Pellam</p>\n    ...\n  </div>\n</article>'
    )
    body = f"""<h1>Web pages</h1>
<p class="lede"><code>cogra.css</code> sets a web page as a mid-century journal
article: justified Schola type in black on white, centred capital headings,
run-in italic headings, rules-only tables and footnotes under a short rule.
This site takes its type and colours from it, and its worn printing from
<code>cogra-filters.html</code>.</p>
<h2 id="try-it">Try it</h2>
<div class="controls cogra-controls" role="group" aria-label="Printing of the demo">
<label><input type="radio" name="look" value="clean"> Clean type</label>
<label><input type="radio" name="look" value="scan" checked> Archival scan (<code>.cogra-worn</code>)</label>
<label><input type="radio" name="look" value="photocopy"> Photocopy (<code>.cogra-worn.cogra-photocopy</code>)</label>
</div>
<div class="demo-live">{DEMO}</div>
<p>The page follows the reader's dark-mode setting and turns into a microfilm
negative; try the theme switch at the top of this page. Readers whose system
asks for more contrast get clean type.</p>
<h2 id="using-it">Using it</h2>
<p>Copy <code>cogra.css</code>, its <code>fonts/</code> folder and the two speck images from
<a href="{BLOB}extras/web"><code>extras/web/</code></a> next to your page:</p>
<pre><code>{snippet}</code></pre>
<p>The filters have to be pasted into the same HTML file, because most browsers
ignore filters loaded from a separate SVG file. The
<a href="tutorial.html#6-web-pages">tutorial</a> lists every class.</p>
<h2 id="the-full-specimen">The full specimen</h2>
<p>An invented 1960 article that uses every class, with its own controls for the
look and the amount of wear (<a href="web/cogra-specimen.html">open on its own</a>).</p>
<iframe class="demo-frame" src="web/cogra-specimen.html" title="cogra.css specimen page" loading="lazy"></iframe>
<script>
document.querySelectorAll('input[name="look"]').forEach(r => r.addEventListener("change", e => {{
  const d = document.getElementById("demo");
  d.classList.toggle("cogra-worn", e.target.value !== "clean");
  d.classList.toggle("cogra-photocopy", e.target.value === "photocopy");
}}));
</script>"""
    (OUT / "web.html").write_text(page("Web pages", body, "web.html"))


# ---------------------------------------------------------------- papers and fonts


PAPERS = [
    (
        "example",
        "The judged duration of tones (1979)",
        "A short report in the house style of about 1979: title block, abstract, a table and one figure.",
    ),
    (
        "regret_value_of_computation",
        "Regret as the value of computation",
        "A modern theory paper: a theorem and its proof, a stopping rule, footnotes, tables and a line figure.",
    ),
    (
        "bayes_bellman",
        "Bayes–Bellman consistency",
        "A longer theory preprint with eleven numbered equations, a theorem, two tables and a bar figure.",
    ),
]


def papers() -> None:
    (OUT / "papers").mkdir()
    cards = []
    for stem, title, text in PAPERS:
        site = OUT / "papers" / stem
        mod = _load(ROOT / "examples" / "paper" / f"make_{stem}.py", f"cogra_make_{stem}")
        mod.build(site_dir=site, pdf=None)
        thumb = _first_page(stem)
        img = (
            f'<a href="papers/{stem}/index.html"><img src="{thumb}" alt="First page of the paper" loading="lazy"></a>'
            if thumb
            else ""
        )
        pdf = ROOT / "examples" / "paper" / f"{stem}.pdf"
        pdf_link = f' · <a href="{BLOB}examples/paper/{stem}.pdf">PDF</a>' if _in_repo(pdf) else ""
        cards.append(
            f'<div class="paper-card">{img}<h3><a href="papers/{stem}/index.html">{title}</a></h3>'
            f'<p>{text}</p><p><a href="papers/{stem}/index.html">Web pages</a>{pdf_link} · '
            f'<a href="{BLOB}examples/paper/{stem}.md">Markdown source</a></p></div>'
        )
    body = f"""<h1>Papers</h1>
<p class="lede"><code>cogra.paper</code> sets a paper written in Markdown as an APA
journal article of about 1980: two justified columns, running heads, footnotes at the
foot of their column, figures across the top of a page, and TeX math in the Schola
math font. The pages paginate themselves in the browser; <code>pdf()</code> prints them.</p>
<pre><code># writes my_paper_site/index.html and my_paper.pdf
cogra-paper my_paper.md --pdf my_paper.pdf</code></pre>
<p>All three examples are invented, authors, journals and data included; each says
so in its author note. The worn look can be switched off with the box above the pages.</p>
<h2 id="examples">Examples</h2>
<div class="papers">{"".join(cards)}</div>
<h2 id="writing-your-own">Writing your own</h2>
<p>The <a href="tutorial.html#4-papers-in-the-1980-journal-layout">tutorial</a>
covers the front matter, figures, tables, math and changing the layout.</p>"""
    (OUT / "papers.html").write_text(page("Papers", body, "papers.html"))


def _in_repo(path: Path) -> bool:
    """True if path exists and .gitignore does not leave it out, so a link to
    it on GitHub works. Handles the patterns this repository uses: globs
    whose * stays within one folder, bare names that match at any depth, and
    folder/ for a whole folder."""
    if not path.exists():
        return False
    rel = path.relative_to(ROOT).as_posix()
    for line in (ROOT / ".gitignore").read_text().splitlines():
        pat = line.strip()
        if not pat or pat.startswith("#"):
            continue
        body = pat.rstrip("/")
        rx = re.escape(body).replace(r"\*", "[^/]*").replace(r"\?", "[^/]")
        rx = (r"(^|.*/)" if "/" not in body else "^") + rx + "(/.*)?$"  # a match also covers what is inside
        if re.match(rx, rel):
            return False
    return True


def _first_page(stem: str) -> str | None:
    """A thumbnail of the paper's first page, from its committed PDF."""
    if stem == "example":
        return "figures/paper.png"
    pdf = ROOT / "examples" / "paper" / f"{stem}.pdf"
    try:
        import pymupdf
    except ImportError:
        return None
    if not _in_repo(pdf):
        return None
    out = OUT / "papers" / f"{stem}-p1.png"
    with pymupdf.open(pdf) as doc:
        doc[0].get_pixmap(dpi=72).save(out)
    return f"papers/{out.name}"


def fonts() -> None:
    shutil.copytree(ROOT / "extras" / "scanfont", OUT / "scanfont", ignore=shutil.ignore_patterns("*.py"))
    text = (ROOT / "extras" / "scanfont" / "README.md").read_text()
    text = re.sub(r"\A# .*\n", "", text)
    body = f"""<h1>Fonts</h1>
<h2 id="in-figures">In figures</h2>
<p>The package ships <b>TeX Gyre Heros</b> (the sans-serif for figure labels) and
<b>TeX Gyre Schola</b> (the serif, for <code>labels="serif"</code> and papers), and
registers them with matplotlib on import. Figures use these clean faces;
<code>save_vintage()</code> adds the wear afterwards, to the whole figure.</p>
<h2 id="in-slides-and-documents">In slides and documents</h2>
<p>For slides, word processors and design apps there are also <b>scanned</b>
versions, installable as ordinary fonts: Schola Scan and Heros Scan, and softer
Soft versions (<a href="{BLOB}extras/scanfont/fonts">download the .ttf files</a>).</p>
<iframe class="demo-frame" src="scanfont/specimen.html" title="Scan font specimen" loading="lazy"></iframe>
{md(text, "extras/scanfont/README.md")}"""
    (OUT / "fonts.html").write_text(page("Fonts", body, "fonts.html"))


# ---------------------------------------------------------------- build


def build(quick: bool = False) -> Path:
    t0 = time.time()
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copyfile(DOCS / "site.css", OUT / "site.css")
    shutil.copytree(ROOT / "examples" / "figures", OUT / "figures")
    (OUT / "assets").mkdir()
    for f in ("cogra-icon-scan-512.png", "favicon-32.png", "cogra-social-1280x640.png"):
        shutil.copyfile(ROOT / "assets" / "logo" / f, OUT / "assets" / f)
    (OUT / ".nojekyll").write_text("")  # serve folders such as _site as they are
    for name in sorted(WORN_FIGURES):
        wear_png(OUT / "figures" / name, OUT / "figures" / name.replace(".png", "-scan.png"))

    web()
    gallery(quick)  # before home(): it draws the home page's strip of figures
    home()
    markdown_page("TUTORIAL.md", "Tutorial", "tutorial.html")
    markdown_page("docs/about.md", "About", "about.html")
    markdown_page("CHANGES.md", "Changes", "changes.html")
    markdown_page("CONTRIBUTING.md", "Contributing", "contributing.html")
    api()
    fonts()
    papers()
    print(f"wrote {OUT} in {time.time() - t0:.0f} s")
    return OUT


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true", help="skip the worn gallery images")
    build(ap.parse_args().quick)
