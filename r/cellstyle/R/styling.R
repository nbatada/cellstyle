#' Apply manuscript styling to a native ggplot
#' @param plot A ggplot, including a single Seurat ggplot.
#' @param size_mm Optional width and height in millimetres.
#' @param output Optional new PDF, SVG or PNG path.
#' @return The styled ggplot, with planned physical size in cellstyle_size_mm.
#' @export
style_plot <- function(plot, size_mm = NULL, output = NULL) {
  if (!inherits(plot, "ggplot")) stop("plot must be a ggplot.", call. = FALSE)
  if (inherits(plot, "patchwork")) stop("style_plot requires one native ggplot; style patchwork panels separately.", call. = FALSE)
  if (is.null(size_mm)) size_mm <- attr(plot, "cellstyle_size_mm")
  if (is.null(size_mm)) {
    size_mm <- c(width = 90, height = 60)
    if (!inherits(plot$facet, "FacetNull")) {
      layout <- ggplot2::ggplot_build(plot)$layout$layout
      columns <- max(layout$COL)
      rows <- max(layout$ROW)
      if (nrow(layout) > 1L)
        size_mm <- c(width = max(90, 45 * columns + 35),
                     height = max(60, 35 * rows + 25))
    }
  }
  if (!is.numeric(size_mm) || length(size_mm) != 2L || anyNA(size_mm) ||
      any(!is.finite(size_mm)) || any(size_mm <= 0))
    stop("size_mm must contain positive finite width and height in millimetres.", call. = FALSE)
  size_mm <- stats::setNames(as.numeric(size_mm), c("width", "height"))
  if (!is.null(output)) {
    if (!is.character(output) || length(output) != 1L || is.na(output) || !nzchar(output))
      stop("output must be one nonempty file path.", call. = FALSE)
    extension <- tolower(tools::file_ext(output))
    if (!extension %in% c("pdf", "svg", "png")) stop("output must end in .pdf, .svg or .png.", call. = FALSE)
    if (!dir.exists(dirname(output))) stop("output parent directory does not exist.", call. = FALSE)
    if (file.exists(output)) stop("output already exists; choose a new path.", call. = FALSE)
    if (extension == "svg") .require_optional("svglite")
  }
  styled <- plot + theme_cellstyle("manuscript")
  attr(styled, "cellstyle_size_mm") <- size_mm
  if (!is.null(output)) {
    device <- switch(extension, pdf = grDevices::pdf, svg = svglite::svglite, png = "png")
    ggplot2::ggsave(output, plot = styled, device = device,
                    width = size_mm[[1]], height = size_mm[[2]], units = "mm",
                    dpi = if (extension == "png") 300 else 72, bg = "white")
  }
  if (!is.null(output)) return(invisible(styled))
  styled
}
