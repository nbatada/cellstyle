"""Reusable density contours for the two-dimensional footprint of labeled cells."""
import warnings

import contourpy
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection


def _selected(available, clusters):
    if clusters is None:
        return list(available)
    wanted = [clusters] if np.isscalar(clusters) else list(clusters)
    if not wanted or len(set(wanted)) != len(wanted):
        raise ValueError("Select one or more distinct cluster IDs")
    unknown = [k for k in wanted if k not in available]
    if unknown:
        raise ValueError(f"Unknown cluster IDs: {unknown}")
    return wanted


def cluster_outlines(data, x, y, group, *, clusters=None, bandwidth=None,
                     mass=.9, grid_size=160, method="density"):
    """Compute unfilled, potentially multipart density contours in embedding units.

    Supply the full embedding even when selecting one cluster. mass is the
    fraction of smoothed density used to choose the contour level. It does not
    specify how many observed cells must lie inside. Returns reusable path
    vertices with columns cluster, path, x, y. Paths can include inner rings.
    With method="territory", only retain locally dominant regions of that
    density support. A small inset separates neighboring outlines. Membership
    labels on the input remain authoritative for all displayed cells.
    """
    if method not in ("density", "territory"):
        raise ValueError("method must be density or territory")
    if not isinstance(grid_size, (int,np.integer)) or not 32 <= grid_size <= 512:
        raise ValueError("grid_size must be an integer between 32 and 512")
    if not np.isfinite(mass) or not 0 < mass < 1:
        raise ValueError("mass must lie strictly between 0 and 1")
    xy = data[[x,y]].to_numpy(dtype=float)
    ids = data[group]
    if not len(xy) or not np.isfinite(xy).all() or ids.isna().any():
        raise ValueError("Supply a nonempty embedding with finite coordinates and complete cluster IDs")
    selected = _selected(pd.unique(ids),clusters)
    span = float(np.ptp(xy,axis=0).max())
    h = .035*span if bandwidth is None else float(bandwidth)
    if not np.isfinite(h) or h <= 0:
        raise ValueError("A positive bandwidth and a nondegenerate embedding are required")
    side = span + 8*h
    step = side/(grid_size-1)
    half_kernel = int(np.ceil(4*h/step))
    weights = np.exp(-.5*(np.arange(-half_kernel,half_kernel+1)*step/h)**2)
    weights /= weights.sum()
    origin = xy.min(axis=0) + .5*(np.ptp(xy,axis=0)-side)
    nodes = np.arange(grid_size)*step
    bins = np.floor((xy-origin)/step+.5).astype(int)

    def smooth(line):
        return np.convolve(np.pad(line,half_kernel),weights,mode="valid")

    # Density outlines are independent. Territories must consider neighbors even
    # when just one cluster is selected for display.
    available = sorted(pd.unique(ids), key=str) if method == "territory" else selected
    density_maps = {}
    strongest = np.full((grid_size, grid_size), -np.inf)
    winner = np.full((grid_size, grid_size), -1)
    for index, identity in enumerate(available):
        keep = (ids == identity).to_numpy(dtype=bool)
        distinct = np.unique(xy[keep],axis=0)
        if len(distinct)<3 or np.linalg.matrix_rank(distinct-distinct[0])<2:
            warnings.warn(f"Cluster {identity!r} has insufficient 2D support; no outline drawn",stacklevel=2)
            continue
        counts = np.zeros((grid_size,grid_size))
        np.add.at(counts,(bins[keep,1],bins[keep,0]),1)
        density = np.apply_along_axis(smooth,0,np.apply_along_axis(smooth,1,counts))
        if method == "territory":
            wins = density > strongest
            strongest[wins] = density[wins]
            winner[wins] = index
        if identity in selected:
            density_maps[identity] = (index, density)

    paths = []
    for identity in selected:
        if identity not in density_maps:
            continue
        index, density = density_maps[identity]
        levels = np.sort(density.ravel())[::-1]
        threshold = levels[np.searchsorted(np.cumsum(levels),mass*levels.sum())]
        if method == "territory":
            mask = ((winner == index) & (density >= threshold)).astype(float)
            kernel = np.exp(-.5*np.arange(-3,4,dtype=float)**2)
            kernel /= kernel.sum()
            def soften(line):
                return np.convolve(np.pad(line,3),kernel,mode="valid")
            density = np.apply_along_axis(soften,0,np.apply_along_axis(soften,1,mask))
            threshold = .75
        contour = contourpy.contour_generator(x=origin[0]+nodes,y=origin[1]+nodes,z=density)
        rings = contour.lines(np.nextafter(threshold,0.))
        if not rings:
            warnings.warn(f"Cluster {identity!r} has no supported {method} outline at this scale", stacklevel=2)
        for ring,vertices in enumerate(rings,1):
            if len(vertices)<4 or not np.allclose(vertices[0],vertices[-1],atol=step*1e-8,rtol=0):
                raise ValueError("The requested contour touches the grid edge; reduce mass or adjust bandwidth")
            paths.append(pd.DataFrame(dict(cluster=identity,path=ring,x=vertices[:,0],y=vertices[:,1])))
    result = pd.concat(paths,ignore_index=True) if paths else pd.DataFrame(columns=["cluster","path","x","y"])
    result.attrs.update(bandwidth=h,mass=mass,grid_size=grid_size,method=method)
    return result


def cluster_outline(ax, adata=None, *, groupby=None, clusters=None, basis="X_umap",
                    paths=None, color="#252525", linewidth=.85, **options):
    """Add outlines to a native embedding Axes. Return the removable line collection.

    Either pass AnnData and groupby, or pass precomputed paths from cluster_outlines.
    This function leaves the underlying cells, colors, aspect and axis limits alone.
    """
    if paths is None:
        if adata is None or groupby is None:
            raise ValueError("Supply adata and groupby, or precomputed paths")
        key = basis if basis in adata.obsm else f"X_{basis}"
        xy = np.asarray(adata.obsm[key])
        if xy.ndim != 2 or xy.shape[1]<2:
            raise ValueError("The embedding must have at least two coordinate columns")
        frame = pd.DataFrame({"x":xy[:,0],"y":xy[:,1],"group":adata.obs[groupby].array})
        paths = cluster_outlines(frame,"x","y","group",clusters=clusters,**options)
    else:
        if adata is not None or groupby is not None or options:
            raise ValueError("Use precomputed paths or compute from data, not both")
        if clusters is not None:
            paths = paths.loc[paths.cluster.isin(_selected(pd.unique(paths.cluster),clusters))]
    segments = [part[["x","y"]].to_numpy(dtype=float)
                for _,part in paths.groupby(["cluster","path"],sort=False,observed=True)]
    lines = LineCollection(segments,colors=color,linewidths=linewidth,zorder=3)
    ax.add_collection(lines,autolim=False)
    return lines
