import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

anndata = pytest.importorskip("anndata")
pytest.importorskip("scanpy")

import cellstyle as cs


@pytest.fixture
def adata():
    obs = pd.DataFrame({"group": pd.Categorical(
        ["B", "A", "B", "A"], categories=["B", "A", "unused"], ordered=True
    )}, index=["c1", "c2", "c3", "c4"])
    var = pd.DataFrame(index=["G1", "G2"])
    data = anndata.AnnData(
        X=np.array([[2., 0.], [0., 4.], [4., 0.], [0., 0.]]),
        obs=obs, var=var,
    )
    data.obsm["X_umap"] = np.array([[0., 0.], [1., 0.], [0., 1.], [1., 1.]])
    data.uns["group_colors"] = ["#112233", "#445566", "#778899"]
    data.raw = data.copy()
    data.layers["alternate"] = np.full((4, 2), 3.)
    return data


def _axis(fig, name):
    return next(ax for ax in fig.axes if ax.get_label() == f"cellstyle.{name}")


def test_native_summary_order_and_caller_preservation(adata):
    before = adata.copy()
    fig = cs.pl.cell_overview(adata, ["G1", "G2"], groupby="group")
    try:
        embedding = _axis(fig, "embedding")
        markers = _axis(fig, "markers")
        _axis(fig, "expression")
        _axis(fig, "fraction")
        assert embedding.get_aspect() == 1
        assert sum(len(c.get_offsets()) for c in embedding.collections) == 4
        assert [tick.get_text() for tick in markers.get_yticklabels()] == ["B", "A"]
        dots = next(c for c in markers.collections if len(c.get_array()) == 4)
        np.testing.assert_allclose(np.asarray(dots.get_array()), [3., 0., 0., 2.])
        np.testing.assert_allclose(dots.get_sizes(), [55., 0., 0., 27.5])
        pd.testing.assert_frame_equal(adata.obs, before.obs)
        pd.testing.assert_frame_equal(adata.var, before.var)
        np.testing.assert_array_equal(adata.X, before.X)
        np.testing.assert_array_equal(adata.raw.X, before.raw.X)
        np.testing.assert_array_equal(adata.obsm["X_umap"], before.obsm["X_umap"])
        np.testing.assert_array_equal(adata.layers["alternate"], before.layers["alternate"])
        assert adata.uns == before.uns
    finally:
        plt.close(fig)


def test_layer_selection_and_raw_layer_conflict(adata):
    fig = cs.pl.cell_overview(adata, ["G1", "G2"], groupby="group", layer="alternate")
    try:
        dots = next(c for c in _axis(fig, "markers").collections if len(c.get_array()) == 4)
        np.testing.assert_allclose(np.asarray(dots.get_array()), 3.)
        np.testing.assert_allclose(dots.get_sizes(), 55.)
    finally:
        plt.close(fig)
    with pytest.raises(ValueError):
        cs.pl.cell_overview(adata, ["G1"], groupby="group", use_raw=True, layer="alternate")


def test_default_uses_raw_when_present(adata):
    adata.X[:] = 9
    fig = cs.pl.cell_overview(adata, ["G1", "G2"], groupby="group")
    try:
        dots = next(c for c in _axis(fig, "markers").collections if len(c.get_array()) == 4)
        np.testing.assert_allclose(np.asarray(dots.get_array()), [3., 0., 0., 2.])
    finally:
        plt.close(fig)


@pytest.mark.parametrize("change,markers", [
    (lambda a: a.obsm.pop("X_umap"), ["G1"]),
    (lambda a: a.obsm["X_umap"].__setitem__((0, 0), np.nan), ["G1"]),
    (lambda a: a.obs.__setitem__("group", ["A", None, "A", "B"]), ["G1"]),
    (lambda a: setattr(a, "var_names", ["G1", "G1"]), ["G1"]),
    (lambda a: setattr(a, "X", np.array([[np.nan, 0], [0, 4], [4, 0], [0, 0]])), ["G1"]),
    (lambda a: None, ["unknown"]),
])
def test_invalid_input_fails_before_plot(adata, change, markers):
    change(adata)
    before = set(plt.get_fignums())
    with pytest.raises((ValueError, KeyError)):
        cs.pl.cell_overview(adata, markers, groupby="group", use_raw=False)
    assert set(plt.get_fignums()) == before
