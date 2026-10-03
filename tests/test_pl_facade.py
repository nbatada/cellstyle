"""Facade compatibility gates; visual candidates are not package defaults."""
import inspect
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

import cellstyle as cs

NAMES = ['embedding','umap','tsne','pca','dotplot','matrixplot','heatmap','violin','stacked_violin']


def test_root_namespace_imports_without_scanpy():
    code = '''
import sys
class BlockScanpy:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'scanpy' or fullname.startswith('scanpy.'):
            raise AssertionError('Scanpy loaded by root/module import')
sys.meta_path.insert(0, BlockScanpy())
import cellstyle as cs
import cellstyle.pl
assert cs.pl is sys.modules['cellstyle.pl']
assert 'scanpy' not in sys.modules
assert 'umap' in dir(cs.pl)
assert 'pl' in cs.__all__
assert callable(cs.focus_embedding) and callable(cs.replicate_distribution)
assert callable(cs.add_comparisons)
'''
    subprocess.run([sys.executable, '-c', code], check=True)


@pytest.mark.parametrize('name', NAMES)
def test_destination_overrides_kwargs_return_and_no_monkeypatch(name, monkeypatch):
    target = Mock(return_value=object())
    native = SimpleNamespace(**{n: target for n in NAMES})
    monkeypatch.setitem(sys.modules, 'scanpy', SimpleNamespace(pl=native))
    kwargs = dict(show=False, save='figure.pdf', ax=object(), return_fig=True,
                  frameon=True, cmap='magma', palette=['red'], wspace=.9,
                  alpha=.2, size=17, rasterized=False)
    before = kwargs.copy()
    args = (object(), 'positional')
    assert getattr(cs.pl, name)(*args, **kwargs) is target.return_value
    assert target.call_args.args == args
    assert target.call_args.kwargs == before == kwargs
    assert getattr(native, name) is target


def test_native_defaults_are_not_replaced_before_visual_selection(monkeypatch):
    target = Mock()
    monkeypatch.setitem(sys.modules, 'scanpy', SimpleNamespace(pl=SimpleNamespace(umap=target)))
    cs.pl.umap('adata', color='cell_type')
    assert target.call_args.kwargs == {'color': 'cell_type'}


def test_missing_scanpy_and_unsupported_name(monkeypatch):
    monkeypatch.setitem(sys.modules, 'scanpy', None)
    with pytest.raises(ImportError, match=r'cellstyle\[scanpy\]'):
        cs.pl.umap('adata')
    with pytest.raises(AttributeError, match='not supported'):
        cs.pl.spatial


def test_real_signature_on_attribute_access():
    sc = pytest.importorskip('scanpy')
    # Fresh wrapper metadata must come from the real supported Scanpy API.
    for name in NAMES:
        wrapper = cs.pl._make_wrapper(name)
        assert inspect.signature(wrapper) == inspect.signature(getattr(sc.pl, name))
        assert wrapper.__wrapped__ is getattr(sc.pl, name)


@pytest.fixture
def data():
    pytest.importorskip('scanpy')
    from anndata import AnnData
    rng = np.random.default_rng(21)
    obs = pd.DataFrame({'cell_type': pd.Categorical(np.repeat([f'Type {i}' for i in range(6)], 8))},
                       index=[str(i) for i in range(48)])
    d = AnnData(rng.random((48, 3)), obs=obs, var=pd.DataFrame(index=['TRDC','CD3D','NKG7']))
    d.obsm['X_umap'] = rng.normal(size=(48, 2))
    return d


@pytest.fixture(autouse=True)
def close_figures():
    yield
    plt.close('all')


@pytest.mark.parametrize('color', ['cell_type', 'TRDC', ['cell_type','TRDC'], ['cell_type','TRDC','CD3D','NKG7']])
def test_real_umap_returns_and_global_state(data, color):
    import scanpy as sc
    native = sc.pl.umap
    rc_before = dict(matplotlib.rcParams)
    result = cs.pl.umap(data, color=color, show=False)
    axes = result if isinstance(result, list) else [result]
    assert len(axes) == (len(color) if isinstance(color, list) else 1)
    assert all(len(ax.collections[0].get_offsets()) == 48 for ax in axes)
    assert sc.pl.umap is native
    assert dict(matplotlib.rcParams) == rc_before


def test_real_ax_return_fig_show_and_save(data, monkeypatch, tmp_path):
    import scanpy as sc
    _, ax = plt.subplots()
    assert cs.pl.umap(data, color='TRDC', ax=ax, show=False, frameon=True) is ax
    assert any(s.get_visible() for s in ax.spines.values())
    assert isinstance(cs.pl.umap(data, color='TRDC', return_fig=True, show=False), matplotlib.figure.Figure)
    show = Mock(); monkeypatch.setattr(plt, 'show', show)
    assert cs.pl.umap(data, color='TRDC', show=True) is None
    show.assert_called_once()
    original_figdir = sc.settings.figdir
    try:
        sc.settings.figdir = tmp_path
        cs.pl.umap(data, color='TRDC', save='_facade.png', show=False)
        assert (tmp_path / 'umap_facade.png').exists()
    finally:
        sc.settings.figdir = original_figdir


def test_explicit_continuous_controls(data):
    from matplotlib.colors import Normalize
    norm = Normalize(0, 1)
    ax = cs.pl.umap(data, color='TRDC', cmap='magma', norm=norm, show=False)
    assert ax.collections[0].cmap.name == 'magma'
    assert ax.collections[0].norm is norm
    ax = cs.pl.umap(data, color='TRDC', color_map='Blues', vmin=.1, vmax=.8, show=False)
    assert ax.collections[0].cmap.name == 'Blues'
    assert ax.collections[0].norm.vmin == .1 and ax.collections[0].norm.vmax == .8
