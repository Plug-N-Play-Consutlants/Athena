# CHANGE MANIFEST — v0.5.0 Drop 3F.3

## Sprint
Sprint 3F.3 — Fantrax Secret Persistence & Sync Preflight

## Objective
Make the local alpha Fantrax secret flow deterministic and observable: `Test & Save Connection` must persist the auth cookie/secret to the local secrets file, and `Sync League` must verify that the same saved secret is available before entering the fetch pipeline.

## Files changed
- `Athena/connect.py`
- `Athena/workspace.py`
- `Athena/sync.py`
- `Athena/__init__.py`
- `Scout/app.py`
- `Tests/validate_fantrax_secret_persistence.py`

## Key changes
- Saves a supplied Fantrax auth cookie/secret before provider validation.
- Forces cached Fantrax provider sessions to disconnect after a newly supplied secret so subsequent validation rebuilds from `Configuration/secrets.local.json`.
- Returns safe `secret_status` metadata from connection results without exposing secret values.
- Adds a Sync preflight stage: `Validate Fantrax session`.
- If no local Fantrax secret is saved, Sync now fails with a specific reason and recommendation before fetch begins.
- Scout connection output now displays safe confirmation that the local secret was saved.
- Bumps Scout/Athena visible version to `v0.5.0-drop3f3` / `0.5.0-drop3f3`.

## Explicit non-goals
- Does not introduce a Fantrax login/browser session capture flow.
- Does not expose or prefill saved secrets in Scout.
- Does not make an invalid or expired Fantrax cookie valid.
- Does not relax transaction validation; transaction auth failures still fail Sync clearly.

## Validation
Run:

```python
runfile(
    "Tests/validate_fantrax_secret_persistence.py",
    wdir=r"F:\Development\Athena"
)
```

Expected result:

```text
Overall status: PASS
Passed: 8
Warnings: 0
Failed: 0
```
