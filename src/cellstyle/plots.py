from numbers import Number

import numpy as np, pandas as pd, seaborn as sns, matplotlib.pyplot as plt


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


def replicate_distribution(data, x, y, order=None, palette=None, ax=None, alpha=.60, point_size=3.0):
    if ax is None: _,ax=plt.subplots()
    cats=_category_order(data,x,order)
    sns.swarmplot(data=data,x=x,y=y,order=cats,hue=x,hue_order=cats,palette=palette,legend=False,size=point_size, alpha=alpha,linewidth=0,ax=ax)
    for i,c in enumerate(cats):
        v=data.loc[data[x]==c,y].dropna().to_numpy()
        if len(v):
            m=np.median(v); q1,q3=np.quantile(v,[.25,.75]); ax.vlines(i,q1,q3,color="#202020",lw=1.6,zorder=10); ax.scatter(i,m,s=36,facecolor="white",edgecolor="#202020",lw=1.1,zorder=11)
    return ax
def quantitative_scatter(x,y,ax=None,color="#1764AB",alpha=.42,size=20,fit=False):
    if ax is None: _,ax=plt.subplots()
    x=np.asarray(x); y=np.asarray(y); ax.scatter(x,y,s=size,color=color,alpha=alpha,lw=0)
    if fit:
        ok=np.isfinite(x)&np.isfinite(y); c=np.polyfit(x[ok],y[ok],1); xx=np.linspace(x[ok].min(),x[ok].max(),200); ax.plot(xx,np.polyval(c,xx),color="#222222",lw=1.2)
    return ax
