# Athena v0.5.0-drop4b2b — Fantrax One-Click Connect Hotfix

## Fixes

- Removes brittle imports from `Athena.workspace.save_fantrax_auth` in the Fantrax connect path.
- Persists Fantrax credentials through `Core.credential_store` directly so Spyder autoreload cannot break the connection workflow when an older workspace module is cached.
- Makes the no-cookie validation scenario deterministic by preventing migration of any real repo-local cookie during that test case.
- Updates version metadata to `0.5.0-drop4b2b`.

## Validation

Run:

```python
runfile(
    "Tests/validate_one_click_fantrax_connect.py",
    wdir=r"F:\Development\Athena"
)
```
