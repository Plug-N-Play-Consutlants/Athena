# AthenaEngine v0.5.6.1.0 Capability Registry Foundation

## Summary

Adds the first Epic 5B.0 observability slice: repository-discovered capability registry foundation.

## Changed/New Files

- Core/capability_registry.py
- Core/__init__.py
- Core/version.py
- Tools/doctor_capability_registry.py
- Tests/validate_capability_registry.py
- Tools/athena_studio.py

## Notes

This build is intentionally observability-only. It does not change Scout routing or answer behavior. It gives Studio a live inventory of capabilities, layers, doctors, validators/tests, entrypoints, and metadata health.
