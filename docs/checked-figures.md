# Check a Python figure and keep its receipt

`cellstyle.check_plot(plot)` checks supported visible layout defects in a native Matplotlib `Figure` or `Axes`. It returns a dictionary with `status` (`PASS`, `WARN`, or `PARTIAL`), `diagnostics` (each with a `code` and `message`, and an axes index when relevant), `coverage` (checked surfaces and limitations), and `size_mm`. A clean check describes only those surfaces. It does not certify scientific labels, data, statistical claims, or manuscript readiness.

For an existing plot, style and save it through the ordinary output argument:

```python
import cellstyle as cs

cs.style_plot(fig, output="figure.pdf")
report = cs.check_plot(fig)
print(report["status"], report["diagnostics"])
```

Saving also writes `figure.pdf.cellstyle.json`. This receipt records the layout check and identifies source provenance as unknown unless supplied through a separate scientific workflow. It does not infer inputs from artists or filenames. Use the existing semantic contract APIs when factual labels and their provenance need validation; a layout receipt does not replace those checks.

Run the complete synthetic example from the repository root:

```bash
python3 examples/checked_figure.py /tmp/cellstyle-checked-example
```

The output directory must be new. The example writes four input CSVs, a reusable `registry.tsv`, and `styled.png` and `styled.pdf` with a receipt for each export. It reuses registry colors across panels and gives every axis and colorbar an explicit synthetic label. The native plot starts with a legend over observations; `style_plot` applies its bounded layout correction. A separate deliberately clipped plot calls `check_plot` and prints its diagnostic without exporting it. Inspect the files and reports: a technical check cannot establish that a visual is scientifically accepted.

This first workflow is Python-only. The existing R plotting and semantic APIs remain separate, as does the frozen 0.4 preview scope. Unsupported layout surfaces are reported as limitations rather than silently treated as checked.

Check a saved report later with `cs.check_saved_plot("figure.pdf")`. This verifies
the current file hash before returning the receipt; edited bytes make the report
stale. It does not authenticate the report or establish source-data provenance.
Both output and companion paths must be unused. Save failures do not leave a new
partial pair. Remove or archive both deliberately before reusing a filename.

Canvas checks run before export. PNG dimensions and SVG physical dimensions are
read back from saved files. PDF measurements/font inspection use the optional
`pypdf` dependency; missing or unsupported PDF inspection is recorded as unverified.
The canvas PASS status does not imply that exported-font inspection passed.
Existing exact-size `export_panel` receipts remain a separate, stricter workflow.
