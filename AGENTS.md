# Agent Contract

Strategy (ChatGPTStrategy or CodexStrategy) owns visual grammar, CSD experiments,
design evidence, API semantics, roadmap, and acceptance criteria.
Implementation (CodexAnalyst/engineering) owns code, tests, packaging, CI, docs,
GitHub, releases. Implementation must not silently change evidence-backed visual
semantics.

At startup, inspect Git status, branch, and remotes; preserve unrelated work.
Read existing NORTH_STAR.md and CURRENT_STATE.md before implementation. When
present, follow the background re-entry sequence: WHY_WE_NEED_THIS.md →
NORTH_STAR.md → CURRENT_STATE.md → VISUAL_GRAMMAR.md → DEVELOPMENT_PROTOCOL.md
→ design_evidence/. These background records currently reside in the project’s
private history; do not invent their contents when absent from a checkout.
Public usage and current limitations are documented in README.md and
[the R backend guide](docs/R_BACKEND.md).

Reconcile review findings against the actual checkout. Reproduce correctness
issues with synthetic fixtures, run appropriate Python/R checks against the final
code, and inspect representative renders for visual changes. Distinguish executed
checks, unavailable checks, and scientist acceptance. Annotation helpers must
never select or run statistical tests automatically. Preserve provenance and
report unresolved findings and blockers explicitly.

At completed checkpoints, commit and push task-related changes to a working
branch. Exclude unrelated files and secrets; never force-push. Report unpushed
changes and push failures. This does not synchronize manual edits automatically
and does not authorize merging main, releases, or publication beyond the scope
explicitly requested by the user.
