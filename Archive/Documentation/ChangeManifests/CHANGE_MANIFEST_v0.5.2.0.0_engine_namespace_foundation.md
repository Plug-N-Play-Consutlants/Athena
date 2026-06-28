# Change Manifest — 0.5.2.0.0 Engine Namespace Foundation

## Version

`0.5.2.0.0`

## Release

Engine Namespace Foundation

## Summary

Introduces the top-level `Engine/` namespace as the reusable deterministic algorithm layer for Athena. This does not change the locked processing pipeline and does not rename the Python package.

## Added

- `Engine/__init__.py`
- `Engine/README.md`
- `Engine/Events/__init__.py`
- `Engine/Events/facade.py`
- `Engine/Evidence/__init__.py`
- `Tools/doctor_engine_namespace.py`
- `Tests/validate_engine_namespace.py`

## Updated

- `Core/version.py`
- `Tools/athena_studio.py`
- `CHANGELOG.md`

## Architectural Contract

- `Knowledge/` remains the factual owner.
- `Engine/` owns reusable deterministic algorithms and facades.
- `Reasoning/` owns conclusions and explanations.
- `Scout/` owns presentation.

## Validation

- Doctor Engine Namespace
- Validate Engine Namespace
- Doctor Everything
- Validate Everything
