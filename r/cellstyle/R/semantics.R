semantic_fact <- function(value = NULL, status = "KNOWN", source) {
  if (missing(source)) stop("source is required", call. = FALSE)
  list(candidates = list(list(status = status, value = value, source = source)))
}

semantic_contract <- function(identities = list(), quantities = list(), labels,
                              statistics = list(), caption) {
  list(schema_version = "cellstyle-semantic-1", identities = identities,
       quantities = quantities, labels = labels, statistics = statistics, caption = caption)
}

.semantic_schema <- function() {
  if (!requireNamespace("jsonlite", quietly = TRUE)) stop("jsonlite is required", call. = FALSE)
  path <- system.file("schema", "cellstyle-semantic-1.schema.json", package = "cellstyle")
  if (!nzchar(path)) path <- "schemas/cellstyle-semantic-1.schema.json"
  if (!file.exists(path)) stop("SCHEMA_MISSING: semantic schema is unavailable", call. = FALSE)
  jsonlite::fromJSON(path, simplifyVector = FALSE)
}

.duplicate_keys <- function(x, path = "$") {
  if (!is.list(x)) return(character())
  out <- if (!is.null(names(x)) && anyDuplicated(names(x))) path else character()
  for (i in seq_along(x)) {
    name <- if (is.null(names(x))) paste0("[", i - 1L, "]") else names(x)[i]
    out <- c(out, .duplicate_keys(x[[i]], paste0(path, ".", name)))
  }
  out
}

.nonfinite_paths <- function(x, path = "$") {
  if (is.numeric(x) && any(!is.finite(x))) return(path)
  if (!is.list(x)) return(character())
  out <- character()
  for (i in seq_along(x)) {
    name <- if (is.null(names(x))) paste0("[", i - 1L, "]") else paste0(".", names(x)[i])
    out <- c(out, .nonfinite_paths(x[[i]], paste0(path, name)))
  }
  out
}

read_semantic_contract <- function(path) {
  if (!requireNamespace("jsonlite", quietly = TRUE)) stop("jsonlite is required", call. = FALSE)
  value <- tryCatch(jsonlite::fromJSON(path, simplifyVector = FALSE),
                    error = function(e) stop(if (any(grepl("NaN|Infinity|-Infinity", readLines(path, warn = FALSE)))) "NONFINITE_NUMBER: invalid JSON number" else paste0("INVALID_JSON: ", conditionMessage(e)), call. = FALSE))
  if (length(.duplicate_keys(value))) stop("DUPLICATE_KEY: ", paste(.duplicate_keys(value), collapse = ", "), call. = FALSE)
  if (length(.nonfinite_paths(value))) stop("NONFINITE_NUMBER: ", paste(.nonfinite_paths(value), collapse = ", "), call. = FALSE)
  value
}

.schema_type <- function(x, type) {
  switch(type, object = is.list(x) && !is.null(names(x)),
         array = is.list(x) && is.null(names(x)),
         string = is.character(x) && length(x) == 1L && !is.na(x),
         number = is.numeric(x) && length(x) == 1L && !is.na(x) && is.finite(x),
         boolean = is.logical(x) && length(x) == 1L && !is.na(x),
         `null` = is.null(x), FALSE)
}

.check_schema <- function(value, rule, schema, path, add) {
  if (!is.null(rule$`$ref`)) {
    key <- sub("^#/[\\$]defs/", "", rule$`$ref`)
    return(.check_schema(value, schema$`$defs`[[key]], schema, path, add))
  }
  types <- unlist(rule$type, use.names = FALSE)
  if (length(types) && !any(vapply(types, function(t) .schema_type(value, t), logical(1)))) {
    add("INVALID_TYPE", "FAIL", path, "Value has the wrong schema type")
    return(invisible(NULL))
  }
  if (!is.null(rule$enum) && !any(vapply(rule$enum, identical, logical(1), value))) add(if (path == "$.schema_version") "UNSUPPORTED_SCHEMA_VERSION" else "INVALID_VALUE", "FAIL", path, "Value is outside the schema enum")
  if (is.character(value) && !is.null(rule$minLength) && nchar(value) < rule$minLength) add("INVALID_VALUE", "FAIL", path, "String is too short")
  if (.schema_type(value, "array")) {
    if (!is.null(rule$minItems) && length(value) < rule$minItems) add("INVALID_VALUE", "FAIL", path, "Array is too short")
    if (!is.null(rule$items)) for (i in seq_along(value)) .check_schema(value[[i]], rule$items, schema, paste0(path, "[", i - 1L, "]"), add)
  }
  if (.schema_type(value, "object")) {
    for (key in unlist(rule$required, use.names = FALSE)) if (!key %in% names(value)) add("MISSING_FIELD", "FAIL", paste0(path, ".", key), "Required field is missing")
    if (identical(rule$additionalProperties, FALSE)) for (key in setdiff(names(value), names(rule$properties))) add("UNKNOWN_FIELD", "FAIL", paste0(path, ".", key), "Unknown field")
    for (key in intersect(names(value), names(rule$properties))) .check_schema(value[[key]], rule$properties[[key]], schema, paste0(path, ".", key), add)
  }
  invisible(NULL)
}

