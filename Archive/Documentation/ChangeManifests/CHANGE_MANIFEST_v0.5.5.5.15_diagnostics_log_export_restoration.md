# AthenaEngine v0.5.5.5.15 — Diagnostics Log Export Restoration

## Purpose
Restore the folder-first diagnostics workflow from Studio.

## Changes
- Added **Export Diagnostics Logs** to Studio Diagnostics and Developer tools.
- Added **Open Reports** to Studio so exported logs can be selected manually.
- Diagnostics export now creates a timestamped `Reports/diagnostics_export_<timestamp>/` folder.
- Export folder includes runtime summary, visible Studio output, Studio history, Scout process log, Scout session logs, recent Scout debug TXT/JSON exports, and a manifest.
- The export folder opens automatically after creation when the OS permits it.
- Added doctor/validator coverage for diagnostics log export workflow.
- Updated stale acceptance release guards and team-render validator expectations to align with the current public output contract.

## Validation
- `Tools/doctor_diagnostics_log_export_workflow.py` PASS
- `Tests/validate_diagnostics_log_export_workflow.py` PASS
- `Tools/doctor_athena_studio_operations_console.py` PASS
- `Tests/validate_athena_studio_operations_console.py` PASS
- `Tests/validate_renderer_cleanup.py` PASS
- `Tests/validate_team_reasoning_engine.py` PASS
- Runtime/live-event acceptance release guards PASS in targeted doctors/validators
