"""
paper: set a paper as an APA journal article of about 1980, as a web page
and a PDF.

    from cogra import paper
    p = paper.Paper.from_markdown("my_paper.md")
    p.save("out/")              # out/index.html, paginated in the browser
    p.pdf("my_paper.pdf")       # same pages as a PDF (needs Chrome or Playwright)

or from the command line:  cogra-paper my_paper.md --pdf my_paper.pdf

The layout (apa1980.css) is the baseline, not a fixed template: every page
dimension and type size is a CSS custom property that Paper(style=...)
overrides, extra stylesheets can be added with css=[...], and columns=1
gives single-column pages. See TUTORIAL.md, "Papers", for the Markdown
conventions (front matter, headings, footnotes, figures, tables, references).

Needs pip install "cogra[paper]" for Markdown input. PDF output prints the
paginated page with headless Chrome (or Chromium, Edge, Brave), found on the
usual install paths or through $COGRA_CHROME, or with Playwright if it is
installed.
"""

from __future__ import annotations

import html
import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from html.parser import HTMLParser
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from matplotlib.figure import Figure

HERE = Path(__file__).resolve().parent
FONTS = HERE.parent / "fonts"
SCHOLA = [
    "texgyreschola-regular.otf",
    "texgyreschola-italic.otf",
    "texgyreschola-bold.otf",
    "texgyreschola-bolditalic.otf",
]
SMALL_WORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "but",
    "by",
    "for",
    "in",
    "nor",
    "of",
    "on",
    "or",
    "the",
    "to",
    "via",
    "vs",
    "with",
}
REF_HEADS = {"references", "reference notes"}
DEFAULT_PAGE = ("531pt", "726pt")
MATHJAX = HERE / "mathjax"
# MathJax (vendored in mathjax/) sets \(...\) and \[...\] as SVG in the Schola
# math font. paginate.js typesets #source before measuring it; fontCache
# "none" keeps every SVG self-contained so the pages can clone it.
MATHJAX_HEAD = """<script>
window.MathJax = {
  loader: { load: ["input/tex", "output/svg"], paths: { "mathjax-schola": "./mathjax/mathjax-schola" } },
  tex: { inlineMath: [["\\\\(", "\\\\)"]], displayMath: [["\\\\[", "\\\\]"]], tags: "ams" },
  svg: { font: "mathjax-schola", fontCache: "none", displayOverflow: "scale" },
  startup: { typeset: false }
};
</script>
<script src="mathjax/startup.js"></script>"""


# ---------------------------------------------------------------- helpers


def title_case(s: str) -> str:
    """Title case as APA journals of the period set it. Words that already
    contain capitals (SSRT, fMRI) are left alone."""
    words = s.split()

    def word(w, i):
        parts = w.split("-")
        out = []
        for j, p in enumerate(parts):
            if not p.islower():
                out.append(p)
            elif i == 0 or i == len(words) - 1 or j > 0 or p not in SMALL_WORDS:
                out.append(p[:1].upper() + p[1:])
            else:
                out.append(p)
        return "-".join(out)

    return " ".join(word(w, i) for i, w in enumerate(words))


def _sup_marks(s):
    """'Name^1' or 'Name^1,2' -> Name<sup>1</sup>."""
    return re.sub(r"\^(\d+(?:,\d+)*|[*\u2020\u2021\u00a7]|[a-z]\b)", r"<sup>\1</sup>", s)


def _urls(h):
    return re.sub(r'(?<!["=>])(https?://[^\s<]+)', r'<span class="url">\1</span>', h)


def _small_caps(h, words):
    for w in words:
        h = re.sub(
            rf"\b{re.escape(w)}(s?)\b", lambda m, w=w: f'<span class="sc">{w.lower()}{m.group(1)}</span>', h
        )
    return h


def _text(h):
    return html.unescape(re.sub(r"<[^>]+>", "", h)).strip()


