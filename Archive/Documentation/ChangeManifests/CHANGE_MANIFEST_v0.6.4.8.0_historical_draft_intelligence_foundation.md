# v0.6.4.8.0 — Historical Draft Intelligence Foundation

## Objective
Convert canonical enriched historical draft observations into reusable, evidence-backed longitudinal intelligence without guessing manager identity or cross-season franchise continuity.

## Changed/New Files
- `Core/version.py`
- `Knowledge/Intelligence/Fantasy/__init__.py`
- `Knowledge/Intelligence/Fantasy/historical_draft.py`
- `Scout/conversation/orchestration.py`
- `Tools/athena_studio.py`
- `Tests/validate_historical_draft_intelligence.py`
- `Tests/validate_historical_identity_resolution.py`
- `Tests/validate_historical_scout_routing.py`
- `CHANGE_MANIFEST_v0.6.4.8.0_historical_draft_intelligence_foundation.md`

## Contracts
- Consumes `Output/Historical/<season>/draft_observations_enriched.json`.
- Preserves multi-position eligibility rather than forcing a single position.
- Permits league-level longitudinal patterns and same-season team profiles.
- Prohibits cross-season team/manager tendency attribution until franchise/manager identity is established.
- Uses coverage-aware position evidence; player-name resolution is not required for supported position findings.
- Existing `fantasy_longitudinal_draft` Scout route consumes the intelligence automatically.

## Current Evidence Result
On the canonical 2016–2025 evidence set, 1,207 of 1,247 draft selections have resolved same-season position context (96.8%). Defense appears in 17.6% of resolved round-1 observations and 50.9% of resolved round-7 observations. Overall defense share remains essentially stable between 2016–2020 (37.7%) and 2021–2025 (37.4%), preventing the round-depth pattern from being misreported as a broad era shift.

## Studio Acceptance
1. Relaunch/Reload Studio.
2. Verify Build and confirm `0.6.4.8.0`.
3. Confirm `Validate Historical Draft Intelligence` PASS within Verify Build.
4. Ask Scout: `What can you tell me about how the JHLPAA draft has changed over the last 10 seasons?`
5. Confirm `historical_draft_intelligence` appears in `intelligence_used`, evidence-backed positional findings appear, and unresolved manager/franchise attribution remains explicit.
