library(cellstyle)
library(ggplot2)

error_matches <- function(expr, pattern) {
  message <- tryCatch({ force(expr); NULL }, error = conditionMessage)
  stopifnot(!is.null(message), grepl(pattern, message))
}

d <- data.frame(x = 1:4, y = c(2, 4, 3, 5), group = c("A", "B", "A", "B"))
s <- quantitative_scatter(d, "x", "y")
stopifnot(identical(attr(s, "cellstyle_size_mm"), c(width = 90, height = 48)),
          identical(s$labels$x, "x"), identical(s$labels$y, "y"),
          ggplot2::calc_element("axis.text.x", s$theme)$size == 7)
if (requireNamespace("ggbeeswarm", quietly = TRUE)) {
  b <- replicate_distribution(d, "group", "y")
  stopifnot(identical(attr(b, "cellstyle_size_mm"), c(width = 90, height = 60)))
}

native <- ggplot(d, aes(x, y, colour = group)) + geom_point(size = 3) +
  scale_colour_manual(values = c(A = "red", B = "blue")) +
  coord_fixed() + labs(title = "Observed")
old_theme <- theme_get()
styled <- style_plot(native, size_mm = c(100, 70))
stopifnot(inherits(styled, "ggplot"), identical(theme_get(), old_theme),
          identical(styled$data, native$data), identical(styled$mapping, native$mapping),
          identical(styled$labels$title, "Observed"),
          identical(styled$layers[[1]]$aes_params$size, 3),
          identical(styled$coordinates$ratio, native$coordinates$ratio),
          identical(unname(styled$scales$get_scales("colour")$palette(2)), c("red", "blue")),
          identical(attr(styled, "cellstyle_size_mm"), c(width = 100, height = 70)),
          ggplot2::calc_element("axis.text.x", styled$theme)$size == 7)
stopifnot((styled + theme(axis.text.x = element_text(size = 11)))$theme$axis.text.x$size == 11)

composite <- native
class(composite) <- c("patchwork", class(composite))
error_matches(style_plot(composite), "one native ggplot")
faceted <- style_plot(native + facet_wrap(~group))
stopifnot(identical(attr(faceted, "cellstyle_size_mm"), c(width = 125, height = 60)))
faceted_override <- style_plot(native + facet_wrap(~group), size_mm = c(101, 66))
stopifnot(identical(attr(faceted_override, "cellstyle_size_mm"), c(width = 101, height = 66)))

output <- tempfile(fileext = ".png")
device_before <- grDevices::dev.cur()
saved <- withVisible(style_plot(ggplot(d, aes(group, y)) + geom_boxplot(), output = output))
stopifnot(!saved$visible, inherits(saved$value, "ggplot"),
          identical(grDevices::dev.cur(), device_before))
stopifnot(file.exists(output), file.info(output)$size > 0)
error_matches(style_plot(native, output = output), "exists")
unlink(output)
cat("PASS: one-shot styling, provenance and explicit PNG export\n")
