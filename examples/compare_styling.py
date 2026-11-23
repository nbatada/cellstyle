"""Compare native-plot styling on five synthetic tasks, without statistical inference.

Run: python examples/compare_styling.py OUTPUT_DIRECTORY
Optionally expose an isolated cnsplots install through PYTHONPATH.
This compares existing-axis styling, not each package's specialist plot helpers.
"""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import cellstyle as cs


def synthetic_inputs():
    rng = np.random.default_rng(42)
    cells = pd.DataFrame({'identity': np.repeat(['A', 'B', 'C'], 60),
                          'x': rng.normal(size=180) + np.repeat([-2, 2, 0], 60),
                          'y': rng.normal(size=180) + np.repeat([0, 0, 2], 60)})
    donors = pd.DataFrame({'donor': np.tile(np.arange(8), 3),
                           'identity': np.repeat(['A', 'B', 'C'], 8),
                           'value': rng.normal(size=24) + np.repeat([3, 5, 4], 8)})
    paired = pd.DataFrame({'donor': np.arange(8), 'before': rng.normal(3, .6, 8),
                           'after': rng.normal(4, .6, 8)})
    dots = pd.DataFrame({'identity': np.repeat(['A', 'B', 'C'], 3),
                         'marker': np.tile(['M1', 'M2', 'M3'], 3),
                         'mean': rng.uniform(0, 2, 9), 'fraction': rng.uniform(.1, 1, 9)})
    return {'cells': cells, 'donors': donors, 'paired': paired, 'dots': dots}


def draw_task(ax, task, data, colors):
    if task == 'embedding':
        for identity, group in data['cells'].groupby('identity'):
            ax.scatter(group.x, group.y, s=8, color=colors[identity], label=identity)
        ax.set(xlabel='Simulated X', ylabel='Simulated Y', title='Synthetic coordinates (not UMAP)')
        ax.legend()
    elif task == 'dotplot':
        table = data['dots']
        points = ax.scatter(table.marker, table.identity, s=table.fraction * 100,
                   c=table['mean'], cmap='Blues', vmin=0, vmax=2)
        ax.figure.colorbar(points, ax=ax, label='Synthetic mean (a.u.)', shrink=.7, pad=.04)
        handles = [ax.scatter([], [], s=fraction * 100, color='#666666', label=f'{fraction:.0%}')
                   for fraction in (.25, .5, 1)]
        ax.legend(handles=handles, title='Fraction', loc='upper left', bbox_to_anchor=(1.02, .35))
        ax.set(xlabel='Marker', ylabel='Identity', title='Synthetic means / fractions')
    elif task == 'donors':
        table = data['donors']
        for index, (identity, group) in enumerate(table.groupby('identity')):
            ax.scatter(np.full(len(group), index), group.value, color=colors[identity], s=20)
        ax.set(xticks=range(3), xticklabels=list(colors), xlabel='Identity',
               ylabel='Synthetic response (a.u.)', title='Eight donors per identity')
    elif task == 'paired':
        for row in data['paired'].itertuples():
            ax.plot([0, 1], [row.before, row.after], '-o', color='#666666', markersize=3)
        ax.set(xticks=[0, 1], xticklabels=['Before', 'After'], xlabel='Condition',
               ylabel='Synthetic response (a.u.)', title='Eight paired donors')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    out = parser.parse_args().output
    out.mkdir(parents=True, exist_ok=False)
    inputs = synthetic_inputs()
    for name, table in inputs.items():
        table.to_csv(out / f'{name}.csv', index=False)
    registry = cs.ColorRegistry()
    for identity, color in zip(['A', 'B', 'C'], cs.editorial_vivid(3)):
        registry.register(identity, color)
    registry.to_tsv(out / 'identities.tsv')
    methods = {'native': lambda ax: None, 'cellstyle': cs.style_plot}
    report = {'scope': 'existing-axis styling only; synthetic data; no quality ranking',
              'versions': {'cellstyle': cs.__version__, 'matplotlib': matplotlib.__version__},
              'render_parameters': {'seed': 42, 'png_dpi': 150,
                                    'single_panel_mm': [90, 60], 'four_panel_mm': [183, 120]},
              'results': []}
    try:
        import cnsplots
        methods['cnsplots'] = cnsplots.setup_ax
        report['versions']['cnsplots'] = cnsplots.__version__
    except ImportError as exc:
        report['cnsplots_unavailable'] = str(exc)
    tasks = ['embedding', 'dotplot', 'donors', 'paired', 'four_panel']
    for task in tasks:
        for method, style in methods.items():
            with matplotlib.rc_context():
                count = 4 if task == 'four_panel' else 1
                size = (183, 120) if count == 4 else (90, 60)
                fig, axes = plt.subplots(2 if count == 4 else 1, 2 if count == 4 else 1,
                                         figsize=np.array(size) / 25.4, layout='constrained')
                for ax, content in zip(np.atleast_1d(axes).flat, tasks[:4] if count == 4 else [task]):
                    draw_task(ax, content, inputs, registry)
                    if method != 'cellstyle':
                        style(ax)
                if method == 'cellstyle':
                    cs.style_plot(fig, size_mm=size)
                fig.canvas.draw()
                path = out / f'{task}-{method}.png'
                fig.savefig(path, dpi=150)
                fig.savefig(path.with_suffix('.pdf'))
                report['results'].append({'task': task, 'method': method,
                    'asset_id': 'cellstyle.adoption.synthetic.' + task + '.' + method,
                    'revision': 2, 'pdf_sha256': hashlib.sha256(path.with_suffix('.pdf').read_bytes()).hexdigest(),
                    'size_mm': (fig.get_size_inches() * 25.4).tolist(),
                    'png': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
                plt.close(fig)
    report['sources'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in [Path(__file__), *out.glob('*.csv'), out / 'identities.tsv']}
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    rows = ''.join(f'<tr><th>{task}</th>' + ''.join(
        f'<td><img width="340" src="{task}-{method}.png"></td>' for method in methods) + '</tr>' for task in tasks)
    (out / 'index.html').write_text('<!doctype html><meta charset="utf-8"><title>CellStyle comparison</title>'
        '<h1>Synthetic existing-axis styling comparison</h1><p>Same data and canvas sizes. '
        'Dot color encodes the supplied mean; dot area encodes the supplied fraction. '
        'No Scanpy, SCpubr, statistical inference, or specialist helper comparison.</p><table><tr><th>Task</th>'
        + ''.join(f'<th>{name}</th>' for name in methods) + '</tr>' + rows + '</table>')


if __name__ == '__main__':
    main()
