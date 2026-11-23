options(device = function(...) grDevices::pdf(NULL))
library(cellstyle); library(ggplot2)
d <- data.frame(x=c(0,.1,2,2.1,4),y=c(0,.1,0,.1,1),identity=c("A","A","B","B","C"))
p <- ggplot(d,aes(x,y,colour=identity))+geom_point()+geom_cell_labels(aes(label=identity),max_displace_mm=4)
stopifnot(inherits(ggplotGrob(p),"gtable"))
short <- c(A="Alpha",B="Beta",C="Gamma")
stopifnot(inherits(ggplotGrob(ggplot(d,aes(x,y))+geom_point()+geom_cell_labels(aes(label=identity),short_labels=short)),"gtable"))
stopifnot(inherits(ggplotGrob(ggplot(d,aes(x,y))+geom_point()+geom_cell_labels(aes(label=identity),short_labels=c(A="Alpha"))),"gtable"))
stopifnot(inherits(try(geom_cell_labels(short_labels=c(A="same",B="same")),silent=TRUE),"try-error"))
if (requireNamespace("svglite", quietly=TRUE) && requireNamespace("xml2", quietly=TRUE)) {
  svg <- tempfile(fileext=".svg")
  ggsave(svg, p, width=90, height=60, units="mm")
  doc <- xml2::read_xml(svg); root <- xml2::xml_root(doc)
  vb <- as.numeric(strsplit(xml2::xml_attr(root,"viewBox"),"[[:space:]]+")[[1]])
  line <- xml2::xml_find_all(doc,"//*[local-name()='line']")
  if (length(line)) {
    x1 <- as.numeric(xml2::xml_attr(line,"x1")); y1 <- as.numeric(xml2::xml_attr(line,"y1"))
    x2 <- as.numeric(xml2::xml_attr(line,"x2")); y2 <- as.numeric(xml2::xml_attr(line,"y2"))
    mm <- sqrt(((x2-x1)*90/(25.4*vb[3]))^2+((y2-y1)*60/(25.4*vb[4]))^2)
    stopifnot(all(mm <= 4.05))
  }
  unlink(svg)
}
