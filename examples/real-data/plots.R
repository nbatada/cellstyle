# Run from the repository root with Rscript examples/real-data/plots.R OUTPUT.
main <- function() {
  args <- commandArgs(trailingOnly = TRUE)
  if (length(args) != 1L) stop("Supply a new output directory.", call. = FALSE)
  output <- args[[1L]]
  inputs <- "examples/real-data/inputs"

  # Girth is the recorded diameter in inches. Each point is one tree.
  DF_trees <- datasets::trees
  names(DF_trees)[match(c("Girth", "Volume"), names(DF_trees))] <-
    c("Diameter (in)", "Timber volume (ft³)")

  # Match each participant's two measurements by ID.
  DF_sleep <- datasets::sleep
  conditions <- c("Drug 1", "Drug 2")
  names(DF_sleep)[match(c("group", "extra"), names(DF_sleep))] <-
    c("Treatment", "Extra sleep (h)")
  DF_sleep$Treatment <- factor(DF_sleep$Treatment, levels = 1:2, labels = conditions)

  DF_iris <- datasets::iris
  names(DF_iris)[names(DF_iris) == "Petal.Length"] <- "Petal length (cm)"

  # Keep the same reference annotation and gene order in both matrices.
  means <- as.matrix(read.csv(file.path(inputs, "mean_log1p_expression.csv"),
                             row.names = 1, check.names = FALSE))
  fractions <- as.matrix(read.csv(file.path(inputs, "fraction_positive.csv"),
                                 row.names = 1, check.names = FALSE))
  colour_label <- "Mean log1p expression"
  size_label <- "Fraction of cells with expression > 0"

  if (!dir.create(output, recursive = TRUE, showWarnings = FALSE)) {
    stop("Could not create a new output directory: ", output, call. = FALSE)
  }
  # Render headlessly while writing each figure to its own PDF.
  grDevices::pdf(NULL)
  on.exit(grDevices::dev.off(), add = TRUE)

  cellstyle::quantitative_scatter(
    DF_trees, "Diameter (in)", "Timber volume (ft³)",
    output = file.path(output, "trees_scatter.pdf")
  )
  cellstyle::paired_distribution(
    DF_sleep, "ID", "Treatment", "Extra sleep (h)", order = conditions,
    output = file.path(output, "sleep_paired.pdf")
  )
  cellstyle::box_distribution(
    DF_iris, "Species", "Petal length (cm)", output = file.path(output, "iris_box.pdf")
  )
  cellstyle::marker_dotplot(
    means, fractions, colour_label, size_label, output = file.path(output, "pbmc3k_dot.pdf")
  )
  cellstyle::marker_heatmap(
    means, colour_label, output = file.path(output, "pbmc3k_heatmap.pdf")
  )
  cat("Saved five PDFs in", normalizePath(output), "\n")
}

main()
