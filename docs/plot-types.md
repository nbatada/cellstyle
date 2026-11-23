# Choose a CellStyle plot

Start with the comparison the reader needs to make. All these helpers return editable native plots. Python accepts an optional output path and FigureRecipe. R accepts an optional output path. Use a fresh filename to save a figure.

| Reader's question | Python | R | What to supply |
|---|---|---|---|
| How are measurements distributed within each group? | `cs.pl.boxplot` | `box_distribution` | One row per observation. A box and 1.5-IQR whiskers summarize the data. The point layer includes the extremes. Optional hue shows subgroups. |
| What shape does the distribution suggest? | `cs.pl.violin` | `violin_distribution` | Individual values. Each density ends at its observed range. Width shows the estimated shape within that group. Inspect raw points before interpreting a second peak. |
| How do subgroups compare within a site or condition? | `cs.pl.grouped_swarm` | `grouped_swarm` | Site, subgroup and one measurement per row. Horizontal displacement separates overlapping observations. An open point and line show the median and IQR. |
| Which individuals changed between visits? | `cs.pl.paired` | `paired_distribution` | A subject ID, visit and value. Supply visit order explicitly or use ordered categories. Each line connects a subject's observed adjacent visits. A missing visit is a missing row. Duplicate subject–visit rows require resolution before plotting. |
| Is expression widespread, intense, or both? | `cs.pl.dotplot` | `marker_dotplot` | Two aligned tables, identities by markers. Dot area represents the fraction passing the declared cutoff. Color shows mean expression. Supply fractions in [0,1]. Name the cutoff, denominator, and expression scale in the guides. |
| Where are the high and low values in a matrix? | `cs.pl.heatmap` | `marker_heatmap` | A labeled numeric table and a scale description. Positive expression uses sequential blue. Set `scale="marker"` for signed scores with a meaningful zero. Row/column order is preserved. |
| Does a pattern repeat across groups or conditions? | `cs.pl.facet` | `facet_plot` | Row and/or column groups plus x and y. Use shared axes with `kind="swarm"` or `kind="scatter"`. Empty combinations are visible. Panel n counts supplied observations. |
| How large are the effects, and how uncertain are they? | `cs.pl.forest` | `forest_plot` | A row label, a supplied estimate, two bounds and the interval definition. Choose a reference and log axis explicitly when the estimand calls for them. |

### Use the public entry points

```python
import cellstyle as cs

ax = cs.pl.paired(visits, pair="donor", x="visit", y="CD8 frequency (%)",
                  order=["Baseline", "Week 4"], output="paired.pdf")
ax = cs.pl.boxplot(samples, "site", "Signal (a.u.)", hue="condition")
ax = cs.pl.dotplot(means, fractions, colour_label="Mean log1p expression",
                   size_label="Cells with expression > 0")
ax = cs.pl.heatmap(centered_scores, scale="marker", scale_label="Centered marker score")
fig = cs.pl.facet(samples, "condition", "Signal (a.u.)", col="site")
ax = cs.pl.forest(estimates, "Contrast", "Risk ratio", "Lower", "Upper",
                  interval_label="95% CI", reference=1, log_scale=True)
```

```r
library(cellstyle)
p <- paired_distribution(visits, "donor", "visit", "CD8 frequency (%)",
                         order = c("Baseline", "Week 4"))
p <- marker_dotplot(means, fractions, "Mean log1p expression",
                    "Fraction of cells with expression > 0")
p <- facet_plot(samples, "condition", "Signal (a.u.)", col = "site")
```

Means and fractions use the same identity and marker axes. In Python supply pandas DataFrames. In R supply named numeric matrices or numeric data frames with explicit row names. Scanpy users can obtain both summaries from one native DotPlot over the chosen assay, gene list, grouping and cutoff. Verify that the selected raw slot actually stores the measurement named in the color guide.

