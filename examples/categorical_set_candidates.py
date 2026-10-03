"""Candidate D: deterministic set-based palette comparison, not package defaults.

Same category set -> stable mapping; changed category set -> mapping may change.
Cross-figure identity persistence is explicit via supplied palettes/ColorRegistry.
Run: python examples/categorical_set_candidates.py --output docs/images
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import to_hex, to_rgb
import numpy as np

import cellstyle as cs
from categorical_color_candidates import SWATCHES, IDENTITIES, synthetic_fixture

VARIANTS = {'D1': 'D1 · Editorial expansion',
            'D2': 'D2 · Vivid, narrow lightness',
            'D3': 'D3 · Broad lightness + hue'}


def rgb_to_lab(rgb):
    """sRGB -> CIELAB (D65); ΔE76 distances are selection heuristics only."""
    rgb = np.asarray(rgb, dtype=float)
    linear = np.where(rgb <= .04045, rgb / 12.92, ((rgb + .055) / 1.055) ** 2.4)
    xyz = linear @ np.array([[.4124564, .3575761, .1804375],
                            [.2126729, .7151522, .0721750],
                            [.0193339, .1191920, .9503041]]).T
    xyz = xyz / np.array([.95047, 1., 1.08883])
    delta = 6 / 29
    f = np.where(xyz > delta**3, np.cbrt(xyz), xyz / (3 * delta**2) + 4 / 29)
    return np.column_stack((116*f[:, 1] - 16,
                            500*(f[:, 0] - f[:, 1]), 200*(f[:, 1] - f[:, 2])))


def candidate_swatches(n, variant):
    if variant not in VARIANTS:
        raise ValueError('Unknown set-based candidate.')
    if not 1 <= n <= 32:
        raise ValueError('Comparison scope is 1–32 identities; 5, 12, 28 are rendered.')
    if variant == 'D1':
        colors = list(SWATCHES)
        labs = rgb_to_lab([to_rgb(c) for c in colors])
        selected = list(range(min(5, n)))  # Preserve existing five-color vocabulary.
    else:
        # Fixed quantized gamut grid; no randomness, hashing, color-cycle input,
        # dataset metadata or notebook state participates in palette generation.
        levels = np.linspace(0, 1, 17)
        rgb = np.stack(np.meshgrid(levels, levels, levels, indexing='ij'), axis=-1).reshape(-1, 3)
        labs = rgb_to_lab(rgb)
        lightness, chroma = labs[:, 0], np.linalg.norm(labs[:, 1:], axis=1)
        if variant == 'D2':
            keep = (lightness >= 48) & (lightness <= 67) & (chroma >= 50)
        else:
            keep = (lightness >= 30) & (lightness <= 78) & (chroma >= 25)
        colors = [to_hex(c) for c in rgb[keep]]
        # Compute distances on final quantized swatches, not pre-hex colors.
        labs = rgb_to_lab([to_rgb(c) for c in colors])
        seed = rgb_to_lab([to_rgb(SWATCHES[0])])[0]
        selected = [int(np.argmin(np.linalg.norm(labs - seed, axis=1)))]
    # Greedy farthest-point expansion maximizes the next swatch's distance from
    # the currently chosen set. This is not a global optimum or perceptual PASS.
    distances = np.min(np.linalg.norm(labs[:, None, :] - labs[selected][None, :, :], axis=2), axis=1)
    while len(selected) < n:
        distances[selected] = -1
        index = int(np.argmax(distances))  # fixed grid order breaks exact ties
        selected.append(index)
        distances = np.minimum(distances, np.linalg.norm(labs - labs[index], axis=1))
    return [colors[i] for i in selected]


def candidate_palette(identities, variant):
    values = list(identities)
    if any(not isinstance(name, str) for name in values):
        raise ValueError('Prototype identities must be strings.')
    names = sorted(set(values))  # exact Unicode codepoint order; no locale input
    return dict(zip(names, candidate_swatches(len(names), variant)))


def observed_palette(data, variant):
    # Unused categorical levels are not populations present in the current plot.
    return candidate_palette(data.obs['cell_type'].dropna().unique(), variant)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('docs/images'))
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    metrics = {}
    # All non-color controls match the original frozen A/B/C comparison.
    with plt.rc_context({'font.size': 8, 'font.family': 'DejaVu Sans',
                         'figure.facecolor': 'white', 'axes.facecolor': 'white',
                         'pdf.fonttype': 42, 'svg.fonttype': 'none'}):
        fig, axes = plt.subplots(3, 3, figsize=(12, 9.5), layout='constrained')
        for row, n in enumerate((5, 12, 28)):
            data, centers = synthetic_fixture(n)
            # Checksum records fixture provenance; it is not a color-assignment hash.
            digest = hashlib.sha256(data.obsm['X_umap'].tobytes() + '\n'.join(data.obs['cell_type']).encode()).hexdigest()
            metrics[str(n)] = {'fixture_sha256': digest, 'variants': {}}
            for col, variant in enumerate(VARIANTS):
                palette = observed_palette(data, variant)
                ax = axes[row, col]
                cs.pl.umap(data.copy(), color='cell_type', palette=palette, frameon=False,
                           legend_loc='none', title='', size=12, alpha=.9, show=False, ax=ax)
                ax.set_aspect('equal', adjustable='box')
                for number, (x, y) in enumerate(centers, 1):
                    ax.text(x, y - .35, f'{number:02d}', ha='center', va='center', fontsize=7, color='#202020')
                ax.set_ylim(centers[:, 1].min() - .65, .5)
                if row == 0:
                    ax.set_title(VARIANTS[variant], fontsize=11, pad=12)
                ax.text(.02, 1.03, f'{n} identities · same coordinates and marks',
                        transform=ax.transAxes, fontsize=8, color='#404040')
                colors = list(palette.values()); labs = rgb_to_lab([to_rgb(c) for c in colors])
                distance = np.linalg.norm(labs[:, None, :] - labs[None, :, :], axis=2)
                np.fill_diagonal(distance, np.inf)
                metrics[str(n)]['variants'][variant] = {
                    'palette': palette, 'repeated_swatches': n - len(set(colors)),
                    'minimum_deltaE76': float(distance.min()),
                    'lightness_range': [float(labs[:, 0].min()), float(labs[:, 0].max())],
                }
        fig.suptitle('Candidate D · Which deterministic palette best separates the current categories?', fontsize=13)
        fig.savefig(args.output/'categorical-set-candidates.png', dpi=150)
        fig.savefig(args.output/'categorical-set-candidates.pdf')
        plt.close(fig)
        # Actual final-size comparison: a single 28-population panel at 90 mm
        # width per candidate, with the same data/marks. This size is a viewing
        # condition for color discrimination, not a proposed default figure size.
        data, centers = synthetic_fixture(28)
        for variant in VARIANTS:
            fig, ax = plt.subplots(figsize=(90/25.4, 70/25.4))
            cs.pl.umap(data.copy(), color='cell_type', palette=observed_palette(data, variant),
                       frameon=False, legend_loc='none', title='', size=12, alpha=.9,
                       show=False, ax=ax)
            ax.set_aspect('equal', adjustable='box')
            for number, (x, y) in enumerate(centers, 1):
                ax.text(x, y-.35, f'{number:02d}', ha='center', va='center', fontsize=7, color='#202020')
            ax.set_ylim(centers[:, 1].min()-.65, .5)
            fig.subplots_adjust(left=.03, right=.97, bottom=.04, top=.96)
            fig.savefig(args.output/f'categorical-set-{variant}-90mm.png', dpi=200)
            fig.savefig(args.output/f'categorical-set-{variant}-90mm.pdf')
            plt.close(fig)
    (args.output/'categorical-set-metrics.json').write_text(json.dumps(metrics, indent=2) + '\n')
    print(json.dumps({n:{v:{k:x for k,x in info.items() if k!='palette'} for v,info in entry['variants'].items()} for n,entry in metrics.items()}, indent=2))


if __name__ == '__main__':
    main()
