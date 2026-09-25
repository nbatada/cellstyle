# R user guide

CellStyle 0.2.0 is provisional source software. It returns native ggplot objects and additive themes, scales, and layers. Installation from GitHub `main` is described in the [README](../README.md); this is not a CRAN or stable-release claim.

## Style an existing plot

```r
library(ggplot2)
library(cellstyle)

d <- data.frame(
  condition = rep(c("control", "treated"), each = 3),
  time = rep(1:3, 2),
  response = c(1.1, 1.3, 1.2, 1.8, 1.9, 1.7)
)
identity_colors <- c(control = "#1764AB", treated = "#D43F3A")
p <- ggplot(d, aes(time, response, colour = condition)) + geom_point() +
  scale_colour_cellstyle(values = identity_colors) +
  theme_cellstyle("manuscript")
print(p)
```

These observations are synthetic. Reuse named identity mappings across figures. An observed identity missing from a supplied map raises an error when building the plot; true missing values retain native NA coloring. Use `scale_fill_cellstyle(values = identity_colors)` for fills.

`theme_cellstyle()` accepts `review`, `explore`, `manuscript`, and `presentation`, with base font sizes of 9, 9, 8, and 12 points. ggplot point sizes use millimetres, so Python marker-size numbers are not interchangeable.

`editorial_vivid(n)` supplies up to five provisional identity colors. `context_color()` supplies neutral gray. For positive magnitudes use `scale_colour_positive()` or `scale_fill_positive()`. Marker-upregulation scales are `scale_colour_marker()` and `scale_fill_marker()`; these are not validated general signed-effect scales.

Retain native Seurat `DimPlot` and `FeaturePlot` when appropriate. Themes/scales can be applied to suitable individual ggplot objects, with scale replacement chosen explicitly by the caller. **Seurat-specific and combined/patchwork behavior remains unvalidated.** There are no dedicated Seurat wrappers.

## Show biological replicates

```r
install.packages("ggbeeswarm")  # once, if not already installed
p_replicates <- replicate_distribution(
  d, x = "condition", y = "response",
  order = c("control", "treated"), palette = identity_colors,
  alpha = 0.60, point_size = 1.5
) + theme_cellstyle("manuscript")
print(p_replicates)
```

This draws a true beeswarm, open median, and IQR. Each row must represent the intended observation; CellStyle does not infer replication. Missing `ggbeeswarm` produces an error, not a substitute jitter plot.

For a quantitative scatter:

```r
print(quantitative_scatter(
  d, x = "time", y = "response", color = "#1764AB",
  alpha = 0.42, point_size = 1.5, fit = FALSE
) + theme_cellstyle("review"))
```

A linear fit is optional and requires justification from the calling analysis.

## Add labels

```r
install.packages("ggrepel")  # once, if not already installed
labels <- data.frame(time = c(1, 3), response = c(1.1, 1.7),
                     label = c("example A", "example B"))
print(ggplot(d, aes(time, response)) + geom_point() +
  repel_labels(labels, mapping = aes(time, response, label = label), seed = 0) +
  theme_cellstyle("review"))
```

## Render an existing statistical result

The number below is an illustrative API value, not a test result from these synthetic observations. Replace it with a result from your analysis. CellStyle never selects or runs a statistical test.

```r
comparisons <- data.frame(
  group_a = "control", group_b = "treated", p_adjusted = 0.018
)
print(add_comparisons(p_replicates, comparisons))
```

Supply `group_a`, `group_b`, and a `p`, `p_adjusted`, or explicit `label` column. Adjusted P takes precedence when supplied; otherwise P is used. Default labels round to three decimals below 0.01 and two otherwise, with `P < 0.001` below 0.001. Use `label` for other precision, effect sizes, or confidence intervals. Labels are literal; these quantities are not calculated.

Annotations support unfaceted categorical-x, linear-y plots. Nonlinear scales, flipped/non-Cartesian coordinates, and fixed y limits are rejected. `y_start`, `step_fraction`, and `bracket_height_fraction` control placement; the step must exceed the bracket height. Later changes to scales or limits can invalidate placement. Brackets stack but do not provide general collision avoidance. Inspect the final plot at its intended size.

## Local installation and help

From the repository root, after installing required R dependencies:

```bash
R CMD INSTALL r/cellstyle
```

Use `help(package = "cellstyle")` for package documentation. Python and R can be used independently. R has no persistent color-registry file interchange; pass named color mappings explicitly.
