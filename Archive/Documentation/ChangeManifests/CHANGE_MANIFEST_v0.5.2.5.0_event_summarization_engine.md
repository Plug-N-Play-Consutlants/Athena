# CHANGE MANIFEST — v0.5.2.5.0

## Release
Event Summarization Engine

## Summary
Adds Scout-ready event summarization on top of the existing Event Intelligence pipeline. The new engine composes canonical events, live event reasoning, timeline intelligence and confidence/corroboration metadata into executive briefs, "what changed" explanations and structured Scout payloads.

## Added
- `Engine/EventSummarization/`
  - `summary_models.py`
  - `summary_engine.py`
  - `__init__.py`
- `Tools/doctor_event_summarization_engine.py`
- `Tests/validate_event_summarization_engine.py`

## Updated
- `Core/version.py`
- `Engine/__init__.py`
- `Tools/athena_studio.py`
- `Tools/doctor_event_intelligence_foundation.py`
- `Tests/validate_event_intelligence_foundation.py`
- `CHANGELOG.md`

## Validation
- Doctor Event Summarization — PASS
- Validate Event Summarization — PASS
- Doctor Event Intelligence — PASS
- Validate Event Intelligence — PASS
- Python compile check — PASS
