"""Native box and violin summaries with an observation layer."""
from contextlib import nullcontext
import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from .colors import editorial_vivid
from .plots import _category_order
from .provenance import _validate_recipe
from .styling import _destination, _save_figure, style_plot
from .theme import theme_context


def _readable_linear_ticks(values):
    """Return three-ish readable ticks inside the measured linear range."""
    values = np.asarray(values, dtype=float)
    lo, hi = values.min(), values.max()
    if lo == hi:
        padding = max(abs(lo), 1) * .05
        lo, hi = lo - padding, hi + padding
    target = (hi - lo) / 2
    unit = 10 ** math.floor(math.log10(target))
    step = max(candidate * unit for candidate in (1, 2, 2.5, 5, 10)
               if candidate * unit <= target)
    first = math.ceil(lo / step - 1e-9) * step
    last = math.floor(hi / step + 1e-9) * step
    return np.arange(first, last + step * .1, step)


def _observed_distribution(kind, data, x, y, hue, palette, ax, output, recipe):
    _validate_recipe(recipe, verify=False)
    destination = _destination(output)
    keys = [x] if hue is None else [x, hue]
    if len(set([*keys, y])) != len(keys) + 1:
        raise ValueError("Use distinct columns for groups, subgroups, and measurements")
    if data.empty or data[keys].isna().any().any():
        raise ValueError("Supply observations with identified groups")
    if not pd.api.types.is_numeric_dtype(data[y]) or not np.isfinite(data[y].to_numpy(dtype=float, na_value=np.nan)).all():
        raise ValueError("Supply a finite numeric measurement for each observation")

    color_by = x if hue is None else hue
    groups = _category_order(data, x, None)
    identities = _category_order(data, color_by, None)
    if palette is None:
        palette = dict(zip(identities, editorial_vivid(len(identities))))
    if any(key not in palette for key in identities):
        raise ValueError("palette must supply a color for every displayed identity")
    palette = dict(palette)
    owned = ax is None
    with theme_context("manuscript") if owned else nullcontext():
        if owned:
            _, ax = plt.subplots(layout="constrained")
        grouping = dict(data=data, x=x, y=y, order=groups, hue=color_by,
                        hue_order=identities, palette=palette, dodge=hue is not None, ax=ax)
        # Swarm dodging uses a categorical width of 0.8. Keep summary centers aligned.
        if kind == "box":
            # Keep Seaborn's .8 dodge centers while matching R's .65/n boxes.
            first = len(ax.patches)
            sns.boxplot(**grouping, width=.8 if hue is not None else .6,
                        gap=1 - .65 / .8 if hue is not None else 0,
                        saturation=1, linewidth=.4, showfliers=False,
                        legend=False)
            for patch in ax.patches[first:]:
                face = patch.get_facecolor()
                edge = patch.get_edgecolor()
                patch.set_facecolor((*face[:3], .25))
                patch.set_edgecolor((*edge[:3], 1))
        else:
            first = len(ax.collections)
            sns.violinplot(**grouping, width=.8 if hue is not None else .6,
                           gap=1 - .65 / .8 if hue is not None else 0, cut=0, inner=None,
                           density_norm="width", saturation=1, linewidth=.4, legend=False)
            for body in ax.collections[first:]:
                face = body.get_facecolor()[0]
                edge = body.get_edgecolor()[0]
                body.set_facecolor((*face[:3], .25))
                body.set_edgecolor((*edge[:3], 1))
        sns.swarmplot(**grouping, size=4.25, edgecolor="none", linewidth=0,
                      zorder=4, legend=hue is not None)
        if owned and hue is not None:
            ax.legend(title=hue, frameon=False, handlelength=1, handletextpad=.35,
                      loc="upper left", bbox_to_anchor=(1.02, 1), borderaxespad=0)
        if owned:
            ax.set_yticks(_readable_linear_ticks(data[y]))
            style_plot(ax, size_mm=(90, 60),
                       output=destination, recipe=recipe)
        elif destination is not None:
            _save_figure(ax.figure, destination, recipe=recipe)
    return ax


def boxplot(data, x, y, *, hue=None, palette=None, ax=None, output=None, recipe=None):
    """Draw median, quartiles and 1.5-IQR whiskers with every observation once.

    Supply one row per observation. Optional hue dodges subgroups at each x level.
    A named palette can extend the five default colors.
    """
    return _observed_distribution("box", data, x, y, hue, palette, ax, output, recipe)


def violin(data, x, y, *, hue=None, palette=None, ax=None, output=None, recipe=None):
    """Draw equal-width KDEs bounded to each observed range and raw points.

    Width describes distribution shape within a group. Constant or singleton
    groups retain their observations where a density cannot be estimated.
    """
    return _observed_distribution("violin", data, x, y, hue, palette, ax, output, recipe)
