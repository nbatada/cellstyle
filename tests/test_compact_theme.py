import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import to_rgba

from cellstyle.plots import quantitative_scatter, replicate_distribution
from cellstyle.theme import theme_context


def test_manuscript_roles_and_context_restoration():
    keys = ("axes.labelsize", "xtick.labelsize", "legend.fontsize", "legend.title_fontsize", "axes.titlesize", "axes.linewidth", "xtick.major.width", "axes.grid")
    before = {key: mpl.rcParams[key] for key in keys}
    with theme_context("manuscript"):
        assert mpl.rcParams["axes.labelsize"] == 8
        assert mpl.rcParams["xtick.labelsize"] == 7
        assert mpl.rcParams["legend.fontsize"] == 7.5
        assert mpl.rcParams["legend.title_fontsize"] == 7.5
        assert mpl.rcParams["axes.titlesize"] == 9
        assert mpl.rcParams["axes.linewidth"] == .7
        assert mpl.rcParams["xtick.major.width"] == .7
        assert mpl.rcParams["axes.grid"] is False
    assert {key: mpl.rcParams[key] for key in keys} == before


def test_sparse_scatter_defaults_and_overrides():
    with mpl.rc_context({"scatter.marker": "."}):
        ax = quantitative_scatter([1, 2], [2, 3])
    dots = ax.collections[0]
    assert np.ptp(dots.get_paths()[0].vertices[:, 0]) == 1
    assert dots.get_sizes()[0] == 20
    assert dots.get_facecolors()[0, 3] == 1
    assert dots.get_linewidths()[0] == .35
    assert tuple(dots.get_edgecolors()[0]) == to_rgba("#202020")
    plt.close(ax.figure)
    ax = quantitative_scatter([1], [2], color="red", alpha=.3, size=42)
    dots = ax.collections[0]
    assert dots.get_sizes()[0] == 42
    assert dots.get_facecolors()[0, 3] == .3
    plt.close(ax.figure)


def test_replicate_points_opaque_and_data_preserved():
    data = pd.DataFrame({"group": ["A", "A", "B"], "value": [1, 2, 3]})
    ax = replicate_distribution(data, "group", "value")
    assert len(ax.collections[0].get_offsets()) == 2
    assert ax.collections[0].get_facecolors()[0, 3] == 1
    assert data["value"].tolist() == [1, 2, 3]
    plt.close(ax.figure)
    ax = replicate_distribution(data, "group", "value", alpha=.4)
    assert ax.collections[0].get_facecolors()[0, 3] == .4
    plt.close(ax.figure)
