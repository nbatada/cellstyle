import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from cellstyle.styling import style_plot


def test_crowded_ticks_are_separated_without_changing_data():
    fig, ax = plt.subplots()
    labels = ['Untreated control'] + [f'Treatment condition {letter}' for letter in 'ABCD']
    points = ax.scatter(range(5), [1, 2, 3, 2, 1])
    ax.set_xticks(range(5), labels)
    limits = ax.get_xlim(), ax.get_ylim()
    offsets = points.get_offsets().copy()
    style_plot(ax)
    renderer = fig.canvas.get_renderer()
    boxes = [label.get_window_extent(renderer) for label in ax.get_xticklabels()]
    assert all(not a.overlaps(b) for a, b in zip(boxes, boxes[1:]))
    assert all(box.y1 < ax.get_window_extent(renderer).y0 for box in boxes)
    assert [label.get_text() for label in ax.get_xticklabels()] == labels
    np.testing.assert_array_equal(points.get_offsets(), offsets)
    assert (ax.get_xlim(), ax.get_ylim()) == limits
    np.testing.assert_allclose(fig.get_size_inches() * 25.4, [90, 60])
    plt.close(fig)


def test_legend_covering_points_moves_outside_axes():
    fig, ax = plt.subplots()
    ax.scatter([0.15, .98], [.90, .02], label='Measured observations')
    ax.set(xlim=(0, 1), ylim=(0, 1))
    legend = ax.legend(loc='upper left')
    style_plot(ax, size_mm=(130, 70))
    renderer = fig.canvas.get_renderer()
    assert not legend.get_window_extent(renderer).overlaps(ax.get_window_extent(renderer))
    assert [t.get_text() for t in legend.get_texts()] == ['Measured observations']
    plt.close(fig)


def test_multi_axes_geometry_is_preserved():
    fig, axes = plt.subplots(1, 2)
    bounds = [ax.get_position().bounds for ax in axes]
    style_plot(fig)
    assert [ax.get_position().bounds for ax in axes] == bounds
    plt.close(fig)


def test_clear_legend_and_explicit_label_rotation_are_preserved():
    fig, ax = plt.subplots()
    ax.scatter([.1], [.1], label='Observed')
    ax.set(xlim=(0, 1), ylim=(0, 1))
    legend = ax.legend(loc='upper right')
    ax.tick_params(axis='x', labelrotation=20)
    style_plot(ax)
    assert legend._loc == 1
    assert all(label.get_rotation() == 20 for label in ax.get_xticklabels())
    plt.close(fig)


def test_unresolved_layout_warns_without_changing_requested_size():
    import pytest
    fig, ax = plt.subplots()
    ax.scatter([0], [0])
    ax.set_xlabel('A deliberately very long axis label ' * 8)
    with pytest.warns(UserWarning, match='CellStyle layout still'):
        style_plot(ax, size_mm=(90, 60))
    np.testing.assert_allclose(fig.get_size_inches() * 25.4, [90, 60])
    plt.close(fig)


def test_grid_legend_reserves_space_without_covering_adjacent_panel():
    fig, axes = plt.subplots(2, 2, figsize=(183 / 25.4, 120 / 25.4), layout='constrained')
    for ax in axes.flat:
        ax.scatter([.12, .95], [.92, .1], label='Observed')
        ax.set(xlim=(0, 1), ylim=(0, 1))
    legend = axes[0, 0].legend(loc='upper left')
    limits = [(ax.get_xlim(), ax.get_ylim()) for ax in axes.flat]
    style_plot(fig)
    renderer = fig.canvas.get_renderer()
    box = legend.get_window_extent(renderer)
    assert all(not box.overlaps(ax.get_window_extent(renderer)) for ax in axes.flat)
    assert fig.bbox.contains(box.x0, box.y0) and fig.bbox.contains(box.x1, box.y1)
    assert limits == [(ax.get_xlim(), ax.get_ylim()) for ax in axes.flat]
    np.testing.assert_allclose(fig.get_size_inches() * 25.4, [183, 120])
    first = box.bounds
    style_plot(fig)
    np.testing.assert_allclose(legend.get_window_extent(fig.canvas.get_renderer()).bounds, first, atol=1)
    plt.close(fig)
