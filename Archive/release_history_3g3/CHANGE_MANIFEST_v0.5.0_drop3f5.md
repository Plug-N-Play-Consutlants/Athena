# CHANGE MANIFEST — v0.5.0 Drop 3F.5

## Sprint
Sprint 3F.5 — Capability-Based Synchronization

## Objective
Convert Athena sync from a binary success/failure model into capability-aware synchronization. Missing optional provider data, especially Fantrax transactions, now limits only the modules that require it instead of blocking league/team/player analysis.

## Changed Files
- `Athena/capabilities.py`
- `Athena/sync.py`
- `Athena/status.py`
- `Athena/__init__.py`
- `Athena/workspace.py`
- `Scout/app.py`
- `Scout/run_scout.py`
- `Scout/conversation/router.py`
- `Tests/validate_capability_based_sync.py`

## Behavior Changes
- Adds a provider-neutral capability assessment model.
- Adds capability dashboard data to Athena status and sync results.
- Marks unavailable transaction-dependent modules as limited/session-required rather than catastrophic failures.
- Scout sync responses now show available and limited capability counts.
- Scout manager-activity and market questions degrade gracefully when transaction evidence is unavailable.
- Developer Mode receives capability dashboard metadata.

## Validation
Run:

```python
runfile(
    "Tests/validate_capability_based_sync.py",
    wdir=r"F:\Development\Athena"
)
```

Expected:

```text
Overall status: PASS
Passed: 10
Warnings: 0
Failed: 0
```
