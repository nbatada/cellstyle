"""The selected cell-map / marker-matrix composition, using native Scanpy data handling."""
from collections.abc import Mapping, Sequence
import math
import warnings

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath
import numpy as np
import pandas as pd
from adjustText import adjust_text

from .embedding import _require_scanpy
from .theme import theme_context
from .styling import _destination, _save_figure
from .provenance import _validate_recipe
from .layout import _overlap


def _plot_data(adata, markers, groupby, basis, use_raw, layer):
    from anndata import AnnData
    if isinstance(markers, str):
        raise ValueError('markers must be a nonempty sequence of unique gene names')
    markers = list(markers)
    if not markers or len(set(markers)) != len(markers):
        raise ValueError('markers must be nonempty and unique')
    if not adata.n_obs or groupby not in adata.obs:
        raise ValueError('Provide cells and an existing groupby column')
    groups = adata.obs[groupby]
    if groups.isna().any():
        raise ValueError('groupby contains missing identities; resolve them before plotting')
    if not isinstance(groups.dtype, pd.CategoricalDtype):
        groups = pd.Series(pd.Categorical(groups, categories=pd.unique(groups)), index=groups.index)
    groups = groups.cat.remove_unused_categories()
    key = basis if basis in adata.obsm else 'X_' + basis
    if key not in adata.obsm:
        raise ValueError(f'Missing embedding: {basis}')
    coords = np.asarray(adata.obsm[key])
    if coords.shape != (adata.n_obs, 2) or not np.isfinite(coords).all():
        raise ValueError('Embedding must have two finite coordinates for every cell')
    if use_raw is not None and type(use_raw) is not bool:
        raise ValueError('use_raw must be True, False or None')
    if layer is not None and use_raw is True:
        raise ValueError('Choose a layer or raw expression, not both')
    if layer is not None and layer not in adata.layers:
        raise ValueError(f'Unknown layer: {layer}')
    raw = (adata.raw is not None) if use_raw is None and layer is None else bool(use_raw)
    if raw and adata.raw is None:
        raise ValueError('use_raw=True requires adata.raw')
    source = adata.raw if raw else adata
    if not source.var_names.is_unique:
        raise ValueError('Expression gene names must be unique')
    missing = [gene for gene in markers if gene not in source.var_names]
    if missing:
        raise ValueError(f'Unknown markers in selected expression matrix: {missing}')
    selected = source[:, markers]
    matrix = selected.layers[layer] if layer is not None else selected.X
    if matrix is None:
        raise ValueError('Selected expression matrix is absent')
    from scipy import sparse
    values = matrix.data if sparse.issparse(matrix) else np.asarray(matrix)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError('This expression overview requires finite nonnegative values; select an appropriate raw matrix or layer')
    # Isolate native Scanpy's category/palette bookkeeping without copying the full assay.
    plot_data = AnnData(X=matrix.copy(), obs=pd.DataFrame({groupby: groups.copy()}),
                       var=pd.DataFrame(index=markers), obsm={key: coords.copy()})
    return plot_data, key


