# Change Manifest — v0.5.0 Drop 3F.1a

## Sprint
3F.1a — Scout Connection Hotfix

## Purpose
Fix a connection-time workspace update regression where Athena passed provider metadata to `update_workspace()` twice, causing Scout's Fantrax connection test to fail with:

`Athena.workspace.update_workspace() got multiple values for keyword argument 'provider'`

## Files Changed

- `Athena/connect.py`
  - Filters reserved workspace keys before passing extra provider/connect metadata into `update_workspace()`.
  - Filters inferred provider context before writing inferred league metadata into the workspace.
  - Preserves canonical `mode`, `provider`, `provider_key`, and `league_id` as explicit workspace fields.

- `Athena/workspace.py`
  - Version bumped to `0.5.0-drop3f1a`.

- `Scout/app.py`
  - Scout version label bumped to `Scout Alpha v0.5.0 Drop 3F.1a`.

- `Tests/validate_scout_connection_hotfix.py`
  - Adds a no-network fake-provider validation proving the connection path no longer throws duplicate keyword errors.
  - Confirms provider, provider key, league ID, and inferred Fantrax context persist into the workspace.

## Validation

Run:

```python
runfile(
    "Tests/validate_scout_connection_hotfix.py",
    wdir=r"F:\Development\Athena"
)
```

Expected result:

```text
Overall status: PASS
Passed: 5
Warnings: 0
Failed: 0
```

## Notes

This patch does not change Fantrax authentication strategy. It only fixes the Scout → Athena connection binding regression uncovered during alpha testing.
