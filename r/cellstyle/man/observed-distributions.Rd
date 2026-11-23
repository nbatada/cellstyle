\name{box_distribution}
\alias{box_distribution}
\alias{violin_distribution}
\alias{grouped_swarm}
\alias{paired_distribution}
\alias{facet_plot}
\title{Compare distributions and paired observations}
\description{Display supplied measurements. Boxplots show quartiles and 1.5-IQR whiskers. Violins show within-group densities trimmed to the observed range. Boxplots and violins retain individual observations. Grouped swarms and paired plots include the median and interquartile range.}
\usage{
box_distribution(data, x, y, hue = NULL, palette = NULL, output = NULL)
violin_distribution(data, x, y, hue = NULL, palette = NULL, output = NULL)
grouped_swarm(data, x, y, hue, palette = NULL, output = NULL)
paired_distribution(data, pair, x, y, order = NULL, output = NULL)
facet_plot(data, x, y, row = NULL, col = NULL, kind = c("swarm","scatter"),
           palette = NULL, output = NULL)
}
\arguments{
\item{data}{Data frame with one row per observation.}
\item{x,y}{Names of the group and finite numeric measurement columns.}
\item{hue}{Name of the subgroup column for dodged observations.}
\item{palette}{Optional named vector of identity colors.}
\item{pair}{Name of the subject identifier. A subject may have at most one row per condition. Lines connect observed adjacent conditions within each subject.}
\item{order}{Ordered conditions. An ordered factor or explicit order is recommended for visits.}
\item{row,col}{Optional facet columns. Supply at least one. Empty factor levels remain visible.}
\item{kind}{Swarm with per-panel median and IQR, or numeric scatter. Panels share axes and n counts supplied observations.}
\item{output}{Optional new PDF, PNG or SVG path.}
}
\value{An editable ggplot object.}
