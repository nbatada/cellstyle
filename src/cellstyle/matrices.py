"""Native Matplotlib marker-summary and matrix plots.

These functions only render supplied summaries.  They do not aggregate AnnData,
select markers, infer identity, or choose an expression transformation.
"""
from __future__ import annotations

from contextlib import nullcontext
import textwrap
from collections.abc import Sequence
import warnings

import matplotlib.pyplot as plt
from matplotlib.colors import Colormap
from matplotlib.ticker import MaxNLocator
import numpy as np
import pandas as pd

from .colors import marker_heatmap_cmap, positive_cmap
from .provenance import _validate_recipe
from .styling import _destination, _save_figure, style_plot
from .theme import theme_context


def _table(value, name):
    if not isinstance(value, pd.DataFrame) or value.empty:
        raise TypeError(f"{name} must be a non-empty pandas DataFrame")
    if not value.index.is_unique or not value.columns.is_unique:
        raise ValueError(f"{name} index and columns must be unique")
    for axis_name, labels in (("index", value.index), ("columns", value.columns)):
        visible = []
        for label in labels:
            if pd.isna(label):
                raise ValueError(f"{name} {axis_name} labels must be non-missing and visibly unique")
            display = str(label)
            if not display.strip():
                raise ValueError(f"{name} {axis_name} labels must be non-missing and visibly unique")
            visible.append(display)
        if len(set(visible)) != len(visible):
            raise ValueError(f"{name} {axis_name} labels must remain visibly unique")
    if not all(pd.api.types.is_numeric_dtype(dtype) for dtype in value.dtypes):
        raise TypeError(f"{name} values must be numeric")
    return value


def _ordered(table, rows, columns):
    rows = list(table.index if rows is None else rows)
    columns = list(table.columns if columns is None else columns)
    if set(rows) != set(table.index) or len(rows) != len(table.index):
        raise ValueError("row_order must contain every table index exactly once")
    if set(columns) != set(table.columns) or len(columns) != len(table.columns):
        raise ValueError("column_order must contain every table column exactly once")
    return table.loc[rows, columns]


def _limits(values, vmin, vmax):
    if np.isinf(values).any():
        raise ValueError("matrix values must be finite or missing (NaN), not infinite")
    finite = values[np.isfinite(values)]
    if not len(finite):
        raise ValueError("matrix must contain at least one finite value")
    low = float(finite.min()) if vmin is None else float(vmin)
    high = float(finite.max()) if vmax is None else float(vmax)
    if not np.isfinite(low) or not np.isfinite(high) or high < low:
        raise ValueError("vmin and vmax must be finite with vmax >= vmin")
    if high == low:
        high = 1.0 if high == 0 else high + abs(high) * .05
    return low, high


