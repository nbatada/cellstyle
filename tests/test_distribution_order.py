import matplotlib; matplotlib.use("Agg")
from matplotlib.collections import LineCollection, PathCollection
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

import cellstyle as cs


def test_categorical_order_aligns_swarm_and_summaries_with_unused_category():
    data = pd.DataFrame({
        "group": pd.Categorical(
            ["treated"] * 3 + ["control"] * 3,
            categories=["control", "unused", "treated"],
            ordered=True,
        ),
        "value": [10, 20, 30, 1, 3, 5],
    })

    ax = cs.replicate_distribution(
        data, "group", "value",
        palette={"control": "#1764AB", "unused": "#00A2A5", "treated": "#D43F3A"},
    )

    summary_x = {
        float(segment[0, 0])
        for collection in ax.collections
        if isinstance(collection, LineCollection)
        for segment in collection.get_segments()
    }
    median_offsets = sorted(
        tuple(map(float, collection.get_offsets()[0]))
        for collection in ax.collections
        if isinstance(collection, PathCollection)
        and len(collection.get_offsets()) == 1
        and np.allclose(collection.get_facecolors()[0, :3], 1)
    )
    observation_x = {
        round(float(offset[0]))
        for collection in ax.collections
        if isinstance(collection, PathCollection)
        and len(collection.get_offsets()) > 1
        for offset in collection.get_offsets()
    }

    assert summary_x == {0.0, 2.0}
    assert median_offsets == [(0.0, 3.0), (2.0, 20.0)]
    assert observation_x == {0, 2}
    plt.close(ax.figure)


def test_numeric_object_categories_keep_numeric_order_and_explicit_override():
    data = pd.DataFrame({
        "group": pd.Series([20, 20, 3, 3], dtype=object),
        "value": [10, 14, 1, 5],
    })
    for order, expected in ((None, [(0.0, 3.0), (1.0, 12.0)]),
                            (np.array([20, 3]), [(0.0, 12.0), (1.0, 3.0)])):
        ax = cs.replicate_distribution(data, "group", "value", order=order)
        medians = sorted(
            tuple(map(float, collection.get_offsets()[0]))
            for collection in ax.collections
            if isinstance(collection, PathCollection)
            and len(collection.get_offsets()) == 1
            and np.allclose(collection.get_facecolors()[0, :3], 1)
        )
        assert medians == expected
        expected_labels = ["3", "20"] if order is None else ["20", "3"]
        assert [tick.get_text() for tick in ax.get_xticklabels()] == expected_labels
        plt.close(ax.figure)


def test_swarm_rejects_hidden_or_missing_observations_and_unregistered_large_palettes():
    data = pd.DataFrame({"group": ["A", "A", "B", "B"], "value": [1., 2., 100., 200.]})
    with pytest.raises(ValueError, match="would hide"):
        cs.pl.swarm(data, "group", "value", order=["A"])
    with pytest.raises(ValueError, match="complete"):
        cs.pl.swarm(data.assign(value=[1., np.nan, 100., 200.]), "group", "value")
    large = pd.DataFrame({"group": list("ABCDEF"), "value": range(6)})
    with pytest.raises(ValueError, match="at most five"):
        cs.pl.swarm(large, "group", "value")


def test_swarm_summaries_follow_existing_categorical_axis_slots():
    data = pd.DataFrame({"group": ["A", "A", "B", "B"], "value": [1., 3., 5., 7.]})
    fig, ax = plt.subplots()
    ax.plot(["B", "A"], [0., 0.], color="grey")
    cs.pl.swarm(data, "group", "value", order=["A", "B"], ax=ax)
    fig.canvas.draw()
    observations = [c.get_offsets() for c in ax.collections if len(c.get_offsets()) == 2]
    np.testing.assert_allclose(observations, [[[1., 1.], [1., 3.]], [[0., 5.], [0., 7.]]])
    medians = [c.get_offsets()[0] for c in ax.collections if c.get_zorder() == 11]
    np.testing.assert_allclose(medians, [[1., 2.], [0., 6.]])
    iqr = [c.get_segments()[0] for c in ax.collections if c.get_zorder() == 10]
    np.testing.assert_allclose(iqr, [[[1., 1.5], [1., 2.5]], [[0., 5.5], [0., 6.5]]])
    plt.close(fig)