# TeX math, by Pandoc's rules: $$display$$, and $inline$ with no space just
# inside the dollars and no digit just after the closing one, so "$3.50" is
# money. \$ is a literal dollar sign.
_DISPLAY_MATH = re.compile(r"\$\$(.+?)\$\$", re.S)
_INLINE_MATH = re.compile(r"(?<![\\$])\$(?=\S)((?:[^$\\\n]|\\.|\n(?![ \t]*\n))+?)(?<=\S)\$(?!\d)")


def _protect_math(s):
    """Swap math for placeholders that Markdown leaves alone; returns the
    text and the math found, for _restore_math."""
    found = []

    def keep(kind):
        def f(m):
            found.append((kind, m.group(1).strip()))
            return f"COGRAMATH{len(found) - 1}Z"

        return f

    s = _DISPLAY_MATH.sub(keep("display"), s)
    s = _INLINE_MATH.sub(keep("inline"), s)
    return s.replace("\\$", "&#36;"), found


def _restore_math(h, found):
    """Put the math back as MathJax delimiters: \\[...\\] and \\(...\\)."""

    def put(m):
        kind, tex = found[int(m.group(1))]
        tex = html.escape(tex, quote=False)
        return f"\\[{tex}\\]" if kind == "display" else f"\\({tex}\\)"

    return re.sub(r"COGRAMATH(\d+)Z", put, h)


class _Blocks(HTMLParser):
    """Split an HTML fragment into its top-level elements: (tag, attrs, outer html)."""

    VOID = frozenset({"hr", "img", "br", "input", "meta", "link"})

    def __init__(self, text):
        super().__init__(convert_charrefs=False)
        self.text, self.depth, self.start, self.tag, self.blocks = text, 0, None, None, []
        self._lines = [0]
        for m in re.finditer("\n", text):
            self._lines.append(m.end())
        self.feed(text)
        self.close()

    def _pos(self):
        line, col = self.getpos()
        return self._lines[line - 1] + col

    def handle_starttag(self, tag, attrs):
        if self.depth == 0:
            self.start, self.tag, self.attrs = self._pos(), tag, dict(attrs)
            if tag in self.VOID:
                end = self.text.index(">", self.start) + 1
                self.blocks.append((tag, self.attrs, self.text[self.start : end]))
                return
        if tag not in self.VOID:
            self.depth += 1

    def handle_startendtag(self, tag, attrs):
        if self.depth == 0:
            s = self._pos()
            end = self.text.index(">", s) + 1
            self.blocks.append((tag, dict(attrs), self.text[s:end]))

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        self.depth -= 1
        if self.depth == 0:
            end = self.text.index(">", self._pos()) + 1
            self.blocks.append((self.tag, self.attrs, self.text[self.start : end]))


def _inner(outer):
    return outer[outer.index(">") + 1 : outer.rindex("<")]


# ---------------------------------------------------------------- the paper


