"""Demonstrate source freshness with a synthetic CSV.

Run: python3 examples/figure_recipe.py NEW_OUTPUT_DIRECTORY
"""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

import cellstyle as cs
import matplotlib.pyplot as plt
import pandas as pd


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path, help="a directory that does not exist yet")
    parser.add_argument("--revision", type=int, default=1, help="positive figure revision")
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=False)

    csv = output_dir / "synthetic.csv"
    csv.write_text("dose,response\n0,1.0\n1,1.4\n2,1.3\n3,2.1\n4,2.5\n", encoding="utf-8")
    original = output_dir / "synthetic.original.csv"
    shutil.copyfile(csv, original)
    script = Path(__file__).resolve()
    script_copy = output_dir / "figure_recipe.py"
    shutil.copyfile(script, script_copy)
    command = [sys.executable, str(script), str(output_dir), "--revision", str(args.revision)]
    (output_dir / "source-manifest.json").write_text(
        json.dumps({"script": str(script), "script_sha256": sha256(script),
                    "script_copy": str(script_copy), "input": str(csv),
                    "input_sha256": sha256(csv), "original_csv": str(original),
                    "command": command}, indent=2) + "\n", encoding="utf-8")

    # Construct the recipe before reading the plotted data.
    recipe = cs.FigureRecipe(script, inputs=[csv], asset_id="demo.figure1",
                             revision=args.revision, command=command)
    data = pd.read_csv(csv)
    output = output_dir / "figure.pdf"
    ax = cs.pl.scatter(data["dose"], data["response"], output=output, recipe=recipe)
    plt.close(ax.figure)
    current = cs.check_saved_plot(output)
    assert current["freshness"]["status"] == "CURRENT", current
    (output_dir / "current-report.json").write_text(json.dumps(current, indent=2) + "\n")
    print("Before input edit:", current["freshness"])

    with csv.open("a", encoding="utf-8") as handle:
        handle.write("5,3.0\n")
    stale = cs.check_saved_plot(output)
    assert stale["freshness"]["status"] == "STALE", stale
    (output_dir / "stale-report.json").write_text(json.dumps(stale, indent=2) + "\n")
    print("After input edit:", stale["freshness"])
    print(f"Original CSV: {original}")
    print(f"Saved figure: {output}")


if __name__ == "__main__":
    main()
