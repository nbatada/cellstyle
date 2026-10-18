.native_text <- function(grob, path = "") {
  out <- list()
  if (inherits(grob, "text")) {
    if (is.expression(grob$label)) {
      out[[length(out) + 1L]] <- list(path = path, text = NULL, unsupported = TRUE)
    } else {
      for (value in as.character(grob$label)) out[[length(out) + 1L]] <- list(path = path, text = value, unsupported = FALSE)
    }
  }
  if (!is.null(grob$children)) for (name in names(grob$children)) out <- c(out, .native_text(grob$children[[name]], paste0(path, "/", name)))
  if (!is.null(grob$grobs)) for (i in seq_along(grob$grobs)) {
    name <- if (!is.null(grob$layout$name)) grob$layout$name[i] else as.character(i)
    out <- c(out, .native_text(grob$grobs[[i]], paste0(path, "/", name)))
  }
  out
}

.has_colorbar <- function(grob) {
  if (!is.null(grob$layout$name) && "bar" %in% grob$layout$name) return(TRUE)
  if (!is.null(grob$grobs) && any(vapply(grob$grobs, .has_colorbar, logical(1)))) return(TRUE)
  if (!is.null(grob$children) && any(vapply(grob$children, .has_colorbar, logical(1)))) return(TRUE)
  FALSE
}

.collect_ggplot_text <- function(plot) {
  if (!inherits(plot, "ggplot")) stop("UNSUPPORTED_PLOT: expected one native ggplot", call. = FALSE)
  previous <- grDevices::dev.cur()
  grDevices::pdf(file = NULL)
  device <- grDevices::dev.cur()
  on.exit({ grDevices::dev.off(device); if (previous > 1L && previous %in% grDevices::dev.list()) grDevices::dev.set(previous) }, add = TRUE)
  # Build as well as draw on the private device: grob construction may open a device.
  grob <- ggplot2::ggplotGrob(plot)
  grid::grid.draw(grob)
  colorbar <- .has_colorbar(grob)
  texts <- list()
  for (i in seq_along(grob$grobs)) texts <- c(texts, .native_text(grob$grobs[[i]], grob$layout$name[i]))
  observed <- list(); limitations <- character()
  supported <- c("x.title", "y.title", "title", "legend.title")
  if (colorbar) {
    supported <- setdiff(supported, "legend.title")
    limitations <- c(limitations, "continuous color guide is unsupported")
  }
  counts <- list(x.tick = 0L, y.tick = 0L, legend.item = 0L, annotation = 0L)
  add <- function(binding, role, value) observed[[length(observed) + 1L]] <<- list(binding = binding, role = role, text = value)
  for (item in texts) {
    path <- item$path
    if (isTRUE(item$unsupported)) { limitations <- c(limitations, paste0("unsupported expression at ", path)); next }
    value <- item$text
    if (!nzchar(value)) next
    if (colorbar && grepl("^guide-box", path)) next
    if (grepl("^xlab-b/", path)) { add("x.title", "axis_title", value); next }
    if (grepl("^ylab-l/", path)) { add("y.title", "axis_title", value); next }
    if (grepl("^title/", path)) { add("title", "figure_title", value); next }
    if (grepl("^axis-b/", path)) { family <- "x.tick"; role <- "axis_tick"
    } else if (grepl("^axis-l/", path)) { family <- "y.tick"; role <- "axis_tick"
    } else if (grepl("^guide-box-[^/]+/guides/title/", path)) { add("legend.title", "legend_title", value); next
    } else if (grepl("^guide-box-[^/]+/guides/label", path)) { family <- "legend.item"; role <- "legend_item"
    } else if (grepl("^panel", path)) { family <- "annotation"; role <- "annotation"
    } else { limitations <- c(limitations, paste0("unclassified native text at ", path)); next }
    counts[[family]] <- counts[[family]] + 1L
    binding <- paste0(family, "[", counts[[family]] - 1L, "]")
    supported <- c(supported, binding)
    add(binding, role, value)
  }
  # Facets and multiple guides do not have a stable one-panel binding here.
  if (any(grepl("^strip", grob$layout$name))) limitations <- c(limitations, "facet strips are unsupported")
  if (sum(grepl("^guide-box-[^/]+/guides/title/", vapply(texts, function(x) x$path, character(1)))) > 1L) limitations <- c(limitations, "multiple guide titles are unsupported")
  list(observed = observed, supported_bindings = unique(supported), limitations = unique(limitations))
}

prepare_semantic_plot <- function(plot_or_callback, contract, mode = "ANALYSIS_RESULT",
                                  visual_intent = "review", base_dir = ".", actual = NULL) {
  if (!visual_intent %in% c("explore", "review", "manuscript", "presentation")) stop("INVALID_VISUAL_INTENT", call. = FALSE)
  preflight <- validate_semantics(contract, mode = mode, base_dir = base_dir, actual = actual)
  blocking <- Filter(function(x) x$severity == "FAIL" && x$code != "NO_RENDER", preflight$diagnostics)
  callback <- is.function(plot_or_callback)
  if (length(blocking)) return(list(plot = if (callback) NULL else plot_or_callback, report = preflight,
                                    preflight = preflight, preflight_before_render = callback))
  plot <- if (callback) plot_or_callback(preflight$resolved) else plot_or_callback
  collected <- .collect_ggplot_text(plot)
  report <- validate_semantics(contract, mode = mode, observed = collected$observed,
                               rendered = TRUE, supported_bindings = collected$supported_bindings,
                               actual = actual, base_dir = base_dir)
  for (limitation in collected$limitations) report$diagnostics[[length(report$diagnostics) + 1L]] <- list(
    code = "UNSUPPORTED_SURFACE", severity = if (mode == "MANUSCRIPT_FINAL") "FAIL" else "WARN",
    path = "$.native_text", message = limitation)
  report$coverage$limitations <- collected$limitations
  if (length(collected$limitations)) report$label_verdict <- if (mode == "MANUSCRIPT_FINAL") "FAIL" else if (report$label_verdict == "PASS") "WARN" else report$label_verdict
  list(plot = plot, report = report, preflight = preflight, preflight_before_render = callback)
}
