# Vendored MathJax

MathJax 4.1.3 (`mathjax` on npm) and its TeX Gyre Schola math font
(`@mathjax/mathjax-schola-font` 4.1.3), both Apache-2.0 (see `LICENSE`).
Only what `cogra.paper` loads is kept: the startup loader, core, TeX input
with its extensions, SVG output, and the Schola SVG font. Accessibility and
speech components are left out. `Paper.save()` copies this folder next to
the page when the paper contains math, so pages and PDFs build offline.
