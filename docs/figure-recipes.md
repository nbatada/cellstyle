# Source freshness for saved Python figures

`FigureRecipe` records the exact SHA-256 hashes of a Python script and declared input files when you construct it. Construct the recipe before reading data, then pass it to an ordinary save:

```python
from pathlib import Path
import cellstyle as cs

script = Path(__file__)
data_file = Path("measurements.csv")
recipe = cs.FigureRecipe(script, inputs=[data_file], asset_id="study.figure1",
                         revision=1, command=["python3", str(script), "results-new"])
# Read measurements.csv and construct your Matplotlib figure here.
cs.style_plot(fig, output="results-new/figure.pdf", recipe=recipe)
print(cs.check_saved_plot("results-new/figure.pdf")["freshness"])
```

`cs.pl.scatter(..., output=path, recipe=recipe)` and `cs.pl.swarm(..., output=path, recipe=recipe)` accept the same recipe. The save checks the tracked files again and refuses to export if one changed during rendering. The companion receipt records the asset ID, revision, source hashes, package versions, an explicitly supplied command list, and file paths relative to the output location. The command is a record for a person to review; CellStyle never runs it.

`check_saved_plot` still verifies the saved artifact hash. Its `freshness` field reports `CURRENT` when the declared files still match, `STALE` with `changed_files` or `missing_files` when they do not, and `UNKNOWN` when no recipe was supplied. Freshness checks the declared files, not whether those files produced the pixels. It does not guarantee that the entire environment, external data, or scientific interpretation is reproducible.

Run the synthetic example from the repository root:

```bash
python3 examples/figure_recipe.py /tmp/cellstyle-recipe-new
```

Choose a new output directory each time. The example writes a CSV, a copy of the script, and a manifest before reading the CSV. It saves a PDF with a receipt, checks `CURRENT`, then deliberately appends a row to the CSV and checks `STALE`. The untouched original CSV is saved as `synthetic.original.csv` for recovery. A rerun must use a new directory and, for a new revision of an existing asset, an incremented revision; saved output paths are protected from overwrite.

This Python feature does not change the frozen preview or the R backend.

## Practical limits

Include every file that can affect the figure: plotting tables, identity registries,
settings and helper scripts as appropriate. Only declared files are checked. Hashing
streams the complete file, so prefer the exact plotting table over an unnecessarily
large raw dataset when that table is the true input. No input is silently copied or
modified by the library; the demonstration separately preserves its original CSV.

CURRENT means those file bytes match the captured hashes. Package versions are
recorded but are not an environment lock and are not part of CURRENT. Unreadable
files yield UNKNOWN. Moving the figure and all declared files together while
preserving their relative locations retains freshness checks. Missing files are
reported as STALE; a recorded command can still contain machine-specific paths.

Commands are explicit argument lists, never shell strings or automatically executed
instructions. Review the recorded command and select a fresh output filename/directory
before rerunning. The example accepts `--revision 2` for a later figure revision.
This workflow detects staleness; it does not automatically regenerate or certify
that every computation is reproducible.

The recipe also preserves the script's exact bytes in `script_snapshot` inside the
receipt (base64 encoding plus SHA-256). This lets you recover the script after an
edit. It does not snapshot data files, imported helper modules or the Python
environment; preserve those through your project's normal versioned data/code
storage. Source contents remain local and are never executed by the checker.
