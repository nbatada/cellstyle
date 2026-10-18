library(ggplot2)
library(cellstyle)
local({
.collect_ggplot_text <- getFromNamespace(".collect_ggplot_text", "cellstyle")
fixture_dir <- system.file("semantics", package = "cellstyle")
stopifnot(nzchar(fixture_dir))
base_dir <- tempfile("cellstyle_semantics_")
dir.create(file.path(base_dir, "tests", "fixtures", "semantics"), recursive = TRUE)
stopifnot(file.copy(file.path(fixture_dir, "source.json"),
                    file.path(base_dir, "tests", "fixtures", "semantics", "source.json")))
on.exit(unlink(base_dir, recursive = TRUE), add = TRUE)
# Regression: a first collection must not open a persistent graphics device.
before_first_device <- grDevices::dev.cur()
invisible(.collect_ggplot_text(ggplot(data.frame(x=1:2,y=1:2),aes(x,y))+geom_point()))
stopifnot(identical(before_first_device,grDevices::dev.cur()))
base <- read_semantic_contract(file.path(fixture_dir, "base.json"))
code <- function(report, name) name %in% vapply(report$diagnostics, function(x) x$code, character(1))

# Schema and declaration checks share the canonical fixture.
stopifnot(validate_semantics(base, base_dir = base_dir)$semantic_verdict %in% c("PASS", "WARN"))
invalid <- base; invalid$surprise <- 1
stopifnot(code(validate_semantics(invalid, base_dir = base_dir), "UNKNOWN_FIELD"))
invalid <- base; invalid$identities[[2]]$color <- invalid$identities[[1]]$color
stopifnot(code(validate_semantics(invalid, base_dir = base_dir), "COLOR_CONFLICT"))
invalid <- base; invalid$quantities[[1]]$requires_denominator <- TRUE
stopifnot(code(validate_semantics(invalid, base_dir = base_dir), "MISSING_DENOMINATOR"))

# Equal top claims resolve independently of input order; conflicting claims fail.
claim <- base$identities[[1]]$label$candidates[[1]]
other <- claim; other$source$kind <- "dictionary"
check <- base; check$identities[[1]]$label$candidates <- list(other, claim)
a <- validate_semantics(check, base_dir = base_dir)
check$identities[[1]]$label$candidates <- rev(check$identities[[1]]$label$candidates)
b <- validate_semantics(check, base_dir = base_dir)
stopifnot(identical(a$resolved$identities[[1]]$label, b$resolved$identities[[1]]$label))
other <- claim; other$value <- "Different"
check$identities[[1]]$label$candidates <- list(other, claim)
stopifnot(code(validate_semantics(check, base_dir = base_dir), "AUTHORITY_CONFLICT"))

# Callback sees resolved claims; native grob text is checked on each render.
plot_fn <- function(resolved) ggplot(data.frame(x = 1:2, y = 1:2), aes(x, y)) + geom_point() +
  labs(x = resolved$labels[[1]]$text$value, y = NULL)
result <- prepare_semantic_plot(plot_fn, base, base_dir = base_dir)
stopifnot(inherits(result$plot, "ggplot"), identical(result$report$coverage$verified, "x.title"),
          identical(result$report$label_verdict, "PASS"))
wrong <- result$plot + labs(x = "Changed")
stopifnot(code(prepare_semantic_plot(wrong, base, base_dir = base_dir)$report, "LABEL_MISMATCH"))
called <- FALSE
fail <- base; fail$labels[[1]]$quantity_id <- "missing"
invisible(prepare_semantic_plot(function(...) { called <<- TRUE }, fail, base_dir = base_dir))
stopifnot(!called)
cat("PASS: R semantics schema, authority, declarations, native text, callback gate\n")

# Shared language parity cases use the same schema and declarations.
cases <- jsonlite::fromJSON(file.path(fixture_dir, "cases.json"), simplifyVector = FALSE)
for (scenario in cases) {
  args <- scenario[c("contract", "mode", "rendered", "observed", "supported_bindings", "actual")]
  report <- do.call(validate_semantics, c(args, list(base_dir = base_dir)))
  got_codes <- vapply(report$diagnostics, function(x) x$code, character(1))
  stopifnot(identical(report$semantic_verdict, scenario$expected_semantic_verdict),
            identical(report$label_verdict, scenario$expected_label_verdict),
            all(unlist(scenario$expected_codes) %in% got_codes))
}
for (file in c("duplicate-key.json", "nonfinite.json", "overflow.json")) {
  error <- tryCatch(read_semantic_contract(file.path(fixture_dir, file)), error = conditionMessage)
  stopifnot(grepl(if (file == "duplicate-key.json") "DUPLICATE_KEY" else "NONFINITE_NUMBER", error))
}
cat("PASS:", length(cases), "shared semantic scenarios and strict JSON read failures\n")

# Native legend collection is based on the drawn grob, including item order.
legend_plot <- ggplot(data.frame(x = 1:2, y = 1:2, identity = c("A", "B")),
                      aes(x, y, colour = identity)) + geom_point() +
  labs(x = "X", y = "Y", title = "Title", colour = "Identity")
collected <- .collect_ggplot_text(legend_plot)
observed_text <- setNames(vapply(collected$observed, function(x) x$text, character(1)),
                          vapply(collected$observed, function(x) x$binding, character(1)))
stopifnot(identical(unname(observed_text[c("x.title", "y.title", "title", "legend.title", "legend.item[0]", "legend.item[1]")]),
                    c("X", "Y", "Title", "Identity", "A", "B")))
cat("PASS: actual ggplotGrob title, axes, legend title and items\n")

n_zero <- base
n_zero$caption$independent_n <- semantic_fact(0.0, source = base$caption$data_source$candidates[[1]]$source)
stopifnot(!code(validate_semantics(n_zero, base_dir = base_dir), "INVALID_FACT_VALUE"))
n_bad <- n_zero
n_bad$caption$independent_n$candidates[[1]]$value <- NaN
stopifnot(code(validate_semantics(n_bad), "INVALID_TYPE"))

before_device <- grDevices::dev.cur()
existing <- prepare_semantic_plot(legend_plot, base, base_dir = base_dir)
stopifnot(!existing$preflight_before_render, identical(grDevices::dev.cur(), before_device))
continuous_plot <- ggplot(data.frame(x = 1:3, y = 1:3, z = 1:3), aes(x, y, colour = z)) + geom_point()
continuous <- .collect_ggplot_text(continuous_plot)
stopifnot(any(grepl("continuous color guide", continuous$limitations)),
          !"legend.title" %in% continuous$supported_bindings,
          !any(grepl("^legend.item", vapply(continuous$observed, function(x) x$binding, character(1)))),
          identical(grDevices::dev.cur(), before_device))
cat("PASS: finite zero N, nonfinite input, offscreen draw and device restoration, unsupported colorbar\n")

# Cross-language edge behavior: provenance, neutral analysis text, duplicate observations.
stopifnot(getFromNamespace(".is_local_file", "cellstyle")(
  file.path(base_dir, "tests", "fixtures", "semantics", "source.json"), base_dir))
stopifnot(!getFromNamespace(".is_local_file", "cellstyle")(base_dir, base_dir),
          !getFromNamespace(".is_local_file", "cellstyle")("https://example.org/source", base_dir))
missing <- validate_semantics(base, rendered = TRUE, observed = list(),
                              supported_bindings = "x.title", base_dir = base_dir)
stopifnot(identical(missing$label_verdict, "WARN"), code(missing, "MISSING_LABEL"))
neutral <- base
neutral$labels[[1]]$original <- "Original title"
neutral$labels[[1]]$text$candidates[[1]]$status <- "UNKNOWN"
neutral$labels[[1]]$text$candidates[[1]]["value"] <- list(NULL)
neutral_report <- validate_semantics(neutral, rendered = TRUE,
  observed = list(list(binding = "x.title", role = "axis_title", text = "Original title")),
  supported_bindings = "x.title", base_dir = base_dir)
stopifnot(identical(neutral_report$resolved$labels[[1]]$display_text, "Original title"),
          !code(neutral_report, "LABEL_MISMATCH"),
          !"x.title" %in% neutral_report$coverage$verified)
observed_twice <- list(list(binding = "x.title", role = "axis_title", text = "Synthetic embedding 1"),
                       list(binding = "x.title", role = "axis_title", text = "Synthetic embedding 1"))
duplicate_report <- validate_semantics(base, rendered = TRUE, observed = observed_twice,
  supported_bindings = "x.title", base_dir = base_dir)
stopifnot(code(duplicate_report, "DUPLICATE_OBSERVED_BINDING"),
          identical(duplicate_report$label_verdict, "FAIL"),
          !"x.title" %in% duplicate_report$coverage$verified)
cat("PASS: absolute source, neutral analysis label, missing label warning, duplicate observation\n")

})
