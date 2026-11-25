options(device = function(...) grDevices::pdf(NULL))
library(cellstyle)
library(ggplot2)

means <- matrix(c(0, 3, 1, NA), nrow = 2, dimnames = list(c("B","A"), c("M2","M1")))
fraction <- matrix(c(0, 1, .25, .2), nrow = 2, dimnames = dimnames(means))
dot <- ggplot_build(marker_dotplot(means, fraction))
stopifnot(nrow(dot$data[[1]]) == 3L, nrow(dot$data[[2]]) == 1L,
          isTRUE(all.equal(dot$data[[1]]$size^2, 16*c(0,1,.25))))
bad <- try(marker_dotplot(means, fraction[2:1,]), silent = TRUE)
stopifnot(inherits(bad, "try-error"))
hm <- ggplot_build(marker_heatmap(means - 1, "Change", scale = "marker"))
stopifnot(nrow(hm$data[[1]]) == 4L, nrow(hm$data[[2]]) == 1L)
d <- data.frame(contrast = c("B","A"), ratio = c(2,1), lo = c(1.1,.8), hi = c(3,1.2))
p <- ggplot_build(forest_plot(d, "contrast","ratio","lo","hi","95% CI", 1, TRUE))
stopifnot(all.equal(p$data[[2]]$x, log10(d$lo)), all.equal(p$data[[2]]$xend, log10(d$hi)))
if (requireNamespace("ggbeeswarm", quietly = TRUE)) {
  d <- data.frame(site = rep(c("A","B"), each = 4), group = rep(c("U","U","V","V"), 2), score = 1:8)
  for (plot in list(box_distribution, violin_distribution, grouped_swarm)) {
    built <- ggplot_build(plot(d, "site", "score", "group"))
    points <- Filter(function(layer) "shape" %in% names(layer) && nrow(layer) == nrow(d), built$data)
    stopifnot(length(points) == 1L, identical(as.numeric(sort(points[[1]]$y)), as.numeric(d$score)))
  }
}
visits <- data.frame(person = c(1,1,1,2,2), visit = c("A","B","C","A","C"), y = 1:5)
paired <- ggplot_build(paired_distribution(visits, "person","visit","y", order = c("A","B","C")))
stopifnot(nrow(paired$data[[1]]) == 2L, nrow(paired$data[[2]]) == 5L)
facets <- data.frame(site = c("A","A","B"), visit = c("pre","post","pre"), x = 1:3, y = 4:6)
for (kind in c("scatter","swarm")) {
  if (kind == "swarm" && !requireNamespace("ggbeeswarm", quietly = TRUE)) next
  f <- ggplot_build(facet_plot(facets, "x","y",row="site",col="visit",kind=kind))
  stopifnot(nrow(f$layout$layout) == 4L, "n = 0" %in% tail(f$data,1)[[1]]$label)
}

dated_visits <- data.frame(person = c(1, 1, 1),
                           visit = as.Date(c("2026-03-01", "2026-01-01", "2026-02-01")),
                           y = c(3, 1, 2))
dated <- ggplot_build(paired_distribution(dated_visits, "person", "visit", "y"))
stopifnot(identical(dated$layout$panel_params[[1]]$x$get_labels(),
                    c("2026-01-01", "2026-02-01", "2026-03-01")),
          identical(as.numeric(dated$data[[1]]$y), c(1, 2)),
          identical(as.numeric(dated$data[[1]]$yend), c(2, 3)))
