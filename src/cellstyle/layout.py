"""Bounded layout correction for single axes and constrained-layout Matplotlib grids."""

import warnings
from copy import copy
from matplotlib.path import Path
from matplotlib.transforms import Affine2D

import numpy as np
from matplotlib.collections import PathCollection
from matplotlib.layout_engine import ConstrainedLayoutEngine


def _ticklabels(axis):
    low, high = sorted(axis.get_view_interval())
    return [label for tick in axis.get_major_ticks() if low <= tick.get_loc() <= high
            for label in (tick.label1, tick.label2) if label.get_visible()]


def _text_boxes(labels, renderer):
    return [label.get_window_extent(renderer) for label in labels
            if label.get_visible() and label.get_text()]



def _text_paths(labels, renderer):
    paths = []
    for label in labels:
        if not label.get_visible() or not label.get_text():
            continue
        box = label.get_window_extent(renderer)
        plain = copy(label)
        plain.stale_callback = None
        plain.set_rotation(0)
        unrotated = plain.get_window_extent(renderer)
        transform = (Affine2D().translate(-.5, -.5)
                     .scale(unrotated.width, unrotated.height)
                     .rotate_deg(label.get_rotation())
                     .translate((box.x0 + box.x1)/2, (box.y0 + box.y1)/2))
        paths.append(Path.unit_rectangle().transformed(transform))
    return paths


def _labels_overlap(labels, renderer):
    paths = _text_paths(labels, renderer)
    return any(a.intersects_path(b, filled=True) for i, a in enumerate(paths) for b in paths[i+1:])


def _overlap(boxes):
    return any(a.overlaps(b) for i, a in enumerate(boxes) for b in boxes[i + 1:])


def _legend_covers_data(ax, box):
    for collection in ax.collections:
        if isinstance(collection, PathCollection) and collection.get_visible():
            points = collection.get_offset_transform().transform(collection.get_offsets())
            if any(box.contains(x, y) for x, y in points if np.isfinite([x, y]).all()):
                return True
    for line in ax.lines:
        if line.get_visible() and line.get_transform().transform_path(line.get_path()).intersects_bbox(box):
            return True
    for patch in ax.patches:
        if patch.get_visible() and patch.get_transform().transform_path(patch.get_path()).intersects_bbox(box):
            return True
    return False



def _legend_covers_labels(ax, box, renderer):
    labels = [ax.title, ax._left_title, ax._right_title]
    if ax.axison:
        for axis in (ax.xaxis, ax.yaxis):
            if axis.get_visible():
                labels.extend([axis.label, *_ticklabels(axis)])
    return any(box.overlaps(label_box) for label_box in _text_boxes(labels, renderer))


def correct_layout(figure):
    """Adjust layout only; preserve canvas size, labels, data and axis limits."""
    if not hasattr(figure.canvas, 'get_renderer'):
        return
    if len(figure.axes) > 1 and not isinstance(figure.get_layout_engine(), ConstrainedLayoutEngine):
        return
    figure.canvas.draw()
    for ax in figure.axes:
        if ax.get_visible() and ax.name == 'rectilinear' and getattr(ax, '_colorbar', None) is None:
            _correct_axes_layout(figure, ax)


def _correct_axes_layout(figure, ax):
    renderer = figure.canvas.get_renderer()
    legend = ax.get_legend()
    if legend is not None and legend.get_visible():
        box = legend.get_window_extent(renderer)
        if _legend_covers_data(ax, box) or _legend_covers_labels(ax, box, renderer):
            # Keep the existing handles, title and labels; only move the legend.
            legend.set_bbox_to_anchor((1.02, 1), transform=ax.transAxes)
            legend._loc = 2  # Upper left; set_loc is unavailable on Matplotlib 3.7.
            figure.canvas.draw()
            renderer = figure.canvas.get_renderer()

    labels = _ticklabels(ax.xaxis)
    if _overlap(_text_boxes(labels, renderer)) and all(label.get_rotation() == 0 for label in labels):
        for angle in (45, 90):
            for label in labels:
                label.set_rotation(angle)
                label.set_horizontalalignment('right' if angle == 45 else 'center')
                label.set_rotation_mode('default')
                label.set_verticalalignment('bottom' if label.get_position()[1] > .5 else 'top')
            figure.canvas.draw()
            renderer = figure.canvas.get_renderer()
            if not _overlap(_text_boxes(labels, renderer)):
                break

    boxes = _text_boxes(_ticklabels(ax.xaxis) + _ticklabels(ax.yaxis) +
                        [ax.xaxis.label, ax.yaxis.label, ax.title,
                         ax._left_title, ax._right_title], renderer)
    if legend is not None and legend.get_visible():
        boxes.append(legend.get_window_extent(renderer))
    canvas = figure.bbox
    clipped = any(box.x0 < canvas.x0 - 1 or box.y0 < canvas.y0 - 1 or
                  box.x1 > canvas.x1 + 1 or box.y1 > canvas.y1 + 1 for box in boxes)
    crowded = (_labels_overlap(_ticklabels(ax.xaxis), renderer) or
               _labels_overlap(_ticklabels(ax.yaxis), renderer))
    if clipped or crowded:
        warnings.warn('CellStyle layout still has clipped or overlapping labels at this size; '
                      'inspect the figure or supply a larger size_mm.', UserWarning, stacklevel=3)
