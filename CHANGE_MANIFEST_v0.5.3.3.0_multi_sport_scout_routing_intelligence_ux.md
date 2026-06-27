# AthenaEngine v0.5.3.3.0 — Multi-Sport Scout Routing & Intelligence UX

## Baseline
Built from the Studio-validated PASS baseline v0.5.3.2.0.

## Changes
- Added deterministic sport-aware Scout routing helpers under `Knowledge.Intelligence.Routing.multi_sport_router`.
- Added route metadata for sport, league, intent, entity labels, source routing, ambiguity, confidence, and evidence.
- Integrated public Scout mode with multi-sport route cards for cross-sport context, event-context, and ambiguous identity prompts.
- Preserved deeper PIF/player/team handlers for richer already-supported public hockey responses.
- Consolidated Athena Studio validation/doctor buttons so the UI emphasizes:
  - Validate Everything
  - Validate Studio
  - Validate Current Sprint
  - Doctor Everything
  - Doctor Studio
  - Doctor Current Sprint
  - Doctor Repository
- Kept all underlying individual doctor/validator methods and scripts available for `Doctor Everything`, `Validate Everything`, and direct developer use.
- Preserved Studio output scrollbar and v0.5.3.1.x Knowledge.Events compatibility fixes.

## Validation
- `Tools/doctor_multi_sport_scout_routing.py`
- `Tests/validate_multi_sport_scout_routing.py`
