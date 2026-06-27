# Athena v0.5.0 Drop 3G.0 — Runtime Hygiene Phase 1

## Purpose
Stop live Alpha state contamination before deeper cleanup. This patch does not redesign Athena and does not remove working engine layers. It establishes a safer runtime baseline so Scout no longer falls back to validation workspace state.

## Changes
- Added `Core/version.py` as the single active version source for Athena, Scout, and debug export.
- Updated Athena/Scout version consumers to use the shared version source.
- Hardened `Athena.workspace` normalization:
  - recognizes `validation_league_id` and other test placeholders,
  - replaces placeholder league IDs with the configured provider league ID when available,
  - strips validation fixture entries from live operation history,
  - refreshes workspace engine version consistently.
- Added `repair_workspace_file()` for explicit runtime repair.
- Updated Fantrax connection flow so the league ID/workspace is saved before browser-cookie validation.
- Changed opaque Fantrax league-secret handling from failed persistence to saved workspace + saved league secret + warning that transaction auth still requires a browser Cookie header.
- Reset committed `Configuration/workspace.json` to a clean runtime baseline.
- Replaced committed `Configuration/secrets.local.json` with an empty local-alpha scaffold.
- Added `Tools/cleanup_3g_phase1_runtime.py` to repair live workspace state after applying the patch.
- Added `Tests/validate_3g_phase1_runtime_hygiene.py`.

## Validation
Run:

```python
runfile(
    "Tools/cleanup_3g_phase1_runtime.py",
    wdir=r"F:\Development\Athena"
)

runfile(
    "Tests/validate_3g_phase1_runtime_hygiene.py",
    wdir=r"F:\Development\Athena"
)
```

Expected result: PASS with a warning if duplicate legacy roots are still present. Duplicate roots are intentionally reported, not deleted, in Phase 1.

## Known Remaining Cleanup
- Duplicate legacy roots remain and should be handled in a later 3G phase.
- Generated `Raw/`, `Output/`, `Reports/`, and `Logs/` clutter still exists.
- Several older validation scripts still assert historical version strings and should not be used as current 3G validators.
- Player master data quality still needs a dedicated builder-validation patch.
