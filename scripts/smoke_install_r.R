# Run in an R process whose .libPaths() contains only the temporary library and base R.
main <- function(args = commandArgs(trailingOnly = TRUE)) {
  suppressPackageStartupMessages(library(cellstyle))
  if (length(args) > 1L) stop("Give at most one VERSION path.", call. = FALSE)
  version_path <- if (length(args)) args[[1L]] else "VERSION"
  expected_version <- trimws(readLines(version_path, warn = FALSE))
  stopifnot(length(expected_version) == 1L, nzchar(expected_version),
            as.character(packageVersion("cellstyle")) == expected_version)

  fixture <- tempfile(fileext = ".tsv")
  on.exit(unlink(fixture), add = TRUE)
  writeLines(c("entity\tparent\tlevel\trole\tcolor",
               "001\t\t\tidentity\t#1764AB",
               "NA\t\t\tidentity\t#00A2A5"), fixture)
  stopifnot(identical(read_identity_colors(fixture),
                      c("001" = "#1764AB", "NA" = "#00A2A5")))
  cat("Installed cellstyle and read_identity_colors passed\n")
}

if (sys.nframe() == 0L) main()
