#' Compute mass-contour paths for embedding clusters
#'
#' @param data Data frame containing embedding coordinates and a cluster column.
#' @param x,y,group Existing column names.
#' @param clusters Optional supplied subset of group values.
#' @param bandwidth Optional isotropic Gaussian bandwidth in coordinate units.
#' @param mass Density-grid mass retained by each contour, between zero and one.
#' @param grid_size Number of nodes on each global square-grid dimension.
#' @return A data frame with `cluster`, `path`, `x`, and `y`.
#' @export
cluster_outlines <- function(data, x, y, group, clusters = NULL, bandwidth = NULL, mass = .9, grid_size = 160,
                             method = c("density", "territory")) {
  if (!is.data.frame(data) || !all(c(x,y,group) %in% names(data))) stop("data must contain x, y, and group columns.", call.=FALSE)
  if (!is.character(c(x,y,group)) || anyNA(c(x,y,group)) || any(!nzchar(c(x,y,group)))) stop("x, y, and group must be nonempty column names.", call.=FALSE)
  if (!is.numeric(data[[x]]) || !is.numeric(data[[y]]) || any(!is.finite(data[[x]])) || any(!is.finite(data[[y]])) || anyNA(data[[group]]))
    stop("x and y must be finite numeric columns and group must be identified.", call.=FALSE)
  .scalar_number(mass, "mass", .Machine$double.eps, 1-.Machine$double.eps)
  method <- match.arg(method)
  .scalar_number(grid_size, "grid_size", 32, 512)
  if (grid_size != as.integer(grid_size)) stop("grid_size must be an integer.", call.=FALSE)
  group_values <- as.character(data[[group]])
  all_ids <- unique(group_values); ids <- all_ids
  if (!is.null(clusters)) {
    selected <- as.character(clusters)
    if (!length(selected) || anyNA(selected) || anyDuplicated(selected) || !all(selected %in% ids)) stop("clusters must be a unique supplied subset of observed group IDs.", call.=FALSE)
    ids <- selected
  }
  xr <- range(data[[x]]); yr <- range(data[[y]]); span <- max(diff(xr), diff(yr))
  if (!is.finite(span) || span <= 0) stop("Embedding needs nonzero global coordinate span.", call.=FALSE)
  h <- if (is.null(bandwidth)) .035 * span else bandwidth
  .scalar_number(h, "bandwidth", .Machine$double.eps)
  midpoint <- c(mean(xr), mean(yr)); width <- span + 8*h; nodes <- seq(-width/2, width/2, length.out=grid_size)
  gx <- midpoint[1] + nodes; gy <- midpoint[2] + nodes; step <- nodes[2]-nodes[1]
  radius <- ceiling(4*h/step); offsets <- -radius:radius; kernel <- exp(-.5*(offsets*step/h)^2); kernel <- kernel/sum(kernel)
  blur <- function(z, offsets, kernel) {
    pass <- function(a, margin) {
      out <- matrix(0, nrow(a), ncol(a))
      for (k in seq_along(offsets)) {
        off <- offsets[k]
        if (margin == 1L) {
          source <- max(1,1-off):min(nrow(a),nrow(a)-off); target <- source+off
          out[target,] <- out[target,] + kernel[k]*a[source,,drop=FALSE]
        } else {
          source <- max(1,1-off):min(ncol(a),ncol(a)-off); target <- source+off
          out[,target] <- out[,target] + kernel[k]*a[,source,drop=FALSE]
        }
      }; out
    }
    pass(pass(z,1L),2L)
  }
  densities <- list(); thresholds <- numeric(); valid_ids <- character()
  competitors <- if (method == "territory") all_ids else ids
  for (id in competitors) {
    d <- data[group_values == id, c(x,y), drop=FALSE]
    distinct <- unique(d)
    if (nrow(distinct) < 3L || qr(cbind(1, distinct[[1]], distinct[[2]]))$rank < 3L) {
      warning("Skipped cluster ", id, ": fewer than three distinct noncollinear cells.", call.=FALSE); next
    }
    ix <- pmin(grid_size, pmax(1L, floor((d[[1]]-gx[1])/step + .5)+1L))
    iy <- pmin(grid_size, pmax(1L, floor((d[[2]]-gy[1])/step + .5)+1L))
    bins <- matrix(tabulate(ix + (iy-1L)*grid_size, nbins=grid_size^2), nrow=grid_size, ncol=grid_size)
    density <- blur(bins, offsets, kernel); ordered <- sort(as.vector(density), decreasing=TRUE)
    densities[[id]] <- density; thresholds[id] <- ordered[which(cumsum(ordered) >= mass*sum(ordered))[1L]]; valid_ids <- c(valid_ids,id)
  }
  ids <- ids[ids %in% valid_ids]
  rows <- list(); path_id <- 0L
  if (method == "territory") {
    # Every observed valid cluster competes before selected paths are filtered; no new identity is assigned.
    winner <- matrix("",grid_size,grid_size); best <- matrix(-Inf,grid_size,grid_size)
    for (id in sort(valid_ids, method="radix")) {
      take <- densities[[id]] > best
      winner[take] <- id; best[take] <- densities[[id]][take]
    }
    mask_offsets <- -3:3
    mask_kernel <- exp(-.5 * mask_offsets^2)
    mask_kernel <- mask_kernel / sum(mask_kernel)
  }
  for (id in ids) {
    rings <- if (method == "density") grDevices::contourLines(gx,gy,densities[[id]],levels=thresholds[[id]]) else
      grDevices::contourLines(gx,gy,blur(((winner == id) & densities[[id]] >= thresholds[[id]])*1, mask_offsets, mask_kernel),levels=.75)
    if (!length(rings)) warning("No ", method, " contour for cluster ", id, ".", call.=FALSE)
    for (ring in rings) {
      if (!length(ring$x)) next
      path_id <- path_id+1L
      xx <- ring$x; yy <- ring$y
      if (!isTRUE(all.equal(xx[1],xx[length(xx)],tolerance=1e-10)) || !isTRUE(all.equal(yy[1],yy[length(yy)],tolerance=1e-10))) {
        warning("Skipped open contour for cluster ", id, ".", call.=FALSE); next
      }
      rows[[length(rows)+1L]] <- data.frame(cluster=id,path=path_id,x=xx,y=yy,stringsAsFactors=FALSE)
    }
  }
  if (!length(rows)) return(data.frame(cluster=character(),path=integer(),x=numeric(),y=numeric()))
  do.call(rbind,rows)
}

