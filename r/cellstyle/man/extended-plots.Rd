\name{marker_dotplot}
\alias{marker_dotplot}
\alias{marker_heatmap}
\alias{forest_plot}
\title{Display supplied marker summaries and estimates}
\usage{
marker_dotplot(means, fractions, expression_label = "Mean expression",
               fraction_label = "Fraction positive", output = NULL)
marker_heatmap(values, value_label, scale = c("positive", "marker"), output = NULL)
forest_plot(data, label, estimate, lower, upper, interval_label,
            reference = NULL, log_scale = FALSE, output = NULL)
}
\arguments{
\item{means, fractions}{Named matrices with identical ordered axes. Supply nonnegative means and fractions from zero to one. Dot area encodes fraction.}
\item{expression_label, fraction_label, value_label}{Guide text describing the measured quantity, unit, and applicable detection threshold.}
\item{values}{A numeric matrix with unique named rows and columns. Missing cells are marked with a cross.}
\item{scale}{Positive for a sequential scale anchored at zero, marker for signed marker values on a symmetric scale with zero at the midpoint.}
\item{output}{Optional new PDF, PNG or SVG path.}
\item{data}{Data frame with one supplied estimate and interval per row.}
\item{label, estimate, lower, upper}{Column names giving row labels, estimates and interval bounds.}
\item{interval_label}{Description of the supplied interval, for example 95 percent confidence interval.}
\item{reference}{Optional numeric reference line, for example one for ratios.}
\item{log_scale}{Use a logarithmic x axis for positive values.}
}
\value{An editable ggplot object.}
\description{Display supplied values in their original order. Missing matrix entries remain distinguishable from measured zero. Forest plots preserve the supplied estimates and interval limits.}
