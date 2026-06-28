# Athena Sports Intelligence Platform

## Version
0.5.1.1.0

## Release
Event Registry & Source Intelligence

## Scope
Epic 5 / Sprint 1 / Patch 1

## Summary
This release turns the Event Intelligence foundation into an operational Knowledge-layer subsystem. It introduces a source intelligence registry, expanded canonical event taxonomy, source-weighted event normalization, entity participation links, and graph binding for event/source/evidence relationships.

## Added
- `Knowledge/Events/source_intelligence.py`
  - SourceRegistry
  - source trust scoring
  - primary fact source filtering
  - official/trusted/provider/opinion source profiles
- `Knowledge/Events/event_graph.py`
  - event node binding
  - reported_by relationships
  - supported_by relationships
  - participated_in relationships
- `Tests/validate_event_registry_source_intelligence.py`
- `Tools/doctor_event_registry_source_intelligence.py`

## Updated
- `Core/version.py` to `0.5.1.1.0`
- `Knowledge/Events/models.py`
  - source freshness/confidence metadata
  - EventEntityLink
  - EventGraphBinding
  - source_ids on EventRecord
- `Knowledge/Events/registry.py`
  - expanded taxonomy
  - event type alias canonicalization
- `Knowledge/Events/normalizer.py`
  - source-weighted evidence confidence
  - entity link normalization
  - canonical event type mapping
- `Knowledge/Events/__init__.py`
  - exported new event/source/graph APIs
- `Tools/athena_studio.py`
  - Event Intelligence validation now points to Patch 1 validator/doctor with foundation fallback
- Foundation event validator/doctor remain backward-compatible with 0.5.1.1.0

## Validation
Local validation passed:
- `Tools/doctor_event_registry_source_intelligence.py`
- `Tests/validate_event_registry_source_intelligence.py`
- `Tools/doctor_event_intelligence_foundation.py`
- `Tests/validate_event_intelligence_foundation.py`
- Renderer validation
- Team reasoning validation
- Comparison validation
- PIF Build 004 validation
- Studio validators
- Repository doctor
- Python compile check

## Packaging
Packaged for extraction into:

```text
F:\Development
```

Expected result:

```text
F:\Development\AthenaEngine
```
