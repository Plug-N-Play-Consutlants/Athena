# AthenaEngine v0.5.3.1.4 — Knowledge.Events Compatibility Completion

## Purpose
Restore the Knowledge.Events compatibility surface required by Event Intelligence, Multi-Sport Provider Connectors, Cross-Domain Impact, Event Timeline, Event Confidence, and Event Summarization.

## Fixes
- Preserved `canonical_event_payload(...)` compatibility alias in `Knowledge.Events.normalizer`.
- Ensured `normalize_event_payload(...)` carries `league` into `EventRecord`.
- Restored `Knowledge.Events` package-level compatibility exports.
- Restored `acquire_events(...)` compatibility helper in `Knowledge.Events.acquisition`.
- Made `StaticPayloadConnector` support both newer payload-map construction and older `source_id, feed_id, payloads` construction.
- Added `FeedRegistry.discover(...)` compatibility method.
- Restored evidence-fusion compatibility aliases:
  - `FusedEvidence`
  - `fuse_events(...)`
  - `event_signature(...)`
  - `FusedEvidenceRecord.resolution_status`
  - `FusedEvidenceRecord.canonical_event`
- Restored `EventReasoningEngine.assess(...)` / `assess_many(...)` compatibility API.
- Relaxed stale exact release/version checks where hotfix versions are valid.
- Added `Tests/validate_knowledge_events_imports.py` as an early import smoke test.

## Version
- `ATHENA_VERSION`: `0.5.3.1.4`
- `ATHENA_BUILD`: `0.5.3.1.4`
- `SCOUT_VERSION`: `v0.5.3.1.4`
- `RELEASE_NAME`: `Knowledge.Events Compatibility Completion`
- `RELEASE_HOTFIX`: `4`

## Local validation in sandbox
- `Tests/validate_knowledge_events_imports.py` — PASS
- `Tools/doctor_multi_sport_provider_connectors.py` — PASS
- `Tools/doctor_cross_domain_event_impact.py` — PASS
- `Tools/doctor_event_timeline_intelligence.py` — PASS
- `Tools/doctor_event_confidence_source_corroboration.py` — PASS
- `Tools/doctor_event_summarization_engine.py` — PASS
- `Tests/validate_cross_domain_event_impact.py` — PASS
- `Tests/validate_multi_sport_provider_connectors.py` — PASS
- `Tests/validate_event_timeline_intelligence.py` — PASS
- `Tests/validate_event_confidence_source_corroboration.py` — PASS
- `Tests/validate_event_summarization_engine.py` — PASS

## Notes
This patch preserves the existing Athena Studio output scrollbar improvement. No Studio UI files are changed.
