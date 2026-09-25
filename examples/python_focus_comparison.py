"""SYNTHETIC categorical embedding: native Matplotlib versus CellStyle focus.

From the repository root, with CellStyle 0.2.0 installed:
    MPLBACKEND=Agg python examples/python_focus_comparison.py \
        --output docs/images/focus_comparison.png

This provisional technical comparison uses generated coordinates and categories.
It is not biological evidence or a claim of measured perceptual improvement.
Both panels contain every observation with identical coordinates and assignments;
only visual encoding changes. No AnnData or Scanpy dependency is needed.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from cellstyle import focus_embedding


def make_synthetic_embedding():
    """Return a deterministic, wholly synthetic embedding with six categories."""
    rng = np.random.default_rng(20260925)
    categories = [f"State {letter}" for letter in "ABCDEF"]
    centers = [(0.8, 0.5), (-1.7, 1.25), (0.05, 2.2),
               (2.0, 1.65), (-1.25, -1.25), (1.35, -1.5)]
    coordinates = []
    assignments = []
    for category, center in zip(categories, centers):
        points = rng.multivariate_normal(
            center, [[0.25, 0.07], [0.07, 0.18]], size=180
        )
        coordinates.append(points)
        assignments.extend([category] * len(points))
    return np.vstack(coordinates), np.asarray(assignments), categories


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=Path("docs/images/focus_comparison.png"))
    args = parser.parse_args()
    coordinates, assignments, categories = make_synthetic_embedding()
    embedding = SimpleNamespace(
        obs=pd.DataFrame({"state": assignments}),
        obsm={"X_demo": coordinates},
    )

    # Preserve native Matplotlib point sizes, categorical colors, and legend.
    with plt.rc_context(plt.rcParamsDefault):
        fig = plt.figure(figsize=(14.4, 6.5), dpi=100, facecolor="white")
        left = fig.add_axes([0.065, 0.21, 0.36, 0.60])
        right = fig.add_axes([0.585, 0.21, 0.36, 0.60])
        for category in categories:
            mask = assignments == category
            left.scatter(coordinates[mask, 0], coordinates[mask, 1], label=category)
        left.legend(loc="center left", bbox_to_anchor=(1.015, 0.5))
        left.set_xlabel("Synthetic dimension 1", fontsize=12)
        left.set_ylabel("Synthetic dimension 2", fontsize=12)

        focus_embedding(
            embedding, basis="X_demo", groupby="state", focus=["State A"],
            ax=right, label_fontsize=15, repel=False,
            context_alpha=1.0, context_size=10, focus_size=20,
        )
        limits = ((coordinates[:, 0].min() - 0.3, coordinates[:, 0].max() + 0.3),
                  (coordinates[:, 1].min() - 0.3, coordinates[:, 1].max() + 0.3))
        for axis, title in zip((left, right),
                               ("Default Matplotlib", "CellStyle focus view")):
            axis.set_xlim(limits[0])
            axis.set_ylim(limits[1])
            axis.set_aspect("equal", adjustable="box")
            axis.set_title(title, fontsize=18, pad=18)
        fig.suptitle("Where is State A?", fontsize=25, y=0.965)
        fig.text(0.5, 0.095,
                 "SYNTHETIC DATA  ·  Same 1,080 points, categories, and coordinates in both panels",
                 ha="center", fontsize=13, color="#404040")
        fig.text(0.5, 0.052,
                 "CellStyle highlights one category while retaining the others as neutral context.",
                 ha="center", fontsize=13, color="#404040")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.output, dpi=100, facecolor="white")
        plt.close(fig)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
