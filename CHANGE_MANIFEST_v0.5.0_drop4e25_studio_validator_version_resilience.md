# Athena v0.5.0-drop4e25 — Studio Validator Version Resilience

## Purpose
Fix stale Studio validators/doctors that failed when Athena advanced beyond the version they were originally built against.

## Changes
- Updated `Core/version.py` to `0.5.0-drop4e25`.
- Updated `Tests/validate_athena_studio_phase1.py` to validate version metadata format and consistency instead of a hard-coded build string.
- Updated `Tests/validate_athena_studio_phase2.py` to validate version metadata format and consistency instead of a hard-coded build string.
- Updated `Tools/doctor_athena_studio_phase1.py` to accept current drop4e version metadata dynamically.

## Validation
- `python Tests/validate_athena_studio_phase1.py`
- `python Tests/validate_athena_studio_phase2.py`
- `python Tools/doctor_athena_studio_phase1.py`
