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
    pytest.importorskip("anndata")
    from cellstyle import embedding
    fig, ax = plt.subplots()
    calls = []
    def capture(adata, **kwargs):
        calls.append(kwargs)
        adata.uns["group_colors"] = ["#FFFFFF"]
    monkeypatch.setattr(embedding, '_require_scanpy', lambda: SimpleNamespace(
        pl=SimpleNamespace(embedding=capture)))
    registry = cs.ColorRegistry()
    registry.register('A', '#1764AB')
    registry.register('B', '#D43F3A')
    adata = SimpleNamespace(obs=pd.DataFrame({'group': pd.Categorical(['B', 'A'], categories=['A', 'B'])}),
                            obsm={'X_umap': np.array([[0, 0], [1, 1]])},
                            uns={'group_colors': ['#112233', '#445566']})
    cs.categorical_embedding(adata, basis='umap', groupby='group', order=['B', 'A'],
                             palette=registry, ax=ax, label=False)
    assert calls[0]['palette'] == dict(registry)
    assert calls[0]['basis'] == 'X_umap'
    assert adata.uns['group_colors'] == ['#112233', '#445566']
    plt.close(fig)


def test_focus_embedding_preserves_embedding_geometry_and_rejects_ambiguous_focus():
    from types import SimpleNamespace
    import numpy as np

    adata = SimpleNamespace(
        obs=pd.DataFrame({"group": ["A", "B"]}),
        obsm={"X_umap": np.array([[0., 0.], [2., 1.]])},
    )
    with pytest.raises(ValueError, match="not present"):
        cs.focus_embedding(adata, basis="X_umap", groupby="group", focus=["missing"])
    with pytest.raises(ValueError, match="missing identities"):
        cs.focus_embedding(adata, basis="X_umap", groupby="group", focus=["A"], palette={})
    ax = cs.focus_embedding(adata, basis="X_umap", groupby="group", focus=["A"])
    try:
        assert ax.get_aspect() == 1
    finally:
        plt.close(ax.figure)


def test_categorical_embedding_preserves_integer_identity_colors_and_labels():
    anndata = pytest.importorskip("anndata")
    pytest.importorskip("scanpy")
    import numpy as np
    from matplotlib.colors import to_rgba

    adata = anndata.AnnData(X=np.empty((4, 0)), obs=pd.DataFrame({"group": [0, 0, 1, 1]}))
    adata.obsm["X_umap"] = np.array([[0., 0.], [1., 0.], [0., 1.], [1., 1.]])
    palette = {0: "#1764AB", 1: "#D43F3A"}
    ax = cs.categorical_embedding(adata, basis="umap", groupby="group", palette=palette, repel=False)
    try:
        ax.figure.canvas.draw()
        colors = ax.collections[0].get_facecolors()
        np.testing.assert_allclose(colors[:2], [to_rgba(palette[0], alpha=.86)] * 2)
        np.testing.assert_allclose(colors[2:], [to_rgba(palette[1], alpha=.86)] * 2)
        assert [text.get_text() for text in ax.texts] == ["0", "1"]
    finally:
        plt.close(ax.figure)


def test_cycle_color_is_frozen_on_registration(tmp_path):
    registry = cs.ColorRegistry()
    with matplotlib.rc_context({"axes.prop_cycle": matplotlib.cycler(color=["red"])}):
        registry.register("T", "C0")
    with matplotlib.rc_context({"axes.prop_cycle": matplotlib.cycler(color=["blue"])}):
        registry.to_tsv(tmp_path / "colors.tsv")
        assert cs.ColorRegistry.from_tsv(tmp_path / "colors.tsv")["T"].lower() == "#ff0000"