def _label(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _reject_hidden_clipping(values, low, high, allow_clipping):
    outside = np.isfinite(values) & ((values < low) | (values > high))
    if outside.any():
        if not allow_clipping:
            raise ValueError("supplied limits would clip finite values; set allow_clipping=True to acknowledge it")
        warnings.warn("finite values are clipped by the supplied colour limits", UserWarning, stacklevel=3)


def _clean_matrix_axis(ax, table):
    ax.set(xticks=range(len(table.columns)), xticklabels=[str(x) for x in table.columns],
           yticks=range(len(table.index)), yticklabels=[str(x) for x in table.index],
           xlim=(-.6, len(table.columns) - .4), ylim=(len(table.index) - .5, -.5))
    ax.tick_params(length=0, pad=4)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    ax.spines[["top", "right"]].set_visible(False)


def _owned_dot_axes():
    figure = plt.figure(layout="constrained")
    grid = figure.add_gridspec(2, 2, height_ratios=(4, 1), width_ratios=(1, 1))
    return figure.add_subplot(grid[0, :]), figure.add_subplot(grid[1, 0]), figure.add_subplot(grid[1, 1])


def _dot_guides(size_ax, colour_ax, *, low, high, cmap, max_area, size_label, colour_label, unit):
    breaks = (.25, .5, .75, 1.)
    size_ax.set_axis_off()
    size_ax.set(xlim=(0, 5), ylim=(0, 1))
    for x, fraction in enumerate(breaks, start=1):
        size_ax.scatter(x, .48, s=max_area * fraction, color="#202020", linewidth=0)
        label = f"{fraction:.0%}" if unit == "percent" else f"{fraction:g}"
        size_ax.text(x + .21, .48, label, ha="left", va="center", fontsize=6)
    size_ax.set_title(size_label, fontsize=7, pad=1)
    gradient = np.linspace(low, high, 256).reshape(1, -1)
    colour_ax.imshow(gradient, aspect="auto", cmap=cmap, vmin=low, vmax=high,
                     extent=(low, high, 0, 1))
    colour_ax.set(yticks=[], xlabel="", title=colour_label)
    colour_ax.xaxis.set_major_locator(MaxNLocator(nbins=4))
    colour_ax.tick_params(axis="x", labelsize=6, length=2)
    colour_ax.spines[["top", "right", "left"]].set_visible(False)
    colour_ax.title.set_fontsize(7)


def dotplot(
    mean_expression: pd.DataFrame,
    fraction_positive: pd.DataFrame,
    *,
    colour_label: str,
    size_label: str,
    row_order: Sequence | None = None,
    column_order: Sequence | None = None,
    ax=None,
    cmap: str | Colormap | None = None,
    vmin: float = 0,
    vmax: float | None = None,
    max_area: float = 55,
    size_guide_unit: str = "fraction",
    allow_clipping: bool = False,
    output=None,
    recipe=None,
):
    """Draw supplied marker summaries; colour is mean_expression, area is fraction_positive.

    ``colour_label`` and ``size_label`` are required because CellStyle cannot
    infer a transform, cutoff, or biological meaning from summary tables.
    Finite zero is retained as zero area/intensity; an unavailable cell is shown
    as a gray x so it is not silently confused with zero.
    """
    _validate_recipe(recipe, verify=False)
    _label(colour_label, "colour_label")
    _label(size_label, "size_label")
    if size_guide_unit not in {"percent", "fraction"}:
        raise ValueError("size_guide_unit must be 'percent' or 'fraction'")
    means = _ordered(_table(mean_expression, "mean_expression"), row_order, column_order)
    fractions = _ordered(_table(fraction_positive, "fraction_positive"), row_order, column_order)
    if not means.index.equals(fractions.index) or not means.columns.equals(fractions.columns):
        raise ValueError("mean_expression and fraction_positive must have identical labels")
    fraction_values = fractions.to_numpy(dtype=float)
    if np.isinf(fraction_values).any():
        raise ValueError("fraction_positive values must be finite or missing (NaN), not infinite")
    if np.any(np.isfinite(fraction_values) & ((fraction_values < 0) | (fraction_values > 1))):
        raise ValueError("finite fraction_positive values must be between 0 and 1")
    if not np.isfinite(max_area) or max_area <= 0:
        raise ValueError("max_area must be a positive finite number")
    values = means.to_numpy(dtype=float)
    if np.any(np.isfinite(values) & (values < 0)):
        raise ValueError("mean_expression must be nonnegative for the sequential positive scale")
    low, high = _limits(values, vmin, vmax)
    if low < 0:
        raise ValueError("vmin must be nonnegative for the sequential positive scale")
    _reject_hidden_clipping(values, low, high, allow_clipping)
    owned = ax is None
    with theme_context("manuscript") if owned else nullcontext():
        if owned:
            ax, size_ax, colour_ax = _owned_dot_axes()
        row, col = np.indices(means.shape)
        valid = np.isfinite(values) & np.isfinite(fraction_values)
        dots = ax.scatter(col[valid], row[valid], s=max_area * fraction_values[valid], c=values[valid],
                          cmap=positive_cmap() if cmap is None else cmap, vmin=low, vmax=high,
                          edgecolor="none", linewidth=0)
        missing = ~valid
        if missing.any():
            ax.scatter(col[missing], row[missing], marker="x", s=18, c="#8c8c8c", linewidth=0.8,
                       label="missing")
        _clean_matrix_axis(ax, means)
        if owned:
            _dot_guides(size_ax, colour_ax, low=low, high=high, cmap=dots.cmap, max_area=max_area,
                        size_label=size_label, colour_label=colour_label, unit=size_guide_unit)
            if missing.any():
                size_ax.text(.5, -.16, "× = missing", transform=size_ax.transAxes, ha="center", fontsize=7)
        else:
            colourbar = ax.figure.colorbar(dots, ax=ax, orientation="horizontal", pad=.18)
            colourbar.ax.tick_params(labelsize=6, length=2)
            colourbar.set_label(colour_label, fontsize=7)
            handles = [plt.Line2D([], [], marker="o", linestyle="", color="#202020",
                                  markersize=np.sqrt(max_area * value) / 1.4, label=(f"{value:.0%}" if size_guide_unit == "percent" else f"{value:g}"))
                       for value in (.25, .5, .75, 1.)]
            ax.legend(handles=handles, title=size_label, loc="upper center", bbox_to_anchor=(.5, -.28),
                      ncol=4, frameon=False, fontsize=6, title_fontsize=7)
    destination = _destination(output)
    if owned:
        style_plot(ax, size_mm=(max(135, 72 + 6 * len(means.columns)), max(80, 42 + 5 * len(means.index))),
                 output=destination, recipe=recipe)
    elif destination is not None:
        _save_figure(ax.figure, destination, recipe=recipe)
    return ax


def heatmap(
    matrix: pd.DataFrame,
    *,
    scale_label: str,
    row_order: Sequence | None = None,
    column_order: Sequence | None = None,
    ax=None,
    cmap: str | Colormap | None = None,
    vmin: float | None = None,
    vmax: float | None = None,
    scale: str = "positive",
    allow_clipping: bool = False,
    output=None,
    recipe=None,
):
    """Draw a supplied marker matrix with an explicit semantic scale label.

    ``scale='positive'`` is the default for nonnegative expression and uses a
    sequential blue map. ``scale='marker'`` is for supplied centered marker
    scores: its symmetric limits place meaningful zero at the frozen near-black
    midpoint between blue negative and yellow positive signal. Missing values
    use neutral gray and finite zero remains a mapped value.
    """
    _validate_recipe(recipe, verify=False)
    _label(scale_label, "scale_label")
    table = _ordered(_table(matrix, "matrix"), row_order, column_order)
    values = table.to_numpy(dtype=float)
    if not np.isfinite(values).any():
        raise ValueError("matrix must contain at least one finite value")
    if scale not in {"positive", "marker"}:
        raise ValueError("scale must be 'positive' or 'marker'")
    if scale == "positive" and np.any(np.isfinite(values) & (values < 0)):
        raise ValueError("positive scale requires nonnegative finite values; use scale='marker' for centered scores")
    if scale == "marker":
        extent = float(np.abs(values[np.isfinite(values)]).max())
        if vmin is None and vmax is None:
            vmin, vmax = (-extent, extent) if extent else (-1.0, 1.0)
        elif vmin is None or vmax is None or float(vmin) >= 0 or float(vmax) <= 0 or not np.isclose(abs(float(vmin)), abs(float(vmax))):
            raise ValueError("marker scale limits must be symmetric around the meaningful zero midpoint")
    if scale == "positive" and vmin is None:
        vmin = 0
    low, high = _limits(values, vmin, vmax)
    if scale == "positive" and low < 0:
        raise ValueError("positive scale vmin must be nonnegative")
    _reject_hidden_clipping(values, low, high, allow_clipping)
    selected = (positive_cmap() if scale == "positive" else marker_heatmap_cmap()) if cmap is None else plt.get_cmap(cmap)
    selected = selected.with_extremes(bad="#d9d9d9")
    owned = ax is None
    with theme_context("manuscript") if owned else nullcontext():
        if owned:
            figure = plt.figure(layout="constrained")
            grid = figure.add_gridspec(3, 2, width_ratios=(4, 1), height_ratios=(1, 3, 1))
            ax, colour_ax = figure.add_subplot(grid[:, 0]), figure.add_subplot(grid[1, 1])
        image = ax.imshow(np.ma.masked_invalid(values), aspect="auto", cmap=selected, vmin=low, vmax=high)
        _clean_matrix_axis(ax, table)
        colourbar = ax.figure.colorbar(image, cax=colour_ax) if owned else ax.figure.colorbar(image, ax=ax, fraction=.045, pad=.025)
        colourbar.locator = MaxNLocator(nbins=4)
        colourbar.update_ticks()
        colourbar.ax.tick_params(labelsize=6, length=2)
        if owned:
            colourbar.ax.set_box_aspect(5)
            colourbar.ax.set_title(textwrap.fill(scale_label, width=14), fontsize=7, loc="center", pad=4)
        else:
            colourbar.set_label(scale_label, fontsize=7)
        if np.isnan(values).any():
            row, col = np.indices(values.shape)
            missing = np.isnan(values)
            ax.scatter(col[missing], row[missing], marker="x", s=18, c="#202020", linewidth=.8)
            ax.text(1.14, .02, "gray = missing", transform=ax.transAxes, fontsize=6)
    destination = _destination(output)
    if owned:
        style_plot(ax, size_mm=(max(95, 55 + 6 * len(table.columns)), max(60, 24 + 5 * len(table.index))),
                 output=destination, recipe=recipe)
    elif destination is not None:
        _save_figure(ax.figure, destination, recipe=recipe)
    return ax
