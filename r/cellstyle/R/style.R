# Color anchors preserve the repository's visual grammar.
.editorial <- c("#1764AB", "#00A2A5", "#E6A700", "#D43F3A", "#8A4FA3")
.blues <- c("#F7FBFF", "#DEEBF7", "#C6DBEF", "#9ECAE1", "#6BAED6", "#4292C6", "#2171B5", "#08519C", "#08306B")
.marker <- c("#2166AC", "#171717", "#F4D03F")

.scalar_number <- function(x, name, lower = -Inf, upper = Inf) {
  if (!is.numeric(x) || length(x) != 1L || is.na(x) || !is.finite(x) || x < lower || x > upper)
    stop(name, " must be one finite number in [", lower, ", ", upper, "].", call. = FALSE)
}

editorial_vivid <- function(n = 5) {
  .scalar_number(n, "n", 0, 5)
  if (n != as.integer(n)) stop("n must be an integer.", call. = FALSE)
  .editorial[seq_len(n)]
}

context_color <- function() "#E8E8E8"

.identity_values <- function(values) {
  if (!is.character(values) || !length(values) || is.null(names(values)) ||
      anyNA(values) || anyNA(names(values)) || any(!nzchar(names(values))) ||
      anyDuplicated(names(values)))
    stop("values must be a nonempty named color vector with unique identity names.", call. = FALSE)
  tryCatch(grDevices::col2rgb(values), error = function(e) stop("values must contain valid colors.", call. = FALSE))
  values
}

.checked_identity_scale <- function(scale, values) {
  original_limits <- scale$limits
  scale$limits <- function(observed) {
    unknown <- setdiff(observed[!is.na(observed)], names(values))
    if (length(unknown)) stop("No CellStyle color supplied for identities: ", paste(unknown, collapse = ", "), call. = FALSE)
    if (is.function(original_limits)) original_limits(observed) else if (is.null(original_limits)) observed else original_limits
  }
  scale
}
scale_colour_cellstyle <- function(values, ...) {
  values <- .identity_values(values)
  .checked_identity_scale(ggplot2::scale_colour_manual(values = values, ...), values)
}
scale_fill_cellstyle <- function(values, ...) {
  values <- .identity_values(values)
  .checked_identity_scale(ggplot2::scale_fill_manual(values = values, ...), values)
}
scale_colour_positive <- function(...) ggplot2::scale_colour_gradientn(colours = .blues, ...)
scale_fill_positive <- function(...) ggplot2::scale_fill_gradientn(colours = .blues, ...)
scale_colour_marker <- function(...) ggplot2::scale_colour_gradientn(colours = .marker, ...)
scale_fill_marker <- function(...) ggplot2::scale_fill_gradientn(colours = .marker, ...)

theme_cellstyle <- function(mode = "review", base_size = NULL, base_family = "sans") {
  mode <- match.arg(mode, c("explore", "review", "manuscript", "presentation"))
  if (is.null(base_size)) base_size <- c(explore = 9, review = 9, manuscript = 8, presentation = 12)[[mode]]
  .scalar_number(base_size, "base_size", .Machine$double.eps)
  if (!is.character(base_family) || length(base_family) != 1L || is.na(base_family))
    stop("base_family must be one font family string.", call. = FALSE)
  ggplot2::theme_classic(base_size = base_size, base_family = base_family) +
    ggplot2::theme(panel.grid = ggplot2::element_blank(),
      plot.background = ggplot2::element_rect(fill = "white", colour = NA),
      panel.background = ggplot2::element_rect(fill = "white", colour = NA),
      axis.line = ggplot2::element_line(colour = "#202020", linewidth = .35),
      axis.ticks = ggplot2::element_line(colour = "#202020", linewidth = .35),
      text = ggplot2::element_text(colour = "#202020"),
      legend.key = ggplot2::element_rect(fill = "white", colour = NA),
      strip.background = ggplot2::element_rect(fill = "#F5F5F5", colour = NA))
}
