# Assembly at physical scale 1

Prefer `assemble_svg(layout, panels, 'figure.svg')` after exporting all SVG panels.
It checks each adjacent receipt against the asset hash, layout and slot, then
embeds editable SVG artboards at their exact recorded x/y and width/height.
It namespaces element IDs to avoid collisions between clip paths. The assembly
receipt records scale 1.0 and each source asset hash. PDF panels use manual import.

1. Open the generated `figure.svg` in Inkscape. Its page already has the layout's
   whole-artwork dimensions. Keep the fonts declared by each panel installed.
2. Check the full panel artboards against their slot dimensions and positions.
   Do not resize panels to their drawing-only bounds or shrink them to fit.
3. Add assembly-owned panel letters once, using the agreed positions. The
   template does not infer letters, reserve their space or accept their placement.
4. If importing PDFs manually, use a page at the approved whole-figure size,
   retain each imported panel's page bounds, and place at its recorded x/y with
   width/height equal to the slot. Verify the imported font and physical sizes.
5. Review the whole figure, at intended print size, and at thumbnail scale.
   Then obtain scientific acceptance for the actual figure and sources.

`validate_assembly("figure.svg")` verifies that the generated file still matches
its receipt and all recorded scales equal 1.0. Any byte change invalidates it;
it does not lint an edited Inkscape document.

The receipt describes the generated assembly, not later Inkscape edits. Any
later transform, regrouping, font substitution or content edit requires renewed
review. Never reuse the generation receipt as proof about a changed final file.
Automatic SVG assembly supports CellStyle-generated SVGs, not arbitrary SVGs
with external stylesheets/scripts or hand-edited receipts. No Inkscape GUI or
real manuscript figure has been validated by the synthetic package tests.
