from __future__ import annotations

from collections.abc import Mapping, Sequence
import numpy as np
import pandas as pd
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
    return list(dict.fromkeys(series.tolist()))


def _clean_embedding_axis(ax):
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)


def _embedding_coordinates(adata, basis):
    key = basis if basis in adata.obsm else f"X_{basis}"
    if key not in adata.obsm:
        raise KeyError(f"Embedding {basis!r} not found in adata.obsm.")
    coordinates = np.asarray(adata.obsm[key], dtype=float)
    if coordinates.ndim != 2 or coordinates.shape[0] != len(adata.obs) or coordinates.shape[1] < 2:
        raise ValueError("Embedding must provide at least two coordinates for every observation")
    if not np.isfinite(coordinates[:, :2]).all():
        raise ValueError("Embedding coordinates must be finite")
    return coordinates


def _validate_order(adata, groupby, order):
    categories = _ordered_categories(adata, groupby, order)
    if not categories or pd.isna(pd.Index(categories)).any() or not pd.Index(categories).is_unique:
        raise ValueError("order must contain unique, nonmissing identities")
    observed = pd.Index(adata.obs[groupby].dropna().unique())
    missing = list(observed.difference(pd.Index(categories)))
    if missing:
        raise ValueError(f"order would hide observed {groupby} identities: {missing}")
    return categories


def _mapping_palette(palette, identities, name):
    palette_map = dict(palette)
    missing = [identity for identity in identities if identity not in palette_map]
    if missing:
        raise ValueError(f"{name} is missing identities: {missing}")
    return palette_map


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
    coords = _embedding_coordinates(adata, basis)
    order = _validate_order(adata, groupby, order)

    if palette is None:
        colors = editorial_vivid(len(order))
        palette_map = dict(zip(order, colors))
    elif isinstance(palette, Mapping):
        palette_map = _mapping_palette(palette, order, "palette")
        colors = [palette_map[x] for x in order]
    else:
        colors = list(palette)
        if len(colors) != len(order):
            raise ValueError("Palette length must match category order.")
        palette_map = dict(zip(order, colors))

    from anndata import AnnData
    key = basis if basis in adata.obsm else f"X_{basis}"
    plot_obs = adata.obs[[groupby]].copy()
    if not isinstance(plot_obs[groupby].dtype, pd.CategoricalDtype):
        plot_obs[groupby] = pd.Categorical(plot_obs[groupby], categories=order)
    plot_data = AnnData(X=np.empty((len(adata.obs), 0)), obs=plot_obs,
                        obsm={key: coords.copy()})
    sc.pl.embedding(
        plot_data,
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
    """Render selected categories over faint neutral embedding context."""
    import matplotlib.pyplot as plt

    if groupby not in adata.obs:
        raise KeyError(f"Annotation {groupby!r} not found in adata.obs.")
    coords = _embedding_coordinates(adata, basis)
    if ax is None:
        _, ax = plt.subplots()

    focus = list(focus)
    observed = list(dict.fromkeys(adata.obs[groupby].astype(str)))
    if not focus or len(set(focus)) != len(focus):
        raise ValueError("focus must contain unique observed identities")
    missing_focus = [identity for identity in focus if str(identity) not in observed]
    if missing_focus:
        raise ValueError(f"focus contains identities not present in {groupby!r}: {missing_focus}")
    if palette is None:
        colors = editorial_vivid(len(focus))
        palette_map = dict(zip(focus, colors))
    elif isinstance(palette, Mapping):
        palette_map = _mapping_palette(palette, focus, "palette")
    else:
        colors = list(palette)
        if len(colors) != len(focus):
            raise ValueError("Palette length must match focus categories.")
        palette_map = dict(zip(focus, colors))

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
