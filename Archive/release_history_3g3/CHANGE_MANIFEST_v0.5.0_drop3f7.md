# Athena v0.5.0 Drop 3F.7 — Debug Download & Credential Persistence

## Purpose
Make Scout's debug export useful as a downloadable artifact and clarify/persist Fantrax local-alpha credential state without exposing secrets.

## Changes
- Added `/api/debug/download` for local report downloads from `Reports/`.
- Updated Scout's Export Debug flow to return file paths/download URLs instead of dumping the full export payload into the UI.
- Added visible export success feedback and automatic text-report download attempt.
- Persisted opaque Fantrax league secrets separately from authenticated browser Cookie headers.
- Preserved valid browser Cookie headers and prevented opaque league secrets from overwriting authenticated cookie auth.
- Extended redacted secret status to show saved credential types without exposing values.
- Added validation: `Tests/validate_debug_download_and_credentials.py`.

## Notes
- A Fantrax league secret is stored for local-alpha convenience only. It does not authenticate transaction endpoints.
- Transaction sync still requires a browser Cookie request header from an already logged-in Fantrax session.
- Debug exports intentionally omit all raw credential values.
