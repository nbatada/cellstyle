"""Save five CellStyle PDFs from public teaching data."""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

import cellstyle as cs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data", type=Path, help="Directory containing trees.csv and iris.csv")
    parser.add_argument("output", type=Path, help="New directory for the five PDFs")
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    output = args.output

    # Girth is the recorded diameter in inches. Each point is one tree.
    diameter = "Diameter (in)"
    volume = "Timber volume (ft³)"
    DF_trees = pd.read_csv(args.data / "trees.csv").rename(
        columns={"Girth": diameter, "Volume": volume}
    )

    # Match each participant's two measurements by ID.
    response = "Extra sleep (h)"
    conditions = ["Drug 1", "Drug 2"]
    DF_sleep = pd.read_csv(here.parent / "sleep.csv").rename(columns={"Drug": "Treatment"})

    length = "Petal length (cm)"
    DF_iris = pd.read_csv(args.data / "iris.csv").rename(columns={"Petal.Length": length})

    # The two matrices share the same reference annotations and genes.
    DF_means = pd.read_csv(here / "inputs/mean_log1p_expression.csv", index_col=0)
    DF_fractions = pd.read_csv(here / "inputs/fraction_positive.csv", index_col=0)
    colour_label = "Mean log1p expression"
    size_label = "Fraction of cells with expression > 0"

    output.mkdir(parents=True, exist_ok=False)
    ax = cs.pl.scatter(DF_trees[diameter], DF_trees[volume],
                       output=output / "trees_scatter.pdf")
    plt.close(ax.figure)

    ax = cs.pl.paired(DF_sleep, pair="Participant", x="Treatment", y=response,
                      order=conditions, output=output / "sleep_paired.pdf")
    plt.close(ax.figure)

    # Extra canvas space resolves the swarm-packing warning at 90 × 60 mm.
    with cs.theme_context("manuscript"):
        fig, ax = plt.subplots(figsize=(180 / 25.4, 105 / 25.4), layout="constrained")
        cs.pl.boxplot(DF_iris, "Species", length, ax=ax, output=output / "iris_box.pdf")
    plt.close(fig)

    ax = cs.pl.dotplot(DF_means, DF_fractions, colour_label=colour_label,
                       size_label=size_label, max_area=55, output=output / "pbmc3k_dot.pdf")
    plt.close(ax.figure)

    ax = cs.pl.heatmap(DF_means, scale_label=colour_label,
                       output=output / "pbmc3k_heatmap.pdf")
    plt.close(ax.figure)
    print(f"Saved five PDFs in {output.resolve()}")


if __name__ == "__main__":
    main()
