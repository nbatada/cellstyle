#' Read identity colors from a Python ColorRegistry TSV
#' @param path Path to a TSV written by `ColorRegistry.to_tsv()`.
#' @return A named character vector of colors, indexed by exact entity IDs.
#' @export
read_identity_colors <- function(path) {
  registry <- utils::read.delim(path, colClasses = "character", check.names = FALSE,
                                na.strings = character(), stringsAsFactors = FALSE)
  fields <- c("entity", "parent", "level", "role", "color")
  if (anyDuplicated(names(registry)) || !identical(names(registry), fields))
    stop("ColorRegistry TSV must have entity, parent, level, role, color columns.", call. = FALSE)
  if (!nrow(registry) || anyNA(registry$entity) ||
      any(!nzchar(trimws(registry$entity))) || anyDuplicated(registry$entity))
    stop("ColorRegistry entities must be nonempty and unique.", call. = FALSE)
  .identity_values(stats::setNames(registry$color, registry$entity))
}
