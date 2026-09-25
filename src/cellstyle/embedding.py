from __future__ import annotations

from collections.abc import Mapping, Sequence
import numpy as np
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


def _ordered_categories(adata, groupby: str, order: Sequence[str] | None):
    if order is not None:
        return list(order)
    series = adata.obs[groupby]
    if hasattr(series.dtype, "categories"):
        return list(series.cat.categories)
    return list(dict.fromkeys(series.astype(str).tolist()))


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
    """Render a categorical embedding using native Scanpy + CellStyle semantics."""
    sc = _require_scanpy()
    order = _ordered_categories(adata, groupby, order)

    if palette is None:
        colors = editorial_vivid(len(order))
        palette_map = dict(zip(order, colors))
    elif isinstance(palette, Mapping):
        palette_map = dict(palette)
        colors = [palette_map[x] for x in order]
    else:
        colors = list(palette)
        if len(colors) != len(order):
            raise ValueError("Palette length must match category order.")
        palette_map = dict(zip(order, colors))

    sc.pl.embedding(
        adata,
        basis=basis,
        color=groupby,
        palette=colors,
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

    if label:
        coords = np.asarray(adata.obsm[basis])
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
    """Render selected categories over faint neutral embedding context."""
    import matplotlib.pyplot as plt

    if basis not in adata.obsm:
        raise KeyError(f"Embedding {basis!r} not found in adata.obsm.")
    if groupby not in adata.obs:
        raise KeyError(f"Annotation {groupby!r} not found in adata.obs.")
    if ax is None:
        _, ax = plt.subplots()

    focus = list(focus)
    if palette is None:
        colors = editorial_vivid(len(focus))
        palette_map = dict(zip(focus, colors))
    elif isinstance(palette, Mapping):
        palette_map = dict(palette)
    else:
        colors = list(palette)
        if len(colors) != len(focus):
            raise ValueError("Palette length must match focus categories.")
        palette_map = dict(zip(focus, colors))

    coords = np.asarray(adata.obsm[basis])
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
    if label and repel and texts:
        repel_labels(texts, ax)
    return ax
