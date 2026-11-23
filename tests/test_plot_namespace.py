"""The public namespace must work on first import and preserve existing APIs."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

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
