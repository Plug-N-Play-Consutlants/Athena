# Athena Sports Intelligence Platform v0.5.1.0.0 — Event Intelligence Foundation

## Release

- Version: `0.5.1.0.0`
- Schema: `Major.Epic.Sprint.Patch.Hotfix`
- Release: `Event Intelligence Foundation`
- Epic: `5`
- Sprint: `1`
- Repository root: `AthenaEngine`
- Python package: `Athena`

## Summary

Epic 5 begins by establishing Event Intelligence as a first-class Knowledge subsystem. This release does not fetch live events and does not reason about events yet. It defines the deterministic event contract, trusted source registry, event taxonomy and normalization layer that future Fetch/Build providers will populate.

## Added

- `Knowledge/Events/`
  - `models.py`
  - `registry.py`
  - `normalizer.py`
  - `__init__.py`
- `Tools/doctor_event_intelligence_foundation.py`
- `Tests/validate_event_intelligence_foundation.py`
- `Tools/doctor_repository.py`

## Updated

- `Core/version.py`
  - switched to recognizable version `0.5.1.0.0`
  - added release metadata
  - added version schema metadata
  - added repository/package naming metadata
- `Athena/__init__.py`
  - updated public package version
- `Tools/athena_studio.py`
  - added Event Intelligence validator tile
  - added Event Intelligence doctor tile
  - added Repository Doctor tile
  - included Event Intelligence and Repository Doctor in Everything runs

## Validation

Validated from a renamed `AthenaEngine` root:

- `Tools/doctor_repository.py` — PASS
- `Tools/doctor_event_intelligence_foundation.py` — PASS
- `Tests/validate_event_intelligence_foundation.py` — PASS
- Python compile check for touched modules — PASS

## Notes

This release preserves the Python package name `Athena`; imports such as `from Athena.orchestrator import ...` remain unchanged.
