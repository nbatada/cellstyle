# CellStyle v0.3.0 — one-call scientific plotting in Python and R

A common plot previously needed several styling and export steps. The standard helpers now apply compact defaults in one call and optionally save the result:

```python
ax = cellstyle.quantitative_scatter(before, after, output="scatter.pdf")
ax = cellstyle.replicate_distribution(df, "Group", "Signal (a.u.)")
```

```r
p <- quantitative_scatter(df, "Before", "After", output = "scatter.pdf")
p <- replicate_distribution(df, "Group", "Signal (a.u.)")
```

`style_plot(native_plot, output=...)` applies the theme to a supported native plot. Python supports Matplotlib Axes/Figure and Scanpy results; existing multi-axes geometry is retained. R supports a single ggplot, including an individual Seurat plot. Saving is optional and refuses to overwrite a file.

This release also includes the native R ggplot2 backend, opt-in scientific label declarations and native text checks, and opt-in physical panel export and SVG assembly. These features keep scientific data and decisions with the calling analysis. See [one-call usage](one-shot.md), [R guide](R_BACKEND.md), [semantic checks](semantic-labels.md), and [panel export](panel-export.md).

The APIs and visual defaults remain provisional before 1.0. Color defaults are established for small category sets; use an explicit mapping and review for larger category sets. R patchwork composites are unsupported. No D1c facade is restored. Semantic checks do not confer manuscript readiness. Export receipts check scoped geometry and provenance, not full artifact quality, visual acceptance, or current journal compliance.

Install from tag `v0.3.0` as shown in the [README](../README.md), or use the wheel, Python source distribution, or R source package attached to the GitHub release. This page records release behavior; build and CI outcomes should be read from the release checks rather than inferred from these notes.

Explicit Python theme choices remain supported: presentation or review intent is not overwritten by one-call manuscript defaults.
