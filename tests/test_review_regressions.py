from types import SimpleNamespace
from unittest.mock import Mock

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from matplotlib.colors import to_rgba

from cellstyle import embedding, labels
from cellstyle import ComparisonResult, add_comparisons, replicate_distribution, quantitative_scatter

@pytest.fixture(autouse=True)
def close_figures():
    yield
    plt.close('all')


def adata(categories=('B', 'A'), basis='X_umap'):
    return SimpleNamespace(obs=pd.DataFrame({'group': pd.Categorical(['A', 'B', 'A'], categories=categories)}),
                           obsm={basis: np.array([[0., 0.], [4., 1.], [1., 2.]])})


def test_categorical_uses_named_palette(monkeypatch):
    plot = Mock()
    monkeypatch.setattr(embedding, '_require_scanpy', lambda: SimpleNamespace(pl=SimpleNamespace(embedding=plot)))
    _, ax = plt.subplots()
    embedding.categorical_embedding(adata(basis='umap'), basis='umap', groupby='group', order=['A', 'B'],
                                    palette={'A': 'red', 'B': 'blue'}, ax=ax, repel=False)
    assert plot.call_args.kwargs['palette'] == {'A': 'red', 'B': 'blue'}
    assert [t.get_color() for t in ax.texts] == ['red', 'blue']


def test_basis_alias_and_equal_aspect():
    ax = embedding.focus_embedding(adata(), basis='umap', groupby='group', focus=['A'], repel=False)
    assert ax.get_aspect() == 1
    assert len(ax.collections[1].get_offsets()) == 2

@pytest.mark.parametrize('coords', [np.zeros((2, 2)), np.zeros((3, 1)), np.zeros((3, 2, 1)), np.full((3, 2), np.nan)])
def test_invalid_embedding_before_mutation(coords):
    data = adata(basis='umap'); data.obsm['umap'] = coords
    _, ax = plt.subplots()
    with pytest.raises(ValueError):
        embedding.focus_embedding(data, basis='umap', groupby='group', focus=['A'], ax=ax)
    assert not ax.collections

@pytest.mark.parametrize('order', [['A'], ['A', 'A', 'B'], ['A', None, 'B']])
def test_distribution_rejects_invalid_order_before_mutation(order):
    _, ax = plt.subplots()
    with pytest.raises(ValueError):
        replicate_distribution(pd.DataFrame({'g': ['A', 'B'], 'v': [1, 2]}), 'g', 'v', order=order, ax=ax)
    assert not ax.collections


def test_distribution_warns_missing():
    with pytest.warns(UserWarning, match='missing'):
        replicate_distribution(pd.DataFrame({'g': ['A', None, 'B'], 'v': [1, 2, np.nan]}), 'g', 'v')

@pytest.mark.parametrize('kwargs', [{'p': -1}, {'p': np.nan}, {'p_adjusted': np.inf}, {'p': 1.01},
                                     {'effect': np.inf}, {'ci_low': 2, 'ci_high': 1}, {'ci_low': 1}])
def test_invalid_result(kwargs):
    with pytest.raises(ValueError):
        ComparisonResult('A', 'B', **kwargs)

@pytest.mark.parametrize('kwargs', [{'step_fraction': -1}, {'step_fraction': .01}, {'y_start': np.nan},
                                     {'positions': {'A': 0, 'B': 0}}, {'positions': {'A': np.inf, 'B': 1}}])
def test_invalid_geometry_atomic(kwargs):
    _, ax = plt.subplots(); ax.set_xticks([0, 1], ['A', 'B'])
    before = ax.get_ylim()
    with pytest.raises(ValueError):
        add_comparisons(ax, [ComparisonResult('A', 'B', p=.05)], **kwargs)
    assert not ax.lines and not ax.texts and ax.get_ylim() == before


def test_late_invalid_group_atomic():
    _, ax = plt.subplots(); ax.set_xticks([0, 1], ['A', 'B'])
    with pytest.raises(KeyError):
        add_comparisons(ax, [ComparisonResult('A', 'B', p=.05), ComparisonResult('A', 'C', p=.05)])
    assert not ax.lines and not ax.texts

@pytest.mark.parametrize('scale', ['log', 'symlog'])
def test_unsupported_axis(scale):
    _, ax = plt.subplots(); ax.set_xticks([0, 1], ['A', 'B']); ax.set_yscale(scale)
    with pytest.raises(ValueError):
        add_comparisons(ax, [ComparisonResult('A', 'B', p=.05)])


def test_force_static_forwarded(monkeypatch):
    adjust = Mock(); monkeypatch.setattr(labels, 'adjust_text', adjust)
    _, ax = plt.subplots()
    labels.repel_labels([ax.text(0, 0, 'A')], ax, force_points=(.4, .6))
    assert adjust.call_args.kwargs['force_static'] == (.4, .6)
    assert 'force_points' not in adjust.call_args.kwargs

@pytest.mark.parametrize('x,y', [([1], [2]), ([1, 1], [2, 3]), ([1, 2], [3]), ([np.nan, 1], [2, 3])])
def test_scatter_fit_invalid_before_mutation(x, y):
    _, ax = plt.subplots()
    with pytest.raises(ValueError):
        quantitative_scatter(x, y, fit=True, ax=ax)
    assert not ax.collections

@pytest.mark.parametrize('kwargs', [{'group_a': 'A', 'group_b': 'A', 'p': .05},
                                    {'group_a': '', 'group_b': 'B', 'p': .05}])
def test_distinct_named_groups(kwargs):
    with pytest.raises(ValueError):
        ComparisonResult(**kwargs)


def test_p_boundaries_and_supplied_label():
    for p in (0, 1):
        assert ComparisonResult('A', 'B', p=p).display_p() == p
    _, ax = plt.subplots(); ax.set_xticks([0, 1], ['A', 'B'])
    add_comparisons(ax, [ComparisonResult('A', 'B', label='Effect = 2 [1, 3]', effect=2, ci_low=1, ci_high=3)])
    assert ax.texts[0].get_text() == 'Effect = 2 [1, 3]'


def test_force_static_precedence(monkeypatch):
    adjust = Mock(); monkeypatch.setattr(labels, 'adjust_text', adjust)
    _, ax = plt.subplots()
    labels.repel_labels([ax.text(0, 0, 'A')], ax, force_points=(.4, .6), force_static=(.8, .9))
    assert adjust.call_args.kwargs['force_static'] == (.8, .9)

@pytest.mark.parametrize('helper', ['categorical_embedding', 'focus_embedding'])
def test_both_helpers_validate_before_backend_or_axis_mutation(helper, monkeypatch):
    backend = Mock(side_effect=AssertionError('Should validate before loading Scanpy'))
    monkeypatch.setattr(embedding, '_require_scanpy', backend)
    data = adata(); data.obsm['X_umap'] = np.zeros((2, 2))
    _, ax = plt.subplots()
    kwargs = {'focus': ['A']} if helper == 'focus_embedding' else {}
    with pytest.raises(ValueError):
        getattr(embedding, helper)(data, basis='umap', groupby='group', ax=ax, **kwargs)
    assert not ax.collections and not backend.called
