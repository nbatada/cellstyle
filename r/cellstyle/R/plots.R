.require_optional <- function(package) {
  if (!requireNamespace(package, quietly = TRUE))
    stop("This helper requires the optional package '", package, "'. Install it with install.packages('", package, "').", call. = FALSE)
}
.columns <- function(data, x, y) {
  if (!is.data.frame(data)) stop("data must be a data frame.", call. = FALSE)
  for (column in list(x, y)) {
    if (!is.character(column) || length(column) != 1L || is.na(column) || !column %in% names(data))
      stop("x and y must name existing data-frame columns.", call. = FALSE)
  }
  if (!is.numeric(data[[y]]) || any(!is.finite(data[[y]]) & !is.na(data[[y]])))
    stop("y must be numeric, with finite values or NA.", call. = FALSE)
}

replicate_distribution <- function(data, x, y, order = NULL, palette = NULL, alpha = .60, point_size = 1.5) {
  .require_optional("ggbeeswarm")
  .columns(data, x, y)
  .scalar_number(alpha, "alpha", 0, 1)
  .scalar_number(point_size, "point_size", .Machine$double.eps)
  groups <- data[[x]]
  if (!is.atomic(groups) || anyNA(groups)) stop("x must contain nonmissing categorical identities.", call. = FALSE)
  if (is.null(order)) {
    order <- if (is.factor(groups)) levels(groups) else if (is.numeric(groups)) sort(unique(groups)) else unique(groups)
  }
  order <- as.character(order)
  if (!length(order) || anyNA(order) || anyDuplicated(order) || !all(as.character(groups) %in% order))
    stop("order must contain every observed identity exactly once; additional empty levels are allowed.", call. = FALSE)
  if (is.null(palette)) palette <- stats::setNames(editorial_vivid(length(order)), order)
  palette <- .identity_values(palette)
  if (!all(order %in% names(palette))) stop("palette must name every displayed identity.", call. = FALSE)
  d <- data.frame(.cellstyle_group = factor(as.character(groups), levels = order), .cellstyle_value = data[[y]])
  summary <- do.call(rbind, lapply(order, function(group) {
    v <- d$.cellstyle_value[d$.cellstyle_group == group]
    v <- v[!is.na(v)]
    if (!length(v)) return(NULL)
    q <- stats::quantile(v, c(.25, .5, .75), type = 7, names = FALSE)
    data.frame(.cellstyle_group = group, q1 = q[1], median = q[2], q3 = q[3])
  }))
  if (is.null(summary)) summary <- data.frame(.cellstyle_group = character(), q1 = numeric(), median = numeric(), q3 = numeric())
  summary$.cellstyle_group <- factor(summary$.cellstyle_group, levels = order)
  ggplot2::ggplot(d, ggplot2::aes(x = .data$.cellstyle_group, y = .data$.cellstyle_value)) +
    ggbeeswarm::geom_beeswarm(ggplot2::aes(colour = .data$.cellstyle_group), method = "swarm", alpha = alpha, size = point_size, show.legend = FALSE) +
    ggplot2::geom_linerange(data = summary, ggplot2::aes(x = .data$.cellstyle_group, ymin = .data$q1, ymax = .data$q3), inherit.aes = FALSE, colour = "#202020", linewidth = .55) +
    ggplot2::geom_point(data = summary, ggplot2::aes(x = .data$.cellstyle_group, y = .data$median), inherit.aes = FALSE, shape = 21, fill = "white", colour = "#202020", size = 2, stroke = .4) +
    scale_colour_cellstyle(palette) + ggplot2::scale_x_discrete(limits = order, drop = FALSE) +
    ggplot2::labs(x = x, y = y) + theme_cellstyle()
}

quantitative_scatter <- function(data, x, y, color = "#1764AB", alpha = .42, point_size = 1.5, fit = FALSE) {
  .columns(data, x, y)
  if (!is.numeric(data[[x]]) || any(!is.finite(data[[x]]) & !is.na(data[[x]]))) stop("x must be numeric, with finite values or NA.", call. = FALSE)
  .scalar_number(alpha, "alpha", 0, 1)
  .scalar_number(point_size, "point_size", .Machine$double.eps)
  if (!is.logical(fit) || length(fit) != 1L || is.na(fit)) stop("fit must be TRUE or FALSE.", call. = FALSE)
  p <- ggplot2::ggplot(data, ggplot2::aes(x = .data[[x]], y = .data[[y]])) + ggplot2::geom_point(colour = color, alpha = alpha, size = point_size) + theme_cellstyle()
  if (fit) {
    usable <- stats::complete.cases(data[c(x, y)])
    if (sum(usable) < 2L || length(unique(data[[x]][usable])) < 2L) stop("A linear fit requires at least two distinct complete x values.", call. = FALSE)
    p <- p + ggplot2::geom_smooth(method = "lm", formula = y ~ x, se = FALSE, colour = "#222222", linewidth = .5)
  }
  p
}

repel_labels <- function(data, mapping, ..., seed = 0L, max.overlaps = Inf) {
  .require_optional("ggrepel")
  ggrepel::geom_text_repel(data = data, mapping = mapping, ..., seed = seed, max.overlaps = max.overlaps, inherit.aes = FALSE)
}