class Paper:
    """A paper laid out as an APA journal article of about 1980.

    title, authors, affiliations: the title block. Authors and affiliations
        are strings or lists of strings; '^1' marks become superscripts.
    abstract: HTML (or Markdown via from_markdown), set across the measure.
    keywords: optional line under the abstract.
    author_note: paragraphs for the foot of the first column (grants,
        acknowledgments, correspondence).
    masthead: top-left lines on the first page (journal, volume, pages).
    first_page_foot: centred line at the foot of the first page.
    running_head / short_authors: running heads on right- and left-hand pages.
    blocks: the body as source HTML elements, in order (from_markdown makes
        these); footnotes: {number: html}.
    figures: {name: matplotlib Figure or image path}, used by blocks made
        with figure_block(), and by '![caption](fig:name)' in Markdown.
    columns: 2 (default) or 1.
    style: {custom property: value} overrides, e.g. {"body": "10pt",
        "page-w": "612pt", "page-h": "792pt"} (see apa1980.css for the list).
    css: extra stylesheet paths, loaded after the default one.
    worn: True for the archival-scan look (default), False for clean type.
    start_page: number on the first page.
    note: HTML shown above the pages on screen (not printed).
    """

    def __init__(
        self,
        title,
        authors=(),
        affiliations=(),
        abstract="",
        keywords="",
        author_note=(),
        masthead="",
        first_page_foot="",
        running_head=None,
        short_authors=None,
        blocks=(),
        footnotes=None,
        figures=None,
        columns=2,
        style=None,
        css=(),
        worn=True,
        start_page=1,
        note="",
        lang="en",
        apply_title_case=True,
    ):
        self.title = title_case(title) if apply_title_case else title
        self.authors = [authors] if isinstance(authors, str) else list(authors)
        self.affiliations = [affiliations] if isinstance(affiliations, str) else list(affiliations)
        self.abstract, self.keywords = abstract, keywords
        self.author_note = [author_note] if isinstance(author_note, str) else list(author_note)
        self.masthead, self.first_page_foot = masthead, first_page_foot
        self.running_head = running_head or _short_title(self.title)
        self.short_authors = short_authors or _short_authors(self.authors)
        self.blocks = list(blocks)
        self.footnotes = dict(footnotes or {})
        self.figures = dict(figures or {})
        self.columns, self.style, self.css = columns, dict(style or {}), [Path(c) for c in css]
        self.worn, self.start_page, self.note, self.lang = worn, start_page, note, lang
        self._fig_files = {}

    # ------------------------------------------------------------ Markdown

    @classmethod
    def from_markdown(
        cls,
        source: str | os.PathLike[str],
        base_dir: str | os.PathLike[str] | None = None,
        figures: Mapping[str, Figure | str | os.PathLike[str]] | None = None,
        small_sections: Sequence[str] = ("Method", "Methods"),
        omit_headings: Sequence[str] = ("Introduction",),
        small_caps: Sequence[str] = ("ANOVA", "MANOVA"),
        **overrides: Any,
    ) -> Paper:
        """Build a Paper from Markdown with a YAML front matter block.

        source: a path or the Markdown text. base_dir: where relative image
        paths are looked up (the file's folder by default). Keyword
        arguments override front-matter fields."""
        try:
            import markdown as md
            import yaml
        except ImportError:
            raise ImportError('Markdown input needs: pip install "cogra[paper]"') from None
        path: Path | None = None
        if isinstance(source, os.PathLike) or (
            isinstance(source, str) and "\n" not in source and Path(source).exists()
        ):
            path = Path(source)
            text = path.read_text()
        elif "\n" not in source and Path(source).suffix.lower() in (".md", ".markdown", ".txt"):
            raise FileNotFoundError(f"no such Markdown file: {source}")
        else:
            text = source
        base = Path(base_dir) if base_dir else (path.parent if path else Path.cwd())
        meta: dict[str, Any] = {}
        body = text
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
        if m:
            meta = yaml.safe_load(m.group(1)) or {}
            body = text[m.end() :]
        meta.update(overrides)

        conv = md.Markdown(extensions=["tables", "smarty", "sane_lists"])

        def block(s):
            s, math = _protect_math(str(s))
            return _restore_math(conv.reset().convert(s), math)

        def inline(s):
            return re.sub(r"^<p>(.*)</p>$", r"\1", block(s).strip(), flags=re.S)

        # footnotes: [^id] in the text, "[^id]: text" definitions
        defs = {}

        def take_def(m):
            defs[m.group(1)] = m.group(2).strip()
            return ""

        body = re.sub(r"^\[\^([^\]]+)\]:[ \t]*(.+(?:\n(?:[ \t]{2,}).+)*)\n?", take_def, body, flags=re.M)
        order: dict[str, int] = {}

        def mark(m):
            k = m.group(1)
            if k not in order:
                order[k] = len(order) + 1
            n = order[k]
            return f'<sup class="fn" data-n="{n}">{n}</sup>'

        body = re.sub(r"\[\^([^\]]+)\]", mark, body)
        footnotes = {n: inline(defs.get(k, "")) for k, n in order.items()}

        # figures: an image alone in its paragraph
        figs = dict(figures or {})
        fig_specs: list[Any] = []

        def fig(m):
            cap, src = m.group(1), m.group(2).strip()
            if src.startswith("fig:"):
                key = src[4:]
                if key not in figs:
                    raise KeyError(f"figure '{key}' is not in figures=")
            else:
                key = f"_file{len(fig_specs) + 1}"
                p = Path(src) if Path(src).is_absolute() else base / src
                figs[key] = p
            fig_specs.append((key, cap))
            return f'\n<div data-cogra-figure="{len(fig_specs)}"></div>\n'

        body = re.sub(r"^!\[(.*?)\]\((.*?)\)[ \t]*$", fig, body, flags=re.M)

        html_body = block(body)
        blocks, section, refs, runin, table_title = [], None, False, None, None
        n_fig = n_tab = 0
        small_set = {s.lower() for s in small_sections}
        omit = {s.lower() for s in omit_headings}
        for tag, attrs, outer in _Blocks(html_body).blocks:
            small = section is not None and section.lower() in small_set
            klass = ' class="small"' if small else ""
            if tag == "h1":
                name = _text(outer)
                section, refs = name, name.lower() in REF_HEADS
                if name.lower() in omit:
                    continue
                extra = " refs-head" if refs else ""
                blocks.append(f'<h2 class="h1{extra}">{_inner(outer)}</h2>')
            elif tag == "h2":
                blocks.append(f'<h3 class="h2">{_inner(outer)}</h3>')
            elif tag in ("h3", "h4"):
                t = _inner(outer).strip()
                runin = t if t.endswith((".", "?", ":")) else t + "."
            elif tag == "div" and "data-cogra-figure" in attrs:
                n_fig += 1
                key, cap = fig_specs[int(attrs["data-cogra-figure"]) - 1]
                blocks.append(figure_block(n_fig, key, inline(cap) if cap else ""))
            elif tag == "p" and table_title is None and re.match(r"<p>Table:\s", outer):
                table_title = inline(_text(outer)[len("Table:") :].strip())
            elif tag == "table":
                n_tab += 1
                title = table_title or ""
                blocks.append(
                    f'<figure class="table" data-fig="t{n_tab}"><figcaption>'
                    f'<span class="lab">Table {n_tab}</span> <span class="tt">{title}</span>'
                    f"</figcaption>{outer}</figure>"
                )
                table_title = None
            elif tag == "p":
                if re.fullmatch(r"\s*\\\[.*\\\]\s*", _inner(outer), re.S):
                    blocks.append(f'<p class="display nosplit">{_inner(outer).strip()}</p>')
                    continue
                inner = _small_caps(_urls(_inner(outer)), small_caps)
                if refs:
                    blocks.append(f'<p class="ref">{inner}</p>')
                    continue
                if runin:
                    inner = f'<span class="runin">{runin}</span> {inner}'
                    runin = None
                blocks.append(f"<p{klass}>{inner}</p>")
            elif tag in ("ul", "ol"):
                items = re.findall(r"<li>(.*?)</li>", outer, re.S)
                for i, it in enumerate(items, 1):
                    it = _small_caps(_urls(re.sub(r"^<p>|</p>$", "", it.strip())), small_caps)
                    if refs:
                        blocks.append(f'<p class="ref">{it}</p>')
                    else:
                        mark_ = "\u2022" if tag == "ul" else f"{i}."
                        c = "li small" if small else "li"
                        blocks.append(f'<p class="{c}" data-mark="{mark_}">{it}</p>')
            elif tag == "blockquote":
                for p in re.findall(r"<p>(.*?)</p>", outer, re.S):
                    blocks.append(f'<p class="small quote">{p}</p>')
            elif tag == "hr":
                blocks.append('<div class="rule nosplit"></div>')
            else:
                blocks.append(
                    outer
                    if "nosplit" in outer[:80]
                    else re.sub(r"^<(\w+)", r'<\1 class="nosplit"', outer, count=1)
                )
        blocks.append('<p class="endmark">&#9632;</p>')

        def lst(v):
            return [v] if isinstance(v, str) else list(v or [])

        return cls(
            title=str(meta.get("title", "Untitled")),
            authors=[_sup_marks(a) for a in lst(meta.get("authors"))],
            affiliations=[_sup_marks(a) for a in lst(meta.get("affiliations"))],
            abstract=block(meta.get("abstract", "")),
            keywords=inline(meta["keywords"]) if meta.get("keywords") else "",
            author_note=[inline(p) for p in lst(meta.get("author_note"))],
            masthead="<br>".join(html.escape(l) for l in str(meta.get("masthead", "")).splitlines()),
            first_page_foot=inline(meta.get("first_page_foot", "")) if meta.get("first_page_foot") else "",
            running_head=meta.get("running_head"),
            short_authors=meta.get("short_authors"),
            blocks=blocks,
            footnotes=footnotes,
            figures=figs,
            columns=int(meta.get("columns", 2)),
            style=meta.get("style"),
            css=[base / c for c in lst(meta.get("css"))],
            worn=meta.get("worn", True),
            start_page=int(meta.get("start_page", 1)),
            note=meta.get("note", ""),
            apply_title_case=meta.get("title_case", True),
        )

    # ------------------------------------------------------------ output

    def _figures(self, out, worn):
        """Write each figure as figures/<name>.png (and -scan.png when worn)."""
        from .. import style, wear

        figdir = out / "figures"
        figdir.mkdir(parents=True, exist_ok=True)
        files = {}
        for key, src in self.figures.items():
            stem = re.sub(r"[^\w-]", "_", key.lstrip("_"))
            clean, scan = figdir / f"{stem}.png", figdir / f"{stem}-scan.png"
            if hasattr(src, "savefig"):
                width_pt = src.get_size_inches()[0] * 72
                src.savefig(clean, dpi=220)
                if worn:
                    style.save_vintage(src, scan, look="scan", dpi=600, scan_dpi=300)
            else:
                src = Path(src)
                if src.suffix.lower() != ".png":
                    clean = figdir / f"{stem}{src.suffix.lower()}"
                shutil.copyfile(src, clean)
                width_pt, gray, dpi = _read_image(src, want_gray=worn)
                if gray is not None:
                    img, out_dpi = wear.apply(gray, look="scan", dpi=dpi, scan_dpi=min(300, dpi))
                    img.save(scan, dpi=(out_dpi, out_dpi))
                else:
                    scan = clean
            files[key] = (clean.name, scan.name if worn else clean.name, width_pt)
        return files

    def html(self, worn: bool | None = None, controls: bool = True, fig_files: dict | None = None) -> str:
        """The page as one HTML string (asset paths relative to its folder)."""
        worn = self.worn if worn is None else worn
        files = fig_files or {k: (f"{k}.png", f"{k}-scan.png", None) for k in self.figures}
        blocks = []
        for b in self.blocks:

            def img(m):
                key, which = m.group(1), m.group(2)
                clean, scan, width = files.get(key, (key, key, None))
                # a figure prints at its own size, shrinking only to fit the measure
                size = f' style="width:{width:.1f}pt"' if width else ""
                return f'src="figures/{scan if which == "scan" else clean}"{size}'

            blocks.append(re.sub(r'src="cogra-fig:([^":]+):(clean|scan)"', img, b))
        notes = "".join(
            f'<p class="note" data-n="{n}"><span class="n">{n}</span> {t}</p>'
            for n, t in sorted(self.footnotes.items())
        )
        author_note = "".join(f'<p class="note">{_urls(p)}</p>' for p in self.author_note)
        abstract = self.abstract or ""
        if abstract and not abstract.lstrip().startswith("<"):
            abstract = f"<p>{abstract}</p>"
        kw = f'<p class="kw"><i>Keywords:</i> {self.keywords}</p>' if self.keywords else ""
        overrides = "".join(f"--{k.lstrip('-')}: {v}; " for k, v in self.style.items())
        page_w = self.style.get("page-w", DEFAULT_PAGE[0])
        page_h = self.style.get("page-h", DEFAULT_PAGE[1])
        extra_css = "".join(f'<link rel="stylesheet" href="{c.name}">' for c in self.css)
        toggle = (
            (
                f'<label><input type="checkbox" id="wornToggle"{" checked" if worn else ""}> '
                f"Worn printing</label>"
            )
            if controls
            else ""
        )
        outside = (
            f'<div class="outside">{f"<p>{self.note}</p>" if self.note else ""}{toggle}</div>'
            if (controls or self.note)
            else ""
        )
        script = (
            "<script>document.getElementById('wornToggle').addEventListener('change',"
            "function(e){document.body.classList.toggle('worn',e.target.checked);});</script>"
            if controls
            else ""
        )
        has_math = re.search(r"\\[(\[]", "".join(blocks) + abstract + notes + author_note + self.title)
        mathjax = MATHJAX_HEAD if has_math else ""
        return f"""<!doctype html>
<html lang="{self.lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(_text(self.title))}</title>
<link rel="stylesheet" href="apa1980.css">{extra_css}
<style>:root {{ {overrides}}} @page {{ size: {page_w} {page_h}; margin: 0; }}</style>
{mathjax}
</head>
<body class="{"worn" if worn else ""}">
{(HERE / "filters.svg").read_text()}
{outside}
<div id="book" data-columns="{self.columns}" data-start="{self.start_page}"
     data-rh-verso="{html.escape(self.short_authors)}" data-rh-recto="{html.escape(self.running_head)}"></div>
<div id="source" lang="{self.lang}">
<div class="front-src">
{f'<p class="masthead">{self.masthead}</p>' if self.masthead else ""}
<h1 class="title">{self.title}</h1>
<p class="authors">{", ".join(self.authors[:-1]) + (", and " if len(self.authors) > 2 else " and ") + self.authors[-1] if len(self.authors) > 1 else "".join(self.authors)}</p>
<p class="affil">{"<br>".join(self.affiliations)}</p>
{f'<div class="abstract">{abstract}{kw}</div>' if abstract else ""}
</div>
<div class="authornote-src">{author_note}</div>
<div class="firstfoot-src">{self.first_page_foot}</div>
<div class="flowsrc">
{chr(10).join(blocks)}
</div>
<div class="notes-src">{notes}</div>
</div>
<script src="paginate.js"></script>
{script}
</body>
</html>
"""

    def save(self, out_dir: str | os.PathLike[str], worn: bool | None = None, controls: bool = True) -> Path:
        """Write the page and its assets to out_dir; returns the index.html path."""
        worn = self.worn if worn is None else worn
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(HERE / "apa1980.css", out / "apa1980.css")
        shutil.copyfile(HERE / "paginate.js", out / "paginate.js")
        (out / "fonts").mkdir(exist_ok=True)
        for f in [*SCHOLA, "GUST-FONT-LICENSE.txt"]:
            shutil.copyfile(FONTS / f, out / "fonts" / f)
        for c in self.css:
            shutil.copyfile(c, out / c.name)
        files = self._figures(out, worn)
        page = self.html(worn=worn, controls=controls, fig_files=files)
        if 'src="mathjax/startup.js"' in page:
            shutil.copytree(MATHJAX, out / "mathjax", dirs_exist_ok=True)
        index = out / "index.html"
        index.write_text(page)
        return index

    def pdf(
        self,
        path: str | os.PathLike[str],
        worn: bool | None = None,
        engine: Literal["auto", "playwright", "chrome"] = "auto",
        timeout: float = 120,
    ) -> Path:
        """Print the paginated pages to a PDF. engine: 'auto', 'playwright'
        or 'chrome'. With worn=True (the default for a worn Paper) text is
        printed as an image and is not searchable; worn=False gives clean,
        searchable type."""
        path = Path(path).resolve()
        with tempfile.TemporaryDirectory() as tmp:
            index = self.save(Path(tmp) / "site", worn=worn, controls=False)
            if engine in ("auto", "playwright"):
                try:
                    import playwright.sync_api  # noqa: F401

                    return _pdf_playwright(index, path, timeout)
                except ImportError:
                    if engine == "playwright":
                        raise
            return _pdf_chrome(index, path, Path(tmp), timeout)


