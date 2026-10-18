# Physical panel exports are opt-in; existing plot themes are unchanged.
.export_deps <- function() {
  for (p in c("jsonlite", "digest", "systemfonts", "xml2", "svglite")) {
    if (!requireNamespace(p, quietly = TRUE)) stop("Panel export requires optional package: ", p)
  }
}

#' Read a shared physical figure layout
#' @param path JSON layout written by Python FigureLayout.write().
#' @export
read_figure_layout <- function(path) {
  .export_deps()
  d <- jsonlite::fromJSON(path, simplifyVector = FALSE)
  if (!identical(d$schema, "cellstyle-layout-1")) stop("Unsupported layout schema")
  if (anyDuplicated(names(d)) || !setequal(names(d), c("schema", "id", "width_mm", "height_mm", "slots", "letter_owner", "profile"))) stop("Invalid layout fields")
  id_ok <- function(x) is.character(x) && length(x) == 1L && !is.na(x) && nzchar(trimws(x))
  num_ok <- function(x, positive = FALSE) is.numeric(x) && length(x) == 1L && is.finite(x) && if (positive) x > 0 else x >= 0
  if (!id_ok(d$id) || !num_ok(d$width_mm, TRUE) || !num_ok(d$height_mm, TRUE)) stop("Invalid layout dimensions or ID")
  if (!d$letter_owner %in% c("assembly", "panel") || !d$profile %in% c("custom", "nature-flagship-final-research")) stop("Unsupported owner/profile")
  if (d$profile == "nature-flagship-final-research" && (!any(abs(d$width_mm - c(89,183)) < .001) || d$height_mm > 170)) stop("Nature artwork size mismatch")
  if (!length(d$slots)) stop("Layout requires slots")
  for (i in seq_along(d$slots)) {
    a <- d$slots[[i]]
    if (anyDuplicated(names(a)) || !setequal(names(a), c("id", "x_mm", "y_mm", "width_mm", "height_mm", "letter_reserve_mm"))) stop("Invalid slot fields")
    if (!id_ok(a$id) || !num_ok(a$x_mm) || !num_ok(a$y_mm) || !num_ok(a$width_mm, TRUE) || !num_ok(a$height_mm, TRUE)) stop("Invalid slot")
    if (a$x_mm+a$width_mm > d$width_mm || a$y_mm+a$height_mm > d$height_mm) stop("Slot outside page")
    if (!is.null(a$letter_reserve_mm)) stop("R letter reserve checking is not yet supported; use an explicitly reviewed layout without a reserve")
    if (i > 1) for (b in d$slots[seq_len(i-1)]) {
      if (a$id == b$id) stop("Duplicate panel ID")
      if (a$x_mm < b$x_mm+b$width_mm && b$x_mm < a$x_mm+a$width_mm && a$y_mm < b$y_mm+b$height_mm && b$y_mm < a$y_mm+a$height_mm) stop("Overlapping slots")
    }
  }
  values <- c(d$id, sprintf("%.9f",c(d$width_mm,d$height_mm)),d$letter_owner,d$profile)
  for (a in d$slots) values <- c(values,a$id,sprintf("%.9f",c(a$x_mm,a$y_mm,a$width_mm,a$height_mm)),"end-slot")
  d$sha256 <- digest::digest(paste0(nchar(values,type="bytes"),":",values,collapse=""), algo="sha256",serialize=FALSE)
  d
}

