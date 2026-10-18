library(cellstyle)
library(ggplot2)

expect_error <- function(expr, pattern) {
  message <- tryCatch({ force(expr); NULL }, error = conditionMessage)
  stopifnot(!is.null(message), grepl(pattern, message))
}
case <- function(label, code) { force(code); cat("PASS:", label, "\n") }

case("1 named identities, native theme and facets compose", {
  colors <- c(A = "#1764AB", B = "#00A2A5")
  d <- data.frame(x = 1:4, y = 4:1, identity = c("B", "A", "B", "A"), panel = c("one", "one", "two", "two"))
  old_theme <- theme_get()
  p <- ggplot(d, aes(x, y, colour = identity)) + geom_point() +
    scale_colour_cellstyle(colors) + theme_cellstyle() + facet_wrap(~panel)
  b <- ggplot_build(p)
  stopifnot(inherits(p, "ggplot"), identical(theme_get(), old_theme),
    identical(b$data[[1]]$colour, unname(colors[d$identity])),
    nrow(b$layout$layout) == 2L,
    identical(editorial_vivid(), c("#1764AB", "#00A2A5", "#E6A700", "#D43F3A", "#8A4FA3")))
  expect_error(scale_fill_cellstyle(unname(colors)), "named")
  expect_error(editorial_vivid(6), "finite number")
  missing <- data.frame(x = 1:2, y = 1:2, identity = c("A", "unmapped"))
  expect_error(ggplot_build(ggplot(missing, aes(x, y, colour = identity)) + geom_point() +
    scale_colour_cellstyle(colors)), "unmapped|missing|Missing|identit")
  missing$identity[2] <- NA_character_
  stopifnot(nrow(ggplot_build(ggplot(missing, aes(x, y, colour = identity)) + geom_point() +
    scale_colour_cellstyle(colors))$data[[1]]) == 2L)
})

case("2 true beeswarm preserves observations and median/IQR", {
  if (requireNamespace("ggbeeswarm", quietly = TRUE)) {
    d <- data.frame(group = factor(rep(c("B", "A"), each = 4), levels = c("B", "A", "empty")), value = c(1, 1, 2, 4, 3, 4, 7, 8))
    before <- d
    p <- replicate_distribution(d, "group", "value")
    b <- ggplot_build(p)
    stopifnot(identical(d, before), identical(p$data$.cellstyle_value, d$value),
      inherits(p$layers[[1]]$position, "PositionBeeswarm"),
      identical(sort(b$data[[1]]$y), sort(d$value)),
      identical(as.character(p$layers[[2]]$data$.cellstyle_group), c("B", "A")),
      isTRUE(all.equal(p$layers[[2]]$data$median, c(1.5, 5.5))),
      isTRUE(all.equal(p$layers[[2]]$data$q1, c(1, 3.75))),
      isTRUE(all.equal(p$layers[[2]]$data$q3, c(2.5, 7.25))),
      identical(p$scales$get_scales("x")$limits, c("B", "A", "empty")),
      p$layers[[3]]$aes_params$shape == 21)
  } else cat("SKIP installed beeswarm geometry; optional dependency absent\n")
})

case("3 quantitative scatter keeps native data and opt-in fit", {
  d <- data.frame(x = 1:6, y = c(2, 3, 2, 6, 4, 7))
  p <- quantitative_scatter(d, "x", "y")
  stopifnot(identical(p$data, d), length(p$layers) == 1L,
    nrow(ggplot_build(p)$data[[1]]) == nrow(d),
    length(quantitative_scatter(d, "x", "y", fit = TRUE)$layers) == 2L)
  expect_error(quantitative_scatter(data.frame(x = c(1, 1), y = 1:2), "x", "y", fit = TRUE), "distinct")
})

case("4 supplied comparisons and quantitative scales compile", {
  observations <- data.frame(group = rep(c("A", "B"), each = 3), value = c(1, 2, 3, 2, 3, 5))
  base <- ggplot(observations, aes(group, value)) + geom_point() + theme_cellstyle()
  comparisons <- data.frame(group_a = "A", group_b = "B", p = .5, p_adjusted = .04)
  annotated <- add_comparisons(base, comparisons)
  stopifnot(identical(annotated$layers[[3]]$data$label, "P = 0.04 adj."),
    nrow(ggplot_build(annotated)$data[[1]]) == nrow(observations),
    length(base$layers) == 1L)
  expect_error(add_comparisons(base + scale_y_log10(), comparisons), "untransformed")
  expect_error(add_comparisons(base + facet_wrap(~group), comparisons), "unfaceted")
  expect_error(add_comparisons(base + coord_cartesian(ylim = c(0, 6)), comparisons), "fixed y limits")
  d <- expand.grid(x = letters[1:3], y = LETTERS[1:2])
  d$value <- seq_len(nrow(d))
  for (scale in list(scale_fill_positive(), scale_fill_marker())) {
    p <- ggplot(d, aes(x, y, fill = value)) + geom_tile() + scale + theme_cellstyle()
    stopifnot(nrow(ggplot_build(p)$data[[1]]) == nrow(d))
  }
})

case("5 optional dependencies fail locally with installation guidance", {
  # Clone the guard in a private environment; never alter package namespaces,
  # installed libraries or availability of another process's dependencies.
  guard <- getFromNamespace(".require_optional", "cellstyle")
  sandbox <- new.env(parent = environment(guard))
  sandbox$requireNamespace <- function(...) FALSE
  environment(guard) <- sandbox
  sandbox$.require_optional <- guard
  replicate_missing <- replicate_distribution
  labels_missing <- repel_labels
  environment(replicate_missing) <- sandbox
  environment(labels_missing) <- sandbox
  expect_error(replicate_missing(data.frame(g = "A", v = 1), "g", "v"), "install.packages.*ggbeeswarm")
  expect_error(labels_missing(data.frame(x = 1), aes(x = x)), "install.packages.*ggrepel")
  if (requireNamespace("ggrepel", quietly = TRUE)) {
    d <- data.frame(x = 1:2, y = 1:2, label = c("A", "B"))
    p <- ggplot(d, aes(x, y)) + geom_point() + repel_labels(d, aes(x, y, label = label))
    stopifnot(length(ggplot_build(p)$data) == 2L,
      identical(p$layers[[2]]$geom_params$max.overlaps, Inf))
  }
})