def figure_block(n, key, caption_html, continued=()):
    """Source HTML for figure n: the image named key in Paper.figures, its
    caption, and caption paragraphs that continue in the columns."""
    out = (
        f'<figure data-fig="{n}">'
        f'<img class="fig-clean" src="cogra-fig:{key}:clean" alt="Figure {n}">'
        f'<img class="fig-scan" src="cogra-fig:{key}:scan" alt="Figure {n}">'
        f'<figcaption><span class="lab">Figure {n}.</span> {caption_html}</figcaption></figure>'
    )
    return out + "".join(f'<p class="capcont" data-fig="{n}">{p}</p>' for p in continued)


def _short_title(title):
    words = _text(title).split(":")[0].split()
    return " ".join(words[:5]).upper() if len(words) > 5 else " ".join(words).upper()


_RASTER = (".png", ".jpg", ".jpeg", ".tif", ".tiff")


def _read_image(path, want_gray):
    """Width in points (None if the file is not an image Pillow reads), and,
    for a raster figure when want_gray, its grey pixels and dpi for the wear.
    A missing dpi is taken as 220 for the width and 300 for the wear."""
    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(path) as im:
            dpi = im.info.get("dpi", (0, 0))[0]
            width_pt = im.width / (dpi or 220) * 72
            if not (want_gray and path.suffix.lower() in _RASTER):
                return width_pt, None, None
            import numpy as np

            return width_pt, np.asarray(im.convert("L")), round(dpi or 300)
    except (UnidentifiedImageError, OSError):  # e.g. an SVG or PDF figure
        return None, None, None


