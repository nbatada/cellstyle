options(device = function(...) grDevices::pdf(NULL))
library(cellstyle); library(ggplot2)
if (all(vapply(c("digest", "jsonlite", "svglite", "xml2"), requireNamespace, logical(1), quietly = TRUE))) {
  parent <- tempfile("cellstyle-delivery-"); dir.create(parent); out <- file.path(parent, "bundle")
  p <- ggplot(data.frame(x = 1:3, y = c(1, 3, 2)), aes(x, y)) + geom_point() +
    labs(title = "γδ T cells", y = "Δ expression") + theme_classic()
  r <- save_for_paper_and_slides(p, out)
  stopifnot(dir.exists(out), file.exists(file.path(out, "manuscript.pdf")), file.exists(file.path(out, "slide.svg")),
            file.exists(file.path(out, "receipt.json")), r$status %in% c("PASS", "REVIEW"),
            identical(r$schema, "cellstyle-paper-slides-1"), all.equal(r$source_size_mm, c(90, 60)),
            all.equal(r$slide$dimensions_mm, c(217.5, 145)))
  root <- xml2::xml_root(xml2::read_xml(file.path(out, "slide.svg")))
  stopifnot(grepl("mm$", xml2::xml_attr(root, "width")), grepl("mm$", xml2::xml_attr(root, "height")), !is.na(xml2::xml_attr(root, "viewBox")))
  slide_text <- xml2::xml_text(xml2::xml_find_all(xml2::read_xml(file.path(out, "slide.svg")), "//*[local-name()='text']"))
  stopifnot(all(c("γδ T cells", "Δ expression") %in% slide_text))
  if (nzchar(Sys.which("pdftotext"))) {
    extracted <- system2(Sys.which("pdftotext"), c(shQuote(file.path(out, "manuscript.pdf")), "-"), stdout = TRUE)
    stopifnot(all(c("γδ T cells", "Δ expression") %in% extracted))
  }
  if (nzchar(Sys.which("gs"))) {
    extracted <- system2(Sys.which("gs"), c("-q", "-dBATCH", "-dNOPAUSE", "-sDEVICE=txtwrite", "-sOutputFile=-",
                                              shQuote(file.path(out, "manuscript.pdf"))), stdout = TRUE)
    stopifnot(any(grepl("γδ T cells", extracted, fixed = TRUE)))
  }
  jitter <- ggplot(data.frame(x = rep(1, 6), y = 1:6), aes(x, y)) + geom_point(position = position_jitter(width = .3))
  set.seed(17); ggplot2::ggplotGrob(jitter); expected_rng <- .Random.seed
  set.seed(17); save_for_paper_and_slides(jitter, file.path(parent, "jitter")); stopifnot(identical(.Random.seed, expected_rng))
  bad <- file.path(parent, "bad")
  stopifnot(inherits(try(save_for_paper_and_slides(p, bad, slide_box_mm = c(0, 1)), silent = TRUE), "try-error"), !dir.exists(bad))
  small <- save_for_paper_and_slides(p, file.path(parent, "small"), slide_box_mm = c(40, 30))
  stopifnot(identical(small$status, "REVIEW"), small$typography$min_slide_text_pt < small$typography$required_min_slide_text_pt)
  unlink(parent, recursive = TRUE)
}
