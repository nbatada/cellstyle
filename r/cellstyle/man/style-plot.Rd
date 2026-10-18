\name{style_plot}
\alias{style_plot}
\title{Style and optionally save a native plot in one call}
\description{Apply CellStyle manuscript typography and choose a practical physical size for a native ggplot. Preserve its data, scales, labels and geometry. This is manuscript-oriented styling, not scientific or journal approval.}
\usage{style_plot(plot, size_mm = NULL, output = NULL)}
\arguments{
\item{plot}{A native ggplot, including a single Seurat plot. Patchwork composites are not supported.}
\item{size_mm}{Optional width and height in millimetres. Otherwise use the helper's planned size or estimate a size from native facet rows and columns.}
\item{output}{Optional new PDF, SVG or PNG path with an existing parent directory. SVG requires svglite. Existing files are refused.}
}
\value{The ordinary styled ggplot with a cellstyle_size_mm attribute. Returned invisibly when saving; otherwise displayed normally. The live viewer controls display size; the planned size is used for export.}
\details{No statistics, biological annotations, unit conversions or inference are added. Explicit plot data encodings remain intact; the call applies a theme. A later ggplot theme addition can override its appearance. Export uses native devices; final-artifact and journal validation remain separate.}
