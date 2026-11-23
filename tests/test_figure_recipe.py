import base64
import json
import shutil

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pytest
import cellstyle as cs


def files(tmp_path):
    script = tmp_path / 'plot.py'
    data = tmp_path / 'data.csv'
    script.write_text('# synthetic plotting script\n')
    data.write_text('x,y\n1,2\n2,3\n')
    return script, data


def test_saved_recipe_detects_changed_inputs_and_script(tmp_path):
    script, data = files(tmp_path)
    recipe = cs.FigureRecipe(script, inputs=[data], asset_id='demo.figure1', command=['python', 'plot.py'])
    out = tmp_path / 'plot.png'
    ax = cs.pl.scatter([1, 2], [2, 3], output=out, recipe=recipe)
    report = cs.check_saved_plot(out)
    assert report['freshness']['status'] == 'CURRENT'
    assert report['source_provenance']['asset_id'] == 'demo.figure1'
    data.write_text('x,y\n1,8\n2,9\n')
    script.write_text('# changed script\n')
    report = cs.check_saved_plot(out)
    assert report['freshness']['status'] == 'STALE'
    assert len(report['freshness']['changed_files']) == 2
    snapshot = report['source_provenance']['script_snapshot']
    assert base64.b64decode(snapshot['content']) == b'# synthetic plotting script\n'
    plt.close(ax.figure)


def test_changed_source_before_save_fails_without_output(tmp_path):
    script, data = files(tmp_path)
    recipe = cs.FigureRecipe(script, inputs=[data], asset_id='demo.figure1')
    data.write_text('changed')
    with pytest.raises(ValueError, match='changed'):
        cs.pl.scatter([1], [2], output=tmp_path / 'plot.png', recipe=recipe)
    assert not (tmp_path / 'plot.png').exists()
    assert not (tmp_path / 'plot.png.cellstyle.json').exists()


def test_missing_source_and_relocation(tmp_path):
    project = tmp_path / 'project'; project.mkdir()
    script, data = files(project)
    recipe = cs.FigureRecipe(script, inputs=[data], asset_id='demo.figure1')
    ax = cs.pl.scatter([1], [2], output=project / 'plot.svg', recipe=recipe)
    moved = tmp_path / 'moved'
    shutil.copytree(project, moved)
    shutil.rmtree(project)
    assert cs.check_saved_plot(moved / 'plot.svg')['freshness']['status'] == 'CURRENT'
    (moved / 'data.csv').unlink()
    report = cs.check_saved_plot(moved / 'plot.svg')
    assert report['freshness']['status'] == 'STALE'
    assert report['freshness']['missing_files'] == ['data.csv']
    plt.close(ax.figure)


def test_save_without_recipe_has_unknown_source_freshness(tmp_path):
    ax = cs.pl.scatter([1], [2], output=tmp_path / 'plot.png')
    assert cs.check_saved_plot(tmp_path / 'plot.png')['freshness']['status'] == 'UNKNOWN'
    plt.close(ax.figure)


def test_change_during_render_prevents_publishing_pair(tmp_path, monkeypatch):
    script, data = files(tmp_path)
    recipe = cs.FigureRecipe(script, inputs=[data], asset_id='demo.figure1')
    fig, ax = plt.subplots()
    save = fig.savefig
    def change_after_save(*args, **kwargs):
        save(*args, **kwargs)
        data.write_text('changed during export')
    monkeypatch.setattr(fig, 'savefig', change_after_save)
    with pytest.raises(ValueError, match='changed'):
        cs.style_plot(fig, output=tmp_path / 'plot.png', recipe=recipe)
    assert not (tmp_path / 'plot.png').exists()
    assert not (tmp_path / 'plot.png.cellstyle.json').exists()
    plt.close(fig)


def test_recorded_command_is_never_executed(tmp_path):
    script, data = files(tmp_path)
    marker = tmp_path / 'must-not-exist'
    recipe = cs.FigureRecipe(script, inputs=[data], asset_id='demo.figure1', command=['touch', str(marker)])
    ax = cs.pl.scatter([1], [2], output=tmp_path / 'plot.svg', recipe=recipe)
    report = cs.check_saved_plot(tmp_path / 'plot.svg')
    assert report['source_provenance']['command'] == ['touch', str(marker)]
    assert not marker.exists()
    plt.close(ax.figure)


def test_retargeted_input_symlink_is_detected(tmp_path):
    script, data = files(tmp_path)
    other = tmp_path / 'other.csv'; other.write_text('different data')
    link = tmp_path / 'current.csv'; link.symlink_to(data)
    recipe = cs.FigureRecipe(script, inputs=[link], asset_id='demo.figure1')
    link.unlink(); link.symlink_to(other)
    with pytest.raises(ValueError, match='changed'):
        recipe.verify()
