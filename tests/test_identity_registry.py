import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import pandas as pd
import pytest

import cellstyle as cs


def test_registry_is_direct_palette_and_preserves_subset_colors():
    registry = cs.ColorRegistry()
    registry.register('A', '#1764AB')
    registry.register('B', '#D43F3A')
    data = pd.DataFrame({'group': ['A', 'A', 'B', 'B'], 'value': [1, 2, 3, 4]})
    for groups in (['A', 'B'], ['B', 'A'], ['B']):
        ax = cs.pl.swarm(data[data.group.isin(groups)], 'group', 'value',
                         order=groups, palette=registry)
        for collection, group in zip(ax.collections[:len(groups)], groups):
            assert colors.to_hex(collection.get_facecolors()[0]).upper() == registry.color(group)
        plt.close(ax.figure)
    assert dict(registry) == {'A': '#1764AB', 'B': '#D43F3A'}


def test_registry_rejects_ambiguous_file(tmp_path):
    path = tmp_path / 'colors.tsv'
    path.write_text('entity\tcolor\nA\t#1764AB\nA\t#D43F3A\n')
    with pytest.raises(ValueError, match='duplicate'):
        cs.ColorRegistry.from_tsv(path)


def test_missing_identity_fails_before_plot_mutation():
    registry = cs.ColorRegistry()
    registry.register('A', '#1764AB')
    fig, ax = plt.subplots()
    with pytest.raises(ValueError, match='B'):
        cs.pl.swarm(pd.DataFrame({'g': ['B'], 'v': [1]}), 'g', 'v', palette=registry, ax=ax)
    assert not ax.collections
    plt.close(fig)


def test_embedding_passes_named_colors_to_scanpy(monkeypatch):
    from types import SimpleNamespace
    import numpy as np
    from cellstyle import embedding
    fig, ax = plt.subplots()
    calls = []
    def capture(adata, **kwargs):
        calls.append(kwargs)
    monkeypatch.setattr(embedding, '_require_scanpy', lambda: SimpleNamespace(
        pl=SimpleNamespace(embedding=capture)))
    registry = cs.ColorRegistry()
    registry.register('A', '#1764AB')
    registry.register('B', '#D43F3A')
    adata = SimpleNamespace(obs=pd.DataFrame({'group': pd.Categorical(['B', 'A'], categories=['A', 'B'])}),
                            obsm={'X_umap': np.array([[0, 0], [1, 1]])})
    cs.categorical_embedding(adata, basis='X_umap', groupby='group', order=['B', 'A'],
                             palette=registry, ax=ax, label=False)
    assert calls[0]['palette'] == dict(registry)
    plt.close(fig)
