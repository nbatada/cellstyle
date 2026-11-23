options(device = function(...) grDevices::pdf(NULL))
library(cellstyle); library(ggplot2)
if (all(vapply(c("digest", "jsonlite", "svglite", "xml2"), requireNamespace, logical(1), quietly = TRUE))) {
  parent <- tempfile("cellstyle-delivery-"); dir.create(parent); out <- file.path(parent, "bundle")
  p <- ggplot(data.frame(x = 1:3, y = c(1, 3, 2)), aes(x, y)) + geom_point() + theme_classic()
  r <- save_for_paper_and_slides(p, out)
  stopifnot(dir.exists(out), file.exists(file.path(out, "manuscript.pdf")), file.exists(file.path(out, "slide.svg")),
            file.exists(file.path(out, "receipt.json")), r$status %in% c("PASS", "REVIEW"),
            identical(r$schema, "cellstyle-paper-slides-1"), all.equal(r$source_size_mm, c(90, 60)),
            all.equal(r$slide$dimensions_mm, c(217.5, 145)))
  root <- xml2::xml_root(xml2::read_xml(file.path(out, "slide.svg")))
  stopifnot(grepl("mm$", xml2::xml_attr(root, "width")), grepl("mm$", xml2::xml_attr(root, "height")), !is.na(xml2::xml_attr(root, "viewBox")))
  bad <- file.path(parent, "bad")
  stopifnot(inherits(try(save_for_paper_and_slides(p, bad, slide_box_mm = c(0, 1)), silent = TRUE), "try-error"), !dir.exists(bad))
  small <- save_for_paper_and_slides(p, file.path(parent, "small"), slide_box_mm = c(40, 30))
  stopifnot(identical(small$status, "REVIEW"), small$typography$min_slide_text_pt < small$typography$required_min_slide_text_pt)
  unlink(parent, recursive = TRUE)
}
