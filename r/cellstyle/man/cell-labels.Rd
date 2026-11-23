\name{geom_cell_labels}
\alias{geom_cell_labels}
\title{Direct labels for grouped embedding observations}
\usage{geom_cell_labels(mapping = NULL, data = NULL, ..., short_labels = NULL, max_displace_mm = 6, na.rm = FALSE, show.legend = FALSE, inherit.aes = TRUE)}
\arguments{\item{mapping,data,...,inherit.aes,show.legend,na.rm}{Standard ggplot layer arguments.}\item{short_labels}{A named, unique supplied mapping from identities to short labels.}\item{max_displace_mm}{Maximum displacement from an observed group anchor.}}
\description{At draw time each identity anchors at the observed cell nearest its coordinate median. Smaller groups are placed first and bounded alternatives are scored against label collisions and cell occlusion.}
\details{No abbreviation is inferred. A warning reports unresolved bounded fit; final-size review remains required.}
