# Change Manifest — v0.5.5.5.19

## Release

Evidence Path Audit and Program Structure Direction

## Purpose

Create the first canonical evidence-path traceability audit before adding more intelligence modules or performing large structural reorganization.

## Added

- `docs/EVIDENCE_PATH_AUDIT_v0.5.5.5.19.md`
- `docs/PROGRAM_STRUCTURE_DIRECTION_v0.5.5.5.19.md`
- `Tools/doctor_evidence_path_audit.py`
- `Tests/validate_evidence_path_audit_v055519.py`

## Changed

- `Core/version.py` advanced to `0.5.5.5.19`.
- Root `__init__.py` now derives `__version__` from `Core.version.ATHENA_VERSION` to prevent stale root package metadata.

## Notes

This is an audit/traceability build. It does not add a new reasoning subsystem. The audit identifies that existing validated subsystems are not all participating in the public Scout answer path.
