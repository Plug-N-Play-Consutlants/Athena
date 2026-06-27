# Athena v0.5.0-drop4b2c — One-Click Fantrax Live Workspace Guard

## Summary
Prevents Fantrax one-click connection from using validator/demo league IDs such as `abc123` in live Scout state.

## Changes
- Added explicit placeholder league ID guard for `abc123`, `validation_league_id`, and other test IDs.
- Workspace league ID is now authoritative over fallback/button payload values.
- One-click connection returns `league_id_required` instead of opening invalid Fantrax URLs when only a placeholder ID is available.
- Added cleanup tool to remove placeholder league IDs from live workspace.
- Updated one-click validation to ensure test IDs cannot drive live navigation.
- Updated version metadata to `0.5.0-drop4b2c`.

## Validation
- `Tests/validate_one_click_workspace_guard.py` — PASS 7/7
- `Tests/validate_one_click_fantrax_connect.py` — PASS 8/8
