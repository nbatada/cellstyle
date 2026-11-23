# Cell overview (Python)

`cs.pl.cell_overview` makes one Matplotlib figure with a categorical embedding,
group labels, and a marker dot matrix. Each embedding point represents one cell.
In the matrix, dot colour shows mean expression and dot area shows the fraction
of cells above `expression_cutoff`. The guides below the matrix explain both
encodings. The function returns a native Matplotlib `Figure`.

```python
import cellstyle as cs

fig = cs.pl.cell_overview(
    adata,
    ["CD3D", "NKG7", "MS4A1"],
    groupby="cell_type",
    title="Cell identity",
    expression_label="Mean expression",
    output="cell-overview.pdf",
)
```

The default basis is `X_umap`. The default group order follows observed
categorical order; unused levels are omitted. Supply `palette` to set group
colours explicitly. Otherwise, stored `adata.uns[f"{groupby}_colors"]` colours
take precedence over native Scanpy categorical defaults. `labels` changes displayed group names
without changing group membership.

`use_raw=None` follows Scanpy's usual raw selection. Set `use_raw=False` to use
`adata.X`, or select a named `layer`. `use_raw=True` and `layer` cannot be used
together. Expression values must be finite and nonnegative. The function rejects
missing genes, repeated gene IDs, missing group values, invalid embedding
coordinates, and empty input before drawing. It does not alter the supplied
AnnData object.

The result can be adjusted with Matplotlib. For targeted changes, the axes have
labels `cellstyle.embedding`, `cellstyle.markers`, `cellstyle.expression`, and
`cellstyle.fraction`. `output=` uses CellStyle's ordinary save behavior; an
existing output is not overwritten.

This API is Python only. Technical checks establish the output contract; the
scientist still decides whether the selected genes, groups, labels, and expression
scale support the intended claim.

This implements the RIGHT direction selected in the PBMC3k comparison: direct
embedding labels, a wider marker matrix, and both guides below. It uses the native
Scanpy embedding renderer and DotPlot summary calculation. It does not add a new
schematic engine or an external runtime dependency beyond the existing Scanpy extra.

Install optional Scanpy support with `pip install 'cellstyle[scanpy]'` for a released
version that includes this API, or `pip install '.[scanpy]'` from this development
checkout. This change is currently local and not included in the frozen preview.

Only selected genes and grouping/coordinate metadata are copied for native plotting;
the complete assay is not copied. No cells are thinned. Missing or negative selected
expression fails rather than being silently filtered or clipped. Size grows with
additional markers/groups when size_mm is omitted; explicit dimensions are preserved.
Very long labels or unusually dense maps may still need inspection. The checker
reports supported text-bound and overlap issues; leader-line crossings and correct
biological label placement are not fully automated. No journal certification is implied.

`use_raw=None` uses raw when present, unless a layer is selected. Only the selected
expression matrix is validated; an unused matrix does not block a valid plot.
The data's normalization and units are not inferred: provide expression_label from
your analysis. With no explicit limits, the color range is zero to the observed
maximum mean (zero to one for an all-zero matrix). Explicit vmin/vmax override it.
