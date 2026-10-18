library(cellstyle)
library(ggplot2)
needed <- c("jsonlite","digest","systemfonts","xml2","svglite")
if (all(vapply(needed,requireNamespace,logical(1),quietly=TRUE))) {
  fixture <- system.file("extdata","four-panel-layout.json",package="cellstyle")
  d <- read_figure_layout(fixture)
  stopifnot(d$sha256 == "f810578d4ce8f67b29230e746e271563dc7a930436d4cfc2534792733c0fbd18")
  font <- intersect(c("Arial","DejaVu Sans","Liberation Sans"),systemfonts::system_fonts()$family)[1]
  if (!is.na(font)) {
    p <- ggplot(data.frame(x=1:3,y=c(1,3,2)),aes(x,y))+geom_point()+
      theme_classic(base_size=6,base_family=font)+theme(axis.text=element_text(size=6),axis.title=element_text(size=6))
    out <- tempfile(fileext=".svg")
    r <- export_cellstyle_panel(p,fixture,"a",out,fixture,font)
    stopifnot(abs(r$measured$width_mm-87)<.02,file.exists(paste0(out,".receipt.json")))
    error <- function(expr) stopifnot(inherits(tryCatch(force(expr),error=identity),"error"))
    error(export_cellstyle_panel(p,fixture,"missing",out,fixture,font))
    error(export_cellstyle_panel(p,fixture,"a",out,fixture,"MissingCellStyleFont"))
    error(export_cellstyle_panel(p+theme(axis.text=element_text(size=8)),fixture,"a",out,fixture,font))
    if (capabilities("cairo") && nzchar(Sys.which("gs")) && nzchar(Sys.which("pdfinfo"))) {
      pdf <- tempfile(fileext=".pdf")
      r <- export_cellstyle_panel(p,fixture,"a",pdf,fixture,font)
      stopifnot(abs(r$measured$height_mm-60)<.02)
      unlink(c(pdf,paste0(pdf,".receipt.json")))
    }
    unlink(c(out,paste0(out,".receipt.json")))
  }
}
