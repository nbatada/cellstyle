# Validate wide scientific summary tables before converting them to ggplot layers.
.named_matrix <- function(x, name) {
  if (is.data.frame(x)) x <- as.matrix(x)
  if (!is.matrix(x) || !is.numeric(x) || any(dim(x) == 0) || any(is.infinite(x)))
    stop(name, " must be a numeric matrix with finite values or NA.", call. = FALSE)
  for (ids in list(rownames(x), colnames(x))) {
    if (is.null(ids) || anyNA(ids) || any(!nzchar(ids)) || anyDuplicated(ids))
      stop(name, " needs unique, nonempty row and column names.", call. = FALSE)
  }
  x
}

.matrix_cells <- function(x) {
  data.frame(row = factor(rep(rownames(x), ncol(x)), levels = rev(rownames(x))),
             column = factor(rep(colnames(x), each = nrow(x)), levels = colnames(x)),
             value = as.vector(x))
}

.matrix_plot <- function(d) {
  ggplot2::ggplot(d, ggplot2::aes(.data$column, .data$row)) +
    ggplot2::scale_x_discrete(drop = FALSE, guide = ggplot2::guide_axis(angle = 45)) + ggplot2::scale_y_discrete(drop = FALSE) +
    ggplot2::labs(x = NULL, y = NULL)
}

.marker_label <- function(label) {
  if (!is.character(label) || length(label) != 1L || is.na(label) || !nzchar(trimws(label)))
    stop("Supply a nonempty measurement or interval label.", call. = FALSE)
}

.readable_linear_breaks <- function(limits) {
  lo <- limits[[1]]
  hi <- limits[[2]]
  if (lo == hi) {
    padding <- max(abs(lo), 1) * .05
    lo <- lo - padding
    hi <- hi + padding
  }
  target <- (hi - lo) / 2
  unit <- 10^floor(log10(target))
  choices <- c(1, 2, 2.5, 5, 10) * unit
  step <- max(choices[choices <= target])
  first <- ceiling(lo / step - 1e-9) * step
  last <- floor(hi / step + 1e-9) * step
  seq(first, last + step * .1, by = step)
}

marker_dotplot <- function(means, fractions, expression_label = "Mean expression",
                           fraction_label = "Fraction positive", output = NULL) {
  means <- .named_matrix(means, "means")
  fractions <- .named_matrix(fractions, "fractions")
  .marker_label(expression_label)
  .marker_label(fraction_label)
  if (!identical(dimnames(means), dimnames(fractions)) || !identical(dim(means), dim(fractions)))
    stop("means and fractions must have identical axes in the same order.", call. = FALSE)
  if (any(means < 0, na.rm = TRUE) || any(fractions < 0 | fractions > 1, na.rm = TRUE))
    stop("Means must be nonnegative and fractions must lie in [0,1].", call. = FALSE)
  d <- .matrix_cells(means)
  d$fraction <- as.vector(fractions)
  known <- stats::complete.cases(d)
  if (!any(known)) stop("At least one complete matrix entry is required.", call. = FALSE)
  p <- .matrix_plot(d) +
    ggplot2::geom_point(data = d[known, , drop = FALSE],
                        ggplot2::aes(size = .data$fraction, colour = .data$value), stroke = 0) +
    ggplot2::scale_size_area(name = fraction_label, limits = c(0,1), breaks = c(.25,.5,.75,1),
                             max_size = 4) +
    scale_colour_positive(name = expression_label, limits = c(0, max(c(d$value[known], .Machine$double.eps)))) +
    ggplot2::guides(size = ggplot2::guide_legend(position = "bottom", nrow = 1,
                      theme = ggplot2::theme(legend.title.position = "top")),
                    colour = ggplot2::guide_colourbar(position = "bottom", direction = "horizontal",
                      theme = ggplot2::theme(legend.title.position = "top")))
  if (any(!known)) p <- p + ggplot2::geom_point(data = d[!known, , drop = FALSE],
                          ggplot2::aes(shape = "Missing"), colour = "#555555", size = 2) +
      ggplot2::scale_shape_manual(NULL, values = c(Missing = 4))
  style_plot(p, size_mm = c(max(135, 72 + 6*ncol(means)), max(80, 42 + 5*nrow(means))), output = output)
}

