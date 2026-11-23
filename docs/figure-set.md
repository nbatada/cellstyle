# Check consistency across a Python figure set

`cs.FigureSet` records explicit links between Matplotlib artists and their meanings. Pass an identity color registry and name only the quantities whose scales should be compared. Call `add_identity(panel_id, identity_id, artist)` for each identity artist and `add_quantity(panel_id, quantity_id, artist, unit="a.u.")` for each scalar mappable. `check()` reads the artists' current colors and scales. It returns `status`, `diagnostics`, observed identities and quantities, and coverage.

Run the synthetic example from the repository root with a new output directory:

```bash
python3 examples/figure_set.py /tmp/cellstyle-figure-set-demo
```

The example draws an embedding, marker plots for two conditions, and a donor comparison. It binds the actual artists to one `FigureSet`, checks for a clean `PASS`, then changes one identity facecolor and one marker plot's color limits. The second report should contain `IDENTITY_COLOR_MISMATCH` and `SCALE_MISMATCH`. `before.png`, `after.png`, and their JSON reports show both states. Input CSVs, `registry.tsv`, and `provenance.json` retain the synthetic inputs, generator hash, seed, colors, scale limits, and deliberate changes. The output directory must be new so existing results are preserved.

Register a quantity as comparable only when its panels share a meaningful measurement. Units are compared literally; FigureSet does not convert them or establish scientific equivalence. It reports observed mismatches and does not repair artists or change plot styling. This increment is Python-only; the frozen preview remains unchanged.

## Minimal use

```python
checks = cs.FigureSet(identity_colors=colors,
                      comparable_quantities={"marker_signal"})
checks.add_identity("embedding", "Group A", group_a_points)
checks.add_identity("donors", "Group A", group_a_donor_points)
checks.add_quantity("markers_before", "marker_signal", before_points, unit="a.u.")
checks.add_quantity("markers_after", "marker_signal", after_points, unit="a.u.")
report = checks.check()
```

The artist variables above are the objects returned by your native plotting calls.
The complete linked example creates all inputs and artists. Identity colors are
copied from the registry at construction. Later edits to artists are inspected by
calling check again. Changing the scientific reference requires a new FigureSet.

PASS means the declared bindings passed these comparisons, not that the whole
figure is correct. FAIL identifies a mismatch; PARTIAL identifies insufficient or
unsupported coverage. Scalar-colored artists cannot stand in for constant identity
colors. Unbound artists are not inspected, and hidden/unsupported bound artists
cannot silently pass. A single quantity artist cannot prove cross-panel agreement.

Current quantity inspection supports scalar-colored scatter and images using
Normalize, LogNorm, TwoSlopeNorm or PowerNorm. It compares actual limits, relevant
normalization parameters and 256 colormap samples plus under/over/missing colors.
Identity checks support scatter face colors and line colors, comparing RGB rather
than opacity or point size. No biological equivalence, normalization of the input
measurements, denominator, source authority or statistical claim is inferred.

Checking draws the existing figures to resolve native encodings. Their existing
layout engines may run as on any normal draw. The checker does not change colors,
scales, data or labels and never repairs a mismatch automatically. This is separate
from check_plot, which checks individual-panel geometry, and the existing sourced
semantic-contract API. R support and persistence of live artist bindings are not
implemented in this increment.
