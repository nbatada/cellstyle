"""Create a checked synthetic multi-panel figure with native Matplotlib plots.

Run: python3 examples/checked_figure.py OUTPUT_DIRECTORY
"""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import cellstyle as cs


def make_inputs(output_dir):
    rng = np.random.default_rng(23)
    identities = ("Group A", "Group B", "Group C")
    cells = pd.DataFrame({
        "identity": np.repeat(identities, 24),
        "synthetic_x": rng.normal(size=72) + np.repeat((-2, 0, 2), 24),
        "synthetic_y": rng.normal(size=72) + np.repeat((0, 1, 0), 24),
    })
    donors = pd.DataFrame({
        "donor": np.tile(np.arange(1, 7), 3),
        "identity": np.repeat(identities, 6),
        "synthetic_signal": rng.normal(size=18) + np.repeat((2, 3, 4), 6),
    })
    paired = pd.DataFrame({
        "donor": np.arange(1, 7),
        "before": rng.normal(2, 0.3, 6),
        "after": rng.normal(2.7, 0.3, 6),
    })
    dots = pd.DataFrame({
        "identity": np.repeat(identities, 3),
        "marker": np.tile(("Marker 1", "Marker 2", "Marker 3"), 3),
        "synthetic_mean": rng.uniform(0, 2, 9),
        "synthetic_fraction": rng.uniform(0.2, 0.9, 9),
    })
    for name, table in (("cells", cells), ("donors", donors), ("paired", paired), ("dots", dots)):
        table.to_csv(output_dir / f"{name}.csv", index=False)
    registry = cs.ColorRegistry()
    for identity, color in zip(identities, cs.editorial_vivid(3)):
        registry.register(identity, color)
    registry.to_tsv(output_dir / "registry.tsv")
    return cells, donors, paired, dots, cs.ColorRegistry.from_tsv(output_dir / "registry.tsv")


def draw_figure(cells, donors, paired, dots, registry):
    figure, axes = plt.subplots(2, 2, figsize=(183 / 25.4, 125 / 25.4), layout="constrained")
    embedding, dot_ax, donor_ax, paired_ax = axes.flat

    for identity, group in cells.groupby("identity", sort=False):
        embedding.scatter(group.synthetic_x, group.synthetic_y, s=12,
                          color=registry.color(identity), label=identity)
    embedding.set(xlabel="Synthetic X (a.u.)", ylabel="Synthetic Y (a.u.)",
                  title="Synthetic coordinates")
    # The initial legend covers observations; style_plot moves it when possible.
    embedding.legend(loc="center")

    points = dot_ax.scatter(dots.marker, dots.identity,
                            s=dots.synthetic_fraction * 130,
                            c=dots.synthetic_mean, cmap="Blues", vmin=0, vmax=2)
    figure.colorbar(points, ax=dot_ax, label="Synthetic mean (a.u.)")
    handles = [dot_ax.scatter([], [], s=fraction * 130, color='#666666', label=f'{fraction:.0%}')
               for fraction in (.25, .5, 1)]
    dot_ax.legend(handles=handles, title='Fraction', loc='upper left', bbox_to_anchor=(1.02, .35))
    dot_ax.set(xlabel="Marker", ylabel="Identity", title="Synthetic marker summary")

    for index, identity in enumerate(registry):
        group = donors.loc[donors.identity == identity]
        donor_ax.scatter(np.full(len(group), index), group.synthetic_signal,
                         s=18, color=registry.color(identity))
    donor_ax.set(xticks=range(3), xticklabels=list(registry), xlabel="Identity",
                 ylabel="Synthetic signal (a.u.)", title="Six donors per identity")

    for row in paired.itertuples():
        paired_ax.plot((0, 1), (row.before, row.after), "-o", color="#666666", markersize=3)
    paired_ax.set(xticks=(0, 1), xticklabels=("Before", "After"), xlabel="Condition",
                  ylabel="Synthetic signal (a.u.)", title="Six paired donors")
    return figure


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    output_dir = parser.parse_args().output_dir
    output_dir.mkdir(parents=True, exist_ok=False)
    inputs = make_inputs(output_dir)
    figure = draw_figure(*inputs)
    for extension in ("png", "pdf"):
        output = output_dir / f"styled.{extension}"
        cs.style_plot(figure, output=output)
        report = cs.check_plot(figure)
        print(f"{output}: {report['status']}; {len(report['diagnostics'])} diagnostics")
    plt.close(figure)

    broken, ax = plt.subplots(figsize=(4, 3))
    ax.scatter((0, 1), (0, 1))
    ax.set(xlabel="Synthetic X (a.u.)", ylabel="Synthetic Y (a.u.)")
    ax.xaxis.set_label_coords(0.5, -1.2)  # deliberately outside the canvas
    report = cs.check_plot(broken)
    print(f"Unexported clipped example: {report['status']}")
    for diagnostic in report["diagnostics"]:
        print(f"  {diagnostic['code']}: {diagnostic.get('text', '')!r} — {diagnostic['message']}")
    plt.close(broken)


if __name__ == "__main__":
    main()
