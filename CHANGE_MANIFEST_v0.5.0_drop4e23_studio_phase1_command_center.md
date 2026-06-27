# Athena v0.5.0-drop4e23 — Studio Phase 1 Command Center

## Purpose
Promote Athena Studio from a launcher into the primary development command center so normal validation, doctor, runtime, and diagnostic work can be performed without opening a terminal.

## Changes
- Updated `Core/version.py` to `0.5.0-drop4e23`.
- Rebuilt `Tools/athena_studio.py` with grouped controls:
  - Runtime
  - Validation Center
  - Doctor Center
  - Developer Tools
- Added one-click validation commands:
  - Validate Runtime
  - Validate PIF
  - Validate Studio
  - Validate Everything
- Added one-click doctor commands:
  - Doctor Runtime
  - Doctor PIF
  - Doctor Studio
  - Doctor Everything
- Added Studio history logging to `Logs/athena_studio_history.jsonl`.
- Added Import Paths inspection.
- Added Diagnostic Bundle generation under `Reports/`.
- Preserved Scout launch/restart/stop, Runtime Audit, PIF prompt inspection, logs, and latest debug export.

## Validation
- `Tests/validate_athena_studio_phase1.py`
- `Tools/doctor_athena_studio_phase1.py`

## Extraction Target
This package includes a top-level `Athena/` folder. Extract to:

`F:\Development`

not:

`F:\Development\Athena`
