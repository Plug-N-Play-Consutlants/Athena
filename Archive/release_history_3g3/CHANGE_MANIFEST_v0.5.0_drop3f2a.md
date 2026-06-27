# Change Manifest — v0.5.0 Drop 3F.2a

## Sprint
Sprint 3F.2a — Diagnostics Version Binding Hotfix

## Purpose
Fix the validation failure caused by the Scout foreground launcher still exporting the older 3F.1 version string into the runtime environment.

## Changes
- Updated `Scout/run_scout.py` launcher `SCOUT_VERSION` to `v0.5.0-drop3f2`.
- Updated `Athena/workspace.py` `ATHENA_VERSION` to `0.5.0-drop3f2` so workspace metadata aligns with the active diagnostics build.

## Validation
- `Tests/validate_diagnostics_recovery.py` now passes 7/7.

## Notes
- No Sync, Provider, Scout UI, or Intelligence behavior was changed.
- This is a metadata/runtime binding hotfix only.
