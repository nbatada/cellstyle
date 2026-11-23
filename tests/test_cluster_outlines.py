from types import SimpleNamespace
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
import cellstyle as cs


def islands():
    rng = np.random.default_rng(17)
    a = np.vstack([rng.normal((0,0),.18,(35,2)),rng.normal((3,0),.18,(22,2)),
                   rng.normal((1.5,1),.2,(40,2))])
    return pd.DataFrame({"a":a[:,0],"b":a[:,1],"id":["4"]*57+["9"]*40})


def test_two_islands_selection_and_native_reuse():
    d=islands()
    all_paths=cs.cluster_outlines(d,"a","b","id")
    one=cs.cluster_outlines(d,"a","b","id",clusters="4")
    assert one.path.nunique()==2
    pd.testing.assert_frame_equal(one,all_paths.loc[all_paths.cluster=="4"].reset_index(drop=True))
    for _,ring in one.groupby("path"):
        np.testing.assert_allclose(ring.iloc[0][["x","y"]].astype(float),ring.iloc[-1][["x","y"]].astype(float))
    fig,ax=plt.subplots()
    cells=ax.scatter(d.a,d.b,c=np.arange(len(d)))
    lim=ax.get_xlim(),ax.get_ylim()
    orig=cells.get_array().copy()
    adata=SimpleNamespace(obs=d,obsm={"X_umap":d[["a","b"]].to_numpy()})
    live=cs.pl.cluster_outline(ax,adata,groupby="id",clusters="4")
    frozen=cs.cluster_outline(ax,paths=all_paths,clusters=["4"])
    assert len(live.get_segments())==len(frozen.get_segments())==2
    for a,b in zip(live.get_segments(),frozen.get_segments()): np.testing.assert_allclose(a,b)
    assert lim==(ax.get_xlim(),ax.get_ylim())
    np.testing.assert_equal(orig,cells.get_array())
    plt.close(fig)


def test_unknown_id_and_insufficient_geometry():
    d=islands()
    with pytest.raises(ValueError,match="Unknown"):
        cs.cluster_outlines(d,"a","b","id",clusters="1")
    d.loc[len(d)]=[0,0,"tiny"]
    with pytest.warns(UserWarning,match="insufficient"):
        paths=cs.cluster_outlines(d,"a","b","id",clusters="tiny")
    assert paths.empty


def test_concave_footprint_can_leave_an_empty_center():
    theta = np.linspace(0,2*np.pi,120,endpoint=False)
    frame = pd.DataFrame({"x":np.cos(theta),"y":np.sin(theta),"id":"ring"})
    result=cs.cluster_outlines(frame,"x","y","id")
    assert result.path.nunique()==2
    from matplotlib.path import Path
    center_membership = [Path(r[["x","y"]]).contains_point((0,0)) for _,r in result.groupby("path")]
    assert sum(center_membership)==2  # even-odd fill leaves the center outside the footprint


def test_territory_competes_with_neighbors_even_for_one_selected_cluster():
    d=islands()
    d.loc[d.id=="9","b"]-=.8
    # Move the neighboring group onto the edge of the first cloud.
    d.loc[d.id=="9","a"]-=1.15
    all_paths=cs.cluster_outlines(d,"a","b","id",method="territory")
    focus=cs.cluster_outlines(d,"a","b","id",method="territory",clusters="4")
    pd.testing.assert_frame_equal(focus,all_paths[all_paths.cluster=="4"].reset_index(drop=True))
    from matplotlib.path import Path
    xy=d[["a","b"]].values
    inside=[]
    for _,rings in all_paths.groupby("cluster"):
        inside.append(np.logical_xor.reduce([Path(r[["x","y"]]).contains_points(xy) for _,r in rings.groupby("path")]))
    assert len(inside)==2 and all(a.any() for a in inside)
    assert not (inside[0]&inside[1]).any()
