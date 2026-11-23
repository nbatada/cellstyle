# Run: Rscript examples/adoption_r.R OUTPUT_DIRECTORY
# All coordinates, expression summaries, and donor measurements below are synthetic.
main <- function(args = commandArgs(trailingOnly = TRUE)) {
  if (length(args) != 1L) stop("Pass one output directory.")
  for (package in c("cellstyle", "ggplot2", "patchwork", "ggbeeswarm")) {
    if (!requireNamespace(package, quietly = TRUE)) stop("Missing package: ", package)
  }
  out <- args[[1]]
  dir.create(out, recursive = TRUE, showWarnings = FALSE)
  set.seed(42)
  identities <- c("A", "B", "C")
  colors <- stats::setNames(cellstyle::editorial_vivid(3), identities)
  cells <- data.frame(identity = rep(identities, each = 60),
                      x = c(rnorm(60, -2), rnorm(60, 2), rnorm(60, 0)),
                      y = c(rnorm(60, 0), rnorm(60, 0), rnorm(60, 2)))
  donors <- expand.grid(donor = sprintf("D%02d", 1:8), identity = identities)
  donors$value <- round(c(rnorm(8, 3), rnorm(8, 5), rnorm(8, 4)), 2)
  paired <- data.frame(donor = rep(sprintf("D%02d", 1:8), each = 2),
                       condition = rep(c("Before", "After"), 8),
                       value = as.vector(rbind(round(rnorm(8, 3), 2), round(rnorm(8, 4), 2))))
  dots <- expand.grid(identity = identities, marker = c("M1", "M2", "M3"))
  dots$mean <- c(1.1, .5, .2, .4, 1.3, .6, .2, .5, 1.2)
  dots$fraction <- c(.75, .4, .2, .3, .8, .5, .2, .4, .7)
  utils::write.csv(cells, file.path(out, "synthetic_cells.csv"), row.names = FALSE)
  utils::write.csv(donors, file.path(out, "synthetic_donors.csv"), row.names = FALSE)
  utils::write.csv(paired, file.path(out, "synthetic_paired.csv"), row.names = FALSE)
  utils::write.csv(dots, file.path(out, "synthetic_dot_summaries.csv"), row.names = FALSE)

  gg <- ggplot2::ggplot
  aes <- ggplot2::aes
  embedding <- gg(cells, aes(x, y, colour = identity)) + ggplot2::geom_point(size = .9) +
    cellstyle::scale_colour_cellstyle(colors) + cellstyle::theme_cellstyle() +
    ggplot2::labs(title = "Synthetic coordinates (not UMAP)", x = "Simulated X", y = "Simulated Y")
  dot <- gg(dots, aes(marker, identity, size = fraction, colour = mean)) +
    ggplot2::geom_point() + cellstyle::scale_colour_positive() +
    ggplot2::scale_size(range = c(1, 6)) + cellstyle::theme_cellstyle() +
    ggplot2::labs(title = "Synthetic precomputed marker summaries", size = "Fraction", colour = "Mean")
  distribution <- cellstyle::replicate_distribution(donors, "identity", "value", palette = colors) +
    ggplot2::labs(title = "Synthetic donor distribution")
  paired_plot <- gg(paired, aes(condition, value, group = donor)) +
    ggplot2::geom_line(colour = "#999999") +
    ggplot2::geom_point(aes(colour = condition), size = 2) +
    cellstyle::scale_colour_cellstyle(c(Before = colors[["A"]], After = colors[["B"]])) +
    cellstyle::theme_cellstyle() + ggplot2::labs(title = "Synthetic paired donors", x = NULL)
  panels <- list(embedding = embedding, dot_plot = dot,
                 donor_distribution = distribution, paired_donors = paired_plot)
  for (name in names(panels)) {
    ggplot2::ggsave(file.path(out, paste0(name, ".png")), panels[[name]],
                    width = 5, height = 4, dpi = 150)
  }
  figure <- patchwork::wrap_plots(panels, ncol = 2)
  ggplot2::ggsave(file.path(out, "four_panel_figure.png"), figure,
                  width = 10, height = 8, dpi = 150)
}

if (sys.nframe() == 0L) main()
