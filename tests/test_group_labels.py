import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pytest
import cellstyle as cs


def test_aliases_observed_anchors_and_redraw(tmp_path):
    fig,ax=plt.subplots(figsize=(3,2))
    xs=[1,1,4,4,2]; ys=[1,2,4,5,3]
    groups=["Long identity A"]*2+["Long identity B"]*2+["C"]
    ax.scatter(xs,ys)
    artist=cs.label_groups(ax,xs,ys,groups,short_labels={"Long identity A":"T","Long identity B":"T"})
    for width in (3,5):
        fig.set_figwidth(width)
        fig.canvas.draw()
        assert len(artist.report)==3
        for r in artist.report:
            assert r["identity"]==r["label"]
            assert not r["outside_panel"]
            pts=np.array([(x,y) for x,y,g in zip(xs,ys,groups) if g==r["identity"]])
            assert np.any(np.isclose(pts,r["anchor"]).all(axis=1))
    fig.savefig(tmp_path/'map.pdf')
    with pytest.raises(ValueError,match="observed"):
        cs.label_groups(ax,xs,ys,groups,short_labels={"X":"A"})
    plt.close(fig)


def test_impossible_layout_is_reported_and_keeps_both_identities():
    fig,ax=plt.subplots(figsize=(.65,.65))
    ax.set(xlim=(0,1),ylim=(0,1))
    layer=cs.label_groups(ax,[.5,.51],[.5,.51],["A very long identity name","A second long identity name"])
    result=cs.check_plot(fig)
    assert len(layer.report)==2
    assert any(d["code"]=="GROUP_LABEL_FIT" for d in result["diagnostics"])
    plt.close(fig)


def test_adaptive_fits_alias_when_full_name_is_wider_than_panel():
    fig,ax=plt.subplots(figsize=(1.05,1.05))
    ax.set(xlim=(0,1),ylim=(0,1))
    full="A very long population name that exceeds the available drawing area"
    layer=cs.label_groups(ax,[.3,.31,.32],[.4,.41,.42],[full]*3,short_labels={full:"Pop A"})
    fig.canvas.draw()
    assert layer.report[0]["label"]=="Pop A"
    assert not layer.report[0]["outside_panel"]
    plt.close(fig)
