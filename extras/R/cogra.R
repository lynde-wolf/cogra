# cogra.R: ggplot2 theme and scales for the Cognitive Revolution Aesthetic
# (cogra) figure look.
#
# Tested with ggplot2 4.0.0 (tests/test_r.py runs it when R and ggplot2 are installed).
# Needs ggplot2 >= 4.0.0, which added ink/paper/accent theme arguments and
# element_geom(); these set defaults for every geom at once. For the TeX Gyre
# fonts to be found, install them on the
# system and save with a device that reads system fonts (ragg, or
# cairo_pdf). Hatched bars need the ggpattern package.

library(ggplot2)

theme_cogra <- function(base_size = 10, base_family = "TeX Gyre Heros") {
  # accent defaults to blue (#3366FF) in ggplot2 and is used by geom_smooth;
  # set to black so no geom introduces colour.
  theme_classic(base_size = base_size, base_family = base_family,
                ink = "black", paper = "white", accent = "black") %+replace%
    theme(
      geom = element_geom(
        ink = "black", paper = "white", accent = "black",
        linewidth = 0.45, borderwidth = 0.45,
        family = base_family, fontsize = base_size,
        pointsize = 1.6, pointshape = 21      # open circle filled with paper
      ),
      text              = element_text(colour = "black"),
      axis.line         = element_line(colour = "black", linewidth = 0.4),
      axis.ticks        = element_line(colour = "black", linewidth = 0.35),
      axis.ticks.length = unit(-3, "pt"),            # inward ticks
      axis.text.x       = element_text(colour = "black", margin = margin(t = 5)),
      axis.text.y       = element_text(colour = "black", margin = margin(r = 5), hjust = 1),
      legend.background = element_blank(),
      legend.key        = element_blank(),
      panel.grid        = element_blank(),
      plot.background   = element_rect(fill = "white", colour = NA),
      strip.background  = element_blank(),
      strip.text        = element_text(face = "plain")
    )
}

# Open circle, filled circle, open square, filled triangle; solid/dashed lines
scale_shape_cogra    <- function(...) scale_shape_manual(values = c(21, 19, 22, 17), ...)
scale_fill_cogra     <- function(...) scale_fill_manual(values = c("white", "black", "white", "black"), ...)
scale_linetype_cogra <- function(...) scale_linetype_manual(values = c("solid", "solid", "dashed", "dashed"), ...)

# ---- Significance brackets ----
# stars_cogra(p): "***", "**", "*" or "" (p < .001, .01, .05).
# signif_cogra(x1, x2, y, p = , label = ): a bracket from x1 to x2 at height y
# with stars above it, as layers to add to a plot. On a discrete axis the
# positions are 1, 2, 3, ...; dodged bars sit at x +/- width / 4 (0.225 for
# the default width 0.9). show = "p" writes an italic "p = .012" instead of
# stars. A p that is not significant adds nothing unless ns = TRUE ("n.s.").
# tick is the length of the bracket's ends, in data units (default 2% of y).
stars_cogra <- function(p) {
  ifelse(p < .001, "***", ifelse(p < .01, "**", ifelse(p < .05, "*", "")))
}

signif_cogra <- function(x1, x2, y, p = NULL, label = NULL, show = c("stars", "p"),
                         ns = FALSE, tick = NULL, size = 3.5, family = "TeX Gyre Heros") {
  show <- match.arg(show)
  parse <- FALSE
  if (is.null(label)) {
    if (is.null(p)) stop("give p or label")
    if (show == "p") {
      parse <- TRUE
      label <- if (p < .001) "italic(p) < '.001'"
               else paste0("italic(p) == '", sub("^0", "", sprintf("%.3f", p)), "'")
    } else {
      label <- stars_cogra(p)
      if (label == "" && ns) label <- "n.s."
    }
  }
  if (label == "") return(list())
  if (is.null(tick)) tick <- 0.02 * abs(y)
  list(
    annotate("path", x = c(x1, x1, x2, x2), y = c(y - tick, y, y, y - tick),
             colour = "black", linewidth = 0.35),
    annotate("text", x = (x1 + x2) / 2, y = y, label = label, parse = parse,
             vjust = -0.3, size = size, family = family, colour = "black"),
    # an invisible point above the label, so the y axis grows to fit it
    annotate("blank", x = (x1 + x2) / 2, y = y + 0.1 * abs(y))
  )
}

# Example:
# ggplot(df, aes(setsize, rt, shape = response, fill = response, linetype = response)) +
#   geom_line() + geom_point(size = 2) +
#   scale_shape_cogra() + scale_fill_cogra() + scale_linetype_cogra() +
#   labs(x = "Size of positive set", y = "Mean RT (msec)") +
#   theme_cogra()
# ggsave("fig1.pdf", width = 3.2, height = 2.6, device = cairo_pdf)

