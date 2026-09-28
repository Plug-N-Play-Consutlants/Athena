# AthenaEngine v0.6.4.1.5 — Validation Release Gate Alignment Hotfix

## Scope
Validation-only hotfix plus release metadata alignment. No Scout, Experience, Reasoning, Knowledge, provider, or fantasy runtime behavior is changed.

## Changes
- Advance Athena/Scout/build metadata from `0.6.4.1.4` to `0.6.4.1.5`.
- Set release name to `Validation Release Gate Alignment Hotfix`.
- Remove stale historical release-name allowlists from the three validators that failed solely because `Fantasy State Reconciliation Hotfix` was newer than their hard-coded lists.
- Retain each validator's existing version/schema/behavior assertions; only the brittle release-name gate is changed to require populated release metadata.

## Replacement files
- `Core/version.py`
- `Tests/validate_experience_layer_foundation.py`
- `Tests/validate_player_experience.py`
- `Tests/validate_scout_intent_orchestration.py`

## New file
- `CHANGE_MANIFEST_v0.6.4.1.5_validation_release_gate_alignment_hotfix.md`

## Acceptance
1. Restart/reload Athena Studio after overlay extraction.
2. `Verify Build` reports Athena, Scout, and Build `0.6.4.1.5` with release `Validation Release Gate Alignment Hotfix`.
3. `Validate Everything` completes with zero failures.
4. Existing substantive Experience, Player Experience, and Scout Intent assertions remain green.
