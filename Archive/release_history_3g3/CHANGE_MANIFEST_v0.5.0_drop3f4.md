# Athena v0.5.0 Drop 3F.4 — Partial Sync & Capability Degradation

## Purpose
Prevent optional provider capability gaps from blocking the entire Athena sync pipeline.

## Key Behavior
- Missing or malformed Fantrax browser Cookie header no longer blocks core sync.
- Fantrax transaction authentication failures no longer fail the whole sync when league/player data is available.
- Transaction-dependent modules are skipped with explicit warnings when the transactions capability is unavailable.
- Sync returns `ok=True`, `partial=True`, and `completed_with_warnings` when required core data succeeds but optional transaction intelligence is unavailable.
- Scout renders partial sync as `League sync — partial` instead of `League sync failed`.

## Files Changed
- `Athena/sync.py`
- `Scout/app.py`
- `Scout/run_scout.py`
- `Tests/validate_partial_sync_degradation.py`
- `Tests/fixtures/fake_fetch_partial_fantrax.py`
- `Tests/fixtures/fake_build_player_pool.py`
- `Tests/fixtures/fake_build_player_master.py`

## Validation
Run:

```python
runfile(
    "Tests/validate_partial_sync_degradation.py",
    wdir=r"F:\Development\Athena"
)
```

Expected:

```text
Overall status: PASS
Passed: 9
Warnings: 0
Failed: 0
```
