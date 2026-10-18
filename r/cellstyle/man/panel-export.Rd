\name{export_cellstyle_panel}
\alias{export_cellstyle_panel}
\alias{read_figure_layout}
\title{Export Native Plots to Physical Panel Slots}
\description{Read the shared CellStyle layout and export a native ggplot to an exact PDF or SVG page. Geometry checks do not establish visual or scientific acceptance.}
\usage{
read_figure_layout(path)
export_cellstyle_panel(plot, layout_path, panel_id, path, source_path,
  font_family)
}
\arguments{
\item{path}{Layout JSON input or panel output path, depending on the function.}
\item{plot}{A native ggplot object.}
\item{layout_path}{Shared layout JSON written by Python FigureLayout.}
\item{panel_id}{Exact slot ID.}
\item{source_path}{Existing plotting source file, hashed for provenance.}
\item{font_family}{Concrete installed family used by all plot text.}
}
\value{The layout record, or invisibly a panel receipt also saved beside the output.}
\details{Optional jsonlite, digest, systemfonts, xml2 and svglite packages are required. PDF also requires Cairo, Poppler pdfinfo and Ghostscript gs. Cairo rounds page sizes to points; Ghostscript extends the page box without scaling. Assembly-owned letters are required. Reserved letter rectangles are currently unsupported in R and cause an error. Rotated text, legend geometry, internal clipping and final font appearance require review. The Nature profile checks ordinary text at 5--7 points; it does not change themes or certify compliance.}
