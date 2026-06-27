# Change Manifest — v0.5.0 Drop 3F.6a

## Sprint
3F.6a — Debug Export Version Binding Hotfix

## Purpose
Fix validation failure where Scout continued to report the previous version when an environment variable or cached launch path provided an older value.

## Changes
- Updated `Scout/app.py` so `SCOUT_VERSION` is fixed to `v0.5.0-drop3f6` for this build instead of being overridable by environment state.
- Updated `Tests/validate_debug_export.py` with a regression check for the fixed version binding.

## Notes
- No debug export logic changed.
- No sync, provider, capability, or auth behavior changed.
