"""D1a/b/c controlled comparison; not package defaults.

Exact frozen fixtures and UMAP mark/layout controls are retained. D1a is the
previous D1. D1b changes only the extended swatch inventory. D1c uses D1b's exact
selected swatches but changes their allocation sequence. The first five colors
remain the existing CellStyle editorial anchor in all three variants.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import to_hex, to_rgb
from matplotlib.patches import Rectangle
import numpy as np

import cellstyle as cs
from categorical_color_candidates import SWATCHES, IDENTITIES, synthetic_fixture
from categorical_set_candidates import rgb_to_lab, candidate_swatches as previous_swatches

VARIANTS = {'D1a': 'D1a · Current editorial expansion',
            'D1b': 'D1b · Moderated extension',
            'D1c': 'D1c · Same swatches, separated neighbors'}


def lab_to_rgb(lab):
    """Inverse of the prototype sRGB/D65 CIELAB conversion; no gamut clipping."""
    lab = np.asarray(lab, dtype=float)
    fy = (lab[:, 0] + 16) / 116
    f = np.column_stack((fy + lab[:, 1] / 500, fy, fy - lab[:, 2] / 200))
    delta = 6/29
    xyz = np.where(f > delta, f**3, 3 * delta**2 * (f - 4/29))
    xyz *= np.array([.95047, 1., 1.08883])
    matrix = np.array([[.4124564, .3575761, .1804375],
                       [.2126729, .7151522, .0721750],
                       [.0193339, .1191920, .9503041]])
    linear = xyz @ np.linalg.inv(matrix).T
    # Suppress fractional powers of negative out-of-gamut values; retain those
    # negative values for rejection rather than clipping them into valid colors.
    return np.where(linear <= .0031308, 12.92 * linear,
                    1.055 * np.maximum(linear, 0)**(1/2.4) - .055)


def refined_inventory():
    # All extension candidates are restrained relative to the earlier broad-
    # gamut D2/D3 prototypes: L* 46–70, C* 24–52. Existing five anchors are kept
    # exactly, including the original gold's greater chroma/lightness.
    colors = list(SWATCHES[:5])
    for lightness in (46., 54., 62., 70.):
        for chroma in (24., 36., 44., 52.):
            angles = np.deg2rad(np.arange(0., 360., 15.))
            lab = np.column_stack((np.full(len(angles), lightness),
                                   chroma*np.cos(angles), chroma*np.sin(angles)))
            rgb = lab_to_rgb(lab)
            colors.extend(to_hex(c) for c in rgb if (c >= 0).all() and (c <= 1).all())
    return list(dict.fromkeys(colors))


def maxmin_swatches(n):
    colors = refined_inventory()
    labs = rgb_to_lab([to_rgb(c) for c in colors])
    selected = list(range(min(n, 5)))
    distances = np.min(np.linalg.norm(labs[:, None, :] - labs[selected][None, :, :], axis=2), axis=1)
    while len(selected) < n:
        distances[selected] = -1
        slot = int(np.argmax(distances))
        selected.append(slot)
        distances = np.minimum(distances, np.linalg.norm(labs - labs[slot], axis=1))
    return [colors[i] for i in selected]


def adjacency_scores(colors):
    labs = rgb_to_lab([to_rgb(c) for c in colors])
    ab = np.linalg.norm(labs[:, None, 1:] - labs[None, :, 1:], axis=2)
    hue = np.rad2deg(np.arctan2(labs[:, 2], labs[:, 1])) % 360
    hue_gap = np.abs(hue[:, None] - hue[None, :]); hue_gap = np.minimum(hue_gap, 360-hue_gap)
    # Prefer chromatic separation over brightness contrast; penalize close hues.
    # A design heuristic, not a validated perceptual or CVD metric.
    return ab - .35*np.abs(labs[:, None, 0] - labs[None, :, 0]) - .6*np.maximum(30-hue_gap, 0)


def separated_allocation(colors):
    if len(colors) <= 5:
        return colors.copy()
    score = adjacency_scores(colors)
    path = list(range(5)); remaining = list(range(5, len(colors)))
    while remaining:
        next_slot = max(remaining, key=lambda i: score[path[-1], i])
        path.append(next_slot); remaining.remove(next_slot)

    def quality(order):
        edges = score[order[:-1], order[1:]]
        return (round(float(edges.min()), 8), round(float(edges.mean()), 8))

    # Bounded deterministic segment reversals improve worst then average
    # adjacency score. The five editorial anchors and their order remain fixed.
    for _ in range(8):
        best, best_quality = path, quality(path)
        for start in range(5, len(path)-1):
            for end in range(start+1, len(path)):
                candidate = path[:start]+list(reversed(path[start:end+1]))+path[end+1:]
                q = quality(candidate)
                if q > best_quality:
                    best, best_quality = candidate, q
        if best == path:
            break
        path = best
    return [colors[i] for i in path]


def candidate_swatches(n, variant):
    if variant not in VARIANTS or not 1 <= n <= 32:
        raise ValueError('Use D1a/b/c with 1–32 identities.')
    if variant == 'D1a':
        return previous_swatches(n, 'D1')
    colors = maxmin_swatches(n)
    return separated_allocation(colors) if variant == 'D1c' else colors


def candidate_palette(identities, variant):
    values = list(identities)
    if any(not isinstance(name, str) for name in values):
        raise ValueError('Prototype identities must be strings.')
    names = sorted(set(values))
    return dict(zip(names, candidate_swatches(len(names), variant)))


def observed_palette(data, variant):
    return candidate_palette(data.obs['cell_type'].dropna().unique(), variant)


def diagnostics(palette):
    colors = list(palette.values())
    lab = rgb_to_lab([to_rgb(c) for c in colors])
    delta = np.linalg.norm(lab[:, None, :] - lab[None, :, :], axis=2)
    np.fill_diagonal(delta, np.inf)
    return {'palette': palette, 'repeated_swatches': len(colors)-len(set(colors)),
            'minimum_pair_deltaE76': float(delta.min()),
            'minimum_adjacent_deltaE76': float(np.linalg.norm(np.diff(lab, axis=0), axis=1).min()),
            'lightness_range': [float(lab[:, 0].min()), float(lab[:, 0].max())],
            'chroma_range': [float(np.linalg.norm(lab[:, 1:], axis=1).min()),
                             float(np.linalg.norm(lab[:, 1:], axis=1).max())]}


def plot_panel(data, centers, variant, ax):
    cs.pl.umap(data.copy(), color='cell_type', palette=observed_palette(data, variant),
               frameon=False, legend_loc='none', title='', size=12, alpha=.9, show=False, ax=ax)
    ax.set_aspect('equal', adjustable='box')
    for number, (x, y) in enumerate(centers, 1):
        ax.text(x, y-.35, f'{number:02d}', ha='center', va='center', fontsize=7, color='#202020')
    ax.set_ylim(centers[:, 1].min()-.65, .5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('docs/images'))
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    metrics = {}
    frozen_path = Path(__file__).resolve().parents[1] / 'docs/images/categorical-set-metrics.json'
    frozen = json.loads(frozen_path.read_text())
    with plt.rc_context({'font.size': 8, 'font.family': 'DejaVu Sans',
                         'figure.facecolor': 'white', 'axes.facecolor': 'white',
                         'pdf.fonttype': 42, 'svg.fonttype': 'none'}):
        fig, axes = plt.subplots(3, 3, figsize=(12, 9.5), layout='constrained')
        for row, n in enumerate((5, 12, 28)):
            data, centers = synthetic_fixture(n)
            digest = hashlib.sha256(data.obsm['X_umap'].tobytes()+'\n'.join(data.obs['cell_type']).encode()).hexdigest()
            assert digest == frozen[str(n)]['fixture_sha256']
            metrics[str(n)] = {'fixture_sha256': digest, 'variants': {}}
            for col, variant in enumerate(VARIANTS):
                palette = observed_palette(data, variant)
                if variant == 'D1a':
                    assert palette == frozen[str(n)]['variants']['D1']['palette']
                plot_panel(data, centers, variant, axes[row, col])
                if row == 0:
                    axes[row, col].set_title(VARIANTS[variant], fontsize=11, pad=12)
                axes[row, col].text(.02, 1.03, f'{n} identities · same coordinates and marks',
                                   transform=axes[row, col].transAxes, fontsize=8, color='#404040')
                metrics[str(n)]['variants'][variant] = diagnostics(palette)
        fig.suptitle('D1 refinement · Restrained colors, clearer category separation', fontsize=13)
        fig.savefig(args.output/'editorial-refinement.png', dpi=150)
        fig.savefig(args.output/'editorial-refinement.pdf'); plt.close(fig)

        # Separate output panels retain the preceding 90 x 70 mm UMAP controls.
        for n in (12, 28):
            data, centers = synthetic_fixture(n)
            for variant in VARIANTS:
                fig, ax = plt.subplots(figsize=(90/25.4, 70/25.4))
                plot_panel(data, centers, variant, ax)
                fig.subplots_adjust(left=.03, right=.97, bottom=.04, top=.96)
                fig.savefig(args.output/f'editorial-{variant}-{n}-90mm.png', dpi=200)
                fig.savefig(args.output/f'editorial-{variant}-{n}-90mm.pdf'); plt.close(fig)

        # The separate swatch strip adds no element or spacing to the UMAPs.
        fig, axes = plt.subplots(3, 1, figsize=(12, 2.5), layout='constrained')
        for ax, variant in zip(axes, VARIANTS):
            palette = candidate_palette(IDENTITIES, variant)
            for rank, (name, color) in enumerate(palette.items()):
                ax.add_patch(Rectangle((rank+.04, .3), .92, .55, facecolor=color, edgecolor='none', alpha=.9))
                ax.text(rank+.5, .14, f'{IDENTITIES.index(name)+1:02d}', ha='center', va='center', fontsize=7)
            ax.set_xlim(0, 28); ax.set_ylim(0, 1); ax.axis('off')
            ax.text(-.01, .6, variant, transform=ax.transAxes, ha='right', va='center', fontsize=9)
        fig.suptitle('28-color allocation order · numbers are frozen-fixture population IDs', fontsize=10)
        fig.savefig(args.output/'editorial-swatches-28.png', dpi=150)
        fig.savefig(args.output/'editorial-swatches-28.pdf'); plt.close(fig)
    (args.output/'editorial-refinement-metrics.json').write_text(json.dumps(metrics, indent=2)+'\n')
    print(json.dumps({n:{v:{k:x for k,x in d.items() if k!='palette'} for v,d in record['variants'].items()} for n,record in metrics.items()}, indent=2))


if __name__ == '__main__':
    main()
