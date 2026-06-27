# Athena v0.5.0 Drop 3F.3a — Fantrax Auth Secret Classification Hotfix

## Purpose
Clarify and harden Fantrax local alpha authentication after Scout showed that a saved value existed but transaction sync still failed authentication.

## Changes
- Added safe classification for Fantrax auth values without exposing secret contents.
- Distinguishes a parseable browser Cookie header from an opaque value/private league secret.
- Prevents malformed/opaque values from overwriting a previously saved valid browser Cookie header.
- Sync now fails early when the saved Fantrax value is not a parseable Cookie header, instead of proceeding to transaction fetch and failing later.
- Scout UI label now explicitly asks for a Fantrax browser Cookie header rather than the ambiguous “auth cookie / secret.”
- Scout context pill now reflects browser-auth readiness based on parseable cookie status.

## Validation
Run:

```python
runfile(
    "Tests/validate_fantrax_auth_secret_classification.py",
    wdir=r"F:\Development\Athena"
)
```

Expected result: PASS.

## Known Limitation
This does not implement OAuth or browser-login capture. It only makes the current local alpha cookie/session path explicit and prevents private league secrets from being treated as authenticated browser sessions.
