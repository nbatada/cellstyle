"""Bounded, rendered figure checks; never infer scientific meaning."""
import hashlib
import json
from pathlib import Path
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from .group_labels import _GroupLabels
from .layout import _legend_covers_labels, _legend_covers_data, _ticklabels, _labels_overlap


def check_plot(plot):
    """Inspect rendered text and axes legends without applying styling.

    PASS means only that the listed checks found no issue. It is not scientific,
    accessibility, exported-font, or journal acceptance. Drawing can run the
    figure's existing layout engine, as a normal canvas draw does.
    """
    figure = plot.figure if isinstance(plot, Axes) else plot
    if not isinstance(figure, Figure):
        raise TypeError('plot must be a Matplotlib Axes or Figure')
    report = {'schema': 'cellstyle-plot-check-1', 'status': 'PARTIAL',
              'size_mm': (figure.get_size_inches() * 25.4).tolist(),
              'diagnostics': [], 'coverage': {'checked': [], 'limitations': [
                  'Scientific meaning, units, denominators and statistical validity are not inferred.',
                  'Font substitution, glyph appearance and accessibility require separate review.',
                  'Mark clipping, annotation collisions and marker-edge overlap are not checked.']}}
    if not hasattr(figure.canvas, 'get_renderer'):
        report['coverage']['limitations'].append('Canvas does not expose a renderer; geometry was not inspected.')
        return report
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    drawn = []
    original = renderer.draw_text

    def record(*args, **kwargs):
        artist = kwargs.get('mtext')
        if artist is not None and artist.get_text().strip() and artist.get_alpha() != 0 and artist not in drawn:
            drawn.append(artist)
        return original(*args, **kwargs)

    renderer.draw_text = record
    try:
        figure.canvas.draw()
    finally:
        renderer.draw_text = original
    report['coverage']['checked'].append('Bounds of text emitted by the canvas renderer')
    for text in drawn:
        box = text.get_window_extent(renderer)
        if (box.x0 < figure.bbox.x0 - 1 or box.y0 < figure.bbox.y0 - 1 or
                box.x1 > figure.bbox.x1 + 1 or box.y1 > figure.bbox.y1 + 1):
            report['diagnostics'].append({'code': 'TEXT_OUTSIDE_CANVAS', 'text': text.get_text(),
                'message': 'Text extends beyond the canvas; move it or increase size_mm.'})
    unsupported = False
    for index, ax in enumerate(figure.axes):
        if not ax.get_visible():
            continue
        for layer in ax.artists:
            if isinstance(layer, _GroupLabels) and layer.get_visible():
                for label in layer.report:
                    if label["overlaps_previous"] or label["outside_panel"]:
                        report["diagnostics"].append({
                            "code":"GROUP_LABEL_FIT", "axes":index, "text":label["label"],
                            "message":"Group label intersects another group label or exceeds the panel."
                        })
                if "Adaptive group label fit" not in report["coverage"]["checked"]:
                    report["coverage"]["checked"].append("Adaptive group label fit")
        if ax.name != 'rectilinear':
            unsupported = True
            report['coverage']['limitations'].append(f'Axes {index}: {ax.name} tick and legend checks unsupported.')
            continue
        if getattr(ax, '_colorbar', None) is not None:
            continue
        for axis_name, axis in [('x', ax.xaxis), ('y', ax.yaxis)]:
            if ax.axison and axis.get_visible() and _labels_overlap(_ticklabels(axis), renderer):
                report['diagnostics'].append({'code': 'TICK_LABEL_OVERLAP', 'axes': index,
                    'message': f'{axis_name} tick labels overlap; increase size_mm or adjust label placement.'})
        legend = ax.get_legend()
        if legend is not None and legend.get_visible():
            box = legend.get_window_extent(renderer)
            for target_index, target in enumerate(figure.axes):
                if target.get_visible() and _legend_covers_labels(target, box, renderer):
                    report['diagnostics'].append({'code': 'LEGEND_COVERS_LABEL', 'axes': index,
                        'message': f'Legend overlaps an axis label, tick or title in axes {target_index}; reserve space outside the labels.'})
                if target.get_visible() and target.name == 'rectilinear' and _legend_covers_data(target, box):
                    report['diagnostics'].append({'code': 'LEGEND_COVERS_DATA', 'axes': index,
                        'message': f'Legend covers supported data marks in axes {target_index}; reserve space outside the panel.'})
    report['coverage']['checked'].extend([
        'Visible rectilinear major tick-label overlap',
        'Axes legends against labels, scatter centres, lines and patch paths'])
    if figure.legends:
        unsupported = True
        report['coverage']['limitations'].append('Figure-level legend overlap is not inspected.')
    report['status'] = 'WARN' if report['diagnostics'] else 'PARTIAL' if unsupported else 'PASS'
    return report


def check_saved_plot(path):
    """Read a save receipt only if its figure bytes still match; not authentication."""
    path = Path(path)
    receipt = json.loads(Path(str(path) + '.cellstyle.json').read_text())
    if receipt.get('schema') != 'cellstyle-save-1':
        raise ValueError('Unsupported save receipt schema')
    if receipt.get('asset_sha256') != hashlib.sha256(path.read_bytes()).hexdigest():
        raise ValueError('Saved figure changed; the layout report is stale. Re-export or review the edited artifact.')
    from .provenance import source_freshness
    receipt['freshness'] = source_freshness(receipt.get('source_provenance'), path.parent.resolve())
    return receipt
