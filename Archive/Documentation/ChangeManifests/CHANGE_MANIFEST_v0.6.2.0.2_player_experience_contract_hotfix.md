# AthenaEngine v0.6.2.0.2 — Player Experience Contract Hotfix

## Purpose

Corrects the remaining Player Experience validation failures by ensuring the Scout response helper and composition layer always attach the canonical Experience Layer contract to player-profile payloads.

## Key Fixes

- Ensures `Scout.conversation.responses.response(...)` routes through `compose_answer_payload(...)`.
- Ensures `compose_answer_payload(...)` calls `attach_experience_contract(...)`.
- Ensures `experience_contract == athena_response_v1` is present on Scout payloads.
- Ensures player-profile payloads expose:
  - `player_profile_header`
  - `player_experience`
  - hidden `expandable_evidence_panel`
  - jersey number
  - identity fields
  - stat boxes
  - Analysis and Stats tabs
- Advances version metadata to `0.6.2.0.2`.

## Validation Targets

- `Tests/validate_experience_layer_foundation.py`
- `Tests/validate_player_experience.py`
- `Tools/doctor_experience_layer_foundation.py`
- `Tools/doctor_player_experience.py`

## Notes

This patch is intentionally narrow. It does not introduce new intelligence or UX features. It fixes the contract attachment path that was missing from the prior hotfix payload.
