# Athena v0.5.0-drop4e9 — Fantrax Connection + Version Fix

## Purpose
Repair the Fantrax connection failure introduced by duplicate workspace keyword updates and harden Scout version rendering.

## Changes
- Fixed `Athena.connect_provider()` so inferred Fantrax context cannot pass `provider` into `update_workspace()` a second time.
- Advanced version metadata to `0.5.0-drop4e9`.
- Replaced `{SCOUT_VERSION}` token server-side before serving Scout HTML.
- Collapsed the Fantrax connection panel by default to reduce initial UI clutter while keeping it available.

## Expected Result
- `Save / Test Connection` should no longer fail with `update_workspace() got multiple values for keyword argument 'provider'`.
- Scout header should display `v0.5.0-drop4e9`.
- Existing public/player analysis behavior is preserved.