#' Overlay precomputed cluster-outline paths on a native ggplot
#'
#' @param paths Output from [cluster_outlines()], or an aesthetic mapping for the one-layer form.
#' @param ... Arguments forwarded to [ggplot2::geom_path()].
#' @return A native ggplot layer.
#' @export
geom_cluster_outline <- function(paths = NULL, data = NULL, clusters = NULL, bandwidth = NULL, mass=.9, grid_size=160, method=c("density","territory"),
                                 ..., mapping=NULL, colour="#202020", linewidth=.45, linetype=1, alpha=1) {
  if (!is.null(mapping)) {
    if (!is.null(paths)) stop("Supply paths or an aesthetic mapping.", call.=FALSE)
    paths <- mapping
  }
  if (is.data.frame(paths) && all(c("cluster","path","x","y") %in% names(paths))) {
    if (!is.null(data) || !missing(bandwidth) || !missing(mass) || !missing(grid_size) || !missing(method))
      stop("Precomputed paths already have fixed geometry.", call.=FALSE)
    if (!is.null(clusters)) {
      wanted <- as.character(clusters)
      if (!length(wanted) || anyDuplicated(wanted) || !all(wanted %in% paths$cluster))
        stop("Select distinct cluster IDs present in the precomputed paths.", call.=FALSE)
      paths <- paths[paths$cluster %in% wanted,,drop=FALSE]
    }
    return(ggplot2::geom_path(data=paths, ggplot2::aes(x=.data$x,y=.data$y,group=interaction(.data$cluster,.data$path,drop=TRUE)),
      inherit.aes=FALSE, colour=colour, linewidth=linewidth, linetype=linetype, alpha=alpha, ...))
  }
  if (!inherits(paths, "uneval")) stop("Supply cluster_outlines output or aes(group = cluster_column).", call.=FALSE)
  structure(list(mapping=paths, data=data, clusters=clusters, bandwidth=bandwidth, mass=mass, grid_size=grid_size, method=match.arg(method),
    dots=list(...), colour=colour, linewidth=linewidth, linetype=linetype, alpha=alpha), class="cellstyle_cluster_outline")
}

ggplot_add.cellstyle_cluster_outline <- function(object, plot, ...) {
  if (!inherits(plot$facet,"FacetNull")) stop("Automatic cluster outlines support one unfaceted embedding; compute paths separately for facets.", call.=FALSE)
  data <- if (is.null(object$data)) plot$data else object$data
  if (!is.data.frame(data)) stop("Automatic cluster outlines need a data-frame plot or layer data.", call.=FALSE)
  merged <- utils::modifyList(plot$mapping, object$mapping)
  name_of <- function(aesthetic) {
    value <- merged[[aesthetic]]
    if (is.null(value)) stop("Automatic cluster outlines require inherited ", aesthetic, " mapping.", call.=FALSE)
    rlang::as_name(rlang::get_expr(value))
  }
  paths <- cluster_outlines(data, name_of("x"), name_of("y"), name_of("group"), clusters=object$clusters,
    bandwidth=object$bandwidth, mass=object$mass, grid_size=object$grid_size, method=object$method)
  layer <- do.call(ggplot2::geom_path, c(list(data=paths,
    mapping=ggplot2::aes(x=.data$x,y=.data$y,group=interaction(.data$cluster,.data$path,drop=TRUE)),
    inherit.aes=FALSE, colour=object$colour, linewidth=object$linewidth, linetype=object$linetype, alpha=object$alpha), object$dots))
  plot + layer
}