# ---- Geom coverage on the R side ----
# ggplot2 itself provides every geom; element_geom() above makes them all
# draw in black on white. Most then match the Python versions directly.
# These need extra work to match the period look, because the Python
# versions draw them differently from ggplot2's defaults:
#   geom_area, geom_ribbon, geom_density (fill), geom_rect, geom_polygon,
#   geom_col/geom_bar groups, geom_map, geom_sf, geom_violin, geom_boxplot
#       -> hatching: ggpattern's geom_*_pattern() equivalents
#   geom_contour_filled, geom_density_2d_filled
#       -> hatching per level: ggpattern, or draw lines only
#   geom_tile, geom_raster, geom_bin_2d, geom_hex
#       -> grey fills vanish in a 1-bit scan; Python draws halftone dots.
#          Closest ggplot2 route: stat_summary_2d()/geom_point(size = value).
#   geom_smooth
#       -> ggplot2 draws a grey ribbon; set fill = NA and add the band edges
#          as dashed lines for the period look.

# ---- p + cogra(): restyle a finished plot, inheriting its mappings ----
#
#   p <- ggplot(df, aes(load, rt, colour = cond)) + geom_line() + geom_point()
#   p + cogra()
#
# What it does (tests/test_r.py checks the discrete and continuous cases):
#   * Finds the grouping aesthetic: colour (or fill) in the plot mapping or
#     any layer's mapping.
#   * If it is discrete, maps the same variable to shape and linetype too,
#     so groups stay distinguishable without colour. ggplot2 merges legends
#     whose scales have the same title, so one legend shows colour, shape
#     and linetype together.
#   * Colour becomes black for every group; fill alternates white and black.
#   * A continuous colour scale becomes a grey ramp ending in black, with a
#     message, because greys do not survive a 1-bit scan.
#   * Adds theme_cogra().
#
# Implementation notes:
#   * `+` dispatches to ggplot_add(); in ggplot2 4.x that is a thin wrapper
#     over update_ggplot(), so an S3 ggplot_add method works in 3.x and 4.x.
#   * plot$mapping is readable and assignable in 4.x (S7 compatibility
#     methods for `$` and `$<-`).
#   * Layers are ggproto objects with reference semantics, so a layer is
#     cloned with ggproto(NULL, layer) before its mapping is changed;
#     otherwise the user's original plot would be modified too.

cogra <- function(base_size = 10, base_family = "TeX Gyre Heros") {
  structure(list(base_size = base_size, base_family = base_family), class = "cogra")
}

.cogra_group_aes <- function(mapping) {
  for (a in c("colour", "fill")) if (!is.null(mapping[[a]])) return(mapping[[a]])
  NULL
}

.cogra_is_discrete <- function(quo, data) {
  vals <- tryCatch(rlang::eval_tidy(quo, data), error = function(e) NULL)
  is.null(vals) || !is.numeric(vals)
}

ggplot_add.cogra <- function(object, plot, object_name, ...) {
  grp <- .cogra_group_aes(plot$mapping)
  data <- plot$data
  if (is.null(grp)) {
    for (l in plot$layers) {
      g <- .cogra_group_aes(l$mapping)
      if (!is.null(g)) { grp <- g; if (!is.null(l$data) && is.data.frame(l$data)) data <- l$data; break }
    }
  }

  if (!is.null(grp)) {
    if (.cogra_is_discrete(grp, data)) {
      # One title for all four scales, so ggplot2 merges them into one legend.
      # A title set with labs(colour = ...) or labs(fill = ...) is kept.
      labs_set <- intersect(c("colour", "fill"), names(plot$labels))
      title <- if (length(labs_set)) plot$labels[[labs_set[1]]] else rlang::as_label(grp)
      add_to <- function(m) {
        for (a in c("shape", "linetype")) if (is.null(m[[a]])) m[[a]] <- grp
        m
      }
      plot$mapping <- add_to(plot$mapping)
      plot$layers <- lapply(plot$layers, function(l) {
        if (is.null(.cogra_group_aes(l$mapping))) return(l)
        l2 <- ggplot2::ggproto(NULL, l)        # clone: do not mutate the original
        l2$mapping <- add_to(l$mapping)
        l2
      })
      plot <- plot +
        scale_colour_manual(title, values = rep("black", 12)) +
        scale_fill_manual(title, values = rep(c("white", "black"), 6)) +
        scale_shape_manual(title, values = rep(c(21, 19, 22, 17, 23, 25), 2)) +
        scale_linetype_manual(title, values = rep(c("solid", "dashed", "dotted", "dotdash", "longdash", "twodash"), 2))
    } else {
      message("cogra(): continuous colour mapped to a grey ramp; ",
              "light greys will disappear in a 1-bit scan look.")
      plot <- plot + scale_colour_gradient(low = "grey75", high = "black") +
        scale_fill_gradient(low = "grey90", high = "black")
    }
  }
  plot + theme_cogra(object$base_size, object$base_family)
}
