from numbers import Number
import warnings

import numpy as np, pandas as pd, seaborn as sns, matplotlib.pyplot as plt


def _category_order(data, x, order):
    if order is not None:
        cats = list(order)
        if any(pd.isna(c) for c in cats) or len(set(cats)) != len(cats):
            raise ValueError("Order must contain unique nonmissing groups.")
        if not set(data[x].dropna().unique()).issubset(cats):
            raise ValueError("Order must include every observed group; filter data explicitly.")
        return cats

    values = data[x]
    if isinstance(values.dtype, pd.CategoricalDtype):
        return list(values.cat.categories)

    categories = list(values.dropna().unique())
    if pd.api.types.is_numeric_dtype(values) or all(
        isinstance(value, (Number, np.bool_)) for value in categories
    ):
        return list(np.sort(categories))
    return categories


def replicate_distribution(data, x, y, order=None, palette=None, ax=None, alpha=.60, point_size=3.0):
    cats=_category_order(data,x,order)
    missing = data[[x, y]].isna().any(axis=1)
    if missing.any():
        warnings.warn(f"Omitting {int(missing.sum())} rows with missing group or value.", UserWarning, stacklevel=2)
        data = data.loc[~missing]
    if ax is None: _,ax=plt.subplots()
    sns.swarmplot(data=data,x=x,y=y,order=cats,hue=x,hue_order=cats,palette=palette,legend=False,size=point_size, alpha=alpha,linewidth=0,ax=ax)
    for i,c in enumerate(cats):
        v=data.loc[data[x]==c,y].dropna().to_numpy()
        if len(v):
            m=np.median(v); q1,q3=np.quantile(v,[.25,.75]); ax.vlines(i,q1,q3,color="#202020",lw=1.6,zorder=10); ax.scatter(i,m,s=36,facecolor="white",edgecolor="#202020",lw=1.1,zorder=11)
    return ax
def quantitative_scatter(x,y,ax=None,color="#1764AB",alpha=.42,size=20,fit=False):
    x=np.asarray(x, dtype=float); y=np.asarray(y, dtype=float)
    if x.ndim != 1 or y.ndim != 1 or len(x) != len(y):
        raise ValueError("x and y must be one-dimensional arrays of equal length.")
    ok=np.isfinite(x)&np.isfinite(y)
    if fit and (ok.sum() < 2 or len(np.unique(x[ok])) < 2):
        raise ValueError("Fit requires at least two finite pairs with distinct x values.")
    if ax is None: _,ax=plt.subplots()
    ax.scatter(x,y,s=size,color=color,alpha=alpha,lw=0)
    if fit:
        c=np.polyfit(x[ok],y[ok],1); xx=np.linspace(x[ok].min(),x[ok].max(),200); ax.plot(xx,np.polyval(c,xx),color="#222222",lw=1.2)
    return ax