#' Export a native ggplot at an exact physical panel size
#' @param plot A ggplot object.
#' @param layout_path Shared layout JSON file.
#' @param panel_id Exact panel ID.
#' @param path Destination PDF or SVG.
#' @param source_path Plotting source file for provenance.
#' @param font_family Concrete installed font family used by the plot.
#' @return Invisibly, a geometry receipt. Visual acceptance remains pending.
#' @export
export_cellstyle_panel <- function(plot, layout_path, panel_id, path, source_path, font_family) {
  d <- read_figure_layout(layout_path)
  found <- Filter(function(s) identical(s$id,panel_id),d$slots)
  if (length(found) != 1) stop("Unknown panel ID")
  s <- found[[1]]
  if (!file.exists(source_path)) stop("Source file does not exist")
  if (!font_family %in% systemfonts::system_fonts()$family) stop("Required font unavailable")
  ext <- tolower(tools::file_ext(path))
  if (!ext %in% c("pdf","svg")) stop("Use PDF or SVG")
  # Probe at the same physical device size; svglite retains live text for inspection.
  probe <- tempfile(fileext=".svg")
  candidate <- tempfile(tmpdir=dirname(path),fileext=paste0(".",ext))
  on.exit(unlink(c(probe,candidate)),add=TRUE)
  ggplot2::ggsave(probe,plot=plot,device=svglite::svglite,width=s$width_mm,height=s$height_mm,units="mm",bg="white")
  doc <- xml2::read_xml(probe)
  text <- xml2::xml_find_all(doc,"//*[local-name()='text']")
  styles <- xml2::xml_attr(text,"style")
  sizes <- as.numeric(sub(".*font-size: ([0-9.]+)px.*","\\1",styles))
  families <- sub(".*font-family: [\"']([^\"']+)[\"'].*","\\1",styles)
  if (anyNA(sizes) || any(families != font_family)) stop("Text font could not be verified or differs from required family")
  # svglite viewBox uses points (72/in); its CSS px are in these user units.
  if (d$profile == "nature-flagship-final-research" && any(sizes < 5 | sizes > 7)) stop("Ordinary text must be 5-7 pt; rerender explicitly")
  if (d$letter_owner != "assembly") stop("R export currently requires assembly-owned panel letters")
  # Detect unrotated out-of-page text; rotated text remains a visual-review item.
  xs <- suppressWarnings(as.numeric(xml2::xml_attr(text,"x")))
  ys <- suppressWarnings(as.numeric(xml2::xml_attr(text,"y")))
  widths <- suppressWarnings(as.numeric(sub("px$","",xml2::xml_attr(text,"textLength"))))
  anchors <- xml2::xml_attr(text,"text-anchor")
  anchors[is.na(anchors)] <- "start"
  left <- xs - ifelse(anchors == "middle",widths/2,ifelse(anchors == "end",widths,0))
  check <- !is.na(xs) & !is.na(ys) & !is.na(widths) & is.na(xml2::xml_attr(text,"transform"))
  if (any(left[check] < -.06 | left[check]+widths[check] > s$width_mm/25.4*72+.06 | ys[check] > s$height_mm/25.4*72+.06 | ys[check]-sizes[check] < -.06)) stop("Text outside panel canvas")
  if (ext == "svg") {
    file.copy(probe,candidate,overwrite=TRUE)
    root <- xml2::xml_root(doc)
    measured <- as.numeric(sub("pt$","",c(xml2::xml_attr(root,"width"),xml2::xml_attr(root,"height"))))*25.4/72
  } else {
    if (!capabilities("cairo")) stop("Cairo PDF device unavailable")
    info <- Sys.which("pdfinfo")
    if (!nzchar(info)) stop("PDF validation requires Poppler pdfinfo on PATH")
    ggplot2::ggsave(candidate,plot=plot,device=grDevices::cairo_pdf,width=s$width_mm,height=s$height_mm,units="mm",family=font_family,bg="white")
    # Cairo rounds page dimensions down to whole points. Extend the page box
    # by <1 pt without FitPage/scaling; preserve all plotted coordinates.
    gs <- Sys.which("gs")
    if (!nzchar(gs)) stop("Exact Cairo PDF page correction requires Ghostscript gs")
    raw <- tempfile(fileext=".pdf")
    on.exit(unlink(raw),add=TRUE)
    file.copy(candidate,raw,overwrite=TRUE)
    status <- system2(gs,c("-q","-dBATCH","-dNOPAUSE","-sDEVICE=pdfwrite","-dFIXEDMEDIA",
      paste0("-dDEVICEWIDTHPOINTS=",s$width_mm/25.4*72),paste0("-dDEVICEHEIGHTPOINTS=",s$height_mm/25.4*72),
      shQuote(paste0("-sOutputFile=",candidate)),shQuote(raw)))
    if (status != 0) stop("PDF page correction failed")
    lines <- system2(info,c("-box",shQuote(candidate)),stdout=TRUE,stderr=TRUE)
    size <- grep("^Page size:",lines,value=TRUE)
    if (length(size) != 1L) stop("Cannot verify PDF page box")
    nums <- regmatches(size,gregexpr("[0-9]+(?:\\.[0-9]+)?",size,perl=TRUE))[[1]]
    measured <- as.numeric(nums[1:2])*25.4/72
  }
  if (length(measured) != 2 || any(!is.finite(measured)) || any(abs(measured-c(s$width_mm,s$height_mm)) > .02)) stop("Exported page differs from slot")
  hash <- function(p) digest::digest(file=p,algo="sha256")
  receipt <- list(schema="cellstyle-panel-receipt-1",status="PANEL_GEOMETRY_CHECKED",layout_id=d$id,layout_sha256=d$sha256,panel_id=panel_id,slot=s,source_path=normalizePath(source_path),source_sha256=hash(source_path),asset_sha256=hash(candidate),measured=list(width_mm=measured[1],height_mm=measured[2]),tolerance_mm=.02,text=list(family=font_family,size_pt=sizes),review_required=c("rotated text and legend bounds","marks and internal clipping","PDF font embedding","raster resolution","font substitution after import","final-size visual and scientific review"))
  if (!file.copy(candidate,path,overwrite=TRUE)) stop("Could not write panel")
  jsonlite::write_json(receipt,paste0(path,".receipt.json"),auto_unbox=TRUE,pretty=TRUE,null="null")
  invisible(receipt)
}
