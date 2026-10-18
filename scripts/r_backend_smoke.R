#!/usr/bin/env Rscript
# Synthetic render smoke: a software composition check, not CSD acceptance.
library(cellstyle)
library(ggplot2)
args <- commandArgs(trailingOnly = TRUE)
output <- if (length(args)) args[[1]] else file.path("dist", "r", as.character(packageVersion("cellstyle")), "smoke")
dir.create(output, recursive = TRUE, showWarnings = FALSE)
# Beeswarm compilation can request device geometry before final rendering.
# Use a null device so compilation never creates an incidental Rplots.pdf.
grDevices::pdf(NULL)
set.seed(20260923)
identities <- c("T cell" = "#1764AB", "B cell" = "#00A2A5", "Myeloid" = "#E6A700")
d <- data.frame(identity = rep(names(identities), each = 16),
  x = rnorm(48), y = rnorm(48), panel = rep(c("Sample 1", "Sample 2"), 24))
p1 <- ggplot(d, aes(x, y, colour = identity)) + geom_point(size = 1.7, alpha = .7) +
  scale_colour_cellstyle(identities) + theme_cellstyle(base_size = 10) + facet_wrap(~panel) +
  labs(title = "Native ggplot + named identities + facets", x = "Synthetic coordinate 1", y = "Synthetic coordinate 2", colour = NULL) +
  theme(legend.position = "bottom")
replicates <- data.frame(group = rep(c("Control", "Treated"), each = 12),
  value = c(rnorm(12, 4, .75), rnorm(12, 5.4, .9)))
p2 <- replicate_distribution(replicates, "group", "value") +
  labs(title = "Replicates + supplied result", x = NULL, y = "Synthetic response")
p2 <- add_comparisons(p2, data.frame(group_a = "Control", group_b = "Treated",
  p_adjusted = .032), y_start = max(replicates$value) + .35)
scatter <- data.frame(x = seq(.2, 4, length.out = 40))
scatter$y <- .5 + .7 * scatter$x + rnorm(40, sd = .45)
p3 <- quantitative_scatter(scatter, "x", "y") +
  labs(title = "Quantitative observations", x = "Synthetic input", y = "Synthetic response")
heat <- expand.grid(identity = names(identities), feature = paste("Feature", 1:6))
heat$magnitude <- sample(seq(0, 10, length.out = 18))
p4 <- ggplot(heat, aes(identity, feature, fill = magnitude)) + geom_tile(colour = "white", linewidth = .4) +
  scale_fill_positive(limits = c(0, 10)) + theme_cellstyle(base_size = 10) +
  labs(title = "Positive magnitude: sequential blue", x = NULL, y = NULL, fill = "Magnitude")
plots <- list(p1, p2, p3, p4)
invisible(lapply(plots, ggplot_build))
grDevices::dev.off()
draw <- function() {
  grid::grid.newpage()
  grid::pushViewport(grid::viewport(layout = grid::grid.layout(3, 2,
    heights = grid::unit(c(.55, 4, 4), "null"))))
  grid::grid.text("SYNTHETIC DATA • R backend render is provisional; not CSD acceptance",
    vp = grid::viewport(layout.pos.row = 1, layout.pos.col = 1:2),
    gp = grid::gpar(fontsize = 12, col = "#444444"))
  for (i in seq_along(plots)) print(plots[[i]], newpage = FALSE,
    vp = grid::viewport(layout.pos.row = 2 + (i - 1) %/% 2, layout.pos.col = 1 + (i - 1) %% 2))
  grid::popViewport()
}
grDevices::png(file.path(output, "synthetic-contact-sheet.png"), width = 1800, height = 1400, res = 150, bg = "white")
draw()
grDevices::dev.off()
grDevices::pdf(file.path(output, "synthetic-contact-sheet.pdf"), width = 12, height = 9.33, useDingbats = FALSE)
draw()
grDevices::dev.off()
writeLines(c("Synthetic data only. Software render check; no scientific or CSD acceptance.", capture.output(sessionInfo())), file.path(output, "session-info.txt"))
cat("Rendered", normalizePath(output), "\n")