.is_local_file <- function(reference, base_dir) {
  if (!is.character(reference) || length(reference) != 1L || is.na(reference) || !nzchar(reference) ||
      grepl("^[A-Za-z][A-Za-z0-9+.-]*://", reference)) return(FALSE)
  path <- if (grepl("^/", reference)) reference else file.path(base_dir, reference)
  info <- file.info(path)
  !is.na(info$isdir) && !info$isdir
}
.same_value <- function(a, b) identical(a$status, b$status) && identical(a$value, b$value)

.resolve_fact <- function(fact, path, mode, base_dir, add, priority) {
  candidates <- fact$candidates
  ranks <- match(vapply(candidates, function(x) x$source$kind, character(1)), priority)
  best <- candidates[ranks == min(ranks)]
  if (length(best) > 1L && !all(vapply(best[-1], .same_value, logical(1), best[[1]]))) {
    add("AUTHORITY_CONFLICT", "FAIL", path, "Top authority claims disagree")
    return(NULL)
  }
  keys <- vapply(best, function(x) paste(x$source$reference, x$source$revision, sep = "\r"), character(1))
  winner <- best[[order(keys)[1]]]
  if (any(vapply(candidates[ranks > min(ranks)], function(x) !.same_value(x, winner), logical(1)))) add("LOWER_PRIORITY_CONFLICT", "WARN", path, "Lower authority claim differs")
  source <- winner$source
  unresolved <- !isTRUE(source$approved) || source$kind %in% c("unknown", "unapproved_proposal") ||
    !nzchar(source$reference) || !nzchar(source$revision) || winner$status %in% c("UNKNOWN", "PROPOSED") ||
    (winner$status == "NOT_APPLICABLE" && (!is.null(winner$value) || !isTRUE(source$approved)))
  if (unresolved) add("UNRESOLVED_FACT", if (mode == "MANUSCRIPT_FINAL") "FAIL" else "WARN", path, "Fact lacks an approved, resolved declaration")
  if (winner$status == "KNOWN" && (is.null(winner$value) || (is.character(winner$value) && !nzchar(trimws(winner$value))))) add("INVALID_FACT_VALUE", "FAIL", path, "Known fact needs a value")
  if (!.is_local_file(source$reference, base_dir)) add("UNRESOLVED_SOURCE", if (mode == "MANUSCRIPT_FINAL") "FAIL" else "WARN", path, "Source reference is not a resolvable local file")
  winner
}

