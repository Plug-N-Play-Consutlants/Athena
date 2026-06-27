# AthenaEngine Change Manifest

## Version
0.5.1.5.0

## Release
Multi-Source Evidence Fusion

## Summary
Adds a Knowledge-layer evidence fusion subsystem that merges duplicate event observations across sources, preserves provenance, computes source-weighted confidence, and exposes conflict records without moving reasoning conclusions into Knowledge.

## Files
- Core/version.py
- Knowledge/Events/evidence_fusion.py
- Knowledge/Events/__init__.py
- Knowledge/Events/source_intelligence.py
- Tools/athena_studio.py
- Tools/doctor_multisource_evidence_fusion.py
- Tests/validate_multisource_evidence_fusion.py
- CHANGELOG.md

## Validation
Run in Athena Studio:

```text
Doctor Everything
Validate Everything
```