marker_heatmap <- function(values, value_label, scale = c("positive", "marker"), output = NULL) {
  values <- .named_matrix(values, "values")
  .marker_label(value_label)
  scale <- match.arg(scale)
  if (all(is.na(values)) || (scale == "positive" && any(values < 0, na.rm = TRUE)))
    stop("Supply measured entries; the positive scale requires nonnegative values.", call. = FALSE)
  d <- .matrix_cells(values)
  if (scale == "positive") {
    guide <- scale_fill_positive(name = value_label, limits = c(0,max(c(values, .Machine$double.eps), na.rm = TRUE)), na.value = "#DDDDDD")
  } else {
    bound <- max(abs(values), .Machine$double.eps, na.rm = TRUE)
    guide <- scale_fill_marker(name = value_label, limits = c(-bound, bound), na.value = "#DDDDDD")
  }
  p <- .matrix_plot(d) + ggplot2::geom_tile(ggplot2::aes(fill = .data$value)) + guide
  if (anyNA(values)) p <- p + ggplot2::geom_point(data = d[is.na(d$value), , drop = FALSE],
        ggplot2::aes(shape = "Missing"), colour = "#202020", size = 2) +
      ggplot2::scale_shape_manual(NULL, values = c(Missing = 4))
  style_plot(p, size_mm = c(max(95, 55 + 6*ncol(values)), max(60, 24 + 5*nrow(values))), output = output)
}

forest_plot <- function(data, label, estimate, lower, upper, interval_label, reference = NULL,
                        log_scale = FALSE, output = NULL) {
  .marker_label(interval_label)
  if (!is.data.frame(data) || !nrow(data) || !all(c(label, estimate, lower, upper) %in% names(data)))
    stop("Supply a nonempty data frame and existing columns.", call. = FALSE)
  if (anyNA(data[[label]]) || anyDuplicated(as.character(data[[label]])))
    stop("Supply one clearly identified row per estimate.", call. = FALSE)
  for (nm in c(estimate, lower, upper))
    if (!is.numeric(data[[nm]]) || any(!is.finite(data[[nm]])))
      stop("Estimates and bounds must be finite numeric values.", call. = FALSE)
  if (any(data[[lower]] > data[[upper]])) stop("Bounds must be ordered.", call. = FALSE)
  if (!is.null(reference)) .scalar_number(reference, "reference")
  if (log_scale && any(c(data[[lower]], data[[estimate]], reference) <= 0))
    stop("A log scale requires positive values and reference.", call. = FALSE)
  d <- data.frame(id = factor(data[[label]], levels = rev(data[[label]])), value = data[[estimate]],
                  lo = data[[lower]], hi = data[[upper]])
  p <- ggplot2::ggplot(d, ggplot2::aes(.data$value, .data$id))
  if (!is.null(reference)) p <- p + ggplot2::geom_vline(xintercept = reference, linetype = 2, colour = "#777777")
  p <- p + ggplot2::geom_segment(ggplot2::aes(x = .data$lo, xend = .data$hi, yend = .data$id)) +
    ggplot2::geom_point(colour = "#1764AB", size = 2) +
    ggplot2::labs(x = paste0(estimate, " (", interval_label, ")"), y = NULL)
  if (log_scale) p <- p + ggplot2::scale_x_log10()
  style_plot(p, size_mm = c(120, max(48, 22 + 5*nrow(d))), output = output)
}

.distribution_rows <- function(data, x, y, hue = NULL) {
  .columns(data, x, y)
  if (!nrow(data) || any(!is.finite(data[[y]])) || anyNA(data[[x]]))
    stop("Supply finite measurements and identified groups.", call. = FALSE)
  category <- function(v) if (is.factor(v)) v else factor(v, levels = if (is.numeric(v)) sort(unique(v)) else unique(v))
  d <- data.frame(group = category(data[[x]]), value = data[[y]])
  if (!is.null(hue)) {
    if (!hue %in% names(data) || anyNA(data[[hue]]) || hue %in% c(x,y))
      stop("hue must identify a separate nonmissing group column.", call. = FALSE)
    d$id <- category(data[[hue]])
  } else d$id <- d$group
  d
}

