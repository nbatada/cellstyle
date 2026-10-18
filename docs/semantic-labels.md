# Scientific declarations and native text checks

CellStyle can now resolve explicitly sourced scientific metadata and check the text in an ordinary Matplotlib/Scanpy or ggplot/Seurat plot. This is an **opt-in semantic check**, not manuscript approval, exported-artifact validation or a journal certification.

Use one callback to create a native plot from resolved declarations:

```python
result = cellstyle.prepare_semantic_plot(
    draw_native, context_contract,
    mode="MANUSCRIPT_FINAL", visual_intent="manuscript", base_dir=project_root)
plot = result["plot"]  # original native callback return object
report = result["report"]
```

```r
result <- cellstyle::prepare_semantic_plot(
    draw_native, context_contract,
    mode="MANUSCRIPT_FINAL", visual_intent="manuscript", base_dir=project_root)
plot <- result$plot  # native ggplot
report <- result$report
```

`draw_native(resolved)` takes the resolved contract and returns a native plot. The Python callback uses the existing scoped CellStyle theme. An R callback adds `theme_cellstyle(visual_intent)` using ordinary ggplot composition. Existing plot objects can also be passed: they are not restyled or replaced, and `preflight_before_render` is false. Single panels do not need a layout or panel slot.

The contract is normally prepared from existing project metadata by the calling analysis workflow. **Do not ask a scientist to write a large JSON document.** Inspect their supplied labels, dictionary and verified object metadata; create facts with `semantic_fact()` and combine records with `semantic_contract()`. Ask only for missing scientific meaning. Object names and assay slots alone do not prove units, normalization, denominators, cell identity or independent n. CellStyle supplies builders and validators; it does not infer these facts, install a global skill or implement a universal automatic object-metadata extractor.

Use synthetic examples or project-controlled metadata when preparing a contract. A displayed embedding alone does not establish a calculated UMAP, cell identity, or measurement unit.

## Public functions

Both languages expose `semantic_fact`, `semantic_contract`, `read_semantic_contract`, `validate_semantics`, and `prepare_semantic_plot`. Python additionally exposes `collect_semantic_text`. The schema version is `cellstyle-semantic-1`, in `schemas/cellstyle-semantic-1.schema.json`; byte-identical copies ship in each package. The schema covers these scoped declarations and checks. `cellstyle-layout-1` remains unchanged.

A fact contains one or more candidates, each with `status`, `value`, and `source={kind,reference,revision,approved}`. Resolution order is ticket, dictionary, verified object metadata, approved proposal, unapproved proposal, unknown. Equal-priority disagreement fails; conflicting lower-priority meaning is retained as a warning. Field-level provenance must be explicit. A local reference must resolve to a file; remote-only references currently warn/fail until a local evidence file is supplied. Reference existence and a nonempty revision **do not authenticate approval or prove biological truth**. Preserve exact source records/hashes in the analysis workflow.

Statuses are KNOWN, UNKNOWN, NOT_APPLICABLE and PROPOSED. Zero is a known number, not missing. NA requires an approved explicit declaration and null value. Unknown/proposed required facts fail final checks. Neutral original labels may remain in analysis mode, with warnings; such text is not counted as verified scientific wording. `resolved.labels[].display_text` contains the known label or explicit `original` fallback, while the underlying unresolved claim is unchanged.

Identities carry exact string IDs, labels and literal colors. No palette is generated. Quantities declare entity, measure, assay, unit, denominator, applied transform, grouping and observation unit; `requires_denominator` is an explicit scientific declaration. An unknown unit/transform or missing required denominator cannot pass final checks. `actual` can supply facts from the plotted source under `quantity_id.field`; contradictory declarations fail. The validator cannot decide whether an unsupported measurement declaration is scientifically true.

Caption metadata requires a resolvable data source, independent observation unit, independent N and its definition, and scientist-authored claim ceiling (or specifically approved engineering NA). Cell counts are never promoted to patient n. Statistical text is supplied, never computed; its group/facet/subset must agree with declared and observed context.

## Results and coverage

`semantic_verdict` and `label_verdict` are independent PASS/WARN/FAIL values. Diagnostics include stable code, severity, field path and an actionable explanation. Coverage separates expected, verified, missing, unsupported and unexpected bindings, plus collector limitations. `rendered=false` cannot pass final label validation. `manuscript_ready` and `submission_ready` are always false in this release.

The validator can check declared text roles including axes, ticks, titles, legends, colorbars, facets and annotations. Native collection coverage is narrower:

- Matplotlib: visible axis titles, ordinary ticks, centered/left/right titles, axes legends, annotations and figure text. Colorbar axes, figure-level legends, extra unselected axes and unmapped native text are reported as unsupported. Occlusion, clipping and exported glyph appearance are not checked.
- R: an ordinary single ggplot's axis titles/ticks, plot title, categorical legend title/items and panel text, collected from an actually drawn offscreen grob. Facets, multiple guides, continuous colorbars, expressions and unclassified grob text cannot receive final PASS. The previous graphics device and global theme are preserved.
- Neither collector infers statistic grouping from a free-text annotation. Nonempty statistic context that cannot be observed is not verified. Low-level supplied observed records permit shared contract tests; they are not evidence that a native collector supports that surface.

Numeric ticks are exempt from individual wording declarations only when their role is numeric axis/colorbar tick. Categorical ticks and every other visible text must be declared. Duplicate observed bindings fail. Expected text hidden or absent does not become verified merely because the object contains a string.

No clinical categories, scientific labels, percentages, tests, models or significance interpretations are inferred. Legacy plots and themes continue unchanged; strict checks only run when requested.
