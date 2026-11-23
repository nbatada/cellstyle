"""Ordered point-and-interval displays of supplied estimates."""
from contextlib import nullcontext

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter, LogLocator

from .provenance import _validate_recipe
from .styling import _destination, _save_figure, style_plot
from .theme import theme_context


def forest(data, label, estimate, lower, upper, *, interval_label, reference=None,
           log_scale=False, ax=None, output=None, recipe=None):
    """Plot supplied intervals in table order. Name their definition explicitly.

    For example, use interval_label="95% CI", reference=1 and log_scale=True
    for ratios with supplied confidence limits. No estimate or interval is fitted.
    """
    _validate_recipe(recipe, verify=False)
    destination = _destination(output)
    if not isinstance(interval_label, str) or not interval_label.strip():
        raise ValueError("interval_label must name the supplied interval")
    if data.empty or data[label].isna().any() or data[label].astype(str).duplicated().any():
        raise ValueError("Supply one clearly identified row per estimate")
    fields = [estimate, lower, upper]
    if any(not pd.api.types.is_numeric_dtype(data[key]) for key in fields):
        raise ValueError("Estimates and bounds must be numeric")
    center, lo, hi = data[fields].to_numpy(dtype=float, na_value=np.nan).T
    if not np.isfinite([center, lo, hi]).all() or np.any(lo > hi):
        raise ValueError("Supply finite estimates and ordered bounds")
    if reference is not None and not np.isfinite(reference):
        raise ValueError("reference must be finite")
    if log_scale and (min(lo.min(), center.min()) <= 0 or (reference is not None and reference <= 0)):
        raise ValueError("A log scale requires positive values and reference")
    owned = ax is None
    set_y_axis = owned or (not ax.has_data() and getattr(ax.yaxis, "isDefault_majloc", False)
                           and getattr(ax.yaxis, "isDefault_majfmt", False))
    with theme_context("manuscript") if owned else nullcontext():
        if owned:
            _, ax = plt.subplots()
        y = np.arange(len(data))
        if reference is not None:
            ax.axvline(reference, color="#777777", linestyle="--", linewidth=.7, zorder=0)
        ax.hlines(y, lo, hi, color="#404040", linewidth=1)
        ax.scatter(center, y, s=20, color="#1764AB", zorder=3)
        if set_y_axis:
            ax.set_yticks(y, data[label].astype(str))
            ax.set_ylim(len(data) - .5, -.5)
        if log_scale:
            ax.set_xscale("log")
            decimal = FuncFormatter(lambda value, _: f"{value:.6g}")
            ax.xaxis.set_major_locator(LogLocator(base=10))
            ax.xaxis.set_major_formatter(decimal)
            ax.xaxis.set_minor_locator(LogLocator(base=10, subs=(2, 5, 7)))
            ax.xaxis.set_minor_formatter(decimal)
        ax.set_xlabel(f"{estimate} ({interval_label})")
        if owned:
            style_plot(ax, size_mm=(120, max(48, 22 + 5 * len(data))), output=destination, recipe=recipe)
        elif destination is not None:
            _save_figure(ax.figure, destination, recipe=recipe)
    return ax
