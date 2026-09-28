# v0.6.5.1.5 — Comparison Presentation Contract Alignment Hotfix

## Scope
- Align the Comparison Intelligence validator with the locked Scout Normal-mode interpretation contract introduced in v0.6.5.1.4.
- Validate user-facing comparison labels (`Career context`, `At their peaks`, `Bottom line`) rather than requiring internal reasoning-layer labels in Normal mode.
- Preserve and explicitly validate the canonical developer comparison assessment sections (`historical_comparison`, `prime_comparison`, `athena_conclusion`).
- No comparison reasoning or user-facing answer behavior is weakened or removed.

## Root cause
v0.6.5.1.4 intentionally translated internal comparison section names for Normal-mode presentation, but `validate_comparison_reasoning_engine.py` still asserted the legacy internal labels against rendered public text. The assessment data remained complete.

## Required verification
- Comparison Intelligence validator passes for player and team comparisons.
- Contextual Intelligence & Scout UX validator passes.
- Scout runtime acceptance validator passes.
- Existing v0.6.5.1.4 knowledge interpretation behavior remains intact.

## Status
Candidate pending Studio verification and runtime acceptance.
