"""Make a synthetic, reproducible FigureSet consistency demonstration.

Run from the repository root: python3 examples/figure_set.py NEW_OUTPUT_DIRECTORY
"""

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import cellstyle as cs


SEED = 23
IDENTITIES = ("Group A", "Group B", "Group C")
COLORS = ("#1764AB", "#D43F3A", "#438B55")


def make_inputs(output_dir):
    rng = np.random.default_rng(SEED)
    cells = pd.DataFrame({
        "identity": np.repeat(IDENTITIES, 20),
        "x": rng.normal(size=60) + np.repeat((-2, 0, 2), 20),
        "y": rng.normal(size=60) + np.repeat((0, 1, 0), 20),
    })
    markers = pd.DataFrame({
        "condition": np.repeat(("Before", "After"), 9),
        "identity": np.tile(np.repeat(IDENTITIES, 3), 2),
        "marker": np.tile(("M1", "M2", "M3"), 6),
        "signal": rng.uniform(0.2, 1.8, 18),
    })
    donors = pd.DataFrame({
        "identity": np.repeat(IDENTITIES, 6),
        "donor": np.tile(np.arange(1, 7), 3),
        "signal": rng.normal(size=18) * 0.2 + np.repeat((0.8, 1.0, 1.2), 6),
    })
    for name, table in (("cells", cells), ("markers", markers), ("donors", donors)):
        table.to_csv(output_dir / f"{name}.csv", index=False)
    registry = cs.ColorRegistry()
    for identity, color in zip(IDENTITIES, COLORS):
        registry.register(identity, color)
    registry.to_tsv(output_dir / "registry.tsv")
    return cells, markers, donors, registry


def draw_set(cells, markers, donors, registry):
    figure, axes = plt.subplots(2, 2, figsize=(10, 7), layout="constrained")
    embedding_ax, before_ax, after_ax, donor_ax = axes.flat
    checked = cs.FigureSet(identity_colors=registry, comparable_quantities={"marker_signal"})
    identity_artists = {}
    for identity, group in cells.groupby("identity", sort=False):
        artist = embedding_ax.scatter(group.x, group.y, s=14, color=registry.color(identity), label=identity)
        checked.add_identity("embedding", identity, artist)
        identity_artists[identity] = artist
    embedding_ax.set(title="Synthetic embedding", xlabel="Synthetic x (a.u.)", ylabel="Synthetic y (a.u.)")
    embedding_ax.legend(frameon=False)

    marker_artists = {}
    for condition, ax in (("Before", before_ax), ("After", after_ax)):
        group = markers.loc[markers.condition == condition]
        artist = ax.scatter(group.marker, group.identity, c=group.signal, cmap="Blues", vmin=0, vmax=2, s=80)
        panel_id = f"markers_{condition.lower()}"
        checked.add_quantity(panel_id, "marker_signal", artist, unit="a.u.")
        marker_artists[condition] = artist
        ax.set(title=f"Synthetic markers: {condition}", xlabel="Marker", ylabel="Identity")
        figure.colorbar(artist, ax=ax, label="Synthetic signal (a.u.)")

    for index, identity in enumerate(IDENTITIES):
        group = donors.loc[donors.identity == identity]
        artist = donor_ax.scatter(np.full(len(group), index), group.signal, s=22, color=registry.color(identity))
        checked.add_identity("donors", identity, artist)
    donor_ax.set(title="Synthetic donor comparison", xticks=range(3), xticklabels=IDENTITIES,
                 xlabel="Identity", ylabel="Synthetic signal (a.u.)")
    return figure, checked, identity_artists["Group A"], marker_artists["After"]


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path, help="new directory for plots, reports, and exact synthetic inputs")
    output_dir = parser.parse_args().output_dir
    output_dir.mkdir(parents=True, exist_ok=False)
    figure, checked, identity_artist, quantity_artist = draw_set(*make_inputs(output_dir))
    clean = checked.check()
    assert clean["status"] == "PASS", clean
    figure.savefig(output_dir / "before.png", dpi=160)
    write_json(output_dir / "before.json", clean)
    print(f"Before: {clean['status']}")

    identity_artist.set_facecolor("#9A40B0")
    quantity_artist.set_clim(0, 3)
    broken = checked.check()
    codes = {item["code"] for item in broken["diagnostics"]}
    assert {"IDENTITY_COLOR_MISMATCH", "SCALE_MISMATCH"} <= codes, broken
    figure.savefig(output_dir / "after.png", dpi=160)
    write_json(output_dir / "after.json", broken)
    print(f"After: {broken['status']} — {', '.join(sorted(codes))}")
    plt.close(figure)

    script = Path(__file__).resolve()
    files = ("cells.csv", "markers.csv", "donors.csv", "registry.tsv", "before.png", "after.png")
    write_json(output_dir / "provenance.json", {
        "generator": str(script),
        "generator_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
        "seed": SEED,
        "synthetic_identity_ids": IDENTITIES,
        "identity_colors": dict(zip(IDENTITIES, COLORS)),
        "marker_scale_before": [0, 2],
        "deliberate_changes": {"Group A facecolor": "#9A40B0", "After marker clim": [0, 3]},
        "files_sha256": {name: hashlib.sha256((output_dir / name).read_bytes()).hexdigest() for name in files},
    })


if __name__ == "__main__":
    main()
