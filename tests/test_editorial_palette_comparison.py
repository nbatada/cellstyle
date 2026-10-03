"""Focused checks for the unselected D1 refinement artifacts."""
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
import numpy as np
import pytest

pytest.importorskip('anndata')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'examples'))
import editorial_palette_refinement as refinement
sys.path.pop(0)


@pytest.mark.parametrize('n', [5, 12, 28])
@pytest.mark.parametrize('variant', ['D1a', 'D1b', 'D1c'])
def test_set_stability_and_editorial_anchors(n, variant):
    data, _ = refinement.synthetic_fixture(n)
    palette = refinement.observed_palette(data, variant)
    colors = list(palette.values())
    assert colors[:5] == refinement.SWATCHES[:5]
    assert len(colors) == len(set(colors)) == n
    reordered = data[::-1].copy()
    reordered.obs['cell_type'] = reordered.obs['cell_type'].cat.reorder_categories(
        list(reversed(data.obs['cell_type'].cat.categories)))
    reordered.obs['cell_type'] = reordered.obs['cell_type'].cat.add_categories(['unused'])
    with plt.rc_context({'axes.prop_cycle': matplotlib.cycler(color=['black']),
                         'axes.facecolor': 'black', 'font.size': 18}):
        assert refinement.observed_palette(reordered, variant) == palette
    if variant in ('D1b', 'D1c'):
        assert set(colors) == set(refinement.candidate_swatches(n, 'D1b'))
        if n > 5:
            lab = refinement.rgb_to_lab([to_rgb(c) for c in colors[5:]])
            # Small tolerances account for quantizing the designed gamut to hex.
            assert (lab[:, 0] >= 45.5).all() and (lab[:, 0] <= 70.5).all()
            chroma = np.linalg.norm(lab[:, 1:], axis=1)
            assert (chroma >= 23.4).all() and (chroma <= 52.6).all()
    else:
        assert colors == refinement.previous_swatches(n, 'D1')


def test_frozen_mark_and_annotation_controls():
    pytest.importorskip('scanpy')
    data, centers = refinement.synthetic_fixture(28)
    fig, ax = plt.subplots(figsize=(90/25.4, 70/25.4))
    try:
        refinement.plot_panel(data, centers, 'D1c', ax)
        points = ax.collections[0]
        assert len(points.get_offsets()) == 28*60
        assert points.get_alpha() == .9 and np.all(points.get_sizes() == 12)
        assert ax.get_aspect() == 1
        assert [text.get_text() for text in ax.texts] == [f'{i:02d}' for i in range(1, 29)]
        assert all(text.get_fontsize() == 7 for text in ax.texts)
        np.testing.assert_allclose(ax.get_ylim(), [centers[:, 1].min()-.65, .5])
    finally:
        plt.close(fig)
