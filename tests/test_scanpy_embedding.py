"""Optional integration checks inspect Scanpy's actual point and legend colors."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from matplotlib.colors import to_rgba

pytest.importorskip('scanpy')
from anndata import AnnData
from cellstyle import categorical_embedding

@pytest.mark.parametrize('categories', [['B', 'A'], ['A', 'B']])
@pytest.mark.parametrize('reverse', [False, True])
@pytest.mark.parametrize('direct', [False, True])
def test_scanpy_points_labels_and_legend(categories, reverse, direct):
    data = AnnData(np.zeros((4, 1)), obs=pd.DataFrame({'group': pd.Categorical(['A', 'B', 'A', 'B'], categories=categories)}))
    data.obsm['X_umap'] = np.array([[0., 0.], [5., 1.], [1., 2.], [4., 2.]])
    if reverse:
        data = data[::-1].copy()
    fig, ax = plt.subplots()
    try:
        categorical_embedding(data, basis='umap', groupby='group', order=['A', 'B'],
                              palette={'A': 'red', 'B': 'blue'}, ax=ax, label=direct, repel=False)
        expected = np.array([to_rgba('red' if x == 'A' else 'blue', alpha=.86) for x in data.obs['group']])
        np.testing.assert_allclose(ax.collections[0].get_facecolors(), expected)
        if direct:
            assert {t.get_text(): to_rgba(t.get_color()) for t in ax.texts} == {'A': to_rgba('red'), 'B': to_rgba('blue')}
        else:
            legend = ax.get_legend()
            for text, handle in zip(legend.get_texts(), legend.legend_handles):
                np.testing.assert_allclose(handle.get_facecolors()[0, :3], to_rgba({'A': 'red', 'B': 'blue'}[text.get_text()])[:3])
        assert ax.get_aspect() == 1
    finally:
        plt.close(fig)


def test_default_palette_stable_with_category_reordering():
    mappings = []
    for categories in (['B', 'A'], ['A', 'B']):
        data = AnnData(np.zeros((2, 1)), obs=pd.DataFrame({'group': pd.Categorical(['B', 'A'], categories=categories)}))
        data.obsm['X_umap'] = np.array([[0., 0.], [1., 1.]])
        fig, ax = plt.subplots()
        categorical_embedding(data, basis='umap', groupby='group', ax=ax, repel=False)
        mappings.append(dict(zip(data.obs['group'], map(tuple, ax.collections[0].get_facecolors()))))
        plt.close(fig)
    assert mappings[0] == mappings[1]
