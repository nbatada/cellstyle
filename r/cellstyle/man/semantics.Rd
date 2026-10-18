\name{semantics}
\alias{semantic_fact}
\alias{semantic_contract}
\alias{read_semantic_contract}
\alias{validate_semantics}
\alias{prepare_semantic_plot}
\title{Opt-in scientific declarations and native text checks}
\description{Resolve supplied scientific metadata and inspect text in a native ggplot. These checks do not establish biological truth, exported-artifact quality, or journal compliance.}
\usage{
semantic_fact(value = NULL, status = "KNOWN", source)
semantic_contract(identities = list(), quantities = list(), labels,
  statistics = list(), caption)
read_semantic_contract(path)
validate_semantics(contract, mode = "ANALYSIS_RESULT", observed = NULL,
  rendered = FALSE, supported_bindings = NULL, actual = NULL, base_dir = ".")
prepare_semantic_plot(plot_or_callback, contract, mode = "ANALYSIS_RESULT",
  visual_intent = "review", base_dir = ".", actual = NULL)
}
\arguments{
\item{value,status,source}{Declared value, knowledge state, and explicit source authority.}
\item{identities,quantities,labels,statistics,caption}{Records described by the packaged cellstyle-semantic-1 schema.}
\item{path}{Path to a strict JSON contract.}
\item{contract}{A semantic contract; source metadata is declared rather than inferred.}
\item{mode}{ANALYSIS_RESULT or MANUSCRIPT_FINAL.}
\item{observed}{Collected native text records.}
\item{rendered}{Whether native rendering was inspected.}
\item{supported_bindings}{Native surfaces the collector can inspect.}
\item{actual}{Explicit observed quantity facts keyed as quantity.field.}
\item{base_dir}{Directory for resolving relative source references.}
\item{plot_or_callback}{Existing ggplot or function taking resolved declarations and returning a ggplot.}
\item{visual_intent}{Existing theme intent; callbacks apply theme_cellstyle explicitly without global mutation.}
}
\value{A fact or contract, or a report with separate semantic and label verdicts. Preparation returns the native plot and report; readiness flags remain false.}
\details{Requires jsonlite. Unknown, unapproved or unsupported required meaning blocks final-mode checks. Facets, continuous guides and unclassified grob text are not supported by the initial native collector and cannot receive final PASS. Reference existence does not authenticate scientific approval. No statistical tests are chosen or computed.}
