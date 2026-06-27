# Change Manifest — v0.5.0 Drop 4A.1

## Sprint
4A.1 — Fantrax Header Auth Connection Integration

## Purpose
Complete the last Fantrax connection usability layer by separating the private league secret from the authenticated browser Cookie header used for transaction-market endpoints.

## Changed
- `Core/version.py`
  - Bumped Athena/Scout versions to `0.5.0-drop4a1` / `v0.5.0-drop4a1`.
- `Athena/connect.py`
  - Added explicit `league_secret` handling separate from `auth_cookie` / `cookie`.
  - Saves opaque Fantrax league secrets without treating them as browser auth.
  - Preserves valid browser Cookie headers and prevents opaque values from overwriting them.
  - Returns a successful settings-saved result when league secret is saved but browser auth is unavailable.
- `Scout/app.py`
  - Split Fantrax connection UI into league secret and browser Cookie header fields.
  - Added in-app instructions for obtaining the browser Cookie request header.
  - Sends league secret and browser Cookie header separately to Athena.
  - Improves connection status language around saved league secret vs browser auth.
- `Tests/validate_fantrax_header_auth_integration.py`
  - Validates secret classification, cookie detection, no-overwrite behavior, league-secret-only save flow, Scout UI labels, and version bump.

## Validation
Run:

```python
runfile(
    "Tests/validate_fantrax_header_auth_integration.py",
    wdir=r"F:\Development\Athena"
)
```

Expected:

```text
Overall status: PASS
Passed: 6
Warnings: 0
Failed: 0
```

## Notes
This patch does not implement automatic browser automation. It adds the final local-alpha bridge: league secret persistence plus authenticated browser Cookie header capture/storage with clear UI separation.