.observed_shape <- function(data, x, y, hue, output, kind, palette) {
  .require_optional("ggbeeswarm")
  d <- .distribution_rows(data, x, y, hue)
  ids <- levels(d$id)
  if (is.null(palette)) palette <- stats::setNames(editorial_vivid(length(ids)), ids)
  palette <- .identity_values(palette)
  if (!all(ids %in% names(palette))) stop("Supply a color for each identity.", call. = FALSE)
  # Numeric group centers retain subgroup slots even when a combination is absent.
  d$center <- as.integer(d$group)
  if (!is.null(hue)) d$center <- d$center + .8 * ((as.integer(d$id) - .5)/length(ids) - .5)
  width <- if (is.null(hue)) .6 else .65/length(ids)
  d$slot <- interaction(d$group, d$id, drop = TRUE)
  p <- ggplot2::ggplot(d, ggplot2::aes(.data$center, .data$value, group = .data$slot))
  if (kind == "box")
    p <- p + ggplot2::geom_boxplot(ggplot2::aes(fill = .data$id), orientation = "x",
                  width = width, outlier.shape = NA, alpha = .25, linewidth = .4, show.legend = FALSE)
  if (kind == "violin")
    p <- p + ggplot2::geom_violin(ggplot2::aes(fill = .data$id), orientation = "x",
                  width = width, trim = TRUE, scale = "width", alpha = .25, linewidth = .4, show.legend = FALSE)
  p <- p + ggbeeswarm::geom_beeswarm(ggplot2::aes(colour = .data$id), method = "swarm",
               priority = "ascending", size = 1.5, show.legend = !is.null(hue))
  if (kind == "swarm")
    p <- p + ggplot2::stat_summary(fun.min = function(v) stats::quantile(v,.25),
               fun.max = function(v) stats::quantile(v,.75), geom = "linerange", orientation = "x") +
      ggplot2::stat_summary(fun = stats::median, geom = "point", shape = 21, fill = "white", orientation = "x")
  if (kind != "swarm") p <- p + scale_fill_cellstyle(palette, guide = "none")
  p <- p + scale_colour_cellstyle(palette) +
    ggplot2::scale_x_continuous(breaks = seq_along(levels(d$group)), labels = levels(d$group),
             limits = c(.5, nlevels(d$group) + .5), oob = function(x, ...) x) +
    ggplot2::scale_y_continuous(breaks = .readable_linear_breaks) +
    ggplot2::labs(x = x, y = y, colour = hue)
  style_plot(p, output = output)
}

box_distribution <- function(data, x, y, hue = NULL, palette = NULL, output = NULL)
  .observed_shape(data, x, y, hue, output, "box", palette)

violin_distribution <- function(data, x, y, hue = NULL, palette = NULL, output = NULL)
  .observed_shape(data, x, y, hue, output, "violin", palette)

grouped_swarm <- function(data, x, y, hue, palette = NULL, output = NULL)
  .observed_shape(data, x, y, hue, output, "swarm", palette)

