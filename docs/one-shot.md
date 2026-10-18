# One-call defaults

The normal workflow is now an ordinary plotting call, not a sequence of theme choices:

```python
ax = cs.quantitative_scatter(DF["Before score (a.u.)"], DF["After score (a.u.)"], output="scatter.pdf")
ax = cs.replicate_distribution(DF, "Group", "Signal (a.u.)", output="distribution.png")
```

```r
p <- quantitative_scatter(DF, "Before score (a.u.)", "After score (a.u.)", output="scatter.pdf")
p <- replicate_distribution(DF, "Group", "Signal (a.u.)", output="distribution.png")
```

These calls apply the existing manuscript typography, compact sizing and vivid sparse-point defaults. Scatter starts at 90×48 mm; distributions at 90×60 mm, with additional width for more groups. Both return native plotting objects. Output is optional; PDF, SVG and 300-DPI PNG are supported. Existing files and missing parent directories are reported rather than overwritten or guessed. R SVG uses the existing optional svglite package; nothing is installed silently.

For a native plot, use one styling call:

```python
ax = cs.style_plot(sns.boxplot(data=DF, x="Group", y="Signal (a.u.)"), output="box.pdf")
ax = cs.style_plot(sc.pl.umap(adata, color="cell_type", show=False))
```

```r
p <- style_plot(ggplot(DF, aes(Group, Signal)) + geom_boxplot(), output="box.pdf")
p <- style_plot(DimPlot(object, combine=FALSE)[[1]])
```

This formats the native result; it does not reconstruct the plot, change size/color encodings, add raw observations to a boxplot, fit a model or infer scientific labels. Python accepts Axes/Figure; R accepts ordinary ggplots, including native facets and a single Seurat plot. Patchwork composites are explicitly unsupported. Python preserves existing multi-axes geometry; R estimates saved facet dimensions from the native rows/columns. A complete figure compositor is not implemented by this helper.

Python named Series supply axis labels. Unnamed arrays retain neutral x/y labels; units and biological meaning cannot be inferred. Data-frame column names are retained. The caller or analysis agent should supply factual labels from trusted context, not ask the scientist to tune typography. Strict scientific/visible-label validation remains the separate opt-in semantic interface; no readiness flag is set by styling.

Native `style_plot` applies a theme as explicitly requested. The standard Python helpers treat a supplied `ax` as caller-owned: they retain its dimensions, labels and styling. Explicit size/color/alpha/order/palette remain available when deliberately needed. R explicit `size_mm` overrides its planned export size, and later ggplot theme additions remain supported. R's live viewer controls display dimensions; the stored `cellstyle_size_mm` is used when saving.

The small-system default colors in Python replicate distributions now use the existing five CellStyle anchors, matching R for the same category order. Explicit palettes take priority. This is not persistent identity allocation across changed category sets: use the existing registry for that. For more than five identities, supply an explicit palette and review the result. The D1c facade has not been restored.

No tests or regression fits run unless the existing explicit fit option is requested. Native export is a best approximation; PDF page rounding, complete clipping/contrast/glyph checks and journal-specific validation are separate. This update does not promise every plot or arbitrary composite is manuscript-ready.


Explicit Python `theme_context(...)` or `set_theme(...)` choices take precedence over automatic manuscript defaults. Switching visual intent resets inherited text-role sizes; a nested context restores its parent.
