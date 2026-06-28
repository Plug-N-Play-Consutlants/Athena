# AthenaEngine v0.5.5.5.9 — Scout Composition Root Fix

## Purpose

Acceptance hotfix for the persistent Scout display/composition failure where public Scout answers could still show reasoning diagnostics, cards, confidence, evidence counters, module language, and internal limitation text as if they were the user-facing answer.

## Root Cause

The prior visibility patch did not fully own the root display contract:

- `renderAnswer(...)` still selected legacy `natural_language_response` before `public_comment`.
- Some answer builders mutated `natural_language_response` after the first composition pass, leaving `public_comment` stale.
- Diagnostics were hidden cosmetically in some branches but the public body could still be composed from internal reasoning prose.
- Studio-managed Scout launch could still request more than one browser open path during launch/reload.

## Changes

- Rebuilt `Scout/conversation/composition.py` as the public/diagnostic boundary.
- Added public-copy cleanup for common internal phrases and evidence-counter leakage.
- Forced `/api/ask` and public overview responses through final composition immediately before returning JSON.
- Changed browser renderer to display `public_comment` as the only normal answer body.
- Moved confidence, cards, engine conclusion, observed facts, known limitations, raw reasoning, and developer JSON inside Developer Mode only.
- Added Studio/Scout browser-open deduplication for managed launches.
- Advanced version metadata to `0.5.5.5.9`.
- Updated affected validators to the new `public_comment_only` contract.
- Added `Tests/validate_scout_composition_root_fix.py`.

## Validation

PASS:

- `Tests/validate_scout_composition_root_fix.py`
- `Tests/validate_response_composition_visibility.py`
- `Tests/validate_renderer_cleanup.py`
- `Tests/validate_scout_runtime_acceptance_hotfix.py`
- `Tests/validate_acceptance_display_and_analysis_hotfix.py`

## Notes

This is not a new intelligence module. It is an acceptance-layer correction: public Scout output now has one canonical surface, while diagnostic evidence remains preserved for Developer Mode and debug exports.
