\name{cluster_outlines}
\alias{cluster_outlines}
\alias{geom_cluster_outline}
\title{Mass contours for embedding clusters}
\usage{cluster_outlines(data, x, y, group, clusters = NULL, bandwidth = NULL, mass = .9, grid_size = 160, method = c("density", "territory"))
geom_cluster_outline(paths = NULL, data = NULL, clusters = NULL, bandwidth = NULL, mass = .9, grid_size = 160, method = c("density", "territory"), ..., mapping = NULL, colour = "#202020", linewidth = .45, linetype = 1, alpha = 1)}
\arguments{\item{data}{Data frame with finite coordinates and identified groups.}\item{x,y,group}{Existing column names.}\item{clusters}{Optional supplied group subset.}\item{bandwidth}{Optional isotropic KDE bandwidth.}\item{mass}{Retained grid-density mass.}\item{grid_size}{Global square-grid node count.}\item{method}{Default density contours or opt-in territory bands.}\item{paths}{Output of \code{cluster_outlines}, or a positional aesthetic mapping.}\item{mapping}{Optional named aesthetic mapping such as \code{aes(group = leiden)}.}\item{...}{Native \code{geom_path} arguments.}\item{colour,linewidth,linetype,alpha}{Outline appearance.}}
\value{A closed-path data frame, or a native ggplot layer.}
\description{Density uses global-grid KDE mass contours. Opt-in territory computes raw-density winners across every valid observed cluster, gates each winner mask by that cluster's mass contour, softens the binary masks, and draws separate unfilled bands.}
\details{Territory is an embedding-space estimate, not ground truth: it may omit intermingled cells and never assigns a new identity. Subset selection occurs after all observed clusters compete. Use either \code{p + geom_cluster_outline(cluster_outlines(data, "x", "y", "leiden"))}, or \code{p + geom_cluster_outline(aes(group = leiden), clusters = "4")}. One unfaceted equal-aspect embedding is supported; facets need separately computed paths.}
