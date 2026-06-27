# Athena v0.5.0-drop4d2d Version-Resilience Hotfix

## Purpose
Remove brittle hard-coded sprint-version expectations from Trend Engine validation/doctor checks.

## Changes
- Advanced Core version metadata to `0.5.0-drop4d2d`.
- Set Trend Engine version to `4D.2-drop4-confidence-explainability`.
- Export comparison/confidence version constants consistently.
- Updated `Tests/validate_trend_engine.py` to assert version consistency against constants/runtime output instead of historical exact drops.
- Updated `Tools/doctor_trend_engine.py` to assert version consistency instead of hard-coded old Athena versions.

## Expected validation
- `Tests/validate_trend_engine.py`
- `Tests/validate_trend_confidence.py`
- `Tools/doctor_trend_engine.py`
- `Tools/doctor_trend_confidence.py`
