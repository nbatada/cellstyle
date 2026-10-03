from __future__ import annotations

from collections.abc import Mapping, Sequence
import numpy as np
import pandas as pd
from matplotlib.colors import is_color_like
from .colors import editorial_vivid, context_color
from .labels import repel_labels


def _require_scanpy():
    try:
        import scanpy as sc
    except ImportError as exc:
        raise ImportError(
            "CellStyle embedding helpers require Scanpy. "
            "Install with: pip install 'cellstyle[scanpy]'"
        ) from exc
    return sc


def _display(label: str, labels: Mapping[str, str] | None) -> str:
    return labels.get(label, str(label)) if labels is not None else str(label)


def _embedding_coordinates(adata, basis, groupby):
    if groupby not in adata.obs:
        raise KeyError(f"Annotation {groupby!r} not found in adata.obs.")
    key = basis if basis in adata.obsm else f"X_{basis}"
    if key not in adata.obsm:
        raise KeyError(f"Embedding {basis!r} not found in adata.obsm.")
    coords = np.asarray(adata.obsm[key])
    if coords.ndim != 2 or coords.shape[0] != len(adata.obs) or coords.shape[1] < 2:
        raise ValueError("Embedding must have one row per observation and at least two dimensions.")
    if not np.issubdtype(coords.dtype, np.number) or not np.isfinite(coords[:, :2]).all():
        raise ValueError("Embedding coordinates must be finite numbers.")
    return key, coords


def _categories(adata, groupby):
    series = adata.obs[groupby]
    values = list(series.cat.categories) if isinstance(series.dtype, pd.CategoricalDtype) else list(series.dropna().unique())
    if any(not isinstance(x, str) for x in values):
        raise ValueError("Embedding categories must be string identities.")
    return values


def _validate_order(order, categories, *, complete=True):
    order = list(order)
    if any(not isinstance(x, str) for x in order) or len(set(order)) != len(order):
        raise ValueError("Category identities must be unique strings.")
    if not order or not set(order).issubset(categories):
        raise ValueError("Requested categories must exist in the annotation.")
    if complete and set(order) != set(categories):
        raise ValueError("Order must include every category; filter the data explicitly.")
    return order


def _palette_map(order, palette):
    if palette is None:
        result = dict(zip(order, editorial_vivid(len(order))))
    elif isinstance(palette, Mapping):
        if not set(order).issubset(palette):
            raise ValueError("Palette must supply a color for every requested category.")
        result = {x: palette[x] for x in order}
    else:
        colors = list(palette)
        if len(colors) != len(order):
            raise ValueError("Palette length must match category order.")
        result = dict(zip(order, colors))
    if not all(is_color_like(color) for color in result.values()):
        raise ValueError("Palette contains an invalid Matplotlib color.")
    return result


def _clean_embedding_axis(ax):
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)


def categorical_embedding(
    adata,
    *,
    basis: str,
    groupby: str,
    order: Sequence[str] | None = None,
    labels: Mapping[str, str] | None = None,
    palette: Mapping[str, str] | Sequence[str] | None = None,
    ax=None,
    size: float = 6.0,
    alpha: float = 0.86,
    label: bool = True,
    repel: bool = True,
    label_fontsize: float = 8.0,
    label_fontweight: str = "bold",
):
    """Render native Scanpy categories with equal coordinate scaling.

    Named palette mappings are stable across category/row reordering. Without
    an explicit order, colors are assigned in sorted identity order. A sequence
    palette follows the explicit order. Order is not a filtering mechanism.
    """
    key, coords = _embedding_coordinates(adata, basis, groupby)
    categories = _categories(adata, groupby)
    # Default assignment follows named identities, independent of row/category order.
    order = _validate_order(sorted(categories) if order is None else order, categories)
    palette_map = _palette_map(order, palette)
    sc = _require_scanpy()

    sc.pl.embedding(
        adata,
        basis=key,
        color=groupby,
        palette=palette_map,
        size=size,
        alpha=alpha,
        frameon=False,
        legend_loc=None if label else "right margin",
        title="",
        ax=ax,
        show=False,
    )

    if ax is None:
        import matplotlib.pyplot as plt
        ax = plt.gca()

    _clean_embedding_axis(ax)
    ax.set_aspect("equal", adjustable="box")

    if label:
        texts = []
        for category in order:
            mask = np.asarray(adata.obs[groupby].astype(str) == str(category))
            if not mask.any():
                continue
            texts.append(
                ax.text(
                    np.median(coords[mask, 0]),
                    np.median(coords[mask, 1]),
                    _display(category, labels),
                    color=palette_map[category],
                    fontsize=label_fontsize,
                    fontweight=label_fontweight,
                    ha="center",
                    va="center",
                    bbox=dict(facecolor="white", edgecolor="none", alpha=0.88, pad=1.0),
                )
            )
        if repel and texts:
            repel_labels(texts, ax)
    return ax


def focus_embedding(
    adata,
    *,
    basis: str,
    groupby: str,
    focus: Sequence[str],
    labels: Mapping[str, str] | None = None,
    palette: Mapping[str, str] | Sequence[str] | None = None,
    ax=None,
    focus_size: float = 6.0,
    focus_alpha: float = 0.86,
    context_size: float = 2.5,
    context_alpha: float = 0.28,
    context_colour: str | None = None,
    label: bool = True,
    repel: bool = True,
    label_fontsize: float = 8.0,
    label_fontweight: str = "bold",
):
    """Render selected categories over faint context with equal coordinate scaling.

    Context defaults to size 2.5, alpha 0.28; callers may explicitly increase
    visibility. A named palette preserves identity across focus reordering.
    """
    import matplotlib.pyplot as plt

    _, coords = _embedding_coordinates(adata, basis, groupby)
    focus = _validate_order(focus, _categories(adata, groupby), complete=False)
    palette_map = _palette_map(focus, palette)
    if context_colour is not None and not is_color_like(context_colour):
        raise ValueError("Invalid context color.")
    if ax is None:
        _, ax = plt.subplots()

    annotations = adata.obs[groupby].astype(str)
    context_mask = ~annotations.isin([str(x) for x in focus]).to_numpy()

    ax.scatter(
        coords[context_mask, 0], coords[context_mask, 1],
        s=context_size,
        color=context_colour or context_color(),
        alpha=context_alpha,
        linewidth=0,
        rasterized=True,
    )

    texts = []
    for category in focus:
        mask = np.asarray(annotations == str(category))
        if not mask.any():
            continue
        ax.scatter(
            coords[mask, 0], coords[mask, 1],
            s=focus_size,
            color=palette_map[category],
            alpha=focus_alpha,
            linewidth=0,
            rasterized=True,
        )
        if label:
            texts.append(
                ax.text(
                    np.median(coords[mask, 0]),
                    np.median(coords[mask, 1]),
                    _display(category, labels),
                    color=palette_map[category],
                    fontsize=label_fontsize,
                    fontweight=label_fontweight,
                    ha="center",
                    va="center",
                    bbox=dict(facecolor="white", edgecolor="none", alpha=0.88, pad=1.0),
                )
            )

    _clean_embedding_axis(ax)
    ax.set_aspect("equal", adjustable="box")
    if label and repel and texts:
        repel_labels(texts, ax)
    return ax
