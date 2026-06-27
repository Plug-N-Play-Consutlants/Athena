# Athena v0.5.0-drop4e6 Scout JS Binding Hotfix

## Purpose
Fix Scout UI buttons appearing non-responsive after the v0.5.0-drop4e5 UX pass.

## Changes
- Fixed a JavaScript syntax error caused by an unescaped apostrophe in the Fantrax credential limitation copy.
- Added server-side Scout version interpolation so `{SCOUT_VERSION}` no longer appears in the UI.
- Updated Core version metadata to v0.5.0-drop4e6.
- Added `VERSION` compatibility alias for older launchers/validators.

## Expected Result
- Scout buttons bind again.
- Ask Scout, Sync League, Export Debug, Save/Test Connection, and Connect Fantrax & Sync should all trigger visible UI activity.
- Header displays `v0.5.0-drop4e6`.