paired_distribution <- function(data, pair, x, y, order = NULL, output = NULL) {
  d <- .distribution_rows(data, x, y)
  if (!pair %in% names(data) || anyNA(data[[pair]]) || pair %in% c(x,y))
    stop("Supply a separate, nonmissing pair identifier.", call. = FALSE)
  d$id <- data[[pair]]
  if (anyDuplicated(d[c("id","group")])) stop("Duplicate pair and condition.", call. = FALSE)
  if (!is.null(order)) {
    if (anyNA(order) || anyDuplicated(order) || !all(as.character(d$group) %in% order))
      stop("order must include each observed condition once.", call. = FALSE)
    d$group <- factor(d$group, levels = order)
  }
  if (nlevels(d$group) < 2) stop("Supply at least two conditions.", call. = FALSE)
  d$slot <- as.integer(d$group)
  # A segment requires measurements at both adjacent visits for the same ID.
  next_visit <- transform(d, slot = d$slot - 1L)
  edges <- merge(d, next_visit, by = c("id", "slot"), suffixes = c("", ".next"))
  p <- ggplot2::ggplot(d, ggplot2::aes(.data$slot, .data$value)) +
    ggplot2::geom_segment(data = edges, ggplot2::aes(xend = .data$slot + 1L, yend = .data$value.next),
                           linewidth = .35, colour = "#999999") +
    ggplot2::geom_point(colour = "#1764AB", size = 1.6) +
    ggplot2::stat_summary(ggplot2::aes(group = .data$slot), fun.min = function(v) stats::quantile(v,.25),
              fun.max = function(v) stats::quantile(v,.75), geom = "linerange", orientation = "x") +
    ggplot2::stat_summary(ggplot2::aes(group = .data$slot), fun = stats::median, geom = "point",
                          shape = 21, fill = "white", orientation = "x") +
    ggplot2::scale_x_continuous(breaks = seq_len(nlevels(d$group)), labels = levels(d$group),
                                limits = c(.5,nlevels(d$group)+.5)) +
    ggplot2::scale_y_continuous(breaks = .readable_linear_breaks) +
    ggplot2::labs(x = x, y = y)
  style_plot(p, output = output)
}

facet_plot <- function(data, x, y, row = NULL, col = NULL, kind = c("swarm","scatter"), palette = NULL, output = NULL) {
  kind <- match.arg(kind)
  if (is.null(row) && is.null(col)) stop("Supply row or col.", call. = FALSE)
  roles <- c(x,y,row,col)
  if (anyDuplicated(roles) || !all(roles %in% names(data)) || anyNA(data[roles]))
    stop("Supply distinct, fully observed measurement and design columns.", call. = FALSE)
  d <- .distribution_rows(data, x, y)
  levels_for <- function(v) if (is.factor(v)) v else factor(v, levels = if (is.numeric(v)) sort(unique(v)) else unique(v))
  d$.row <- if (is.null(row)) factor("") else levels_for(data[[row]])
  d$.col <- if (is.null(col)) factor("") else levels_for(data[[col]])
  counts <- as.data.frame(table(.row = d$.row, .col = d$.col))
  if (kind == "swarm") {
    .require_optional("ggbeeswarm")
    ids <- levels(d$group)
    if (is.null(palette)) palette <- stats::setNames(editorial_vivid(length(ids)), ids)
    p <- ggplot2::ggplot(d, ggplot2::aes(.data$group, .data$value)) +
      ggbeeswarm::geom_beeswarm(ggplot2::aes(colour = .data$group), method = "swarm",
                                 size = 1.5, show.legend = FALSE) +
      scale_colour_cellstyle(palette) +
      ggplot2::stat_summary(fun.min = function(v) stats::quantile(v,.25), fun.max = function(v) stats::quantile(v,.75),
                            geom = "linerange") +
      ggplot2::stat_summary(fun = stats::median, geom = "point", shape = 21, fill = "white") +
      ggplot2::scale_x_discrete(drop = FALSE)
  } else {
    if (!is.numeric(data[[x]]) || any(!is.finite(data[[x]]))) stop("Scatter x must be numeric and finite.", call. = FALSE)
    d$x <- data[[x]]
    p <- ggplot2::ggplot(d, ggplot2::aes(.data$x, .data$value)) +
      ggplot2::geom_point(colour = "#1764AB", size = 1.6)
  }
  p <- p + ggplot2::facet_grid(rows = if (!is.null(row)) ggplot2::vars(.row),
                               cols = if (!is.null(col)) ggplot2::vars(.col), drop = FALSE) +
    ggplot2::geom_text(data = counts, ggplot2::aes(label = paste0("n = ", .data$Freq)),
                       x = -Inf, y = Inf, hjust = -.1, vjust = 1.2, size = 2.4, inherit.aes = FALSE) +
    ggplot2::scale_y_continuous(expand = ggplot2::expansion(mult = c(.05,.18)), breaks = .readable_linear_breaks) +
    ggplot2::labs(x = x, y = y)
  style_plot(p, output = output)
}
