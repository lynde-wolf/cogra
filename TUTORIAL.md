# Cognitive Revolution Aesthetic (cogra): tutorial

How to get the cogra look in each place it is supported: Python
figures (including seaborn, pandas, plotnine, plotly and Altair), whole papers, R
figures, web pages, LaTeX documents, and other apps through the scan fonts. Each part stands on its own, so skip to
the one you need.

- [1. Install](#1-install)
- [2. Python figures](#2-python-figures)
- [3. seaborn, pandas and other plotting libraries](#3-seaborn-pandas-and-other-plotting-libraries)
- [4. Papers in the 1980 journal layout](#4-papers-in-the-1980-journal-layout)
- [5. R and ggplot2](#5-r-and-ggplot2)
- [6. Web pages](#6-web-pages)
- [7. LaTeX documents](#7-latex-documents)
- [8. The fonts in other apps](#8-the-fonts-in-other-apps)
- [9. Troubleshooting](#9-troubleshooting)

## 1. Install

```bash
pip install "cogra @ git+https://github.com/lynde-wolf/cogra"
```

This installs the Python package and its fonts (TeX Gyre Heros and Schola).
Python does not need the fonts installed on your system. The R, web and
LaTeX parts are plain files in `extras/`: clone the repository, or download
the folder you need.

```bash
git clone https://github.com/lynde-wolf/cogra
```

To install the fonts on your system (R, LaTeX, slides and word processors
need this), open the `.otf` files in `src/cogra/fonts/`. The scan fonts
are in `extras/scanfont/fonts/` (see [section 8](#8-the-fonts-in-other-apps)). On a Mac,
double-click each one and click *Install Font*.

## 2. Python figures

### Your first figure

```python
import matplotlib.pyplot as plt
import cogra

cogra.use()

fig, ax = plt.subplots(figsize=(3.2, 2.6))
ax.plot([2, 4, 6], [510, 548, 590], label="Go")
ax.plot([2, 4, 6], [520, 571, 625], label="Stop-fail")
ax.set_xlabel("Memory load")
ax.set_ylabel("Mean RT (msec)")
ax.legend()
fig.savefig("first.pdf")
```

`cogra.use()` is the same as `plt.style.use("cogra")`: importing cogra registers
its fonts and four styles with matplotlib. Stack `"cogra-serif"` for Schola
labels, and `"cogra-column"` (2.65 in) or `"cogra-page"` (5.46 in) for figures
sized, with their type, for one column or the full width of a `cogra.paper`
page: `plt.style.use(["cogra", "cogra-column"])`, or
`cogra.use(labels="serif", size="column")`.

The style sets the fonts, black ink, inward ticks, no grid, and a cycle of
marker and line styles (open circle with a solid line, then a filled circle
with a dashed line, and so on). Each series therefore looks different without
colour. Call it once at the top of a script or notebook. For serif labels in
Schola, matching the body text of a page, use `cogra.use(labels="serif")`.

Save figures for a paper as PDF. The text stays editable, and the fonts are
embedded as TrueType (`pdf.fonttype: 42`), which journals accept.

### Bars, violins and rainclouds

The style file cannot set fills, so bars need a helper. `cogra.bars` draws white
bars with black outlines and a different hatching for each bar:

```python
fig, ax = plt.subplots(figsize=(3.0, 2.6))
cogra.bars(ax, [0, 1, 2], [212, 236, 251], yerr=[8, 9, 11])
ax.set_xticks([0, 1, 2], ["Simple", "Feature", "Conjunction"])
ax.set_ylabel("SSRT (msec)")
```

To choose the patterns, pass `hatches=["", "////", "...."]`. `cogra.HATCHES`
lists the default order.

Distributions:

```python
import numpy as np
rng = np.random.default_rng(1)
groups = [rng.normal(230, 30, 50), rng.normal(255, 35, 50)]

fig, (a, b) = plt.subplots(1, 2, figsize=(5.5, 2.6))
cogra.violin(a, groups)
cogra.raincloud(b, groups)
```

### Significance brackets

`cogra.signif` draws a bracket between two x positions with stars above it:

```python
from scipy import stats

fig, ax = plt.subplots(figsize=(3.0, 2.8))
cogra.bars(ax, [0, 1, 2], [212, 236, 251], yerr=[8, 9, 11])
ax.set_xticks([0, 1, 2], ["Simple", "Feature", "Conjunction"])
ax.set_ylabel("SSRT (msec)")
cogra.signif(ax, 0, 1, p=0.03)       # *
cogra.signif(ax, 1, 2, p=0.2)        # not significant: nothing is drawn
cogra.signif(ax, 0, 2, p=0.0004)     # ***, above the first bracket
```

Pass the p value from your test (for a paired t-test,
`t, p = stats.ttest_rel(a, b)`). The stars are `*` for *p* < .05, `**` for
*p* < .01 and `***` for *p* < .001.

| argument | what it does |
|---|---|
| `p` | the p value, shown as stars |
| `show="p"` | write the p value instead, APA style: *p* = .012, *p* < .001 |
| `text=` | your own label instead: `"n.s."`, `"d = 0.54"` |
| `ns=True` | write "n.s." for a p that is not significant (by default nothing is drawn) |
| `y=` | the bracket's height in data units; by default just above the highest thing between the two positions |
| `pad`, `tick` | the gap below the bracket and the length of its ends, as fractions of the y range |

Call it after the data are drawn. The bracket clears everything between its
two ends (bars, error bars, lines, points, violins and earlier brackets), so
several brackets stack without overlapping. It never moves the x axis, and
the y axis grows if a label would otherwise be cut off. `cogra.stars(p)` and
`cogra.format_p(p)` give the labels on their own, for a table or a caption.
`examples/demo_signif.py` draws a full example: brackets on `cogra.bars`, and
a test per block on a seaborn bar plot that is then restyled.

### ggplot2-style geoms

`cogra.geoms` has one function per ggplot2 geom, 50 in all. Each takes
the axes first, then the data. Pass `group=` for a variable that splits the
data into groups: each group gets its own marker, line style or hatching, as
`aes(shape = ...)` would in R.

```python
from cogra import geoms as g

load = np.array([2, 4, 6, 2, 4, 6])
rt = np.array([510, 548, 590, 520, 571, 625])
cond = np.array(["Go"] * 3 + ["Stop-fail"] * 3)

fig, ax = plt.subplots(figsize=(3.2, 2.6))
g.geom_line(ax, load, rt, group=cond, markers=True)
g.geom_errorbar(ax, load, rt - 12, rt + 12, width=0.2)
ax.legend()
```

A few more:

```python
g.geom_point(ax, x, y, group=cond)               # scatter, one symbol per group
g.geom_smooth(ax, x, y, method="lm")             # fit line with a stippled CI band
g.geom_col(ax, labels, heights, group=cond)      # dodged, hatched bars
g.geom_pointrange(ax, x, y, lo, hi, group=cond)  # point estimates with intervals
g.geom_tile(ax, xs, ys, values)                  # heatmap drawn as halftone dots
```

Every geom is drawn in `examples/gallery.py`. Run it to see them all, with
the code for each panel.

Continuous fills (tiles, rasters, 2-D bins, hexbins, colorbars) are drawn as
halftone dots, with dot area proportional to the value. A printed journal
of the period could not show smooth greys, and a 1-bit scan would turn them
into solid black or white. To draw dots directly, use
`cogra.halftone(ax, cx, cy, values, cell_w, cell_h)`.

### Restyling a figure you already have

If the figure already exists, made with your usual matplotlib or seaborn
code in colour, `restyle` converts it (more on seaborn and other libraries in
[section 3](#3-seaborn-pandas-and-other-plotting-libraries)):

```python
import seaborn as sns
import pandas as pd

df = pd.DataFrame({"load": [2, 4, 6] * 2, "rt": [510, 548, 590, 520, 571, 625],
                   "cond": ["Go"] * 3 + ["Stop-fail"] * 3})
ax = sns.lineplot(df, x="load", y="rt", hue="cond", marker="o", palette="deep")
fig = cogra.restyle(ax.figure)
print(fig.cogra_report)
```

Each colour becomes a group encoding (marker, line style, hatching). The same
colour gets the same encoding in every panel and in the legend. Translucent
bands become stippling, and heatmaps and colorbars become halftones.
`fig.cogra_report` lists what was changed.

Things to watch:

- Pass an explicit `palette=` to seaborn. After `cogra.use()` the default
  palette is all black, so every group would look the same to `restyle`.
- Restyle a figure only once. A second call warns and changes nothing,
  because the original colours are gone after the first.
- `restyle` also applies the style for later figures, as `cogra.use()` would.
- You can also write it as `fig | cogra.cogra()`.

### Worn copies

`save_vintage` writes a raster copy that looks like an old reprint:

```python
cogra.save_vintage(fig, "fig-scan.png")                 # 1-bit archival scan
cogra.save_vintage(fig, "fig-xerox.png", look="xerox")  # photocopy of a photocopy
cogra.save_vintage(fig, "fig-aged.png", look="aged")    # toned paper, uneven ink
```

| setting | what it does |
|---|---|
| `strength` | edge roughness and breaks (default 1; try 0.5 to 2) |
| `weight` | how much heavier some strokes come out than others |
| `scan_dpi` | resolution of the scan look; lower is coarser (default 300) |
| `generations` | xerox look: how many times it was copied (default 2) |
| `fade` | aged look: how faded the ink is (0 to 1) |
| `specks` | dust specks; off by default because they look like data points |
| `seed` | the same seed gives the same wear |

Worn copies are for talks, posters and websites. Submit the clean PDF to
journals. Wear on a large figure takes a few seconds. Results are cached, so
re-running an unchanged notebook is fast. `cogra.clear_cache()` empties the
cache.

### A typical notebook

Here `df` is a data frame with columns `load`, `rt` and `cond`, one row per
mean.

```python
import matplotlib.pyplot as plt
import cogra
from cogra import geoms as g

cogra.use()

def fig_load_effect(df):
    fig, ax = plt.subplots(figsize=(3.2, 2.6))
    g.geom_line(ax, df.load, df.rt, group=df.cond, markers=True)
    ax.set(xlabel="Memory load", ylabel="Mean RT (msec)")
    ax.legend()
    return fig

fig = fig_load_effect(df)
fig.savefig("figures/load_effect.pdf")                   # for the paper
cogra.save_vintage(fig, "figures/load_effect-scan.png")  # for slides
```

## 3. seaborn, pandas and other plotting libraries

Libraries built on matplotlib hand you a matplotlib figure, so `restyle`
converts it. plotly and Altair draw their own figures, so they get a
template or theme instead.

| library | how to get the look |
|---|---|
| seaborn | draw in colour, then `cogra.restyle(fig)` |
| pandas `.plot` | `cogra.use()` for lines; colours plus `restyle` for bars |
| plotnine | build the plot with a cogra theme |
| statsmodels, and anything else that returns a matplotlib figure | `cogra.restyle(fig)` |
| plotly | a cogra template |
| Altair | a cogra theme |

The examples in this section use two small data frames:

```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import cogra

rng = np.random.default_rng(1)
df = pd.DataFrame({"load": [2, 4, 6] * 2, "rt": [510, 548, 590, 520, 571, 625],
                   "cond": ["Go"] * 3 + ["Stop-fail"] * 3})
trials = pd.DataFrame({"cond": np.repeat(["Feature", "Conjunction"], 60),
                       "ssrt": np.r_[rng.normal(240, 30, 60), rng.normal(280, 35, 60)],
                       "block": np.tile(np.repeat(["1", "2", "3"], 20), 2)})
```

### seaborn

Draw the plot as usual, in colour with an explicit palette, and restyle the
figure. Axes-level functions (`lineplot`, `barplot`, `kdeplot`, `heatmap`
and so on) return axes, so pass `ax.figure`:

```python
import seaborn as sns

fig, ax = plt.subplots(figsize=(3.4, 2.8))
sns.barplot(trials, x="block", y="ssrt", hue="cond", palette="deep", capsize=0.2, ax=ax)
ax.set(xlabel="Block", ylabel="SSRT (msec)", ylim=(0, 380))
ax.legend(title=None, loc="upper left", ncols=2)
cogra.restyle(fig)
```

Figure-level functions (`relplot`, `catplot`, `displot`, `lmplot`,
`pairplot`, `jointplot`) return a grid; pass `g.figure`:

```python
g = sns.catplot(trials, x="cond", y="ssrt", col="block", kind="violin",
                hue="cond", palette="deep", height=2.4)
cogra.restyle(g.figure)
```

What becomes what:

- each `hue` level becomes a marker, line style and hatching, the same in
  every panel and in the legend;
- error bars, caps and the boxes inside violins become plain black rules;
- filled densities and confidence bands become stippling;
- `heatmap` cells and their colorbar become halftone dots.

Things to watch:

- Pass `palette=`. After `cogra.use()` (or after an earlier `restyle`) the
  default palette is all black, and `restyle` cannot tell the groups apart.
- `sns.set_theme()` is fine: `restyle` removes the grey background and the
  grid. It does change later figures, so `restyle` each one.
- seaborn titles its legend with the column name. `ax.legend(title=None)`
  or `sns.move_legend(ax, "upper left", title=None)` removes it.
- Significance brackets go on with `cogra.signif`, before or after
  `restyle`. seaborn puts category *k* at x = *k* (0, 1, 2, ...), and dodged
  bars beside it: x ± 0.2 for two `hue` levels, x − 0.27, x, x + 0.27 for
  three. So `cogra.signif(ax, -0.2, 0.2, p=p)` compares the two bars in the
  first category.

### pandas

Lines from `DataFrame.plot` take the style's markers and line styles
directly:

```python
cogra.use()
wide = df.pivot(index="load", columns="cond", values="rt")
ax = wide.plot(figsize=(3.2, 2.6))
ax.set(xlabel="Memory load", ylabel="Mean RT (msec)")
```

Bars are filled from the colour cycle, which is all black after
`cogra.use()`. Give them colours and restyle, and they come out white with
hatching:

```python
ax = wide.plot.bar(figsize=(3.2, 2.6), color=["tab:blue", "tab:orange"], rot=0)
ax.set(xlabel="Memory load", ylabel="Mean RT (msec)", ylim=(0, 800))
ax.legend(title=None, loc="upper left", ncols=2)
cogra.restyle(ax.figure)
```

### plotnine

plotnine draws its legend keys itself, where `restyle` cannot reach them, so
build the plot in the style instead. Map the grouping variable to `shape`,
`fill` and `linetype` together so they share one legend, as in the R
version ([section 5](#5-r-and-ggplot2)). `import cogra` has already
registered the fonts with matplotlib, which plotnine uses.

```python
from plotnine import (ggplot, aes, geom_line, geom_point, labs, theme, theme_classic,
                      element_text, element_blank, scale_shape_manual,
                      scale_fill_manual, scale_linetype_manual)

theme_cogra = theme_classic() + theme(
    text=element_text(family="TeX Gyre Heros", color="black", size=10),
    axis_ticks_length=-4,                 # negative = ticks point inward
    legend_title=element_blank(),
)

p = (ggplot(df, aes("load", "rt", shape="cond", fill="cond", linetype="cond"))
     + geom_line()
     + geom_point(size=2.5, stroke=0.6, color="black")
     + scale_shape_manual(values=["o", "o"])
     + scale_fill_manual(values=["white", "black"])          # open, then filled
     + scale_linetype_manual(values=["solid", "dashed"])
     + labs(x="Memory load", y="Mean RT (msec)")
     + theme_cogra + theme(figure_size=(3.4, 2.6)))

fig = p.draw()                             # a matplotlib figure
cogra.save_vintage(fig, "load-scan.png")   # wear works as for any figure
```

For more groups, extend the value lists: shapes `"o"`, `"s"`, `"^"`, fills
alternating white and black, line types `"solid"`, `"dashed"`, `"dotted"`,
`"dashdot"`.

### statsmodels and other matplotlib-based libraries

Anything that returns a matplotlib figure can be restyled:

```python
import statsmodels.api as sm

fig = sm.qqplot(trials.ssrt, line="s")
cogra.restyle(fig)
```

### plotly

Register a template once, at the top of the script or notebook. Each trace
then takes the next marker and dash in the cycle, and bars get hatching:

```python
import plotly.graph_objects as go
import plotly.io as pio
import plotly.express as px

INK, FONT = "black", "TeX Gyre Heros, Helvetica, Arial, sans-serif"
axis = dict(showgrid=False, zeroline=False, showline=True, linecolor=INK, linewidth=1,
            ticks="inside", tickcolor=INK, ticklen=4, color=INK)
pio.templates["cogra"] = go.layout.Template(
    layout=dict(font=dict(family=FONT, size=12, color=INK), colorway=[INK],
                paper_bgcolor="white", plot_bgcolor="white",
                xaxis=axis, yaxis=axis, legend=dict(bgcolor="rgba(0,0,0,0)")),
    data=dict(
        scatter=[go.Scatter(marker=dict(symbol=s, size=7, color=INK, line=dict(color=INK, width=1)),
                            line=dict(color=INK, width=1.2, dash=d))
                 for s, d in [("circle-open", "solid"), ("circle", "dash"),
                              ("square-open", "dot"), ("triangle-up", "dashdot")]],
        bar=[go.Bar(marker=dict(color="white", line=dict(color=INK, width=1),
                                pattern=dict(shape=h, fgcolor=INK, bgcolor="white", solidity=0.3)))
             for h in ["", "/", ".", "x"]],
    ))
pio.templates.default = "cogra"

fig = px.line(df, x="load", y="rt", line_dash="cond", symbol="cond", markers=True,
              labels={"load": "Memory load", "rt": "Mean RT (msec)", "cond": ""})
fig.update_layout(width=420, height=320)
fig.write_image("load.png", scale=3)       # needs: pip install kaleido
```

With `plotly.express`, map the groups to `symbol` and `line_dash` (lines) or
`pattern_shape` (bars) rather than `color`, which the template sets to black.

Plotly renders text with the fonts installed on your system, so install
TeX Gyre Heros ([section 1](#1-install)); otherwise the labels fall back to
Helvetica or Arial. For a worn copy, wear the exported PNG. Plotly images
are 96 dots per inch times `scale`:

```python
from PIL import Image
from cogra import wear

gray = np.asarray(Image.open("load.png").convert("L"))
img, dpi = wear.apply(gray, look="scan", dpi=96 * 3)
img.save("load-scan.png", dpi=(dpi, dpi))
```

### Altair

Altair 5.5 or later. Register a theme once:

```python
import altair as alt

INK = "black"

@alt.theme.register("cogra", enable=True)
def cogra_theme():
    return alt.theme.ThemeConfig({"config": {
        "font": "TeX Gyre Heros",
        "background": "white",
        "view": {"stroke": None},
        "axis": {"grid": False, "domainColor": INK, "tickColor": INK, "labelColor": INK,
                 "titleColor": INK, "titleFontWeight": "normal",
                 "labelFontSize": 11, "titleFontSize": 12},
        "legend": {"labelColor": INK, "titleColor": INK, "titleFontWeight": "normal"},
        "range": {"category": [INK], "symbol": ["circle", "circle", "square", "triangle-up"],
                  "strokeDash": [[1, 0], [6, 3], [2, 2], [6, 2, 2, 2]]},
        "line": {"color": INK, "strokeWidth": 1.2},
        "point": {"filled": True, "fill": "white", "stroke": INK, "opacity": 1,
                  "size": 45, "strokeWidth": 1},
        "bar": {"fill": "white", "stroke": INK, "strokeWidth": 1},
    }})
```

Draw lines and points as two layers. The lines carry the dashes (legend
hidden) and the points carry the symbols, open and filled in turn, so there
is a single legend:

```python
base = alt.Chart(df).encode(
    x=alt.X("load:Q", title="Memory load", axis=alt.Axis(values=[2, 4, 6])),
    y=alt.Y("rt:Q", title="Mean RT (msec)", scale=alt.Scale(zero=False)))
lines = base.mark_line().encode(strokeDash=alt.StrokeDash("cond:N", legend=None))
points = base.mark_point().encode(
    shape=alt.Shape("cond:N", title=None),
    fill=alt.Fill("cond:N", title=None, scale=alt.Scale(range=["white", "black", "white", "black"])))
chart = (lines + points).properties(width=260, height=200)
```

Vega-Lite has no hatching, so tell bars apart by fill:
`fill=alt.Fill("cond:N", scale=alt.Scale(range=["white", "black"]))`.

Where the font comes from depends on where the chart is drawn:

- **In a notebook or browser**, the browser draws it, so install TeX Gyre
  Heros on your system ([section 1](#1-install)).
- **Saved as PNG or SVG** (`chart.save("load.png", scale_factor=3)`, which
  needs `pip install vl-convert-python`), point vl-convert at the fonts that
  come with cogra first:

```python
from pathlib import Path
import vl_convert as vlc

vlc.register_font_directory(str(Path(cogra.__file__).parent / "fonts"))
chart.save("load.png", scale_factor=3)
```

A worn copy works as for plotly. A saved PNG is 72 dots per inch times
`scale_factor`.

## 4. Papers in the 1980 journal layout

`cogra.paper` sets a paper as an APA journal article of about 1980: two
justified columns of Schola, the title block and abstract across the first
page with the author note at the foot of its first column, centred running
heads in capitals, the Method section and the notes and references in small
type, and figures and tables across the page at the top. The measurements
come from a 1980 APA article. You write the paper in Markdown; cogra makes a
paginated web page and, if you like, a PDF of the same pages.

```bash
pip install "cogra[paper] @ git+https://github.com/lynde-wolf/cogra"
```

### Writing the paper

A Markdown file with a front-matter block at the top:

```markdown
---
title: "Judged duration of a tone as a function of its pitch"
authors: ["Harold B. Whitcombe^1", "Ruth E. Lindqvist^1", "Morris K. Abernathy^2"]
affiliations: ["^1Department of Psychology, Halvorsen College", "^2Marlow Institute"]
masthead: |
  Journal of Sensory and Temporal Processes
  1979, Vol. 12, No. 3, 101–109
running_head: "Judged duration of a tone"
abstract: |
  The abstract, set across the measure in slightly smaller type.
author_note:
  - "This work was supported by ..."
  - "Correspondence concerning this article should be addressed to ..."
---

# Introduction

Text. A footnote marker goes here.[^1]

# Method

## Subjects

### Procedure

Text that the "Procedure." heading runs in to.

# Results

![Mean reproduced duration by number of clicks. Bars show one standard error.](fig:clicks)

Table: Mean Reproduced Duration (msec) by Pitch and Number of Clicks

| Clicks | 500 Hz | 2,000 Hz |
|--------|-------:|---------:|
| 0      | 1,042  | 1,071    |

# References

Abernathy, M. K. (1971). On the counting of brief auditory events. *Journal of Sensory and Temporal Processes, 4*, 211–224.

[^1]: Footnotes are numbered and set at the foot of the column.
```

| Markdown | on the page |
|---|---|
| `# Heading` | centred heading. One named "Introduction" is left out, as APA did then |
| `## Heading` | italic heading, flush left |
| `### Heading` | italic heading run in to the next paragraph ("Procedure.") |
| text under `# Method` or `# Methods` | small type (change with `small_sections=`) |
| `[^1]` and `[^1]: text` | numbered footnote at the foot of its column |
| `![caption](fig:name)` on its own line | Figure *n*, across the page at the top; `name` is a matplotlib figure you pass in |
| `![caption](plot.png)` | the same with an image file (relative to the Markdown file) |
| `Table: title` then a Markdown table | Table *n*, ruled top and bottom, across the page |
| `- item` / `1. item` | bulleted or numbered paragraphs |
| paragraphs under `# References` | references in small type with hanging indents |
| `ANOVA` | set in small capitals |
| `$x_t$` | inline math (TeX) |
| `$$...$$` alone in a paragraph | a display equation, centred; `\tag{1}` numbers it at the column's edge |

### Math

Math is written in TeX and typeset by MathJax as SVG in the TeX Gyre Schola
math font, so it matches the text. MathJax comes with the package and is
copied next to the page only when the paper has math, so pages and PDFs
build offline. Dollar signs follow Pandoc's rules: `$...$` is math only when
there is no space just inside the dollars and no digit just after the
closing one, so "paid $3.50" stays money; write `\$` for a dollar sign that
would otherwise start math.

```markdown
The update is $b' = \tau(b, a, o)$, and

$$\begin{aligned} Q_V(b, a) = {} & r(b, a) \\
  & + \gamma \sum_{o} p(o \mid b, a)\, V(\tau(b, a, o)) \end{aligned} \tag{3}$$
```

Displays are typeset at the width of one column. One that is still too wide
is scaled down to fit, so break long equations across lines with
`aligned`, as a typesetter of the period would have.

The title is set in title case; words that already have capitals (fMRI,
SSRT) are left alone. Turn this off with `title_case: false`.

Other front-matter fields: `keywords`, `first_page_foot` (the small centred
line at the foot of page 1), `short_authors` (left-hand running head; the
default is "Author et al."), `start_page`, `columns`, `style`, `css`, `worn`
and `note` (a line shown above the pages on screen, not printed).

### Building it

```bash
cogra-paper my_paper.md                      # writes my_paper_site/index.html
cogra-paper my_paper.md --pdf my_paper.pdf   # and a PDF
cogra-paper my_paper.md --pdf my_paper.pdf --clean --columns 1
cogra-paper my_paper.md --figure clicks=plots/clicks.png   # an image for ![caption](fig:clicks)
```

From Python, which you need for matplotlib figures:

```python
from cogra import paper

p = paper.Paper.from_markdown("my_paper.md", figures={"clicks": fig})
p.save("site/")                    # open site/index.html, or serve the folder
p.pdf("my_paper.pdf")              # archival-scan look
p.pdf("my_paper-clean.pdf", worn=False)
```

`examples/paper/make_example.py` builds a complete example: `example.md`, an
invented 1979 article on the judged duration of tones, with a cogra figure.
Everything in it is fictional, including the authors, journal and
references. `examples/paper/make_bayes_bellman.py` builds a second, longer
example, `bayes_bellman.md`: an invented grand-unified-theory preprint with
eleven numbered equations, a theorem and proof, two tables and a bar figure. It
cites real works for real results alongside an invented one; its author
note says which is which. `examples/paper/make_regret_value_of_computation.py` builds a
third, `regret_value_of_computation.md`: an invented theory paper arguing that
expected regret is the value of further thought, with a theorem, a stopping
rule, an experiment and a line figure with a reference rule. It too says in
its author note what is invented.

- **The web page.** The page paginates itself in the browser, so open it
  from a local server (`python3 -m http.server --directory site`) or straight
  from the file. On screens narrower than 640 px it shows a single readable
  column instead of pages. A "Worn printing" box above the pages switches
  between the archival-scan look and clean type.
- **The PDF.** `pdf()` prints the paginated page with a Chrome-family
  browser already on your machine (Chrome, Chromium, Edge or Brave; set
  `COGRA_CHROME` to its path if it is somewhere unusual), or with Playwright
  if it is installed. It takes about 10 to 40 seconds. With the worn look,
  text is printed as an image, so it is not searchable or selectable. Use
  `worn=False` (`--clean`) for a PDF with real text, for example one you
  will send to anyone.

### Changing the layout

The 1980 page is the starting point. Every dimension is a CSS custom property
that `style=` overrides:

```python
p = paper.Paper.from_markdown("my_paper.md", style={
    "page-w": "612pt", "page-h": "792pt",      # US letter
    "margin-l": "54pt", "margin-r": "54pt",
    "body": "10pt", "lead": "12pt",            # body type and line spacing
    "gutter": "18pt",
})
```

| property | default | what it sets |
|---|---|---|
| `page-w`, `page-h` | 531pt, 726pt | page size (the PDF uses it too) |
| `margin-l`, `margin-r`, `body-top`, `margin-b` | 62, 76, 66, 84pt | text block |
| `gutter` | 11pt | space between columns |
| `body`, `lead`, `indent` | 9.2pt, 11pt, 10pt | body type, line spacing, paragraph indent |
| `small`, `small-lead` | 8.1pt, 9.1pt | Method, notes, captions |
| `ref`, `ref-lead` | 7.6pt, 9pt | references |
| `title`, `author`, `affil`, `abstract` | 13.6, 10.4, 8.6, 8.7pt | first-page type |
| `abstract-w` | 79% of the text width | abstract measure |
| `face` | TeX Gyre Schola | typeface stack |

`columns=1` sets the text in a single column. For anything else, add a
stylesheet with `css=["my.css"]`; it loads after the default one, so its
rules win. The default stylesheet is `cogra/paper/apa1980.css` and the page
maker `cogra/paper/paginate.js`.

### Writing the body in HTML

If your text comes from somewhere else (another document converter, a PDF),
build the `Paper` directly. `blocks` is the body as a list of HTML elements
in order: `<p>`, `<h2 class="h1">` (centred heading), `<h3 class="h2">`
(italic heading), `<p class="small">`, `<p class="ref">`, and figures made
with `paper.figure_block(n, "name", caption_html)`. Footnote markers are
`<sup class="fn" data-n="1">1</sup>`, with the note text in
`footnotes={1: "..."}`. Math is `\(...\)` inline and
`<p class="display nosplit">\[...\]</p>` for a display; the page loads
MathJax when it finds either.

## 5. R and ggplot2

Needs ggplot2 4.0 or later. Install the TeX Gyre fonts on your system (see
[Install](#1-install)) so R can find them.

```r
library(ggplot2)
source("extras/R/cogra.R")     # path to the file in this repository
```

### Option A: add `cogra()` to a plot you already have

```r
p <- ggplot(df, aes(load, rt, colour = cond)) +
  geom_line() + geom_point(size = 2) +
  labs(x = "Memory load", y = "Mean RT (msec)", colour = "Trial")

p + cogra()
```

`cogra()` finds the variable mapped to colour (or fill) and maps it to
shape and line type as well. It then makes everything black on white and
adds the theme. The four scales share one title, so you get a single legend.
A continuous colour becomes a grey ramp, with a message warning that light
greys disappear in a scan.

### Option B: build the plot in the style

```r
ggplot(df, aes(load, rt, shape = cond, fill = cond, linetype = cond)) +
  geom_line() + geom_point(size = 2) +
  scale_shape_cogra() + scale_fill_cogra() + scale_linetype_cogra() +
  labs(x = "Memory load", y = "Mean RT (msec)") +
  theme_cogra()
```

The scales give open circle, filled circle, open square and filled triangle,
with solid and dashed lines. Map the same variable to `shape`, `fill` and
`linetype` so they combine into one legend. `theme_cogra(base_size = 10,
base_family = "TeX Gyre Heros")` takes the usual theme arguments.

### Significance brackets

`signif_cogra(x1, x2, y, p = )` adds a bracket at height `y` with stars
above it. Unlike the Python version it does not find the height itself, so
give `y` in data units, just above the taller bar. On a discrete axis the
categories sit at 1, 2, 3, ...; dodged bars of the default width sit at
x − 0.225 and x + 0.225.

```r
ggplot(df, aes(block, ssrt, fill = cond)) +
  geom_col(position = position_dodge(0.9), colour = "black") +
  scale_fill_cogra(name = NULL) + theme_cogra() +
  signif_cogra(1 - 0.225, 1 + 0.225, 300, p = .003) +   # **
  signif_cogra(1, 3, 330, p = .012, show = "p")          # italic p = .012
```

`show = "p"`, `label = "n.s."` and `ns = TRUE` work as in Python, and
`stars_cogra(p)` gives the stars alone. A p that is not significant adds
nothing unless `ns = TRUE`. The y axis grows to fit the labels.

To compute the tests inside the plot, the `ggsignif` package works with
`theme_cogra()`. Give it room at the top, or its labels are cut off:

```r
library(ggsignif)
ggplot(d, aes(cond, ssrt)) + geom_boxplot(fill = "white") +
  geom_signif(comparisons = list(c("Feature", "Conjunction")), map_signif_level = TRUE,
              textsize = 3.5, family = "TeX Gyre Heros", tip_length = 0.02, size = 0.35) +
  scale_y_continuous(expand = expansion(mult = c(0.05, 0.12))) +
  theme_cogra()
```

### Saving

```r
ggsave("fig1.pdf", width = 3.2, height = 2.6, device = cairo_pdf)  # embeds the font
ggsave("fig1.png", width = 3.2, height = 2.6, dpi = 300)           # needs ragg for the font
```

The default PDF device cannot use system fonts, so use `cairo_pdf`. For PNG,
install `ragg`: `ggsave` then picks it automatically. Without it, R falls
back to a default sans font. Hatched bars need the `ggpattern` package.

For a worn copy of an R figure, save a PNG at 600 dpi and pass it to the
Python wear functions:

```python
import numpy as np
from PIL import Image
from cogra import wear

gray = np.asarray(Image.open("fig1.png").convert("L"))
img, dpi = wear.apply(gray, look="scan", dpi=600)
img.save("fig1-scan.png", dpi=(dpi, dpi))
```

## 6. Web pages

`extras/web/` contains:

| file | what it is |
|---|---|
| `cogra.css` | colours, the Schola face, and journal-page layout classes |
| `fonts/` | Schola as `.woff2`; keep it next to the CSS |
| `cogra-specks-a.png`, `cogra-specks-b.png` | dust specks for worn pages; keep them next to the CSS |
| `cogra-specimen.html` | a sample journal page, an invented 1960 article, using every class |
| `cogra-filters.html` | SVG filters for worn-looking text |

### On a web page

Copy `cogra.css`, `fonts/` and the two speck images next to your page and link the CSS. Wrap the
content in `<article class="cogra-page">`. The CSS styles headings,
paragraphs, figures, tables, notes and references inside it in journal-page
fashion. The full set of classes, with an example of each, is in
`cogra-specimen.html`:

| class | use |
|---|---|
| `.cogra-page` | the page: paper colour, column width, justified Schola |
| `.cogra-runhead` | running head (a flex row; put two spans in it) |
| `.cogra-author`, `.cogra-affil` | author line in small caps, affiliation in italics |
| `.cogra-summary` | an indented abstract in smaller type |
| `.cogra-runin` | an italic run-in heading at the start of a paragraph |
| `.cogra-notes` | footnotes, with a short rule above |
| `.cogra-label`, `.cogra-tablewrap`, `.cogra-tabno` | figure labels and tables |
| `.cogra-refs` | reference list with hanging indents |
| `.cogra-folio` | the page number |
| `.cogra-controls` | checkboxes, radio buttons, sliders, menus and buttons drawn in ink (also applied inside `.cogra-page`) |

For worn-looking text, paste the `<svg>` block from
`cogra-filters.html` into the page `<body>` once. Then add `cogra-worn` to
the page and wrap the text in `.cogra-ink`. Add `cogra-photocopy` for a photocopy
instead of a scan. A worn page also gets dust specks, and a clean one none;
add `cogra-nospecks` to keep a worn page free of them. The filter has to be inside the same HTML file, because
most browsers ignore filters loaded from a separate SVG file. Readers whose
system asks for more contrast get clean text.

The CSS follows each reader's dark-mode setting and switches to light text
on a dark page (a "microfilm negative"). To show everyone the same page, put
`data-theme="light"` (or `"dark"`) on the `<html>` element.

Form controls inside `.cogra-page` or a `.cogra-controls` element are drawn in
ink instead of the system's accent colour: a checkbox is a ballot box with a
cross. Put them inside `.cogra-ink` too, and the worn filter wears them with
the type.

Don't use the worn filters on anything that must look the same in every
browser: they blur edges in ways that depend on the browser.

## 7. LaTeX documents

Copy `extras/latex/cogra.sty` next to your `.tex` file.

```latex
\documentclass[10pt]{article}
\usepackage[journal]{cogra}
\cograrunning{E. G. Pellham and D. R. Okonkwo}{Goal-Box Illumination and Running Speed}

\begin{document}
\cogratitle{Running Speed in a Straight Alley as a Function of Goal-Box Illumination}
\cograauthor{Edwin G. Pellham and Dorothy R. Okonkwo}
\cograaffil{Department of Psychology, Halvorsen College}
\cogranote{Footnote under the title: funding, correspondence.}
\cogramaketitle

\begin{cograsummary}
A short abstract, indented on both sides.
\end{cograsummary}

\section{Method}
...
\end{document}
```

| option | layout |
|---|---|
| `journal` (default) | 7 × 10 in page, one column, 10 pt |
| `twocol` | letter paper, two narrow columns |
| `thesis` | letter paper, 1 in margins, looser leading |
| `aged` | tints the page like old paper (screen only; leave off for printing) |

Compile with LuaLaTeX or XeLaTeX to get TeX Gyre Schola; it ships with TeX
Live and MacTeX. pdfLaTeX works but uses the `newcent` font instead.
`extras/latex/demo.tex` is a complete example with a bibliography, an
invented 1950s article whose authors, data and references are all fictional:

```bash
cd extras/latex
lualatex demo && bibtex demo && lualatex demo && lualatex demo
```

Section heads come out centred in capitals, subsections centred in italics,
and subsubsections as italic run-in heads. Footnotes are marked with symbols
(\*, †, ‡). Citations use natbib (`\citet`, `\citep`).

## 8. The fonts in other apps

Two sets of fonts come with the package:

- **TeX Gyre Heros and Schola** (`src/cogra/fonts/`). These are clean,
  free clones of Helvetica and Century Schoolbook. Install them for Keynote,
  PowerPoint, Word, Illustrator or Figma, and set figure labels in Heros and
  body text in Schola.
- **Heros Scan and Schola Scan** (`extras/scanfont/fonts/`). The same faces
  with the 1-bit scan texture built into every letter, so text typed in any
  app looks scanned.
- **Heros Scan Soft and Schola Scan Soft** (same folder). The scan letters
  with a faint, uneven one-pixel grey bleed on some edges, mostly the lower
  right. Apps that cannot show colour fonts show the plain scan letters
  instead.

The scan fonts are ready-made `.ttf` files; install them like any other font
(on a Mac, double-click each one and click *Install Font*). Each family has
regular, italic, bold and bold italic. `extras/scanfont/README.md` covers
Canva, embedding the fonts in a deck you send to others, and rebuilding them
with different settings (roughness, how coarse the stair-steps are, how much
the Soft fonts bleed).

For the full look in slides, set the scan font in black on a white
background, and use worn PNGs from `save_vintage` for the figures. A tinted
"paper" background reads as a tinted screen, not as paper.

## 9. Troubleshooting

| problem | fix |
|---|---|
| Python figure text is in DejaVu Sans | call `cogra.use()` before making the figure |
| every seaborn group looks the same after `restyle` | pass `palette="deep"` (or any palette) to seaborn |
| `restyle` warns "already restyled" | rebuild the figure from scratch; restyle runs once per figure |
| R falls back to a default font | install the TeX Gyre fonts, use `cairo_pdf` for PDF and `ragg` for PNG |
| R shows two legends | map one variable to `shape`, `fill` and `linetype`, or use `+ cogra()` |
| a bracket's stars are cut off at the top in R | `signif_cogra` makes room itself; with `ggsignif`, add `scale_y_continuous(expand = expansion(mult = c(0.05, 0.12)))` |
| plotnine legend keys stay in colour after `restyle` | build the plot with `theme_cogra` instead ([section 3](#3-seaborn-pandas-and-other-plotting-libraries)) |
| plotly or Altair labels are in Helvetica or Arial | install TeX Gyre Heros on your system; for Altair PNG/SVG, `vl_convert.register_font_directory` |
| web page is dark for some readers | add `data-theme="light"` to `<html>` |
| web text has no worn effect | paste the SVG filter block into the same HTML file |
| scatter has stray dots in a worn copy | specks are on; drop `specks=True` |
| worn copy takes a long time | normal for the `aged` look on big figures; it is cached afterwards |
| `pdf()` says it needs Chrome | install Chrome, Chromium, Edge or Brave, set `COGRA_CHROME`, or `pip install playwright && playwright install chromium` |
| PDF text cannot be selected | the worn look prints text as an image; use `worn=False` (`--clean`) |
| a figure prints very large or small | figures print at their own size (a 3.2-inch figure is 3.2 inches); change `figsize` |
