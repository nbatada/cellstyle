# Run from the repository root:
# Rscript examples/r_replicate_comparison.R [output.png]
# Requires cellstyle, ggplot2, and the optional ggbeeswarm package.
# Every row represents one independent biological sample in this synthetic
# example. No cells, technical replicates, or repeated measures are pooled.

library(ggplot2)
library(cellstyle)

args <- commandArgs(trailingOnly = TRUE)
output <- if (length(args)) args[[1]] else "docs/images/replicates_comparison.png"
dir.create(dirname(output), recursive = TRUE, showWarnings = FALSE)

group_order <- c("Group A", "Group B")
samples <- data.frame(
  sample_id = sprintf("sample_%02d", seq_len(16)),
  group = factor(rep(group_order, each = 8), levels = group_order),
  measurement = c(4.2, 4.2, 4.8, 5.3, 5.3, 6.1, 6.6, 7.1,
                  4.8, 5.5, 6.2, 6.2, 6.8, 7.4, 7.4, 8.1)
)
palette <- c("Group A" = "#1764AB", "Group B" = "#00A2A5")
y_limits <- c(3.5, 8.8)

# Native ggplot2 defaults: discrete x, default geom_point(), default colours,
# and the default theme. Tied measurements genuinely overlap.
before <- ggplot(samples, aes(group, measurement, colour = group)) +
  geom_point() +
  scale_x_discrete(limits = group_order, drop = FALSE) +
  coord_cartesian(ylim = y_limits) +
  labs(title = "Default ggplot2", x = NULL, y = "Measurement (a.u.)")

# The same observations: horizontal swarm displacement only, an open median,
# and a vertical IQR. No statistical tests or biological claims are made.
after <- replicate_distribution(
  samples, "group", "measurement", order = group_order,
  palette = palette, point_size = 2.6
) +
  theme_cellstyle(base_size = 11) +
  coord_cartesian(ylim = y_limits) +
  labs(title = "CellStyle replicate view", x = NULL, y = "Measurement (a.u.)")

# Base grid composition keeps the example free of layout-package dependencies.
png(output, width = 1440, height = 650, res = 180, bg = "white")
grid::grid.newpage()
grid::pushViewport(grid::viewport(layout = grid::grid.layout(
  nrow = 3, ncol = 2,
  heights = grid::unit(c(0.43, 2.78, 0.40), "in")
)))
grid::grid.text(
  "SYNTHETIC DATA  |  16 independent samples  |  Same values and y limits",
  x = 0.02, just = "left", gp = grid::gpar(fontsize = 10, col = "#444444"),
  vp = grid::viewport(layout.pos.row = 1, layout.pos.col = 1:2)
)
print(before, vp = grid::viewport(layout.pos.row = 2, layout.pos.col = 1))
print(after, vp = grid::viewport(layout.pos.row = 2, layout.pos.col = 2))
grid::grid.text(
  "Tied values overlap",
  gp = grid::gpar(fontsize = 10, col = "#444444"),
  vp = grid::viewport(layout.pos.row = 3, layout.pos.col = 1)
)
grid::grid.text(
  "Individual samples + open median + IQR",
  gp = grid::gpar(fontsize = 10, col = "#444444"),
  vp = grid::viewport(layout.pos.row = 3, layout.pos.col = 2)
)
grid::popViewport()
invisible(dev.off())
message("Saved ", output)
