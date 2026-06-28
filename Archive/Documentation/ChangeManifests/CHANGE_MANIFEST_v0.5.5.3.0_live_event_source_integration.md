# AthenaEngine v0.5.5.3.0 — Live Event Source Integration

## Summary
Adds network-capable, test-safe live RSS event source integration on top of the validated v0.5.5.2.0 Cross-Sport Reasoning Engine baseline.

## Scope
- Added `Knowledge.Events.live_sources` with:
  - `LiveRssConnector`
  - RSS/Atom parsing
  - deterministic sample RSS payloads
  - live source/feed registries
  - explicit opt-in network acquisition
  - live source diagnostics summary
- Added live RSS feed definitions for NHL/trusted news and a configurable multi-sport RSS slot.
- Integrated live source registry evidence into cross-sport event-context reasoning.
- Exposed live source diagnostics through `Engine.Events.facade`.
- Added Studio current-sprint controls for Live Event Source Integration.
- Added Doctor/Validate scripts for the new sprint.
- Relaxed stale exact release-name checks in prior sprint validators.
- Preserved prior event, reasoning, explainability, identity, connector, and Studio compatibility.

## Validation
Sandbox checks passed:
- `Tools/doctor_live_event_source_integration.py`
- `Tests/validate_live_event_source_integration.py`
- `Tools/doctor_cross_sport_reasoning_engine.py`
- `Tests/validate_cross_sport_reasoning_engine.py`
- `Tools/doctor_explainable_intelligence_pipeline.py`
- `Tests/validate_explainable_intelligence_pipeline.py`
- `Tools/doctor_multi_sport_intelligence_foundation.py`
- `Tests/validate_multi_sport_intelligence_foundation.py`
- `Tools/doctor_multi_sport_provider_connectors.py`
- `Tests/validate_multi_sport_provider_connectors.py`
- `Tools/doctor_unified_identity_cross_sport_graph.py`
- `Tests/validate_unified_identity_cross_sport_graph.py`
- `Tools/doctor_athena_studio_operations_console.py`
- `Tests/validate_athena_studio_operations_console.py`

## Notes
Live HTTP acquisition is read-only and opt-in. Validators use static RSS payloads so development does not depend on external network availability.
