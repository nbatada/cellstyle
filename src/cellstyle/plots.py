from numbers import Number
from contextlib import nullcontext

import numpy as np, pandas as pd, seaborn as sns, matplotlib.pyplot as plt

from .styling import style_plot, _destination, _save_figure
from .theme import theme_context, _active_mode
from .colors import editorial_vivid


def _category_order(data, x, order):
    if order is not None:
        return list(order)

    values = data[x]
    if isinstance(values.dtype, pd.CategoricalDtype):
        return list(values.cat.categories)

    categories = list(values.dropna().unique())
    if pd.api.types.is_numeric_dtype(values) or all(
        isinstance(value, (Number, np.bool_)) for value in categories
    ):
        return list(np.sort(categories))
    return categories


def replicate_distribution(data, x, y, order=None, palette=None, ax=None, alpha=1, point_size=3.0, output=None):
    destination = _destination(output)
    cats=_category_order(data,x,order)
    if palette is None and len(cats) <= 5:
        palette = dict(zip(cats, editorial_vivid(len(cats))))
    owned = ax is None
    mode = _active_mode.get() or "manuscript"
    with theme_context(mode) if owned else nullcontext():
        if owned: _,ax=plt.subplots()
        sns.swarmplot(data=data,x=x,y=y,order=cats,hue=x,hue_order=cats,palette=palette,legend=False,size=point_size, alpha=alpha,linewidth=0,ax=ax)
        for i,c in enumerate(cats):
            v=data.loc[data[x]==c,y].dropna().to_numpy()
            if len(v):
                m=np.median(v); q1,q3=np.quantile(v,[.25,.75]); ax.vlines(i,q1,q3,color="#202020",lw=1.6,zorder=10); ax.scatter(i,m,s=36,facecolor="white",edgecolor="#202020",lw=1.1,zorder=11)
    if owned and mode == "manuscript":
        style_plot(ax, size_mm=(max(90, 90 + 15 * (len(cats) - 3)), 60), output=destination)
    elif destination is not None:
        _save_figure(ax.figure, destination)
    return ax
def quantitative_scatter(x,y,ax=None,color="#1764AB",alpha=1,size=20,fit=False,output=None):
    destination = _destination(output)
    x_name = x.name if isinstance(x, pd.Series) and x.name is not None else "x"
    y_name = y.name if isinstance(y, pd.Series) and y.name is not None else "y"
    owned = ax is None
    mode = _active_mode.get() or "manuscript"
    with theme_context(mode) if owned else nullcontext():
        if owned: _,ax=plt.subplots()
        x=np.asarray(x); y=np.asarray(y); ax.scatter(x,y,s=size,color=color,alpha=alpha,marker="o",edgecolors="#202020",lw=.35)
        if fit:
            ok=np.isfinite(x)&np.isfinite(y); c=np.polyfit(x[ok],y[ok],1); xx=np.linspace(x[ok].min(),x[ok].max(),200); ax.plot(xx,np.polyval(c,xx),color="#222222",lw=1.2)
        if owned:
            ax.set_xlabel(x_name)
            ax.set_ylabel(y_name)
    if owned and mode == "manuscript":
        style_plot(ax, size_mm=(90, 48), output=destination)
    elif destination is not None:
        _save_figure(ax.figure, destination)
    return ax
