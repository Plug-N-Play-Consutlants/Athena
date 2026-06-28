# Athena v0.5.0-drop4b2a — Fantrax One-Click Connect & Persistent Credentials

## Purpose

Reduce Scout Alpha Fantrax connection friction while preserving the deterministic provider/auth boundaries.

## Changes

- Added persistent external credential store in `Core/credential_store.py`.
- Migrates `Configuration/secrets.local.json` into `~/.athena/secrets.local.json` or `ATHENA_SECRETS_FILE`.
- Keeps league secret and browser Cookie/session auth separated.
- Prevents opaque league-secret values from overwriting valid browser Cookie headers.
- Adds Fantrax guided connection workflow in `Providers/Fantrax/auth/connection_wizard.py`.
- Adds Scout `/api/fantrax/connect-and-sync` endpoint.
- Changes Scout button text to `Connect Fantrax & Sync`.
- Keeps manual Cookie header as an advanced validation bridge, not the final workflow.
- Updates version metadata to `0.5.0-drop4b2a`.
- Adds `Tests/validate_one_click_fantrax_connect.py`.

## Important Limitation

This patch does not silently scrape browser profiles or passwords. Without a captured browser Cookie/session, the one-click workflow opens Fantrax and returns a bounded `browser_session_required` state. If a valid browser Cookie is already saved, the workflow can connect and sync.

## Validation

Run:

```python
runfile(
    "Tests/validate_one_click_fantrax_connect.py",
    wdir=r"F:\Development\Athena"
)
```

Expected: 8/8 PASS.
