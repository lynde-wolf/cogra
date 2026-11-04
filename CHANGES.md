# Changes

## 0.1.0 (unreleased)

First public version.

- **Styles**: `import cogra` registers the fonts and four matplotlib styles,
  `cogra`, `cogra-serif`, `cogra-column` and `cogra-page`, for
  `plt.style.use` and `plt.style.context`. `cogra.use(labels=, size=)` applies
  the same.
- **Geoms**: one function per ggplot2 4.0 geom, drawn in the period style, with
  halftone dots for continuous fills.
- **`restyle()`** for finished matplotlib and seaborn figures. seaborn's error
  bars, caps and violin boxes come out as plain black rules, even when the
  cogra style was active while they were drawn.
- **Styles**: `mathtext.cal` is set to the cogra faces, so `cogra.use()` no
  longer warns about a missing cursive font (Apple Chancery on macOS).
- **`signif()`**: significance brackets with stars, an APA-style p value or
  your own label. They clear everything between their ends, stack, and never
  move the x axis. `stars()` and `format_p()` give the labels alone; R has
  `signif_cogra()` and `stars_cogra()`. `examples/demo_signif.py` draws the
  README picture.
- **Wear**: `save_vintage()` and `cogra.wear` with the scan, xerox and aged
  looks, computed in tiles, cached, and with irregular dust specks.
- **`cogra.paper`** and the `cogra-paper` command: papers in Markdown set as an
  APA journal article of about 1980, as a paginated web page and a PDF.
- **`cogra.paper` math**: `$...$` and `$$...$$` (TeX) are typeset by a
  bundled MathJax 4.1.3 in the TeX Gyre Schola math font, before pagination
  and at the width of one column. `examples/paper/bayes_bellman.md` is a
  second example paper that uses it.
- **Third example paper**: `examples/paper/regret_value_of_computation.md`
  (and `make_regret_value_of_computation.py`), an invented paper on regret as
  the value of computation.
- **Checks on input**: `stars()` and `format_p()` raise `ValueError` for a p
  outside [0, 1] or NaN; `Paper.from_markdown("typo.md")` raises
  `FileNotFoundError` instead of setting the file name as the paper's text;
  `cogra-paper` checks its arguments and files before building.
- **Typed**: the public functions have type hints and the package ships
  `py.typed`; mypy runs in CI.
- **Development**: ruff (lint and format), mypy, coverage and a `uv.lock`;
  CI uses uv; `.pre-commit-config.yaml` and `CONTRIBUTING.md`.
- **Documentation site** (`docs/build.py`, published to https://lynde-wolf.github.io/cogra/):
  the tutorial, every geom with its code (clean and worn), an API reference
  from the docstrings, the example papers as live pages, and a live demo of
  `cogra.css`, which styles the site itself.
- **White paper by default**: `cogra.css` (and the specimen page) now set
  black ink on white, with a neutral grey surround and a neutral dark mode,
  instead of a tinted newsprint colour, which on screen looks like a tinted
  screen rather than paper. Set `--cogra-paper` to tint it.
- **Specks on worn web pages**: a `.cogra-worn` page (scan or photocopy)
  carries dust specks from `cogra-specks-a.png` and `-b.png`, drawn by
  `cogra.wear`'s speck routine; clean pages have none, and `.cogra-nospecks`
  turns them off. On the docs site, samples (the demo, the specimen, the
  gallery figures) show only their own specks.
- **Selected text in ink**: `cogra.css` (inside `.cogra-page` and
  `.cogra-controls`) and the paper pages highlight a selection in ink with
  paper-coloured letters instead of the system's highlight colour.
- **Ink form controls**: `cogra.css` draws checkboxes (a ballot box with a
  cross), radio buttons, sliders, menus and buttons in ink inside
  `.cogra-page` or `.cogra-controls`, so a page shows no system accent colour
  and the worn filters wear them; the paper pages' switch matches.
- **About page** on the docs site (`docs/about.md`), and a shorter home page.
- **Docs code blocks wrap**: long lines continue, indented, on the next line
  instead of running off the side; copied code is unchanged.
- **Docs site printed worn**: by default every page is shown as an archival
  scan (the `#cogra-scan` filter on the text, `save_vintage` copies of the
  figures, and dust specks drawn by `cogra.wear`), with a "worn printing"
  switch in the top bar that each reader's browser remembers.
- **Example paper scripts** expose `make_figure()` and `build(site_dir, pdf)`.
- **Extras**: ggplot2 theme, LaTeX style, CSS for web pages, and the
  Schola Scan / Heros Scan fonts (with Soft versions).
