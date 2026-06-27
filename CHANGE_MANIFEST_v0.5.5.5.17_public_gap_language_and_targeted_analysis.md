# AthenaEngine v0.5.5.5.17 Public Gap Language and Targeted Analysis

## Purpose
Acceptance hotfix after Scout testing showed public answers still sounded like developer diagnostics for knowledge gaps and targeted team-risk questions.

## Changed Files
- `Core/version.py`
- `Knowledge/Intelligence/Public/public_answers.py`
- `Scout/conversation/router.py`
- `Tests/validate_live_event_filtering_and_analytical_routing_v055516.py`
- `Tests/validate_public_gap_language_and_targeted_analysis_v055517.py`

## Fixes
- Replaced public "knowledge pack needed" language with analyst-facing gap explanations.
- Removed public route/status cards from gap answers.
- Made draft/prospect gap answers explain required evidence without exposing route/domain internals.
- Added team-specific draft framing for Leafs draft questions without hallucinating picks/prospects.
- Made weakness/risk/problem prompts route to targeted weakness analysis instead of generic team profile language.
- Sanitized seeded-context phrasing in public analytical responses.
- Updated the previous live-event/analytical-routing validator to accept later hotfix versions.

## Validated
- `python Tests/validate_public_gap_language_and_targeted_analysis_v055517.py` PASS
- `python Tests/validate_response_composition_visibility.py` PASS
- `python Tests/validate_live_event_filtering_and_analytical_routing_v055516.py` PASS

## Notes
This does not add draft intelligence. It improves public-facing behavior when draft evidence is not attached.
