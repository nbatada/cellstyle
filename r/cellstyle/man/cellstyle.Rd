\name{cellstyle}
\alias{cellstyle}
\alias{theme_cellstyle}
\alias{editorial_vivid}
\alias{context_color}
\alias{scale_colour_cellstyle}
\alias{scale_fill_cellstyle}
\alias{scale_colour_positive}
\alias{scale_fill_positive}
\alias{scale_colour_marker}
\alias{scale_fill_marker}
\alias{replicate_distribution}
\alias{quantitative_scatter}
\alias{repel_labels}
\alias{add_comparisons}
\title{Composable CellStyle Helpers for Native ggplot2}
\description{Scientific styling, semantic colors, raw observations with median/IQR summaries, and rendering of supplied statistical results. Helpers return ordinary ggplot2 objects or components. No Seurat dependency is required.}
\usage{
theme_cellstyle(mode = "review", base_size = NULL, base_family = "sans")
editorial_vivid(n = 5)
context_color()
scale_colour_cellstyle(values, ...)
scale_fill_cellstyle(values, ...)
scale_colour_positive(...)
scale_fill_positive(...)
scale_colour_marker(...)
scale_fill_marker(...)
replicate_distribution(data, x, y, order = NULL, palette = NULL,
  alpha = .60, point_size = 1.5)
quantitative_scatter(data, x, y, color = "#1764AB", alpha = .42,
  point_size = 1.5, fit = FALSE)
repel_labels(data, mapping, ..., seed = 0L, max.overlaps = Inf)
add_comparisons(plot, comparisons, y_start = NULL, step_fraction = .08,
  bracket_height_fraction = .025)
}
\arguments{
\item{mode}{One of explore, review, manuscript, presentation, with default base sizes 9, 9, 8, 12 points respectively.}
\item{base_size, base_family}{Optional positive font size in points and font family.}
\item{n}{Number of categorical colors, an integer from zero through five.}
\item{values}{Required named color vector: names are biological identities.}
\item{...}{Arguments forwarded to the corresponding ggplot2 scale or ggrepel text layer. Do not repeat arguments explicitly supplied by the helper.}
\item{data}{Data frame. Each row is a supplied observation; the caller establishes the biological replicate unit.}
\item{x, y}{Single character strings naming data columns. Scatter x and all y values must be numeric.}
\item{order}{Explicit discrete category order. Must include every observed identity; extra empty levels are allowed. Defaults preserve factor levels, sort numeric categories, and retain first appearance for other categories.}
\item{palette}{Named identity-to-color vector covering all displayed groups. NULL assigns the five-color palette in category order; supply a persistent named mapping for stable colors across subsets.}
\item{alpha}{Observation opacity between zero and one.}
\item{point_size}{Positive ggplot2 point size; not numerically equivalent to Python point units.}
\item{color}{Scatter observation color.}
\item{fit}{If TRUE, add an explicitly requested linear least-squares fit without a confidence band. Defaults to FALSE.}
\item{mapping}{A ggplot2 aesthetic mapping including x, y and label.}
\item{seed}{Seed passed to ggrepel for reproducible placement.}
\item{max.overlaps}{Maximum overlaps allowed by ggrepel before omitting a label. Defaults to Inf so overlap counts do not automatically discard supplied labels; callers may explicitly choose a finite threshold.}
\item{plot}{Unfaceted ggplot with discrete x, linear continuous y, and unflipped Cartesian coordinates. Fixed y limits are unsupported.}
\item{comparisons}{Data frame containing group_a and group_b, plus p, p_adjusted, or label. Probabilities must lie in [0,1]; missing adjusted values fall back to p. Nonmissing character labels override formatting and are drawn literally.}
\item{y_start}{Optional finite starting bracket baseline in data coordinates.}
\item{step_fraction}{Positive bracket stacking interval relative to the original panel y range; must exceed bracket_height_fraction.}
\item{bracket_height_fraction}{Nonnegative bracket height relative to that range.}
}
\details{
Categorical colors are \code{#1764AB}, \code{#00A2A5}, \code{#E6A700}, \code{#D43F3A}, \code{#8A4FA3}. Neutral context is \code{#E8E8E8}. Positive scales use nine Matplotlib Blues anchors; marker scales use dark blue, near-black, yellow. Continuous interpolation is native ggplot2 and is not a pixel-equivalence claim.

Replicate distributions require optional package ggbeeswarm and use its true swarm geometry. Raw observations are primary; open medians and IQR lines use type-7 quantiles. Missing y values remain in the point-layer data and are omitted by the native geometry with its standard warning; summaries omit them. Missing group identities and infinite numeric values are rejected. Empty levels remain visible. No aggregation identifies biological replicates on the caller's behalf.

Label repelling requires optional ggrepel. Supplied labels are not automatically omitted because of overlap counts by default; callers control this with max.overlaps. Missing optional packages cause an actionable error at helper use, without preventing use of themes and scales.

Comparisons render supplied results only and never compute or select a test. Adjusted P values take precedence and are identified. Formatting preserves the Python convention: P below 0.001 is thresholded, below 0.01 has three decimal places, otherwise two. Brackets and literal text are neutral. Stacking is a compact default; users should inspect long labels at final output size. Facets, flipped/non-Cartesian coordinates, transformed y and fixed y limits are rejected. Later transformations or limits added by the caller require a fresh review of annotation positions.

R defaults are provisional. Seurat-specific and combined plot behavior has not been validated; prefer native Seurat plots and apply themes to suitable individual ggplot objects.
}
\value{Theme and scale functions return additive ggplot2 components; palette helpers return character vectors; plot helpers and add_comparisons return ggplot objects; repel_labels returns a layer.}
\examples{
library(ggplot2)
d <- data.frame(condition = c("control", "treated"), response = c(1, 2))
ids <- c(control = "#1764AB", treated = "#00A2A5")
ggplot(d, aes(condition, response, colour = condition)) +
  geom_point() + scale_colour_cellstyle(ids) + theme_cellstyle()
quantitative_scatter(data.frame(a = 1:3, b = c(2, 4, 3)), "a", "b")
}
