#' Save a native ggplot for a manuscript and PowerPoint placement
#'
#' @param plot A native ggplot object.
#' @param directory A new output directory; its parent must already exist.
#' @param slide_box_mm Maximum PowerPoint placement box in millimetres.
#' @param min_slide_text_pt Minimum text size at slide placement in points.
#' @return Invisibly, the delivery receipt also written as `receipt.json`.
#' @export
save_for_paper_and_slides <- function(plot, directory, slide_box_mm = c(250, 145), min_slide_text_pt = 16) {
  if (!inherits(plot, "ggplot")) stop("plot must be a ggplot.", call. = FALSE)
  valid_size <- function(x, name) {
    if (!is.numeric(x) || length(x) != 2L || anyNA(x) || any(!is.finite(x)) || any(x <= 0))
      stop(name, " must contain two positive finite millimetre values.", call. = FALSE)
    as.numeric(x)
  }
  if (!is.character(directory) || length(directory) != 1L || is.na(directory) || !nzchar(directory) ||
      file.exists(directory) || !dir.exists(dirname(directory)))
    stop("directory must be a new path with an existing parent directory.", call. = FALSE)
  slide_box_mm <- valid_size(slide_box_mm, "slide_box_mm")
  if (!is.numeric(min_slide_text_pt) || length(min_slide_text_pt) != 1L || is.na(min_slide_text_pt) ||
      !is.finite(min_slide_text_pt) || min_slide_text_pt <= 0)
    stop("min_slide_text_pt must be one positive finite number.", call. = FALSE)
  for (pkg in c("digest", "jsonlite", "svglite", "xml2"))
    if (!requireNamespace(pkg, quietly = TRUE)) stop("Delivery export requires optional package: ", pkg, call. = FALSE)

  source_size <- attr(plot, "cellstyle_size_mm")
  if (is.null(source_size)) source_size <- c(90, 60)
  source_size <- valid_size(source_size, "cellstyle_size_mm")
  scale <- min(slide_box_mm[[1]] / source_size[[1]], slide_box_mm[[2]] / source_size[[2]])
  slide_size <- source_size * scale
  temporary <- tempfile("cellstyle-delivery-", tmpdir = dirname(normalizePath(directory, mustWork = FALSE)))
  dir.create(temporary)
  committed <- FALSE
  on.exit(if (!committed && dir.exists(temporary)) unlink(temporary, recursive = TRUE), add = TRUE)
  if (!capabilities("cairo")) stop("Paper-and-slide export requires a Cairo PDF device to preserve scientific Unicode text.", call. = FALSE)
  manuscript <- file.path(temporary, "manuscript.pdf")
  slide <- file.path(temporary, "slide.svg")
  # Resolve stochastic positions and statistics once so both deliverables show the same drawing.
  frozen_plot <- ggplot2::ggplotGrob(plot)
  render_warnings <- character()
  withCallingHandlers({
    ggplot2::ggsave(manuscript, frozen_plot, device = grDevices::cairo_pdf,
                    width = source_size[[1]], height = source_size[[2]], units = "mm", bg = "white")
    ggplot2::ggsave(slide, frozen_plot, device = svglite::svglite,
                    width = source_size[[1]], height = source_size[[2]], units = "mm", bg = "white")
  }, warning = function(w) render_warnings <<- c(render_warnings, conditionMessage(w)))
  doc <- xml2::read_xml(slide); root <- xml2::xml_root(doc); view_box <- xml2::xml_attr(root, "viewBox")
  numbers <- suppressWarnings(as.numeric(strsplit(trimws(view_box), "[[:space:]]+")[[1]]))
  if (length(numbers) != 4L || any(!is.finite(numbers)) || any(numbers[3:4] <= 0)) stop("svglite did not create a usable SVG viewBox.", call. = FALSE)
  xml2::xml_set_attr(root, "width", sprintf("%.3fmm", slide_size[[1]]))
  xml2::xml_set_attr(root, "height", sprintf("%.3fmm", slide_size[[2]]))
  xml2::write_xml(doc, slide)
  text <- xml2::xml_find_all(doc, "//*[local-name()='text']")
  px <- suppressWarnings(as.numeric(sub(".*font-size: ([0-9.]+)px.*", "\\1", xml2::xml_attr(text, "style"))))
  placed_pt <- px * (slide_size[[1]] / 25.4 * 72) / numbers[3]
  observed_min_pt <- if (length(placed_pt) && any(is.finite(placed_pt))) min(placed_pt, na.rm = TRUE) else NA_real_
  pdfinfo <- Sys.which("pdfinfo")
  paper_size <- c(NA_real_, NA_real_)
  if (nzchar(pdfinfo)) {
    lines <- system2(pdfinfo, shQuote(manuscript), stdout = TRUE, stderr = TRUE)
    page_size <- grep("^Page size:", lines, value = TRUE)
    values <- if (length(page_size) == 1L) regmatches(page_size, gregexpr("[0-9]+(?:\\.[0-9]+)?", page_size, perl = TRUE))[[1]] else character()
    if (length(values) >= 2L) paper_size <- as.numeric(values[1:2]) * 25.4 / 72
  }
  exact_paper_size <- all(is.finite(paper_size)) && all(abs(paper_size - source_size) <= .02)
  status <- if (length(text) && is.finite(observed_min_pt) && observed_min_pt + 1e-8 >= min_slide_text_pt &&
                exact_paper_size && !length(render_warnings)) "PASS" else "REVIEW"
  hash <- function(path) digest::digest(file = path, algo = "sha256")
  receipt <- list(
    schema = "cellstyle-paper-slides-1", status = status,
    manuscript = list(path = "manuscript.pdf", requested_dimensions_mm = unname(source_size),
                      dimensions_mm = unname(paper_size), sha256 = hash(manuscript)),
    slide = list(path = "slide.svg", dimensions_mm = unname(slide_size), viewBox = view_box,
                 svg_integrity = "explicit mm width/height with svglite viewBox; geometry is proportionally fitted", sha256 = hash(slide)),
    slide_box_mm = unname(slide_box_mm), source_size_mm = unname(source_size),
    typography = list(min_slide_text_pt = observed_min_pt, required_min_slide_text_pt = min_slide_text_pt,
                      conversion = "SVG font-size in viewBox user units multiplied by placed physical width in pt / viewBox width"),
    sha256 = list("manuscript.pdf" = hash(manuscript), "slide.svg" = hash(slide)),
    limitations = c(if (!nzchar(pdfinfo)) "PDF dimensions were not measured because pdfinfo is unavailable." else NULL,
                    if (!exact_paper_size && nzchar(pdfinfo)) "Cairo PDF page dimensions differ from the requested manuscript size." else NULL,
                    if (length(render_warnings)) paste0("Rendering warning: ", unique(render_warnings)) else NULL,
                    "PowerPoint import, font substitution and final text appearance require visual review.",
                    "Explicit-size geom text can require review if it bypasses theme typography."))
  jsonlite::write_json(receipt, file.path(temporary, "receipt.json"), auto_unbox = TRUE, pretty = TRUE, null = "null")
  if (file.exists(directory) || !file.rename(temporary, directory)) stop("Could not atomically create delivery directory.", call. = FALSE)
  committed <- TRUE
  invisible(receipt)
}
