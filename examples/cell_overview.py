"""Render the selected CellStyle layout from the public processed PBMC3k file.

Run with an existing Scanpy environment:
    python examples/cell_overview.py INPUT.h5ad NEW_OUTPUT_DIRECTORY
No data download, reannotation, embedding or statistical test is performed.
"""
import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scanpy as sc
import cellstyle as cs


MARKERS = ['IL7R', 'CD3D', 'CD8A', 'NKG7', 'GNLY', 'MS4A1', 'CD79A',
           'LYZ', 'S100A8', 'FCGR3A', 'FCER1A', 'PPBP']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    recipe = cs.FigureRecipe(__file__, inputs=[args.input],
        asset_id='cellstyle.visual-value.pbmc3k', revision=2,
        command=[sys.executable, str(Path(__file__).resolve()), str(args.input.resolve()), str(args.output.resolve())])
    data = sc.read_h5ad(args.input)
    fig = cs.pl.cell_overview(data, MARKERS, groupby='louvain', use_raw=True,
        title='PBMC3k', subtitle=f'{data.n_obs:,} cells · eight reference annotations',
        expression_label='Mean log1p expression', size_mm=(183,115),
        output=args.output/'overview.pdf', recipe=recipe)
    # Native save creates the display preview without changing the accepted layout.
    fig.savefig(args.output/'overview.png', dpi=220)
    matrix = next(ax for ax in fig.axes if ax.get_label() == 'cellstyle.markers')
    dots = matrix.collections[0]
    groups = list(data.obs.louvain.cat.categories)
    pd.DataFrame(np.asarray(dots.get_array()).reshape(len(groups), len(MARKERS)),
                 index=groups, columns=MARKERS).to_csv(args.output/'mean_expression.csv')
    pd.DataFrame(dots.get_sizes().reshape(len(groups), len(MARKERS))/55,
                 index=groups, columns=MARKERS).to_csv(args.output/'fraction_positive.csv')
    report = cs.check_plot(fig)
    (args.output/'layout-check.json').write_text(json.dumps(report,indent=2)+'\n')
    code = Path(cs.pl.cell_overview.__code__.co_filename)
    (args.output/'implementation.json').write_text(json.dumps({
        'cellstyle_version':cs.__version__,'scanpy_version':version('scanpy'),
        'source_path':str(code.resolve()),'source_sha256':hashlib.sha256(code.read_bytes()).hexdigest(),
        'recipe_asset_id':recipe.asset_id,'revision':recipe.revision,
        'params':{'size_mm':[183,115],'markers':MARKERS,'groupby':'louvain','use_raw':True},
        'layout_status':report['status'],
        'output_sha256':{name:hashlib.sha256((args.output/name).read_bytes()).hexdigest()
                         for name in ('overview.png','overview.pdf','mean_expression.csv','fraction_positive.csv')}},indent=2)+'\n')
    plt.close(fig)
    print(f'Saved {args.output}; layout checks: {report["status"]}')


if __name__ == '__main__':
    main()
