import hashlib
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pytest

import cellstyle as cs


def test_check_reports_specific_clipped_text_without_changing_data():
    fig, ax = plt.subplots()
    line, = ax.plot([0, 1], [1, 2])
    fig.text(1.1, .5, 'Clipped explanation')
    limits = ax.get_xlim(), ax.get_ylim()
    result = cs.check_plot(fig)
    assert result['status'] == 'WARN'
    assert any(d['code'] == 'TEXT_OUTSIDE_CANVAS' and d['text'] == 'Clipped explanation'
               for d in result['diagnostics'])
    assert (ax.get_xlim(), ax.get_ylim()) == limits
    assert list(line.get_ydata()) == [1, 2]
    plt.close(fig)


def test_save_writes_hash_bound_report_and_refuses_orphan_receipt(tmp_path):
    out = tmp_path / 'plot.png'
    ax = cs.pl.scatter([1, 2], [3, 4], output=out)
    receipt = json.loads((tmp_path / 'plot.png.cellstyle.json').read_text())
    assert receipt['asset_sha256'] == hashlib.sha256(out.read_bytes()).hexdigest()
    assert receipt['inspection']['status'] == 'PASS'
    assert receipt['source_provenance'] == 'not supplied'
    assert receipt['artifact']['format'] == 'png'
    assert receipt['artifact']['width_px'] > 0
    out.unlink()
    with pytest.raises(FileExistsError):
        cs.style_plot(ax, output=out)
    assert not out.exists()
    plt.close(ax.figure)


def test_renderer_failure_does_not_leave_output(tmp_path, monkeypatch):
    fig, ax = plt.subplots()
    def fail(*args, **kwargs):
        raise RuntimeError('save failed')
    monkeypatch.setattr(fig, 'savefig', fail)
    with pytest.raises(RuntimeError, match='save failed'):
        cs.style_plot(fig, output=tmp_path / 'plot.svg')
    assert not list(tmp_path.iterdir())
    plt.close(fig)


def test_polar_check_reports_partial_coverage():
    fig, ax = plt.subplots(subplot_kw={'projection': 'polar'})
    ax.plot([0, 1], [1, 2])
    report = cs.check_plot(fig)
    assert report['status'] == 'PARTIAL'
    assert any('polar' in item for item in report['coverage']['limitations'])
    plt.close(fig)


def test_saved_report_rejects_changed_artifact(tmp_path):
    out = tmp_path / 'plot.svg'
    ax = cs.pl.scatter([1, 2], [2, 3], output=out)
    assert cs.check_saved_plot(out)['schema'] == 'cellstyle-save-1'
    out.write_text(out.read_text() + '\n')
    with pytest.raises(ValueError, match='changed'):
        cs.check_saved_plot(out)
    plt.close(ax.figure)


def test_check_detects_legend_over_axis_label():
    fig, ax = plt.subplots()
    ax.scatter([0], [0], label='Observed')
    legend = ax.legend(loc='upper right')
    fig.canvas.draw()
    box = legend.get_window_extent(fig.canvas.get_renderer())
    x, y = ax.transAxes.inverted().transform([(box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2])
    ax.set_xlabel('Covered axis label')
    ax.xaxis.set_label_coords(x, y)
    report = cs.check_plot(fig)
    assert any(d['code'] == 'LEGEND_COVERS_LABEL' for d in report['diagnostics'])
    plt.close(fig)


def test_parallel_rotated_tick_labels_do_not_trigger_false_overlap():
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.set_xlim(0, 4)
    ax.set_xticks([1, 1.5], ['LongMarkerNameOne', 'LongMarkerNameTwo'])
    plt.setp(ax.get_xticklabels(), rotation=55, ha='right', rotation_mode='anchor', fontsize=8)
    report = cs.check_plot(fig)
    assert not any(d['code'] == 'TICK_LABEL_OVERLAP' for d in report['diagnostics'])
    plt.close(fig)


def test_rotated_tick_labels_that_really_intersect_are_reported():
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.set_xlim(0, 4)
    ax.set_xticks([1, 1.02], ['LongMarkerNameOne', 'LongMarkerNameTwo'])
    plt.setp(ax.get_xticklabels(), rotation=55, ha='right', rotation_mode='anchor', fontsize=8)
    report = cs.check_plot(fig)
    assert any(d['code'] == 'TICK_LABEL_OVERLAP' for d in report['diagnostics'])
    plt.close(fig)
