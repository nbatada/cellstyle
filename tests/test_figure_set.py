import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pytest

import cellstyle as cs


def fixture():
    fig, axes = plt.subplots(1, 2)
    identity = [ax.scatter([0, 1], [1, 2], color='#1764AB') for ax in axes]
    quantity = [ax.scatter([2, 3], [2, 3], c=[.2, .8], cmap='Blues', vmin=0, vmax=1) for ax in axes]
    project = cs.FigureSet(identity_colors={'A': '#1764AB'}, comparable_quantities={'signal'})
    for index in range(2):
        project.add_identity(f'p{index}', 'A', identity[index])
        project.add_quantity(f'p{index}', 'signal', quantity[index], unit='a.u.')
    fig.canvas.draw()
    return fig, identity, quantity, project


def test_actual_artist_mismatches_are_detected_without_repair():
    fig, identities, quantities, project = fixture()
    assert project.check()['status'] == 'PASS'
    identities[1].set_facecolor('red')
    quantities[1].set_clim(0, 2)
    limits = [(ax.get_xlim(), ax.get_ylim()) for ax in fig.axes]
    report = project.check()
    assert report['status'] == 'FAIL'
    assert {'IDENTITY_COLOR_MISMATCH', 'SCALE_MISMATCH'} <= {d['code'] for d in report['diagnostics']}
    assert quantities[1].get_clim() == (0, 2)
    assert limits == [(ax.get_xlim(), ax.get_ylim()) for ax in fig.axes]
    plt.close(fig)


def test_scales_are_not_compared_without_explicit_comparability():
    fig, identities, quantities, _ = fixture()
    quantities[1].set_clim(0, 2)
    group = cs.FigureSet()
    for i, artist in enumerate(quantities):
        group.add_quantity(f'p{i}', 'signal', artist, unit='a.u.')
    report = group.check()
    assert not any(d['code'] == 'SCALE_MISMATCH' for d in report['diagnostics'])
    assert report['status'] == 'PARTIAL'
    plt.close(fig)


def test_unknown_color_mapping_cannot_pass_as_constant_identity():
    fig, identities, quantities, _ = fixture()
    group = cs.FigureSet(identity_colors={'A': '#1764AB'})
    group.add_identity('p1', 'A', quantities[0])
    assert group.check()['status'] == 'PARTIAL'
    plt.close(fig)


def test_units_and_actual_normalization_are_checked():
    fig, identities, quantities, group = fixture()
    quantities[1].set_norm(matplotlib.colors.LogNorm(.01, 1))
    group.add_quantity('p2', 'signal', quantities[0], unit='percent')
    report = group.check()
    codes = {d['code'] for d in report['diagnostics']}
    assert {'UNIT_MISMATCH', 'SCALE_MISMATCH'} <= codes
    plt.close(fig)


def test_empty_or_incompletely_bound_set_is_not_pass():
    assert cs.FigureSet().check()['status'] == 'PARTIAL'
    fig, ax = plt.subplots()
    artist = ax.scatter([0], [0], c=[1], vmin=0, vmax=2)
    group = cs.FigureSet(comparable_quantities={'signal'})
    group.add_quantity('p1', 'signal', artist, unit='a.u.')
    assert group.check()['status'] == 'PARTIAL'
    with pytest.raises(ValueError, match='already'):
        group.add_quantity('p1', 'signal', artist, unit='a.u.')
    plt.close(fig)


def test_colormap_change_and_same_name_custom_colors_are_detected():
    fig, identities, quantities, group = fixture()
    original = quantities[1].get_cmap()
    changed = matplotlib.colors.ListedColormap(['black', 'red'], name=original.name)
    quantities[1].set_cmap(changed)
    assert any(d['code'] == 'SCALE_MISMATCH' for d in group.check()['diagnostics'])
    plt.close(fig)


def test_shared_artist_cannot_establish_two_panel_comparison():
    fig, identities, quantities, _ = fixture()
    group = cs.FigureSet(comparable_quantities={'signal'})
    group.add_quantity('p1', 'signal', quantities[0], unit='a.u.')
    group.add_quantity('p2', 'signal', quantities[0], unit='a.u.')
    assert group.check()['status'] == 'PARTIAL'
    plt.close(fig)


def test_hidden_axes_cannot_verify_identity_or_scale():
    fig, identities, quantities, group = fixture()
    fig.axes[1].set_visible(False)
    report = group.check()
    assert report['status'] == 'PARTIAL'
    codes = {d['code'] for d in report['diagnostics']}
    assert {'UNSUPPORTED_IDENTITY', 'UNSUPPORTED_SCALE'} <= codes
    plt.close(fig)


def test_empty_line_cannot_verify_identity_color():
    fig, ax = plt.subplots()
    line, = ax.plot([], [], color='red')
    group = cs.FigureSet(identity_colors={'A': 'red'})
    group.add_identity('p1', 'A', line)
    assert group.check()['status'] == 'PARTIAL'
    plt.close(fig)
