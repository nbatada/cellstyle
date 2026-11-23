# Run with: Rscript examples/first_plot.R [output.pdf]
main <- function(args = commandArgs(trailingOnly = TRUE)) {
  suppressPackageStartupMessages(library(cellstyle))
  if (length(args) > 1L) stop("Give at most one PDF output path.", call. = FALSE)
  output <- if (length(args)) args[[1L]] else "first-plot.pdf"
  if (!grepl("[.]pdf$", output, ignore.case = TRUE)) stop("Output must be a PDF path.", call. = FALSE)
  if (file.exists(output)) stop("Output already exists; choose a new path.", call. = FALSE)

  # Synthetic scores for a first-use example; they are not experimental data.
  scores <- data.frame(
    `Before score (a.u.)` = c(1.0, 1.8, 2.6, 3.2, 4.1, 5.0),
    `After score (a.u.)` = c(1.3, 2.1, 2.4, 3.8, 4.0, 5.4),
    check.names = FALSE
  )
  p <- quantitative_scatter(scores, "Before score (a.u.)", "After score (a.u.)", output = output)
  cat(normalizePath(output), "\n")
  invisible(p)
}

if (sys.nframe() == 0L) main()
