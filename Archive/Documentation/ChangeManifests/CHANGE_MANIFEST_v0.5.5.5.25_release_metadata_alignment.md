# v0.5.5.5.25 — Release Metadata Alignment

## Purpose
Align Studio doctor and validator release metadata checks with the canonical `Core.version` source of truth.

## Changes
- Advanced canonical Athena/Scout/build metadata to `0.5.5.5.25`.
- Updated release name to `Release Metadata Alignment`.
- Relaxed legacy release-name allowlists so doctors validate metadata presence and version compatibility instead of hard-coded historical release names.
- Added release metadata doctor and validator.
- Preserved cleanup behavior; no repository cleanup or archive actions are performed by this patch.
- Corrected targeted contender routing so prompts such as `Why are the Oilers contenders?` use bounded analytical routing instead of only the team profile path.

## Validation Target
- `Tools/doctor_release_metadata_alignment.py`
- `Tests/validate_release_metadata_alignment.py`
- Runtime orchestration doctor/validator
- Scout runtime acceptance doctor/validator
- Live event source integration doctor/validator
