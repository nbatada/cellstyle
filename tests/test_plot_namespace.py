"""The public namespace must work on first import and preserve existing APIs."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

import cellstyle as cs
from cellstyle.pl import scatter, swarm


def test_namespace_preserves_helpers_and_one_call_export(tmp_path):
    assert scatter is cs.quantitative_scatter is cs.pl.scatter
    assert swarm is cs.replicate_distribution is cs.pl.swarm
    ax = cs.pl.scatter([1, 2], [3, 4], output=tmp_path / 'scatter.png')
    assert (tmp_path / 'scatter.png').stat().st_size > 0
    plt.close(ax.figure)
    ax = cs.pl.swarm(pd.DataFrame({'Group': ['A', 'A', 'B'], 'Value': [1, 2, 3]}),
                     'Group', 'Value', output=tmp_path / 'swarm.pdf')
    assert (tmp_path / 'swarm.pdf').stat().st_size > 0
    assert ax.get_ylabel() == 'Value'
    plt.close(ax.figure)


@pytest.mark.parametrize("x, y", [([1, np.nan], [2, 3]), ([np.nan], [np.nan]), ([1, 2], [3])])
def test_scatter_rejects_missing_or_misaligned_observations(x, y):
    with pytest.raises(ValueError):
        cs.pl.scatter(x, y)


def test_scatter_rejects_rank_deficient_fit():
    with pytest.raises(ValueError, match="distinct x"):
        cs.pl.scatter([1, 1], [2, 3], fit=True)


def test_scatter_rejects_series_with_mismatched_indexes():
    with pytest.raises(ValueError, match="identical indexes"):
        cs.pl.scatter(pd.Series([1., 2.], index=["a", "b"]),
                      pd.Series([3., 4.], index=["b", "a"]))
