import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import numpy as np
import pandas as pd
import pytest

from cellstyle.distributions import grouped_swarm, paired


def test_paired_draws_every_complete_pair_and_summary_without_data_mutation(tmp_path):
    data = pd.DataFrame({"donor": ["d1", "d1", "d2", "d2", "d3", "d3"],
                         "time": ["before", "after"] * 3, "score": [1, 3, 2, 4, 3, 5]})
    original = data.copy(deep=True)
    ax = paired(data, "donor", "time", "score", order=["before", "after"], output=tmp_path / "paired.png")
    assert data.equals(original)
    assert (tmp_path / "paired.png").exists()
    assert ax.get_xlabel() == "time" and ax.get_ylabel() == "score"
    assert 2 <= len([tick for tick in ax.get_yticklabels() if tick.get_text()]) <= 4
    assert len(ax.collections) >= 4  # observations plus open median markers
    assert len(ax.lines) == 3  # one connector for each donor
    plt.close(ax.figure)


def test_paired_keeps_incomplete_pairs_but_rejects_duplicates_and_skips_gaps():
    data = pd.DataFrame({"id": pd.Categorical(["a", "a", "b", "b", "c"], categories=["a", "b", "c", "unused"]),
                         "time": [1, 2, 1, 3, 2], "value": [1., 2., 3., 4., 5.]})
    ax = paired(data, "id", "time", "value")
    assert [line.get_xdata().tolist() for line in ax.lines] == [[0, 1]]
    assert [tick.get_text() for tick in ax.get_xticklabels()] == ["1", "2", "3"]
    plt.close(ax.figure)
    duplicate = pd.concat([data, data.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="Duplicate pair and condition"):
        paired(duplicate, "id", "time", "value")


def test_paired_sorts_datetime_visits_and_preserves_explicit_caller_ticks():
    dates = pd.to_datetime(["2026-02-01", "2026-01-01", "2026-02-01", "2026-01-01"])
    data = pd.DataFrame({"id": ["a", "a", "b", "b"], "visit": dates, "value": [2., 1., 4., 3.]})
    ax = paired(data, "id", "visit", "value")
    assert [item.get_text()[:10] for item in ax.get_xticklabels()] == ["2026-01-01", "2026-02-01"]
    plt.close(ax.figure)
    fig, ax = plt.subplots()
    ax.set(xticks=(-1, 2), xticklabels=("Caller left", "Caller right"))
    paired(data, "id", "visit", "value", ax=ax)
    assert [item.get_text() for item in ax.get_xticklabels()] == ["Caller left", "Caller right"]
    plt.close(fig)


def test_grouped_swarm_uses_true_swarm_reports_unbalanced_counts_and_summaries():
    data = pd.DataFrame({"site": ["s1"] * 5 + ["s2"] * 7,
                         "group": ["A"] * 3 + ["B"] * 2 + ["A"] * 4 + ["B"] * 3,
                         "value": np.arange(12, dtype=float)})
    original = data.copy(deep=True)
    with pytest.warns(UserWarning, match="Observed"):
        ax = grouped_swarm(data, "site", "value", "group", order=["s1", "s2"], hue_order=["A", "B"])
    assert data.equals(original)
    assert ax.get_xlabel() == "site" and ax.get_ylabel() == "value"
    assert len(ax.collections) >= 8  # swarm collections plus one median marker per x-by-hue combination
    assert sum(isinstance(item, LineCollection) for item in ax.collections) == 4  # one IQR for each observed combination
    plt.close(ax.figure)


def test_grouped_swarm_preserves_empty_combination_and_rejects_missing_values():
    missing_combo = pd.DataFrame({"site": ["s1", "s1", "s2"], "group": ["A", "B", "A"], "value": [1., 2., 3.]})
    with pytest.warns(UserWarning, match="empty combinations"):
        ax = grouped_swarm(missing_combo, "site", "value", "group", order=["s1", "s2"], hue_order=["A", "B"])
    assert sum(isinstance(item, LineCollection) for item in ax.collections) == 3
    plt.close(ax.figure)
    missing_value = pd.DataFrame({"site": ["s1", "s1"], "group": ["A", "B"], "value": [1., np.nan]})
    with pytest.raises(ValueError, match="Missing values"):
        grouped_swarm(missing_value, "site", "value", "group")


def test_grouped_swarm_order_cannot_hide_values_and_three_hues_use_seaborn_centers():
    data = pd.DataFrame({"site": ["s2", "s1", "s1", "s1"], "group": ["A", "A", "B", "C"], "value": [1., 2., 3., 4.]})
    with pytest.raises(ValueError, match="would hide observed"):
        grouped_swarm(data, "site", "value", "group", order=["s1"], hue_order=["A", "B", "C"])
    with pytest.warns(UserWarning):
        ax = grouped_swarm(data, "site", "value", "group", order=["s1", "s2"], hue_order=["A", "B", "C"])
    summary_x = sorted(collection.get_segments()[0][0, 0] for collection in ax.collections
                       if isinstance(collection, LineCollection))
    assert np.allclose(summary_x[:3], [-.2666667, 0, .2666667])
    plt.close(ax.figure)
