# CHANGE MANIFEST — v0.5.0-drop3f0

## Sprint
Sprint 3F.0 — Alpha Experience Launch Foundation

## Goal
Make Athena easier and safer to validate by establishing one supported local launch path and ensuring Scout's Fantrax connection flow persists the active workspace through Athena.

## Changes
- Added root-level `launch.py` as the canonical local Athena/Scout entry point.
- Added Windows convenience launcher `launch.bat`.
- Updated `Scout/run_scout.py` to advertise the new canonical launch path and version.
- Updated Scout version to `v0.5.0-drop3f0`.
- Added a thin `test_fantrax_connection()` Scout binding that delegates Fantrax connection and workspace persistence to `Athena.connect_fantrax()`.
- Preserved Athena ownership of provider resolution, local secret storage, and workspace persistence.
- Added validation script for launch layer and workspace persistence behavior.

## Files Added
- `launch.py`
- `launch.bat`
- `Tests/validate_alpha_launch_experience.py`
- `CHANGE_MANIFEST_v0.5.0_drop3f0.md`

## Files Modified
- `Scout/app.py`
- `Scout/run_scout.py`
- `Athena/__init__.py`
- `Athena/status.py`
- `Athena/workspace.py`

## Notes
This patch does not implement provider session/OAuth/auth-cookie improvements. It only removes launch ambiguity and verifies that the current Scout connection path can persist workspace configuration via Athena.
