# AthenaEngine Change Manifest

## Version
0.5.2.3.0

## Release
Event Timeline Intelligence

## Summary
Introduces a first-class Event Timeline Intelligence engine under the Engine namespace. Athena can now group related canonical events by subject, order them chronologically, build timeline nodes and links, generate deterministic narratives, and expose timeline reasoning payloads for future Scout and Intelligence-layer consumption.

## Added
- `Engine/EventTimeline/__init__.py`
- `Engine/EventTimeline/timeline_models.py`
- `Engine/EventTimeline/timeline_builder.py`
- `Engine/EventTimeline/timeline_reasoning.py`
- `Tools/doctor_event_timeline_intelligence.py`
- `Tests/validate_event_timeline_intelligence.py`

## Updated
- `Core/version.py`
- `Engine/__init__.py`
- `Tools/athena_studio.py`
- `Tools/doctor_event_intelligence_foundation.py`
- `Tests/validate_event_intelligence_foundation.py`
- `CHANGELOG.md`

## Validation
- Doctor Event Timeline
- Validate Event Timeline
- Validate Event Intelligence aggregate
- Python compile check

## Packaging
Extract to `F:\Development`; files land in `F:\Development\AthenaEngine`.
