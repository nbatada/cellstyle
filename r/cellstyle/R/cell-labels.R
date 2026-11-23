#' Direct, collision-aware labels for grouped embeddings
#'
#' @param mapping,data,...,inherit.aes,show.legend,na.rm Standard ggplot layer arguments.
#' @param short_labels Optional named character vector mapping supplied identities to supplied short labels.
#' @param max_displace_mm Maximum label displacement from an observed group anchor.
#' @export
geom_cell_labels <- function(mapping = NULL, data = NULL, ..., short_labels = NULL,
                             max_displace_mm = 6, na.rm = FALSE, show.legend = FALSE,
                             inherit.aes = TRUE) {
  if (!is.null(short_labels) && (!is.character(short_labels) || is.null(names(short_labels)) ||
      anyNA(short_labels) || anyNA(names(short_labels)) || any(!nzchar(trimws(short_labels))) ||
      any(!nzchar(trimws(names(short_labels)))) || anyDuplicated(short_labels) || anyDuplicated(names(short_labels))))
    stop("short_labels must be a named vector of unique, nonempty supplied alternatives.", call. = FALSE)
  .scalar_number(max_displace_mm, "max_displace_mm", .Machine$double.eps)
  ggplot2::layer(geom = GeomCellLabels, mapping = mapping, data = data, stat = "identity", position = "identity",
    show.legend = show.legend, inherit.aes = inherit.aes,
    params = list(short_labels = short_labels, max_displace_mm = max_displace_mm, na.rm = na.rm, ...))
}

.cell_label_grob <- function(data, short_labels, max_displace_mm) {
  grid::gTree(children = grid::gList(), data = data, short_labels = short_labels,
    max_displace_mm = max_displace_mm, cl = "cellstyle_cell_labels")
}

makeContent.cellstyle_cell_labels <- function(x) {
  d <- x$data; ids <- unique(as.character(d$label)); aliases <- character()
  if (!is.null(x$short_labels)) {
    aliases <- x$short_labels[intersect(ids, names(x$short_labels))]
    if (any(vapply(seq_along(aliases), function(i) aliases[i] %in% setdiff(ids, names(aliases)[i]), logical(1))))
      stop("short_labels cannot duplicate a different displayed identity.", call. = FALSE)
  }
  anchor <- vapply(ids, function(id) {
    rows <- which(as.character(d$label) == id); center <- c(stats::median(d$x[rows]), stats::median(d$y[rows]))
    rows[which.min((d$x[rows]-center[1])^2 + (d$y[rows]-center[2])^2)]
  }, integer(1))
  count <- vapply(ids, function(id) sum(as.character(d$label) == id), numeric(1))
  directions <- rbind(c(1,0),c(-1,0),c(0,1),c(0,-1),c(1,1),c(-1,1),c(1,-1),c(-1,-1))
  max_pt <- x$max_displace_mm / 25.4 * 72.27
  gaps <- c(3,10,20); gaps <- gaps[gaps <= max_pt]
  candidates <- rbind(c(0,0,0), if (length(gaps)) do.call(rbind, lapply(gaps, function(gap) cbind(directions, gap))) else NULL)
  placed <- list(); children <- grid::gList(); unresolved <- 0L
  for (i in order(count, -nchar(ids), ids)) {
    row <- anchor[i]; size <- d$size[row] * 72.27 / 25.4
    colour <- if (is.na(d$colour[row])) "#202020" else grDevices::adjustcolor(d$colour[row], alpha.f = d$alpha[row])
    gp <- grid::gpar(fontsize = size, col = colour,
      fontfamily = d$family[row], fontface = d$fontface[row])
    words <- c(ids[i], if (ids[i] %in% names(aliases)) unname(aliases[ids[i]]))
    best <- NULL
    for (word_index in seq_along(words)) {
      probe <- grid::textGrob(words[word_index], gp = gp)
      w <- grid::convertWidth(grid::grobWidth(probe), "npc", valueOnly = TRUE)/2
      h <- grid::convertHeight(grid::grobHeight(probe), "npc", valueOnly = TRUE)/2
      score <- vapply(seq_len(nrow(candidates)), function(k) {
        divisor <- max(1, sqrt(sum(candidates[k,1:2]^2)))
        gx <- grid::convertWidth(grid::unit(candidates[k,3]/divisor, "pt"), "npc", valueOnly = TRUE)
        gy <- grid::convertHeight(grid::unit(candidates[k,3]/divisor, "pt"), "npc", valueOnly = TRUE)
        px <- d$x[row]+candidates[k,1]*(w+gx); py <- d$y[row]+candidates[k,2]*(h+gy)
        outside <- px-w < 0 || px+w > 1 || py-h < 0 || py+h > 1
        hits <- sum(vapply(placed, function(q) abs(px-q$x)<w+q$w && abs(py-q$y)<h+q$h, logical(1)))
        occluded <- sum(d$x >= px-w & d$x <= px+w & d$y >= py-h & d$y <= py+h)
        leader_pt <- sqrt(grid::convertWidth(grid::unit(px-d$x[row], "npc"), "pt", valueOnly=TRUE)^2 + grid::convertHeight(grid::unit(py-d$y[row], "npc"), "pt", valueOnly=TRUE)^2)
        1e6*outside + 1e4*hits + 10*occluded + .25*leader_pt + if (word_index == 1) 0 else 2
      }, numeric(1))
      candidate <- list(score=min(score), k=which.min(score), word=words[word_index], w=w, h=h)
      if (is.null(best) || candidate$score < best$score) best <- candidate
    }
    k <- best$k
    divisor <- max(1, sqrt(sum(candidates[k,1:2]^2)))
    gx <- grid::convertWidth(grid::unit(candidates[k,3]/divisor, "pt"), "npc", valueOnly = TRUE)
    gy <- grid::convertHeight(grid::unit(candidates[k,3]/divisor, "pt"), "npc", valueOnly = TRUE)
    px <- d$x[row]+candidates[k,1]*(best$w+gx); py <- d$y[row]+candidates[k,2]*(best$h+gy)
    if (best$score >= 1e4) unresolved <- unresolved+1L
    if (candidates[k,3] > 0) {
      edge_x <- px - sign(candidates[k,1]) * best$w
      edge_y <- py - sign(candidates[k,2]) * best$h
      children <- grid::gList(children, grid::segmentsGrob(d$x[row],d$y[row],edge_x,edge_y,default.units="npc",gp=grid::gpar(col="#666666",lwd=.4)))
    }
    children <- grid::gList(children, grid::textGrob(best$word,x=px,y=py,default.units="npc",gp=gp))
    placed[[length(placed)+1L]] <- list(x=px,y=py,w=best$w,h=best$h)
  }
  if (unresolved) warning(unresolved, " CellStyle labels retained a heuristic point or label overlap; review at final size.", call. = FALSE)
  grid::setChildren(x, children)
}

GeomCellLabels <- ggplot2::ggproto("GeomCellLabels", ggplot2::Geom,
  required_aes = c("x", "y", "label"),
  default_aes = ggplot2::aes(colour="#202020", size=2.46, alpha=1, family="", fontface=1),
  draw_panel = function(data, panel_params, coord, short_labels = NULL, max_displace_mm = 6, na.rm = FALSE) {
    keep <- stats::complete.cases(data[c("x","y","label")])
    if (any(!keep) && !na.rm) warning("Removed rows with missing x, y, or label.", call. = FALSE)
    .cell_label_grob(coord$transform(data[keep,,drop=FALSE], panel_params), short_labels, max_displace_mm)
  })