def cell_overview(adata, markers, *, groupby, basis='X_umap', use_raw=None, layer=None,
                  palette=None, labels=None, size_mm=None, title=None, subtitle=None,
                  expression_label='Mean expression', expression_cutoff=0, vmin=None, vmax=None,
                  point_size=4, alpha=.85, output=None, recipe=None):
    """Draw the selected two-panel layout; never compute an embedding or change input data.

    Native Scanpy DotPlot supplies group means and fractions above expression_cutoff.
    use_raw=None follows Scanpy: raw when available, unless a layer was supplied.
    The output is a normal Matplotlib Figure. Source normalization is not inferred.
    """
    destination = _destination(output)
    _validate_recipe(recipe, verify=False)
    sc = _require_scanpy()
    data, key = _plot_data(adata, markers, groupby, basis, use_raw, layer)
    markers = list(data.var_names)
    categories = list(data.obs[groupby].cat.categories)
    if labels is not None and not isinstance(labels, Mapping):
        raise TypeError('labels must map category IDs to display names')
    names = [str(category) if labels is None else labels.get(category, str(category)) for category in categories]
    if any(not isinstance(name, str) or not name.strip() for name in names):
        raise ValueError('Display labels must be nonempty strings')
    for name, value in [('expression_cutoff', expression_cutoff), ('point_size', point_size), ('alpha', alpha)]:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f'{name} must be finite')
    if point_size <= 0 or not 0 < alpha <= 1:
        raise ValueError('point_size must be positive and alpha must be in (0, 1]')
    for name in ('title', 'subtitle'):
        if locals()[name] is not None and not isinstance(locals()[name], str):
            raise ValueError(f'{name} must be a string')
    if not isinstance(expression_label, str) or not expression_label.strip():
        raise ValueError('expression_label must be a nonempty string')
    if palette is None and f'{groupby}_colors' in adata.uns:
        source_categories = list(adata.obs[groupby].cat.categories) if isinstance(adata.obs[groupby].dtype, pd.CategoricalDtype) else list(pd.unique(adata.obs[groupby]))
        stored = adata.uns[f'{groupby}_colors']
        if len(stored) != len(source_categories):
            raise ValueError('Stored colors do not match category levels; supply an explicit palette')
        palette = dict(zip(source_categories, stored))
    if palette is not None:
        if isinstance(palette, Mapping):
            if any(category not in palette for category in categories):
                raise ValueError('Palette must include every observed identity')
            palette = {category: palette[category] for category in categories}
        else:
            palette = list(palette)
            if len(palette) != len(categories):
                raise ValueError('Palette length must match observed identities')
            palette = dict(zip(categories, palette))
        for color in palette.values():
            to_rgba(color)
    if size_mm is not None and (not isinstance(size_mm, Sequence) or len(size_mm) != 2):
        raise ValueError('size_mm must contain two positive finite numbers')
    width, height = (183 + 6 * max(0, len(markers)-12), 115 + 5 * max(0, len(categories)-8)) if size_mm is None else size_mm
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0 for v in (width, height)):
        raise ValueError('size_mm must contain two positive finite numbers')
    table = sc.pl.DotPlot(data, markers, groupby, use_raw=False, categories_order=categories,
                         expression_cutoff=expression_cutoff)
    means = table.dot_color_df.loc[categories, markers]
    fractions = table.dot_size_df.loc[categories, markers]
    low = 0 if vmin is None else vmin
    observed_max = float(means.to_numpy().max())
    high = (observed_max if observed_max > 0 else 1.0) if vmax is None else vmax
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in (low, high)) or high <= low:
        raise ValueError('vmin/vmax must be finite with vmax greater than vmin')
    with theme_context('manuscript'), mpl.rc_context({'font.family': 'DejaVu Sans'}):
        label_width = max(TextPath((0, 0), name, prop=FontProperties(size=7)).get_extents().width for name in names) * 25.4 / 72
        left = max(.56, .34 + label_width / width + .035)
        if .965 - left < .20:
            raise ValueError('Requested width leaves too little marker space beside the full labels; increase size_mm')
        fig = plt.figure(figsize=(width/25.4, height/25.4))
        try:
            if title:
                fig.text(.05, .95, title, fontsize=12, weight='bold')
            if subtitle:
                fig.text(.24 if title else .05, .95, subtitle, fontsize=8, color='#555555')
            map_ax = fig.add_axes([.055, .28, .285, .53], label='cellstyle.embedding')
            sc.pl.embedding(data, basis=key, color=groupby, palette=palette, ax=map_ax,
                            show=False, title='', size=point_size, alpha=alpha,
                            frameon=False, legend_loc=None)
            map_ax.set_aspect('equal', adjustable='box')
            fig.text(.055, .87, 'A', weight='bold', fontsize=10)
            fig.text(.085, .87, 'Cell map', fontsize=9)
            fig.canvas.draw()
            texts = []
            for category, name in zip(categories, names):
                points = data.obsm[key][np.asarray(data.obs[groupby] == category)]
                x, y = np.median(points, axis=0)
                texts.append(map_ax.text(x, y, name, fontsize=7, color='#202020', ha='center',
                    bbox={'facecolor': 'white', 'edgecolor': 'none', 'alpha': .9, 'pad': .8}))
            random_state = np.random.get_state()
            try:
                np.random.seed(0)
                adjust_text(texts, ax=map_ax, expand=(1.08, 1.2), force_text=(.3, .5),
                            arrowprops={'arrowstyle': '-', 'color': '#555555', 'lw': .5},
                            ensure_inside_axes=False, iter_lim=200)
            finally:
                np.random.set_state(random_state)
            matrix_ax = fig.add_axes([left, .32, .965-left, .51], label='cellstyle.markers')
            row, col = np.indices(means.shape)
            dots = matrix_ax.scatter(col.ravel(), row.ravel(), s=fractions.to_numpy().ravel()*55,
                c=means.to_numpy().ravel(), cmap='Blues', vmin=low, vmax=high, linewidths=.2, edgecolors='#555555')
            matrix_ax.set(xlim=(-.6,len(markers)-.4), ylim=(len(categories)-.5,-.5),
                          xticks=range(len(markers)), xticklabels=markers,
                          yticks=range(len(categories)), yticklabels=names)
            matrix_ax.tick_params(length=0, pad=5, labelsize=7)
            plt.setp(matrix_ax.get_xticklabels(), rotation=55, ha='right', rotation_mode='anchor')
            for spine in matrix_ax.spines.values():
                spine.set_visible(False)
            fig.text(.39, .87, 'B', weight='bold', fontsize=10)
            fig.text(.42, .87, 'Marker expression', fontsize=9)
            cax = fig.add_axes([.70, .105, .25, .022], label='cellstyle.expression')
            fig.colorbar(dots, cax=cax, orientation='horizontal', ticks=[low, (low+high)/2, high])
            cax.tick_params(labelsize=6, length=2)
            cax.set_title(expression_label, fontsize=7, loc='left', pad=5)
            guide = fig.add_axes([.40, .085, .25, .07], label='cellstyle.fraction')
            guide.set_axis_off()
            guide.set(xlim=(0,5),ylim=(0,1))
            for i, fraction in enumerate((.25,.5,.75,1)):
                guide.scatter(i+.5,.55,s=fraction*55,color='#555555')
                guide.text(i+.5,0,str(int(fraction*100)),ha='center',va='top',fontsize=6)
            fig.text(.40,.15,f'Cells with expression > {expression_cutoff:g} (%)',fontsize=7)
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()
            boxes = [text.get_window_extent(renderer) for text in texts]
            other = [text.get_window_extent(renderer) for text in matrix_ax.get_yticklabels()]
            if _overlap(boxes) or any(box.overlaps(b) for box in boxes for b in other):
                warnings.warn('Overview labels still overlap; inspect the figure or increase size_mm.', UserWarning, stacklevel=2)
            if destination is not None:
                _save_figure(fig, destination, recipe=recipe)
            return fig
        except Exception:
            plt.close(fig)
            raise
