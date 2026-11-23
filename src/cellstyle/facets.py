"""Small multiples of comparable measurements on shared axes."""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .plots import _category_order, quantitative_scatter, replicate_distribution
from .provenance import _validate_recipe
from .styling import _destination, style_plot
from .theme import theme_context
from .shapes import _readable_linear_ticks


def facet(data, x, y, *, row=None, col=None, kind="swarm", palette=None, output=None, recipe=None):
    """Return a Figure of shared-scale scatter or swarm panels, retaining empty design cells.

    Specify at least one facet column. Categorical levels control panel order and
    unused levels. Each n counts supplied rows with finite measurements.
    """
    _validate_recipe(recipe, verify=False)
    destination = _destination(output)
    if row is None and col is None:
        raise ValueError("Supply row or col for the facet design")
    roles = [name for name in (x, y, row, col) if name is not None]
    if len(set(roles)) != len(roles) or kind not in ("swarm", "scatter"):
        raise ValueError("Use distinct columns and kind='swarm' or 'scatter'")
    if data.empty or data[roles].isna().any().any():
        raise ValueError("Supply observations with complete measurements and facet assignments")
    for name in ([x, y] if kind == "scatter" else [y]):
        if not pd.api.types.is_numeric_dtype(data[name]) or not np.isfinite(data[name].to_numpy(dtype=float)).all():
            raise ValueError(f"{name} must contain finite numeric measurements")
    rows = _category_order(data, row, None) if row is not None else [None]
    cols = _category_order(data, col, None) if col is not None else [None]
    groups = _category_order(data, x, None) if kind == "swarm" else []
    with theme_context("manuscript"):
        fig, axes = plt.subplots(len(rows), len(cols), sharex=True, sharey=True,
                                 squeeze=False, layout="constrained")
        for i, r in enumerate(rows):
            for j, c in enumerate(cols):
                subset = data
                if row is not None:
                    subset = subset.loc[subset[row] == r]
                if col is not None:
                    subset = subset.loc[subset[col] == c]
                ax = axes[i, j]
                if subset.empty:
                    ax.text(.5, .5, "No observations", ha="center", transform=ax.transAxes)
                elif kind == "scatter":
                    quantitative_scatter(subset[x], subset[y], ax=ax)
                else:
                    replicate_distribution(subset, x, y, order=groups, palette=palette, ax=ax)
                ax.set(xlabel="", ylabel="")
                ax.set_yticks(_readable_linear_ticks(data[y]))
                ax.annotate(f"n = {len(subset)}", (.02, .98), xycoords="axes fraction",
                            fontsize=6, color="#555555", va="top")
                if i == 0 and col is not None:
                    ax.set_title(str(c), pad=10, bbox={"facecolor": "#F5F5F5", "edgecolor": "none", "pad": 3})
                if j == len(cols) - 1 and row is not None:
                    ax.annotate(str(r), (1.02, .5), xycoords="axes fraction",
                                va="center", rotation=90, fontsize=8,
                                bbox={"facecolor": "#F5F5F5", "edgecolor": "none", "pad": 3})
        if kind == "swarm":
            axes[0, 0].set_xlim(-.5, len(groups) - .5)
        fig.supxlabel(str(x), fontsize=8)
        fig.supylabel(str(y), fontsize=8)
        style_plot(fig, size_mm=(max(90, 45 * len(cols) + 35), max(60, 35 * len(rows) + 25)),
                   output=destination, recipe=recipe)
    return fig