validate_semantics <- function(contract, mode = "ANALYSIS_RESULT", observed = NULL,
                               rendered = FALSE, supported_bindings = NULL,
                               actual = NULL, base_dir = ".") {
  if (!mode %in% c("ANALYSIS_RESULT", "MANUSCRIPT_FINAL")) stop("INVALID_MODE", call. = FALSE)
  schema <- .semantic_schema()
  diagnostics <- list()
  add <- function(code, severity, path, message) diagnostics[[length(diagnostics) + 1L]] <<- list(code = code, severity = severity, path = path, message = message)
  report <- function(resolved, expected = character(), verified = character(), unsupported = character(), missing = character(), unexpected = character()) {
    semantic <- diagnostics[vapply(diagnostics, function(x) !grepl("^(NO_RENDER|UNSUPPORTED_SURFACE|MISSING_LABEL|LABEL_MISMATCH|ROLE_MISMATCH|UNCONTRACTED_LABEL|DUPLICATE_OBSERVED_BINDING)$", x$code) && !grepl("^\\$\\.(labels|observed)", x$path), logical(1))]
    labels <- diagnostics[vapply(diagnostics, function(x) grepl("^(NO_RENDER|UNSUPPORTED_SURFACE|MISSING_LABEL|LABEL_MISMATCH|ROLE_MISMATCH|UNCONTRACTED_LABEL|DUPLICATE_OBSERVED_BINDING)$", x$code) || grepl("^\\$\\.(labels|observed)", x$path), logical(1))]
    verdict <- function(items) if (any(vapply(items, function(x) x$severity == "FAIL", logical(1)))) "FAIL" else if (length(items)) "WARN" else "PASS"
    schema_failed <- any(vapply(diagnostics, function(x) x$code %in% c("INVALID_TYPE", "INVALID_VALUE", "MISSING_FIELD", "UNKNOWN_FIELD", "UNSUPPORTED_SCHEMA_VERSION", "DUPLICATE_KEY"), logical(1)))
    list(schema_version = "cellstyle-semantic-1", semantic_verdict = if (schema_failed) "FAIL" else verdict(semantic), label_verdict = if (schema_failed) "FAIL" else verdict(labels), diagnostics = diagnostics,
         resolved = resolved, coverage = list(rendered = isTRUE(rendered), expected = unname(expected), verified = unname(verified), unsupported = unname(unsupported), missing = unname(missing), unexpected = unname(unexpected)),
         manuscript_ready = FALSE, submission_ready = FALSE, inspection_scope = "native text only")
  }
  duplicates <- .duplicate_keys(contract)
  for (path in duplicates) add("DUPLICATE_KEY", "FAIL", path, "Duplicate object key")
  .check_schema(contract, schema, schema, "$", add)
  if (length(diagnostics)) return(report(NULL))
  priority <- unlist(schema$`x-cellstyle`$authority_priority, use.names = FALSE)
  resolved <- contract
  resolve_set <- function(items, fields, root) {
    for (i in seq_along(items)) for (field in fields) {
      path <- paste0("$.", root, "[", i - 1L, "].", field)
      resolved[[root]][[i]][[field]] <<- .resolve_fact(items[[i]][[field]], path, mode, base_dir, add, priority)
    }
  }
  resolve_set(contract$identities, c("label", "color"), "identities")
  resolve_set(contract$quantities, unlist(schema$`x-cellstyle`$quantity_fields, use.names = FALSE), "quantities")
  resolve_set(contract$labels, "text", "labels")
  for (i in seq_along(resolved$labels)) {
    claim <- resolved$labels[[i]]$text
    approved <- !is.null(claim) && claim$status == "KNOWN" && isTRUE(claim$source$approved) &&
      !claim$source$kind %in% c("unknown", "unapproved_proposal") &&
      nzchar(claim$source$reference) && nzchar(claim$source$revision)
    resolved$labels[[i]]["display_text"] <- list(if (approved) claim$value else contract$labels[[i]]$original)
  }
  resolve_set(contract$statistics, "text", "statistics")
  for (field in names(contract$caption)) resolved$caption[[field]] <- .resolve_fact(contract$caption[[field]], paste0("$.caption.", field), mode, base_dir, add, priority)
  for (root in c("identities", "quantities", "statistics")) {
    ids <- vapply(contract[[root]], function(x) x$id, character(1))
    if (anyDuplicated(ids)) add("DUPLICATE_ID", "FAIL", paste0("$.", root), "Identifiers must be unique")
  }
  ids <- vapply(contract$labels, function(x) x$element_id, character(1))
  bindings <- vapply(contract$labels, function(x) x$binding, character(1))
  if (anyDuplicated(ids) || anyDuplicated(bindings)) add("DUPLICATE_ID", "FAIL", "$.labels", "Element IDs and bindings must be unique")
  colors <- character()
  for (i in seq_along(resolved$identities)) for (field in c("label", "color")) {
    claim <- resolved$identities[[i]][[field]]
    if (is.null(claim) || claim$status != "KNOWN") next
    value <- claim$value
    if (!is.character(value) || length(value) != 1L || !nzchar(trimws(value)) || (field == "color" && !grepl("^#[0-9A-Fa-f]{6}$", value))) add("INVALID_FACT_VALUE", "FAIL", paste0("$.identities[", i - 1L, "].", field), "Identity requires a nonempty label or uppercase #RRGGBB color")
    if (field == "color" && is.character(value) && grepl("^#[0-9A-Fa-f]{6}$", value)) {
      resolved$identities[[i]]$color$value <- toupper(value)
      colors <- c(colors, stats::setNames(toupper(value), resolved$identities[[i]]$id))
    }
  }
  if (length(colors) && any(vapply(split(names(colors), colors), function(ids) length(unique(ids)) > 1L, logical(1)))) add("COLOR_CONFLICT", "FAIL", "$.identities", "Different identities share a color")
  for (i in seq_along(resolved$quantities)) {
    quantity <- resolved$quantities[[i]]
    for (field in unlist(schema$`x-cellstyle`$quantity_fields, use.names = FALSE)) {
      claim <- quantity[[field]]
      path <- paste0("$.quantities[", i - 1L, "].", field)
      if (!is.null(claim) && claim$status == "KNOWN" && (!is.character(claim$value) || !nzchar(trimws(claim$value)))) add("INVALID_FACT_VALUE", "FAIL", path, "Quantity value must be nonempty text")
    }
    if (isTRUE(quantity$requires_denominator) && (is.null(quantity$denominator) || quantity$denominator$status != "KNOWN" || !is.character(quantity$denominator$value) || !nzchar(quantity$denominator$value))) add("MISSING_DENOMINATOR", "FAIL", paste0("$.quantities[", i - 1L, "].denominator"), "Denominator is required")
    for (pair in list(c("unit", "MISSING_UNITS"), c("transform", "MISSING_TRANSFORM"))) if (is.null(quantity[[pair[1]]]) || quantity[[pair[1]]]$status %in% c("UNKNOWN", "PROPOSED")) add(pair[2], if (mode == "MANUSCRIPT_FINAL") "FAIL" else "WARN", paste0("$.quantities[", i - 1L, "].", pair[1]), "Required quantity declaration is unresolved")
  }
  quantity_ids <- vapply(contract$quantities, function(x) x$id, character(1))
  statistic_ids <- vapply(contract$statistics, function(x) x$id, character(1))
  for (i in seq_along(resolved$labels)) {
    label <- resolved$labels[[i]]
    if (nzchar(label$quantity_id) && !label$quantity_id %in% quantity_ids) add("UNKNOWN_REFERENCE", "FAIL", paste0("$.labels[", i - 1L, "].quantity_id"), "Quantity does not exist")
    if (nzchar(label$statistic_id)) {
      index <- match(label$statistic_id, statistic_ids)
      if (is.na(index)) add("UNKNOWN_REFERENCE", "FAIL", paste0("$.labels[", i - 1L, "].statistic_id"), "Statistic does not exist") else {
        statistic <- resolved$statistics[[index]]
        if (!identical(label$context, statistic$context)) add("STATISTIC_CONTEXT_MISMATCH", "FAIL", paste0("$.labels[", i - 1L, "].context"), "Statistic context differs")
        if (!is.null(label$text) && !is.null(statistic$text) && !identical(label$text$value, statistic$text$value)) add("STATISTIC_TEXT_MISMATCH", "FAIL", paste0("$.labels[", i - 1L, "].text"), "Statistic text differs")
      }
    }
    if (!is.null(label$text) && label$text$status == "KNOWN" && (!is.character(label$text$value) || !nzchar(trimws(label$text$value)))) add("INVALID_FACT_VALUE", "FAIL", paste0("$.labels[", i - 1L, "].text"), "Label text must be nonempty text")
  }
  for (field in names(resolved$caption)) {
    claim <- resolved$caption[[field]]
    if (is.null(claim) || claim$status != "KNOWN") next
    valid <- if (field == "independent_n") is.numeric(claim$value) && length(claim$value) == 1L && is.finite(claim$value) && claim$value >= 0 && claim$value == floor(claim$value) else is.character(claim$value) && nzchar(claim$value)
    if (!valid) add("INVALID_FACT_VALUE", "FAIL", paste0("$.caption.", field), "Caption field has an invalid value")
  }
  if (is.null(resolved$caption$data_source) || resolved$caption$data_source$status != "KNOWN" || !.is_local_file(resolved$caption$data_source$value, base_dir)) add("DATA_SOURCE_UNRESOLVED", if (mode == "MANUSCRIPT_FINAL") "FAIL" else "WARN", "$.caption.data_source", "Caption data source is not a resolvable local file")
  if (!is.null(actual)) for (key in names(actual)) {
    parts <- strsplit(key, ".", fixed = TRUE)[[1]]
    index <- match(parts[1], quantity_ids)
    if (length(parts) != 2L || is.na(index) || !parts[2] %in% unlist(schema$`x-cellstyle`$quantity_fields, use.names = FALSE)) add("UNKNOWN_REFERENCE", "FAIL", paste0("$.actual.", key), "Actual value has no quantity declaration") else if (!identical(actual[[key]], resolved$quantities[[index]][[parts[2]]]$value)) add("ACTUAL_MISMATCH", "FAIL", paste0("$.actual.", key), "Actual plotted value differs from declaration")
  }
  expected <- bindings
  verified <- unsupported <- missing <- unexpected <- character()
  if (!isTRUE(rendered)) add("NO_RENDER", if (mode == "MANUSCRIPT_FINAL") "FAIL" else "WARN", "$.labels", "Native text was not inspected") else {
    if (is.null(supported_bindings)) supported_bindings <- vapply(observed, function(x) x$binding, character(1))
    observed_bindings <- vapply(observed, function(x) x$binding, character(1))
    if (anyDuplicated(observed_bindings)) add("DUPLICATE_OBSERVED_BINDING", "FAIL", "$.observed", "Observed bindings must be unique")
    for (i in seq_along(resolved$labels)) {
      label <- resolved$labels[[i]]; binding <- label$binding; path <- paste0("$.labels[", i - 1L, "]")
      missing_severity <- if (mode == "MANUSCRIPT_FINAL" && isTRUE(label$required)) "FAIL" else "WARN"
      if (!binding %in% supported_bindings) { unsupported <- c(unsupported, binding); add("UNSUPPORTED_SURFACE", if (mode == "MANUSCRIPT_FINAL" && isTRUE(label$required)) "FAIL" else "WARN", path, "Native binding cannot be inspected"); next }
      matches <- Filter(function(x) identical(x$binding, binding), observed)
      if (!length(matches)) { missing <- c(missing, binding); add("MISSING_LABEL", missing_severity, path, "Expected native text is absent"); next }
      if (length(matches) != 1L) next
      item <- matches[[1]]
      if (!identical(item$role, label$role)) add("ROLE_MISMATCH", "FAIL", path, "Native role differs")
      claim <- label$text
      approved_known <- !is.null(claim) && claim$status == "KNOWN" && isTRUE(claim$source$approved) &&
        !claim$source$kind %in% c("unknown", "unapproved_proposal") &&
        nzchar(claim$source$reference) && nzchar(claim$source$revision)
      if (approved_known && !identical(item$text, claim$value)) add("LABEL_MISMATCH", "FAIL", path, "Native text differs")
      if (!approved_known && mode == "ANALYSIS_RESULT" && !identical(item$text, label$display_text))
        add("UNRESOLVED_FACT", "WARN", path, "Unresolved label does not match neutral original")
      if (nzchar(label$statistic_id) && (!is.list(item$context) || !identical(item$context, label$context))) add("STATISTIC_CONTEXT_MISMATCH", "FAIL", path, "Native statistic context is unverified")
      if (identical(item$role, label$role) && approved_known && identical(item$text, claim$value) && (!nzchar(label$statistic_id) || identical(item$context, label$context))) verified <- c(verified, binding)
    }
    for (item in observed) if (!item$binding %in% expected && !is.null(item$text) && nzchar(item$text) && !(item$role %in% c("axis_tick", "colorbar_tick") && grepl("^[+-]?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+)(?:[eE][+-]?[0-9]+)?%?$", item$text, perl = TRUE))) {
      unexpected <- c(unexpected, item$binding); add("UNCONTRACTED_LABEL", if (mode == "MANUSCRIPT_FINAL") "FAIL" else "WARN", paste0("$.observed.", item$binding), "Native text lacks a declaration")
    }
  }
  report(resolved, expected, verified, unsupported, missing, unexpected)
}
