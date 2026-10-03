# Correctness review receipt

Base: public `nbatada/cellstyle` main at
`2a86eafdc902149619e870afa0030f58a092507f`. Work was isolated from the private-history
checkout (`ea3c201`, `codex/r-ggplot2-backend`) and its uncommitted panel-export
and strategy changes. No private scientific datasets or background documents
were copied into this branch. Four small historical Python test modules were
restored; release metadata checks were rewritten for the current public package.

## Reproductions and fixes

The initial synthetic review suite produced 29 failures and one pass on the base.

- Categorical embedding now passes a named color mapping to Scanpy, so native
  points, legend entries, and direct labels agree under reordered categories and
  rows. Default colors follow sorted string identities; supply a named palette
  for identity persistence across datasets with different category sets. Explicit
  sequence palettes follow the requested order. Categories must be string IDs;
  explicit order must cover all categories, including unused categorical levels.
- Distribution order rejects omitted observed groups, duplicate entries, and
  missing entries before drawing. Filter data explicitly to select groups.
  Rows with missing group/value are omitted with a count warning. Unused levels
  remain supported. R already rejects omitted groups and missing group IDs.
- Supplied statistical results reject nonfinite/out-of-range P values, same-group
  comparisons, nonfinite effects, incomplete or reversed CI bounds. Rendering
  validates all groups, finite distinct positions, spacing, colors, and geometry
  before drawing. Log/symlog and non-Cartesian axes are rejected. Matplotlib does
  not expose ggplot-style facet/flip metadata; callers must supply categorical x
  positions on each ordinary linear axis. There is no automatic test computation
  or general artist collision detection. CI/effect data are metadata; use an
  explicit label to display them without a P value.
- Both embedding helpers resolve exact obsm keys first, then `X_` aliases, and
  reject invalid coordinate shape, row count, or nonfinite first-two dimensions.
- Repelled labels use adjustText's supported `force_static`. Existing
  `force_points` calls remain a compatible alias; explicit `force_static` wins.
  This helper supplies label anchors, not observation coordinates, and does not
  promise avoidance of all plotted points.
- Both embedding helpers enforce equal coordinate scaling. Focus context remains
  size 2.5, alpha 0.28, color `#E8E8E8`; the published example explicitly uses
  alpha 1.0 and size 10. Those are example overrides, not the default. Final-size
  default context is very faint; a visibility change requires design evidence.
- Related scatter-fit input guards now reject mismatched/nonvector inputs and
  fewer than two finite pairs or constant x before drawing.

## Executed validation (2026-10-03, M5)

- Python 3.11.15: **57 passed** with Scanpy 1.11.5 and adjustText 1.4.0.
  Actual Scanpy collection/legend colors were inspected by assertions across
  category ordering, row reversal, direct-label and legend modes. AnnData emitted
  ten harmless index coercion warnings from tiny fixtures.
- Python core environment without Scanpy: **48 passed, one module skipped**.
- Editable package installed from this isolated checkout; `pip check`: no broken
  requirements. Metadata tests check version and the five required dependencies.
- R 4.5.3: independent `R CMD build` and `R CMD check --no-manual`: **Status: OK**,
  including the added synthetic review contracts. Repository index requests were
  unavailable in the sandbox; all required local dependencies were installed and
  checks completed. R implementation was unchanged.
- Representative 180 mm by 61 mm synthetic PNG/PDF render inspected for named
  colors, equal geometry, faint focus context, and supplied-result brackets.
  This is technical validation, not scientist acceptance or biological evidence.
- Restored CI runs Python 3.10/3.13 with Scanpy and an R package build/check.
  Remote run status must be verified against the final pushed commit separately.

## Remaining audit findings

These are outside this correctness patch, not claimed resolved:

- Theme modes update partial rcParams, so spine/PDF settings can depend on the
  previously selected theme. An explicit full mode contract is still needed.
- ColorRegistry accepts invalid colors/IDs and overwrites duplicate IDs; TSV type
  inference can also lose identifier spelling. A registry schema and migration
  policy need a separate scoped patch.
- Python/R palette behavior differs for positive and marker heatmaps/context.
  Harmonization requires the strategy owner's visual evidence and acceptance.
- Automatic bracket/text collision detection, categorical dataset-set changes,
  and focus context visibility at final size remain explicit limitations.
