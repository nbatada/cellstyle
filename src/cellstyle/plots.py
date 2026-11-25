from numbers import Number
from contextlib import nullcontext
from collections.abc import Mapping

import numpy as np, pandas as pd, seaborn as sns, matplotlib.pyplot as plt

from .styling import style_plot, _destination, _save_figure
from .theme import theme_context, _active_mode
from .colors import editorial_vivid
from .provenance import _validate_recipe


def _category_order(data, x, order):
    if order is not None:
        categories = list(order)
        levels = pd.Index(categories)
        if not categories or levels.isna().any() or not levels.is_unique:
            raise ValueError("order must contain unique, nonmissing levels")
        missing = list(pd.Index(data[x].unique()).difference(levels))
        if missing:
            raise ValueError(f"order would hide observed {x} values: {missing}")
        return categories

    values = data[x]
    if isinstance(values.dtype, pd.CategoricalDtype):
        return list(values.cat.categories)

    categories = list(values.dropna().unique())
    if pd.api.types.is_numeric_dtype(values) or all(
        isinstance(value, (Number, np.bool_)) for value in categories
    ):
        return list(np.sort(categories))
    return categories


def replicate_distribution(data, x, y, order=None, palette=None, ax=None, alpha=1, point_size=3.0, output=None, *, recipe=None):
    _validate_recipe(recipe, verify=False)
    destination = _destination(output)
    if not isinstance(data, pd.DataFrame) or x not in data or y not in data:
        raise ValueError("data must be a DataFrame containing the requested x and y columns")
    if data.empty:
        raise ValueError("Distribution data must contain at least one observation")
    if data[[x, y]].isna().any().any():
        raise ValueError("Distribution plots require complete group and measurement values")
    if not pd.api.types.is_numeric_dtype(data[y]) or not np.isfinite(data[y].to_numpy(dtype=float)).all():
        raise ValueError(f"{y!r} must contain only finite numeric observations")
    cats = _category_order(data, x, order)
    if palette is None:
        palette = dict(zip(cats, editorial_vivid(len(cats))))
    if isinstance(palette, Mapping):
        palette = dict(palette)
        missing = [category for category in cats if category not in palette]
        if missing:
            raise ValueError(f"Palette missing identities: {missing}")
    owned = ax is None
    mode = _active_mode.get() or "manuscript"
    with theme_context(mode) if owned else nullcontext():
        if owned:
            _, ax = plt.subplots()
        sns.swarmplot(data=data, x=x, y=y, order=cats, hue=x, hue_order=cats, palette=palette,
                      legend=False, size=point_size, alpha=alpha, linewidth=0, ax=ax)
        for category, label in zip(cats, pd.Index(cats).astype(str)):
            values = data.loc[data[x] == category, y].to_numpy(dtype=float)
            if len(values):
                position = ax.convert_xunits(label)
                q1, median, q3 = np.quantile(values, (.25, .5, .75))
                ax.vlines(position, q1, q3, color="#202020", lw=1.6, zorder=10)
                ax.scatter(position, median, s=36, facecolor="white", edgecolor="#202020", lw=1.1, zorder=11)
    if owned and mode == "manuscript":
        style_plot(ax, size_mm=(max(90, 90 + 15 * (len(cats) - 3)), 60), output=destination, recipe=recipe)
    elif destination is not None:
        _save_figure(ax.figure, destination, recipe=recipe)
    return ax
def quantitative_scatter(x,y,ax=None,color="#1764AB",alpha=1,size=20,fit=False,output=None,*,recipe=None):
    _validate_recipe(recipe, verify=False)
    destination = _destination(output)
    x_name = x.name if isinstance(x, pd.Series) and x.name is not None else "x"
    y_name = y.name if isinstance(y, pd.Series) and y.name is not None else "y"
    if isinstance(x, pd.Series) and isinstance(y, pd.Series) and not x.index.equals(y.index):
        raise ValueError("x and y Series must have identical indexes to preserve paired observations")
    try:
        x_values = np.asarray(x, dtype=float)
        y_values = np.asarray(y, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("x and y must contain finite numeric observations") from exc
    if x_values.ndim != 1 or y_values.ndim != 1 or not len(x_values) or len(x_values) != len(y_values):
        raise ValueError("x and y must be equally sized, nonempty one-dimensional vectors")
    if not np.isfinite(x_values).all() or not np.isfinite(y_values).all():
        raise ValueError("x and y must contain only finite observations")
    if fit and np.unique(x_values).size < 2:
        raise ValueError("A linear fit requires at least two distinct x values")
    owned = ax is None
    mode = _active_mode.get() or "manuscript"
    with theme_context(mode) if owned else nullcontext():
        if owned:
            _, ax = plt.subplots()
        ax.scatter(x_values, y_values, s=size, color=color, alpha=alpha, marker="o", edgecolors="#202020", lw=.35)
        if fit:
            coefficients = np.polyfit(x_values, y_values, 1)
            fit_x = np.linspace(x_values.min(), x_values.max(), 200)
            ax.plot(fit_x, np.polyval(coefficients, fit_x), color="#222222", lw=1.2)
        if owned:
            ax.set_xlabel(x_name)
            ax.set_ylabel(y_name)
    if owned and mode == "manuscript":
        style_plot(ax, size_mm=(90, 48), output=destination, recipe=recipe)
    elif destination is not None:
        _save_figure(ax.figure, destination, recipe=recipe)
    return ax
