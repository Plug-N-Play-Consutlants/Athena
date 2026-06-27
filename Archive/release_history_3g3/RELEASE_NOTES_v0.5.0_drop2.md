# v0.5.0 Drop 2 — Athena Workspace + Connect

## Purpose

Move provider connection ownership out of Scout and into Athena.

Scout and future consumers should call Athena's public API instead of writing
workspace/secrets files or instantiating provider clients directly.

## Added

- `Athena/connect.py`
  - `connect_fantrax()`
  - `infer_fantrax_context()`
- `Tests/validate_athena_connect.py`

## Updated

- `Athena/orchestrator.py`
  - `athena.connect()` now owns Fantrax workspace/secret persistence.
- `Athena/workspace.py`
  - Adds safe local secret persistence helpers.
  - Adds workspace normalization for legacy flat workspace files.
- `Athena/status.py`
  - Updates Athena version to `0.5.0-drop2`.
- `Athena/__init__.py`
  - Exposes connection helpers.
- `Scout/app.py`
  - Fantrax connection endpoint delegates to `Athena.connect()`.
  - Scout context reads Athena status/workspace metadata.

## Not included

- `athena.sync()` remains reserved for Drop 3.
- `athena.ask()` remains reserved for Drop 4.
- Scout still uses its existing analysis/ask routes until the sync and ask drops are implemented.

## Validation

Run:

```python
runfile('F:/Development/Sports_Intelligence_Engine_2.0/Tests/validate_athena_connect.py', wdir='F:/Development/Sports_Intelligence_Engine_2.0')
```
