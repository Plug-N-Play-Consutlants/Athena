# Change Manifest — v0.5.5.5.23 Core Namespace Recovery

## Purpose

Restore the root `Core/` namespace expected by Athena runtime modules, Studio doctors, validators, launchers, and build scripts.

## Files Added

- `Core/__init__.py`
- `Core/config.py`
- `Core/constants.py`
- `Core/credential_store.py`
- `Core/json_utils.py`
- `Core/knowledge_builder.py`
- `Core/logger.py`
- `Core/project_paths.py`
- `Core/version.py`
- `Tools/doctor_core_namespace_recovery.py`
- `Tests/validate_core_namespace_recovery.py`

## Files Modified

- `Intelligence/Core/version.py`
- `Tools/doctor_studio_repository_operations.py`

## Notes

`Intelligence/Core/` is retained for now as a legacy namespace candidate. No deletion or migration is performed in this patch.

The root `Core/` namespace is restored because active Athena modules import `Core.*` directly. Removing or omitting it creates runtime failures in Studio, Scout, build scripts, and validation tools.

## Validation

Run:

```text
python Tools/doctor_core_namespace_recovery.py
python Tests/validate_core_namespace_recovery.py
python Tools/doctor_repository_governance.py
python Tests/validate_repository_governance.py
```
