# Change Manifest — v0.5.0 Drop 3F.6

## Sprint
3F.6 — Scout Debug Export & Capability Evidence Correction

## Purpose
Make Scout/Athena alpha diagnostics exportable instead of requiring manual copy/paste from the UI, while correcting a capability-evidence parsing issue discovered during real Scout testing.

## Changes
- Added `Athena/debug_export.py`.
  - Builds a redacted debug snapshot containing workspace state, Athena status, capability dashboard, Raw/Output file health, operation history, and latest diagnostic context.
  - Writes JSON and text exports to `Reports/scout_debug_export_<timestamp>.json` and `.txt`.
  - Explicitly omits secret values and browser Cookie headers.
- Added Scout `/api/debug/export` endpoint.
- Added `Export Debug` button to Scout.
- Updated Scout version display to `v0.5.0-drop3f6`.
- Updated Athena status version to `0.5.0-drop3f6`.
- Corrected Fantrax capability detection for `league_info.json` files where teams are stored under `teamInfo`.
- Added dictionary record counting for Fantrax payloads such as `teamInfo` and `playerInfo`.
- Added validation script `Tests/validate_debug_export.py`.

## Validation
Run:

```python
runfile(
    "Tests/validate_debug_export.py",
    wdir=r"F:\Development\Athena"
)
```

Expected result:

```text
Overall status: PASS
Passed: 6
Warnings: 0
Failed: 0
```

## Notes
This patch does not change Fantrax authentication behavior or transaction access. It makes the current alpha state easier to inspect and share for debugging.
