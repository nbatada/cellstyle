import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PathCollection
import numpy as np
import pandas as pd
import pytest

from cellstyle import pl


@pytest.mark.parametrize("plot", [pl.boxplot, pl.violin])
def test_grouped_shapes_keep_every_observation_and_align(plot):
    data = pd.DataFrame({"site": ["A"] * 4 + ["B"] * 4,
                         "group": ["U", "U", "V", "V"] * 2, "value": range(8)})
    ax = plot(data, "site", "value", hue="group")
    ax.figure.canvas.draw()
    points = np.vstack([item.get_offsets() for item in ax.collections
                        if isinstance(item, PathCollection) and len(item.get_offsets())])
    np.testing.assert_array_equal(np.sort(points[:, 1]), data.value)
    np.testing.assert_allclose(points[:, 0], np.repeat([-.2, .2, .8, 1.2], 2), atol=.01)
    assert [s.get_text() for s in ax.get_legend().get_texts()] == ["U", "V"]
    assert ax.get_legend().get_bbox_to_anchor()._bbox.x0 > 1
    plt.close(ax.figure)


def test_shape_geometry_matches_r_reference_widths_and_light_outlines():
    data = pd.DataFrame({"group": ["A"] * 4 + ["B"] * 4, "value": range(8)})
    ax = pl.boxplot(data, "group", "value")
    # Seaborn box paths are retained in data coordinates before the axes transform.
    assert np.isclose(np.ptp(ax.patches[0].get_path().vertices[:, 0]), .6)
    assert np.isclose(ax.patches[0].get_facecolor()[-1], .25)
    assert np.isclose(ax.patches[0].get_edgecolor()[-1], 1)
    plt.close(ax.figure)
    ax = pl.violin(data, "group", "value")
    body = next(item for item in ax.collections if hasattr(item, "get_facecolor") and len(item.get_facecolor()))
    assert np.isclose(body.get_facecolor()[0, -1], .25)
    assert np.isclose(body.get_linewidths()[0], .4)
    assert np.isclose(body.get_edgecolor()[0, -1], 1)
    plt.close(ax.figure)


@pytest.mark.parametrize("values", [[1.3, 2.9, 8.8], [.013, .019, .027], [3., 3., 3.]])
def test_distribution_defaults_use_readable_low_count_data_derived_ticks(values):
    data = pd.DataFrame({"group": ["A"] * len(values), "value": values})
    ax = pl.boxplot(data, "group", "value")
    ax.figure.canvas.draw()
    labels = [tick.get_text() for tick in ax.get_yticklabels() if tick.get_text()]
    assert 2 <= len(labels) <= 4
    plt.close(ax.figure)


@pytest.mark.parametrize("plot", [pl.violin, pl.boxplot])
def test_singleton_and_missing(plot):
    data = pd.DataFrame({"type": ["A"], "score": [3.]})
    ax = plot(data, "type", "score")
    assert any(isinstance(a, PathCollection) and 3. in a.get_offsets()[:,1] for a in ax.collections)
    plt.close(ax.figure)
    with pytest.raises(ValueError, match="finite"):
        plot(data.assign(score=np.nan), "type", "score")


@pytest.mark.parametrize("kind", ["scatter", "swarm"])
def test_facets_keep_design_and_shared_scales(tmp_path, kind):
    data = pd.DataFrame({"score": [1, 2, 5], "value": [10, 20, 30],
                         "site": pd.Categorical(["A","A","B"], categories=["B","A"]),
                         "stage": ["early","late","early"]})
    fig = pl.facet(data, "score", "value", row="site", col="stage", kind=kind,
                   output=tmp_path / "facet.pdf")
    a, b, c, d = fig.axes
    assert [ax.get_title() for ax in (a,b)] == ["early","late"]
    assert [t.get_text() for t in b.texts][:2] == ["No observations","n = 0"]
    for ax in fig.axes:
        assert ax.get_xlim() == a.get_xlim() and ax.get_ylim() == a.get_ylim()
    assert (tmp_path / "facet.pdf.cellstyle.json").exists()
    plt.close(fig)


def test_facet_dimensions_and_strip_fill_match_r_reference():
    data = pd.DataFrame({"x": [1, 2], "y": [3, 4], "row": ["A", "B"], "col": ["pre", "post"]})
    fig = pl.facet(data, "x", "y", row="row", col="col", kind="scatter")
    assert np.allclose(fig.get_size_inches() * 25.4, [125, 95])
    assert np.allclose(fig.axes[0].title.get_bbox_patch().get_facecolor()[:3], [.9608, .9608, .9608], atol=1e-5)
    plt.close(fig)


def test_forest_uses_supplied_bounds_order_and_reference():
    d = pd.DataFrame({"contrast": ["B","A"], "ratio": [2.,1.], "lo": [1.2,.8], "hi": [3.,1.4]})
    ax = pl.forest(d, "contrast", "ratio", "lo", "hi", interval_label="95% CI",
                   reference=1, log_scale=True)
    np.testing.assert_allclose(ax.collections[0].get_segments(),
                               [[[1.2,0],[3.,0]], [[.8,1],[1.4,1]]])
    assert ax.get_xscale() == "log" and [t.get_text() for t in ax.get_yticklabels()] == ["B","A"]
    ax.figure.canvas.draw()
    assert all("×" not in tick.get_text() and "^" not in tick.get_text() and "$" not in tick.get_text()
               for tick in ax.get_xticklabels(minor=False) + ax.get_xticklabels(minor=True) if tick.get_text())
    plt.close(ax.figure)
    with pytest.raises(ValueError, match="positive"):
        pl.forest(d.assign(lo=0), "contrast","ratio","lo","hi",interval_label="95% CI",log_scale=True)


def test_forest_preserves_explicit_caller_y_axis():
    d = pd.DataFrame({"contrast": ["B", "A"], "ratio": [2., 1.], "lo": [1.2, .8], "hi": [3., 1.4]})
    fig, ax = plt.subplots()
    ax.set(yticks=(-1, 3), yticklabels=("Caller low", "Caller high"), ylim=(-2, 4))
    pl.forest(d, "contrast", "ratio", "lo", "hi", interval_label="95% CI", ax=ax)
    assert [tick.get_text() for tick in ax.get_yticklabels()] == ["Caller low", "Caller high"]
    assert ax.get_ylim() == (-2, 4)
    plt.close(fig)
