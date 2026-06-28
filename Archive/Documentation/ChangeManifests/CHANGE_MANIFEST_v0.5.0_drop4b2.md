# Athena v0.5.0-drop4b2 — Context Intelligence & Evaluation Profiles

## Sprint
Epic 4B / Sprint 4B.2

## Purpose
Introduce context intelligence so Athena can use one shared evidence layer with multiple interpretation profiles: public, fantasy, projection, and odds/probability.

## Added
- `Intelligence/Context/context_intelligence.py`
  - Evaluation profile registry
  - Profile inference from question language
  - Context dimension availability assessment
  - Profile-specific weighting
  - Scenario-aware contextual evaluation
  - Odds/probability disclaimer handling
- `Intelligence/Context/__init__.py`
- `Tests/validate_context_intelligence_profiles.py`
- `Tools/query_context_intelligence.py`

## Updated
- `Scout/conversation/router.py`
  - Player answers now attach context profile data when available.
  - Odds/projection/fantasy phrasing can route through player intelligence.
  - Developer Mode includes context profile and module execution trace.
- `Core/version.py`
  - Athena/Scout version updated to `0.5.0-drop4b2`.

## Validation
- `Tests/validate_context_intelligence_profiles.py`
- Local result: PASS 13/13

## Design Principle
One evidence graph, many evaluation profiles. Public, fantasy, projection, and odds contexts use the same facts with different weighting and output framing.
