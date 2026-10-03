"""Controlled categorical-color comparison; these are NOT package defaults.

Synthetic data only. Run from the checkout with Scanpy installed:
    python examples/categorical_color_candidates.py --output docs/images

Only the identity-to-color strategy changes between columns. Counts, coordinates,
point size, alpha, typography, aspect, annotation placement and figure layout
are held constant. Numbers identify populations; the key is exported separately.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
import numpy as np
import pandas as pd
from anndata import AnnData

import cellstyle as cs

# Shared finite swatch inventory for ALL candidates. Five existing CellStyle
# colors plus qualitative swatches; no accessibility/perceptual guarantees.
SWATCHES = [
    '#1764AB', '#00A2A5', '#E6A700', '#D43F3A', '#8A4FA3',
    '#593315', '#58A34C', '#C561A6', '#33493F', '#8296CE',
    '#B26C2E', '#6F7478', '#A2B737', '#AB294D', '#5E4281',
    '#49B8B0', '#E77F49', '#454A90', '#DF9FBE', '#346E32',
    '#748D37', '#A87569', '#A7C7DA', '#C8A54F', '#863A72',
    '#497587', '#C5BDB2', '#95512D', '#A9D086', '#397DBB',
    '#554E56', '#DBB087',
]
IDENTITIES = [
    'Naive T', 'Memory T', 'Cytotoxic T', 'Activated T', 'Exhausted T',
    'Regulatory T', 'Gamma delta T', 'NK', 'Cycling NK', 'Naive B',
    'Memory B', 'Plasma', 'Classical monocyte', 'Nonclassical monocyte',
    'cDC1', 'cDC2', 'pDC', 'Macrophage', 'Mast', 'Basophil', 'Neutrophil',
    'Erythroid', 'Megakaryocyte', 'Endothelial', 'Fibroblast', 'Epithelial',
    'Smooth muscle', 'Cycling',
]
TITLES = {'A': 'A · Sorted allocation', 'B': 'B · Stable identity hash',
          'C': 'C · Hash with conflict resolution'}


def preferred_slot(identity):
    # Python's built-in hash is randomized between processes; SHA256 is fixed.
    return int.from_bytes(hashlib.sha256(identity.encode('utf-8')).digest()[:8], 'big') % len(SWATCHES)


def candidate_palette(identities, strategy):
    names = sorted(set(identities))
    if strategy not in TITLES:
        raise ValueError('Unknown candidate.')
    if len(names) > len(SWATCHES):
        raise ValueError('These finite-inventory candidates support at most 32 identities.')
    if strategy == 'A':
        return dict(zip(names, SWATCHES))
    if strategy == 'B':
        return {name: SWATCHES[preferred_slot(name)] for name in names}
    # Resolve exact slot collisions in canonical name order. Pick a free swatch
    # maximizing minimum RGB distance from assigned swatches; RGB distance is
    # only a prototype heuristic, not a perceptual/accessibility metric.
    rgb = np.array([to_rgb(color) for color in SWATCHES])
    used = []
    mapping = {}
    for name in names:
        slot = preferred_slot(name)
        if slot in used:
            free = [i for i in range(len(SWATCHES)) if i not in used]
            distances = [min(np.linalg.norm(rgb[i] - rgb[j]) for j in used) for i in free]
            slot = free[int(np.argmax(distances))]
        used.append(slot)
        mapping[name] = SWATCHES[slot]
    return mapping


def synthetic_fixture(n):
    rng = np.random.default_rng(2603 + n)
    names = IDENTITIES[:n]
    columns = min(7, int(np.ceil(np.sqrt(n * 1.5))))
    centers = np.array([(i % columns, -(i // columns)) for i in range(n)], dtype=float)
    coords = np.vstack([rng.normal(center, [.16, .12], size=(60, 2)) for center in centers])
    obs = pd.DataFrame({'cell_type': pd.Categorical(np.repeat(names, 60), categories=names)},
                       index=[str(i) for i in range(n * 60)])
    d = AnnData(np.zeros((n * 60, 1)), obs=obs)
    d.obsm['X_umap'] = coords
    return d, centers


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('docs/images'))
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    metrics = {}
    # This rc context belongs to the comparison artifact, not to cs.pl defaults.
    with plt.rc_context({'font.size': 8, 'font.family': 'DejaVu Sans',
                         'figure.facecolor': 'white', 'axes.facecolor': 'white',
                         'pdf.fonttype': 42, 'svg.fonttype': 'none'}):
        fig, axes = plt.subplots(3, 3, figsize=(12, 9.5), layout='constrained')
        for row, n in enumerate((5, 12, 28)):
            data, centers = synthetic_fixture(n)
            names = IDENTITIES[:n]
            metrics[str(n)] = {}
            for col, strategy in enumerate(TITLES):
                palette = candidate_palette(names, strategy)
                ax = axes[row, col]
                cs.pl.umap(data.copy(), color='cell_type', palette=palette, frameon=False,
                           legend_loc='none', title='', size=12, alpha=.9, show=False, ax=ax)
                ax.set_aspect('equal', adjustable='box')
                for number, (x, y) in enumerate(centers, 1):
                    ax.text(x, y - .35, f'{number:02d}', ha='center', va='center', fontsize=7, color='#202020')
                ax.set_ylim(centers[:, 1].min() - .65, .5)
                if row == 0:
                    ax.set_title(TITLES[strategy], fontsize=11, pad=12)
                repeats = n - len(set(palette.values()))
                ax.text(.02, 1.03, f'{n} identities · {repeats} repeated swatches',
                        transform=ax.transAxes, fontsize=8, color='#404040')
                shuffled = candidate_palette(list(reversed(names)), strategy)
                assert palette == shuffled
                # Remove an identity near the middle to show category-set sensitivity.
                subset = names[:n//2] + names[n//2+1:]
                changed = sum(palette[name] != candidate_palette(subset, strategy)[name] for name in subset)
                metrics[str(n)][strategy] = {'repeated_swatches': repeats,
                                            'remaining_identities_changed_after_removing_one': changed,
                                            'palette': palette}
        fig.suptitle('Categorical color strategy — choose a candidate, not final visual defaults', fontsize=13)
        fig.savefig(args.output/'categorical-color-candidates.png', dpi=150)
        fig.savefig(args.output/'categorical-color-candidates.pdf')
        plt.close(fig)
        # Population names are recoverable without competing with the color comparison.
        fig, ax = plt.subplots(figsize=(8, 6)); ax.axis('off')
        for i, identity in enumerate(IDENTITIES):
            col, row = divmod(i, 14)
            ax.text(.02 + col * .5, .96 - row * .065, f'{i+1:02d}  {identity}', transform=ax.transAxes, fontsize=10)
        ax.set_title('Synthetic population key · same identities in every candidate', fontsize=11)
        fig.savefig(args.output/'categorical-color-key.png', dpi=120, bbox_inches='tight');plt.close(fig)
    (args.output/'categorical-color-metrics.json').write_text(json.dumps(metrics, indent=2) + '\n')
    print(json.dumps({n:{s:{k:v for k,v in result.items() if k!='palette'} for s,result in choices.items()} for n,choices in metrics.items()}, indent=2))


if __name__ == '__main__':
    main()
