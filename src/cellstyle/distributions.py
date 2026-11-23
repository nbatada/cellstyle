"""Native Matplotlib distribution helpers with explicit replicate semantics."""
from __future__ import annotations

from contextlib import nullcontext
import warnings
from collections.abc import Mapping

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from .colors import editorial_vivid
from .plots import _category_order
from .provenance import _validate_recipe
from .styling import _destination, _save_figure, style_plot
from .theme import theme_context
from .shapes import _readable_linear_ticks


def _require_columns(data, columns):
    missing = [column for column in columns if column not in data]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    if data.empty:
        raise ValueError("Distribution data must contain at least one observation")


def _valid_values(data, columns, y):
    if data.loc[:, columns].isna().any().any():
        raise ValueError(f"Missing values are not silently dropped in distribution plots: {columns}")
    if not pd.api.types.is_numeric_dtype(data[y]) or not np.isfinite(data[y]).all():
        raise ValueError(f"{y!r} must contain only finite numeric observations")


def _summary(ax, position, values):
    q1, median, q3 = np.quantile(values, (.25, .5, .75))
    ax.vlines(position, q1, q3, color="#202020", lw=1.1, zorder=10)
    ax.scatter(position, median, s=36, facecolor="white", edgecolor="#202020", lw=.9, zorder=11)


def _set_readable_linear_ticks(ax, values):
    """Use the same low-count, data-derived linear tick intent as the R backend."""
    ax.set_yticks(_readable_linear_ticks(values))


def _display_order(data, column, order):
    """Return every requested level, rejecting orders that would hide records."""
    if order is None:
        values = _category_order(data, column, None)
        if pd.api.types.is_datetime64_any_dtype(data[column]):
            return list(sorted(values))
        return values
    values = list(order)
    values_index = pd.Index(values)
    if not values or pd.isna(values_index).any() or not values_index.is_unique:
        raise ValueError("order must contain unique, nonmissing levels")
    missing = list(pd.Index(data[column].unique()).difference(pd.Index(values)))
    if missing:
        raise ValueError(f"order would hide observed {column} values: {missing}")
    return values


def paired(data, pair, x, y, order=None, ax=None, color="#1764AB", point_size=4.25,
           line_color="#999999", line_width=.35, output=None, *, recipe=None):
    """Draw matched observations with subtle adjacent lines and median/IQR.

    A pair may miss visits; its observed measurements remain visible and a line
    is drawn only between adjacent observed visits. Duplicate pair-by-visit
    measurements are rejected rather than guessed.
    """
    _validate_recipe(recipe, verify=False)
    _require_columns(data, (pair, x, y))
    _valid_values(data, (pair, x, y), y)
    categories = _display_order(data, x, order)
    if len(categories) < 2:
        raise ValueError("paired requires at least two displayed x levels")
    duplicate = data.groupby([pair, x], observed=True).size()
    duplicate = duplicate[duplicate > 1]
    if not duplicate.empty:
        raise ValueError("Duplicate pair and condition: " + repr(duplicate.index.tolist()))
    destination = _destination(output)
    owned = ax is None
    set_ticks = owned or (not ax.has_data() and getattr(ax.xaxis, "isDefault_majloc", False)
                          and getattr(ax.xaxis, "isDefault_majfmt", False))
    with theme_context("manuscript") if owned else nullcontext():
        if owned:
            _, ax = plt.subplots(layout="constrained")
        positions = np.arange(len(categories))
        slots = {category: position for position, category in enumerate(categories)}
        for _, sample in data.groupby(pair, sort=False, observed=True):
            sample = sample.assign(_slot=sample[x].map(slots)).sort_values("_slot")
            observed_slots = sample["_slot"].to_numpy()
            for left, right in zip(range(len(sample) - 1), range(1, len(sample))):
                if observed_slots[right] == observed_slots[left] + 1:
                    ax.plot(sample["_slot"].iloc[[left, right]], sample[y].iloc[[left, right]],
                            color=line_color, lw=line_width, zorder=1)
        for position, category in enumerate(categories):
            values = data.loc[data[x] == category, y].to_numpy()
            ax.scatter(np.full(len(values), position), values, s=point_size ** 2,
                       color=color, edgecolor="none", linewidth=0, zorder=3)
            _summary(ax, position, values)
        if set_ticks:
            ax.set(xticks=positions, xticklabels=categories, xlabel=x, ylabel=y)
        if owned:
            ax.set_xlim(-.5, len(categories) - .5)
            _set_readable_linear_ticks(ax, data[y])
    if owned:
        style_plot(ax, size_mm=(90, 60), output=destination, recipe=recipe)
    elif destination is not None:
        _save_figure(ax.figure, destination, recipe=recipe)
    return ax


def grouped_swarm(data, x, y, hue, order=None, hue_order=None, palette=None, ax=None,
                  alpha=1, point_size=4.25, output=None, *, recipe=None):
    """Draw a dodged true beeswarm with a median/IQR for every group combination.

    Empty x-by-hue combinations and unequal sample counts remain explicit:
    they receive no invented points or summaries, and issue a warning.
    """
    _validate_recipe(recipe, verify=False)
    _require_columns(data, (x, y, hue))
    _valid_values(data, (x, y, hue), y)
    x_order = _display_order(data, x, order)
    hue_order = _display_order(data, hue, hue_order)
    if not x_order or not hue_order:
        raise ValueError("grouped_swarm requires at least one x and hue level")
    observed = data.groupby([x, hue], observed=True).size()
    counts = {(str(x_level), str(hue_level)): int(observed.get((x_level, hue_level), 0))
              for x_level in x_order for hue_level in hue_order}
    empty = [key for key, count in counts.items() if count == 0]
    positive = [count for count in counts.values() if count]
    if empty or len(set(positive)) > 1:
        message = f"Observed x-by-hue sample counts are plotted unchanged: {counts}"
        if empty:
            message += f"; empty combinations receive no summary: {empty}"
        warnings.warn(message, UserWarning, stacklevel=2)
    if palette is None and len(hue_order) <= 5:
        palette = dict(zip(hue_order, editorial_vivid(len(hue_order))))
    if isinstance(palette, Mapping):
        missing_colors = [level for level in hue_order if level not in palette]
        if missing_colors:
            raise ValueError(f"Palette missing identities: {missing_colors}")
    destination = _destination(output)
    owned = ax is None
    with theme_context("manuscript") if owned else nullcontext():
        if owned:
            _, ax = plt.subplots(layout="constrained")
        sns.swarmplot(data=data, x=x, y=y, hue=hue, order=x_order, hue_order=hue_order,
                      palette=palette, dodge=True, size=point_size, alpha=alpha, linewidth=0,
                      edgecolor="none", ax=ax, zorder=3)
        offsets = [.8 * ((index + .5) / len(hue_order) - .5) for index in range(len(hue_order))]
        for x_index, x_level in enumerate(x_order):
            for offset, hue_level in zip(offsets, hue_order):
                values = data.loc[(data[x] == x_level) & (data[hue] == hue_level), y].to_numpy()
                if len(values):
                    _summary(ax, x_index + offset, values)
        if owned:
            ax.set(xlabel=x, ylabel=y)
            _set_readable_linear_ticks(ax, data[y])
            ax.legend(title=hue, frameon=False, handlelength=1, handletextpad=.35,
                      loc="upper left", bbox_to_anchor=(1.02, 1), borderaxespad=0)
    if owned:
        style_plot(ax, size_mm=(90, 60), output=destination, recipe=recipe)
    elif destination is not None:
        _save_figure(ax.figure, destination, recipe=recipe)
    return ax
