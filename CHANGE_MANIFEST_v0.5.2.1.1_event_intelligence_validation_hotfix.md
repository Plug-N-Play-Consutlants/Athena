# CHANGE MANIFEST — 0.5.2.1.1

**Release:** Event Intelligence Validation Hotfix  
**Repository:** AthenaEngine  
**Package:** Athena  

## Scope

Narrow hotfix for the Event Intelligence aggregate validation path after `0.5.2.1.0` Live Event Reasoning.

## Changes

- Advanced version metadata to `0.5.2.1.1`.
- Updated Multi-Source Evidence Fusion doctor/validator to accept current and future Epic 5 versions instead of pinning to `0.5.1.5.0`.
- Updated Live Event Reasoning doctor/validator to accept `0.5.2.1.x` hotfixes.
- Repaired NHL official sample entity-link payload compatibility with the canonical EventEntityLink model.
- Restored EventEntityLink label compatibility used by the event normalizer and downstream timeline/explorer views.
- Preserved all Event Reasoning, Evidence Fusion, and acquisition behavior.

## Validation Targets

- Doctor Everything
- Validate Everything
- Doctor Event Intelligence
- Validate Event Intelligence
- Doctor Live Event Reasoning
- Validate Live Event Reasoning
