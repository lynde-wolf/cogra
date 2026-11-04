import shutil
import subprocess

import pytest
from conftest import ROOT

RSCRIPT = shutil.which("Rscript")
pytestmark = pytest.mark.skipif(RSCRIPT is None, reason="R not installed")


def test_r_theme(tmp_path):
    has_gg = subprocess.run([RSCRIPT, "-e", "quit(status = !requireNamespace('ggplot2', quietly = TRUE))"])
    if has_gg.returncode:
        pytest.skip("ggplot2 not installed")
    script = tmp_path / "t.R"
    script.write_text(f"""
suppressMessages(library(ggplot2))
source("{ROOT / "extras" / "R" / "cogra.R"}")
df <- data.frame(s = rep(1:6, 2), rt = c(392 + 38 * 1:6, 397 + 38 * 1:6), r = rep(c("P", "N"), each = 6))
p <- ggplot(df, aes(s, rt, shape = r, fill = r, linetype = r)) + geom_line() + geom_point() +
  scale_shape_cogra() + scale_fill_cogra() + scale_linetype_cogra() + theme_cogra()
ggsave("{tmp_path / "fig.png"}", p, width = 3, height = 2.4, dpi = 100)
""")
    r = subprocess.run([RSCRIPT, str(script)], capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "fig.png").stat().st_size > 0


def test_r_cogra_pipe_merges_legends(tmp_path):
    """p + cogra() maps the colour groups to shape and linetype too and
    shows one legend, whatever the colour title is."""
    has_gg = subprocess.run([RSCRIPT, "-e", "quit(status = !requireNamespace('ggplot2', quietly = TRUE))"])
    if has_gg.returncode:
        pytest.skip("ggplot2 not installed")
    script = tmp_path / "t.R"
    script.write_text(f"""
suppressMessages(library(ggplot2))
source("{ROOT / "extras" / "R" / "cogra.R"}")
df <- data.frame(load = rep(c(2, 4, 6), 2), rt = c(510, 548, 590, 520, 571, 625), cond = rep(c("Go", "Stop"), each = 3))
n_legends <- function(p) {{
  g <- ggplotGrob(p)
  box <- g$grobs[[grep("guide-box-right", g$layout$name)]]
  sum(grepl("^guides", box$layout$name))
}}
base <- ggplot(df, aes(load, rt, colour = cond)) + geom_line() + geom_point()
for (p in list(base + cogra(), base + labs(colour = NULL) + cogra(),
               base + labs(colour = "Trial") + cogra()))
  stopifnot(n_legends(p) == 1)
d2 <- data.frame(x = 1:5, y = 1:5, z = 1:5)
cont <- ggplot(d2, aes(x, y, colour = z)) + geom_point() + cogra()
ggsave("{tmp_path / "cont.png"}", cont, width = 3, height = 2.4, dpi = 100)
""")
    r = subprocess.run([RSCRIPT, str(script)], capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    assert "grey ramp" in r.stderr


def test_r_signif(tmp_path):
    has_gg = subprocess.run([RSCRIPT, "-e", "quit(status = !requireNamespace('ggplot2', quietly = TRUE))"])
    if has_gg.returncode:
        pytest.skip("ggplot2 not installed")
    script = tmp_path / "t.R"
    script.write_text(f"""
suppressMessages(library(ggplot2))
source("{ROOT / "extras" / "R" / "cogra.R"}")
stopifnot(identical(stars_cogra(c(.0004, .005, .03, .2)), c("***", "**", "*", "")))
df <- data.frame(g = factor(1:3), y = c(240, 280, 260))
p <- ggplot(df, aes(g, y)) + geom_col(fill = "white", colour = "black") + theme_cogra() +
  signif_cogra(1, 2, 300, p = .003) + signif_cogra(2, 3, 300, p = .2) +
  signif_cogra(2, 3, 300, p = .2, ns = TRUE) + signif_cogra(1, 3, 330, p = .012, show = "p")
b <- ggplot_build(p)
labs <- unlist(lapply(b$data, function(d) if ("label" %in% names(d)) as.character(d$label)))
stopifnot(identical(labs, c("**", "n.s.", "italic(p) == '.012'")))
stopifnot(length(signif_cogra(1, 2, 300, p = .5)) == 0)
ggsave("{tmp_path / "fig.png"}", p, width = 3, height = 2.4, dpi = 100)
""")
    r = subprocess.run([RSCRIPT, str(script)], capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 0, r.stderr
