add_comparisons <- function(plot, comparisons, y_start = NULL, step_fraction = .08, bracket_height_fraction = .025) {
  if (!inherits(plot, "ggplot")) stop("plot must be a ggplot object.", call. = FALSE)
  if (!is.data.frame(comparisons) || !all(c("group_a", "group_b") %in% names(comparisons)))
    stop("comparisons must be a data frame with group_a and group_b columns.", call. = FALSE)
  .scalar_number(step_fraction, "step_fraction", .Machine$double.eps)
  .scalar_number(bracket_height_fraction, "bracket_height_fraction", 0)
  if (step_fraction <= bracket_height_fraction) stop("step_fraction must exceed bracket_height_fraction to separate brackets.", call. = FALSE)
  if (!is.null(y_start)) .scalar_number(y_start, "y_start")
  if (!nrow(comparisons)) return(plot)
  if (!inherits(plot$facet, "FacetNull") || !inherits(plot$coordinates, "CoordCartesian") || inherits(plot$coordinates, "CoordFlip"))
    stop("Comparisons support only unfaceted, unflipped Cartesian plots.", call. = FALSE)
  built <- ggplot2::ggplot_build(plot)
  xs <- built$layout$panel_scales_x[[1L]]
  ys <- built$layout$panel_scales_y[[1L]]
  if (!xs$is_discrete() || ys$is_discrete() || ys$get_transformation()$name != "identity")
    stop("Comparisons require discrete x and untransformed continuous y.", call. = FALSE)
  if (!is.null(ys$limits) || !is.null(plot$coordinates$limits$y))
    stop("Remove fixed y limits before adding comparisons so brackets can expand the range.", call. = FALSE)
  levels <- as.character(xs$get_limits())
  a <- as.character(comparisons$group_a)
  b <- as.character(comparisons$group_b)
  if (anyNA(a) || anyNA(b) || !all(a %in% levels) || !all(b %in% levels) || any(a == b))
    stop("Each comparison must identify two distinct displayed x groups.", call. = FALSE)
  for (field in intersect(c("p", "p_adjusted"), names(comparisons))) {
    values <- comparisons[[field]]
    if (!is.numeric(values) || any(!is.na(values) & (!is.finite(values) | values < 0 | values > 1)))
      stop(field, " must contain probabilities in [0, 1] or NA.", call. = FALSE)
  }
  if ("label" %in% names(comparisons) && !is.character(comparisons$label)) stop("label must be a character column (NA uses the supplied P value).", call. = FALSE)
  labels <- vapply(seq_len(nrow(comparisons)), function(i) {
    if ("label" %in% names(comparisons) && !is.na(comparisons$label[i])) return(comparisons$label[i])
    adjusted <- "p_adjusted" %in% names(comparisons) && !is.na(comparisons$p_adjusted[i])
    p <- if (adjusted) comparisons$p_adjusted[i] else if ("p" %in% names(comparisons)) comparisons$p[i] else NA_real_
    if (is.na(p)) stop("Each comparison needs a label or a supplied P value.", call. = FALSE)
    label <- if (p < .001) "P < 0.001" else if (p < .01) sprintf("P = %.3f", p) else sprintf("P = %.2f", p)
    if (adjusted) paste0(label, " adj.") else label
  }, character(1))
  yrange <- built$layout$panel_params[[1L]]$y.range
  span <- diff(yrange)
  if (length(span) != 1L || !is.finite(span) || span <= 0) stop("plot must have a finite y range.", call. = FALSE)
  if (is.null(y_start)) y_start <- yrange[2L] + .05 * span
  y <- y_start + (seq_len(nrow(comparisons)) - 1L) * step_fraction * span
  height <- bracket_height_fraction * span
  x1 <- as.numeric(xs$map(a))
  x2 <- as.numeric(xs$map(b))
  segments <- rbind(data.frame(x = x1, xend = x1, y = y, yend = y + height),
    data.frame(x = x1, xend = x2, y = y + height, yend = y + height),
    data.frame(x = x2, xend = x2, y = y + height, yend = y))
  text <- data.frame(x = (x1 + x2) / 2, y = y + height + .012 * span, label = labels)
  plot + ggplot2::geom_segment(data = segments, ggplot2::aes(x = .data$x, xend = .data$xend, y = .data$y, yend = .data$yend), inherit.aes = FALSE, colour = "#202020", linewidth = .3) +
    ggplot2::geom_text(data = text, ggplot2::aes(x = .data$x, y = .data$y, label = .data$label), inherit.aes = FALSE, colour = "#202020", size = 2.5, vjust = 0, parse = FALSE) +
    ggplot2::expand_limits(y = max(text$y) + .06 * span)
}
