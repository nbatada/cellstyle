library(cellstyle)
library(ggplot2)

fixture <- tempfile(fileext = ".tsv")
writeLines(c("entity\tparent\tlevel\trole\tcolor",
             "001\t\t\tidentity\t#1764AB",
             "NA\t\t\tidentity\t#00A2A5",
             "null\t\t\tidentity\t#E6A700"), fixture)
colors <- read_identity_colors(fixture)
stopifnot(identical(colors, c("001" = "#1764AB", "NA" = "#00A2A5", "null" = "#E6A700")))
d <- data.frame(x = 1:3, y = 1:3, entity = names(colors))
p <- ggplot(d, aes(x, y, colour = entity)) + geom_point() + scale_colour_cellstyle(colors)
stopifnot(identical(ggplot_build(p)$data[[1]]$colour, unname(colors[d$entity])))

bad <- function(rows) {
  writeLines(c("entity\tparent\tlevel\trole\tcolor", rows), fixture)
  stopifnot(inherits(try(read_identity_colors(fixture), silent = TRUE), "try-error"))
}
bad(c("A\t\t\tidentity\t#1764AB", "A\t\t\tidentity\t#00A2A5"))
bad("\t\t\tidentity\t#1764AB")
bad("A\t\t\tidentity\tno-such-color")
unlink(fixture)
