# v0.5.0 Drop 1 — Athena Foundation

This drop introduces Athena as a first-class public package without changing Scout behavior yet.

## Added

- `Athena/` package
- `Athena.orchestrator.AthenaOrchestrator`
- `Athena.workspace` helpers
- `Athena.status` helpers
- Athena-specific exceptions
- `Tests/validate_athena_foundation.py`

## Public API Shape

Reserved public surface:

- `Athena.connect()`
- `Athena.sync()`
- `Athena.ask()`
- `Athena.status()`
- `Athena.workspace()`

In Drop 1, `connect()`, `status()`, and `workspace()` are active. `sync()` and `ask()` are reserved and intentionally raise `AthenaNotImplementedError` until later drops wire them into the engine.

## Notes

Scout still runs as before. This drop establishes the foundation so later v0.5.0 drops can move Scout from direct file/module behavior to Athena orchestration.
