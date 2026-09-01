# CHANGE MANIFEST — v0.6.3.0.1

## Release

Foundational Governance Cleanup Tolerance Hotfix

## Purpose

Fixes the two Studio-visible failures introduced by the v0.6.3.0.0 foundational governance patch.

The failures were both caused by the same root-history cleanup rule: the v0.6.3.0.0 change manifest remained at repository root after extraction. Patch extraction cannot reliably delete or move a pre-existing root file, so the consensus cleanup doctor must tolerate this known root-history residue until Studio Safe Cleanup archives it.

## Changes

- Advanced version metadata to `0.6.3.0.1`.
- Updated `Tools/doctor_consensus_repository_cleanup.py` to tolerate the v0.6.3.0.0 root change manifest as known cleanup residue.
- Added archived copy of the v0.6.3.0.0 foundational governance manifest.
- Added this hotfix manifest directly under `Archive/Documentation/ChangeManifests/`.
- Updated Epic 6/foundational validators and doctors to accept the hotfix release name.

## Expected Result

The following gates should pass after applying this patch:

- `Tools/doctor_consensus_repository_cleanup.py`
- `Tests/validate_consensus_repository_cleanup.py`
- `Tools/doctor_foundational_governance.py`
- `Tests/validate_foundational_governance.py`
- `Tools/doctor_experience_layer_foundation.py`
- `Tests/validate_experience_layer_foundation.py`
- `Tools/doctor_player_experience.py`
- `Tests/validate_player_experience.py`
- `Tools/doctor_scout_intent_orchestration.py`
- `Tests/validate_scout_intent_orchestration.py`

## Notes

This hotfix does not change Athena runtime behavior. It only aligns release hygiene gates with the Studio-first safe cleanup workflow.
