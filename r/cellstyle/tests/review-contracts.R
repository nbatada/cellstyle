library(cellstyle)
library(ggplot2)
rejects <- function(expr) stopifnot(inherits(tryCatch(force(expr), error = identity), "error"))
d <- data.frame(group = c("A", "A", "B", "B"), value = c(1, 2, 3, 4))
if (requireNamespace("ggbeeswarm", quietly = TRUE)) {
  rejects(replicate_distribution(d, "group", "value", order = "A"))
  p <- replicate_distribution(d, "group", "value")
  rejects(add_comparisons(p, data.frame(group_a = "A", group_b = "B", p = -1)))
  rejects(add_comparisons(p, data.frame(group_a = "A", group_b = "A", p = .05)))
  rejects(add_comparisons(p, data.frame(group_a = "A", group_b = "B", p = .05), step_fraction = .01))
  stopifnot(inherits(add_comparisons(p, data.frame(group_a = "A", group_b = "B", p = .05)), "ggplot"))
}
rejects(quantitative_scatter(data.frame(x = c(1, 1), y = c(2, 3)), "x", "y", fit = TRUE))
