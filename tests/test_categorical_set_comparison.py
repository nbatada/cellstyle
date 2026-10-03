"""Prototype contract checks; no D variant is installed as a visual default."""
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pytest

pytest.importorskip('anndata')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'examples'))
import categorical_set_candidates as candidates
sys.path.pop(0)


@pytest.mark.parametrize('n', [5, 12, 28])
@pytest.mark.parametrize('variant', ['D1', 'D2', 'D3'])
def test_same_observed_set_has_stable_mapping(n, variant):
    data, _ = candidates.synthetic_fixture(n)
    before = candidates.observed_palette(data, variant)
    reordered = data[::-1].copy()
    reordered.obs['cell_type'] = reordered.obs['cell_type'].cat.reorder_categories(
        list(reversed(data.obs['cell_type'].cat.categories)))
    reordered.obs['cell_type'] = reordered.obs['cell_type'].cat.add_categories(['unused identity'])
    with plt.rc_context({'axes.prop_cycle': matplotlib.cycler(color=['red', 'black']),
                         'axes.facecolor': 'black', 'font.size': 18}):
        after = candidates.observed_palette(reordered, variant)
    assert before == after
    assert len(before) == len(set(before.values())) == n
    assert 'unused identity' not in before
    assert list(before) == sorted(before)
    # No RNG participation or mutation is permitted.
    state = np.random.get_state()
    assert candidates.candidate_palette(list(before), variant) == before
    after_state = np.random.get_state()
    assert state[0] == after_state[0] and np.array_equal(state[1], after_state[1])
    assert state[2:] == after_state[2:]
