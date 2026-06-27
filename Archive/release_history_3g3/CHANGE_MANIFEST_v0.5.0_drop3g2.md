# CHANGE MANIFEST — v0.5.0-drop3g2

## Sprint
3G Phase 2 — Repository Residue Cleanup & Doctor

## Purpose
Remove legacy root contamination and validation/runtime residue after the 3G runtime hygiene reset.

## Added
- `Tools/cleanup_3g_phase2_residue.py`
- `Tools/doctor.py`
- root `doctor.py` convenience launcher
- `Tests/validate_3g_phase2_residue_cleanup.py`

## Changed
- `Core/version.py` updated to `0.5.0-drop3g2` / `v0.5.0-drop3g2`.
- `.gitignore` hardened for secrets, runtime artifacts, and Python cache.

## Cleanup behavior
The cleanup script removes:
- top-level legacy `Sports_Intelligence_Engine_2.0` root inside Athena
- nested copied project roots inside the `Athena/` Python package
- Python `__pycache__` and `.pyc` files
- validation/test entries from live workspace operation history

The cleanup script preserves:
- `Raw/`, `Output/`, `Reports/`, and `Logs/` contents
- `Configuration/secrets.local.json`
- active source package modules