def _short_authors(authors):
    names = [re.sub(r"<[^>]+>", "", re.sub(r"<sup>.*?</sup>", "", a)).strip() for a in authors]
    if not names:
        return ""

    def last(n):
        return n.split()[-1] if n.split() else n

    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{last(names[0])} and {last(names[1])}"
    return f"{last(names[0])} et al."


# ---------------------------------------------------------------- PDF engines

CHROME_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


def find_chrome() -> str | None:
    """A Chrome-family browser for headless printing, or None."""
    env = os.environ.get("COGRA_CHROME")
    if env and Path(env).exists():
        return env
    for name in (
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "microsoft-edge",
        "brave-browser",
        "chrome",
    ):
        p = shutil.which(name)
        if p:
            return p
    return next((p for p in CHROME_PATHS if Path(p).exists()), None)


def _pdf_chrome(index, path, tmp, timeout):
    chrome = find_chrome()
    if not chrome:
        raise RuntimeError(
            "PDF output needs Chrome, Chromium, Edge or Brave (set $COGRA_CHROME "
            "to its path), or Playwright: pip install playwright && "
            "playwright install chromium"
        )
    cmd = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=30000",
        "--window-size=1200,900",
        f"--user-data-dir={tmp / 'profile'}",
        f"--print-to-pdf={path}",
        index.as_uri(),
    ]
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        cmd.insert(1, "--no-sandbox")  # Chrome will not run as root otherwise
    if path.exists():
        path.unlink()
    subprocess.run(cmd, check=True, capture_output=True, timeout=timeout)
    if not path.exists() or path.stat().st_size == 0:
        raise RuntimeError(f"{Path(chrome).name} did not write {path}")
    return path


def _pdf_playwright(index, path, timeout):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1200, "height": 900})
            page.goto(index.as_uri())
            page.wait_for_function(
                "document.documentElement.dataset.paginated === '1'", timeout=timeout * 1000
            )
            page.pdf(path=str(path), prefer_css_page_size=True, print_background=True)
        finally:
            browser.close()
    return path
