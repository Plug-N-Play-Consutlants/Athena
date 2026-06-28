# Athena v0.5.0-drop4e13 — Canonical Runtime / Source-Path Patch

Purpose: fix the runtime/source-path confusion that made Scout appear to run older builds after patches were applied.

## Changes

- Updates `Core/version.py` to `v0.5.0-drop4e13`.
- Updates nested compatibility `Athena/Core/version.py` to the same version.
- Adds startup/runtime path reporting to Scout.
- Adds `/api/version` fields for:
  - Scout version
  - Athena version
  - project root
  - active `Scout/app.py`
  - active `Core/version.py`
  - runtime start timestamp
- Purges `__pycache__` on launch to prevent stale module behavior in Spyder/Anaconda.
- Forces `python -B` launch through `Scout.bat`.
- Keeps `Scout.bat` and `Stop Scout Port 8765.bat` as the canonical launch controls.
- Adds `Clean Athena Runtime.bat` to remove obsolete duplicate launch helpers and Python caches.
- Keeps Fantrax controls hidden in Public Sports mode and visible in Fantasy League mode.
- Preserves the 4e10/4e11 league routing behavior.

## Apply

1. Extract into Athena root and overwrite.
2. Run `Clean Athena Runtime.bat` once.
3. Run `Stop Scout Port 8765.bat`.
4. Run `Scout.bat`.
5. In Scout, check the header/runtime line or `/api/version`; it should show `v0.5.0-drop4e13`.

## Test

- Public Sports: `Analyze Auston Matthews`
- Fantasy League: select Fantasy League, confirm Fantrax panel appears.
- Fantasy League: `Analyze my league`
