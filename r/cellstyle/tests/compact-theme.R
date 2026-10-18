library(ggplot2)
library(cellstyle)

p <- ggplot(data.frame(x = 1, y = 2), aes(x, y)) + geom_point() + theme_cellstyle("manuscript")
t <- ggplot2::calc_element("axis.text.x", p$theme)
stopifnot(t$size == 7, ggplot2::calc_element("axis.title.x", p$theme)$size == 8,
          ggplot2::calc_element("plot.title", p$theme)$size == 9,
          ggplot2::calc_element("legend.text", p$theme)$size == 7.5,
          ggplot2::calc_element("legend.title", p$theme)$size == 7.5,
          ggplot2::calc_element("axis.line.x", p$theme)$linewidth == .7 / 2.845276)

original_theme <- ggplot2::theme_get()
invisible(theme_cellstyle("manuscript"))
stopifnot(identical(ggplot2::theme_get(), original_theme))

d <- data.frame(x = c(1, 2), y = c(2, 3))
s <- quantitative_scatter(d, "x", "y")
stopifnot(length(s$layers[[1]]$aes_params$stroke) == 1L,
          s$layers[[1]]$aes_params$stroke == .35 / 2.845276,
          s$layers[[1]]$aes_params$alpha == 1,
          s$layers[[1]]$aes_params$shape == 21)
s2 <- quantitative_scatter(d, "x", "y", color = "red", alpha = .3, point_size = 2)
stopifnot(s2$layers[[1]]$aes_params$alpha == .3,
          s2$layers[[1]]$aes_params$size == 2)

if (requireNamespace("ggbeeswarm", quietly = TRUE)) {
  d <- data.frame(group = c("A", "A", "B"), value = c(1, 2, 3))
  b <- replicate_distribution(d, "group", "value")
  stopifnot(b$layers[[1]]$aes_params$alpha == 1,
            identical(as.numeric(b$data$.cellstyle_value), d$value))
  b2 <- replicate_distribution(d, "group", "value", alpha = .4)
  stopifnot(b2$layers[[1]]$aes_params$alpha == .4)
}

# An explicit base size scales the approved role ratios instead of being ignored.
large <- theme_cellstyle("manuscript", base_size = 16)
stopifnot(large$axis.title$size == 16, large$axis.text$size == 14,
          large$legend.text$size == 15, large$plot.title$size == 18)
cat("PASS: compact theme, native marker overrides, replicate opacity and explicit base size\n")
