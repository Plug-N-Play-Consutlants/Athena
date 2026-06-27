# Athena v0.5.0-drop4d2d Engine Explainability Hotfix

## Files changed

- `Knowledge/Trends/engine.py`

## Fixes

- Ensures trend engine serialized results include `properties.confidence_explanation`.
- Adds `properties.explainability` alias for the structured explanation payload.
- Keeps `properties.confidence`, `properties.quality`, and `properties.confidence_engine` on each trend result.
- Preserves existing 4D.2c comparison/window/momentum behavior.
- Preserves version-resilient validation expectations for `0.5.0-drop4d2d` and `4D.2-drop4-confidence-explainability`.

## Verified locally

- `Tests/validate_trend_engine.py`: PASS
- `Tests/validate_trend_confidence.py`: PASS
- `Tools/doctor_trend_engine.py`: PASS
- `Tools/doctor_trend_confidence.py`: PASS