```python
import scanpy as sc

native = sc.pl.DotPlot(adata, markers, groupby="cell_type",
                       use_raw=True, expression_cutoff=0)
ax = cs.pl.dotplot(native.dot_color_df, native.dot_size_df,
                   colour_label="Mean log1p expression",
                   size_label="Cells with expression > 0")
```

The two backends share scientific conventions and have native typography, density, guide and layout behavior. R swarm layers use the optional ggbeeswarm package. The data determine the unit of observation. For a donor comparison, supply one relevant observation per donor and condition. A figure of thousands of cells alone cannot establish variation across donors.

### See the plots and refine them

[Rendered Python and R examples](gallery.md)

For existing categorical embeddings, focus views, quantitative scatter, single-group swarms and the combined cell overview, see the [existing examples](../README.md).

### Label an existing embedding

Keep the native point plot. In Python add `cs.label_groups(ax, x, y, identities, short_labels=aliases)`. In R add `geom_cell_labels(aes(label = identity), short_labels = aliases)` to a ggplot with x and y mapped. A Python dictionary or named R character vector can supply accepted alternate names for a subset of identities. Inspect the final render when a cluster splits across distant islands or several identities occupy the same area. One observed anchor per identity cannot identify every island. [PBMC3k label comparison](showcase/comparison-65mm.png)

### Save paper and slide copies

`cs.save_for_paper_and_slides(ax, "figure-1")` and `save_for_paper_and_slides(p, "figure-1")` preserve the plot's manuscript dimensions and export an SVG fitted to a slide placement box. The default box is 250 × 145 mm. The receipt records a 16-pt minimum slide-text target and the measured size at that placement. Review the smaller lettering if a plot is placed at a different size. Python uses the export extra; R requires svglite, xml2, digest and jsonlite for delivery. Both use a fresh directory. [Example PowerPoint file](showcase/placement-example.pptx)

### Outline one or all Leiden clusters on a marker map

Keep color available for expression. The outline is a smoothed footprint of the assigned cells in the supplied 2D embedding. A disconnected footprint can have two rings with the same cluster ID. Isolated cells remain drawn even when they fall outside a ring.

```python
ax = sc.pl.umap(adata, color="NKG7", show=False)
cs.cluster_outline(ax, adata, groupby="leiden", clusters=["4"])
# Omit clusters to draw all observed groups on a fresh map.
```

```r
p <- ggplot(cells, aes(x = UMAP1, y = UMAP2)) +
  geom_point(aes(colour = NKG7)) + coord_equal()
p + geom_cluster_outline(aes(group = leiden), clusters = "4")
p + geom_cluster_outline(aes(group = leiden))
```

For several marker panels, compute paths **once from the full embedding** and reuse them at the same coordinates. Python takes a DataFrame and R takes a data frame; both return a table with `cluster`, `path`, `x`, and `y`.

```python
paths = cs.cluster_outlines(cells, "UMAP1", "UMAP2", "leiden", clusters=["4"])
cs.cluster_outline(ax, paths=paths)
```

```r
paths <- cluster_outlines(cells, "UMAP1", "UMAP2", "leiden", clusters = "4")
p + geom_cluster_outline(paths)
```

The default contour encloses a level set of a Gaussian-smoothed density with approximately 90% of the **grid density mass**. The fraction of observed members inside can differ from 90%. Bandwidth defaults to 3.5% of the full embedding's longest axis span and is expressed in coordinate units. Increasing it can merge islands. Other clusters can occupy the same 2D region. Use equal coordinate aspect and reuse paths only on plots of the same embedding. [Real Leiden example](showcase/python-one-and-all.png)

For neighboring Leiden groups within one dense island, try `method="territory"` in either backend. It compares smoothed counts from all observed groups at each grid position, retains the locally leading group's supported density region, and draws a narrow gap between adjacent bands. No cell labels change. A minority group can have many cells but no drawable band at a given scale. Use the full dataset as input even if you select just one ID. Check the colored point map alongside the outlines. [NSCLC comparison with ggforce](showcase/nsclc-all-clusters.png)
