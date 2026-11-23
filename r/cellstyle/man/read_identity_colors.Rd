\name{read_identity_colors}
\alias{read_identity_colors}
\title{Read identity colors from a Python ColorRegistry TSV}
\usage{read_identity_colors(path)}
\arguments{\item{path}{Path to a TSV written by \code{ColorRegistry.to_tsv()}.}}
\value{A named character vector of colors, indexed by exact entity IDs.}
\description{Reads shared identity colors for \code{scale_colour_cellstyle()},
\code{scale_fill_cellstyle()}, and \code{replicate_distribution()}.}
