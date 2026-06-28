# Athena v0.5.0-drop4e4 — Scout Runtime/UI Shell Stabilization

## Scope

This patch stabilizes Scout as the local operating surface before the next intelligence build.

## Changes

- Removed the duplicate fallback Scout UI repair script embedded in `Scout/app.py`.
  - The fallback was binding `Ask Scout` a second time.
  - The second handler rendered to a missing generic response target and fell back to `alert(...)`, causing browser popups.
  - Native Scout rendering now owns all button behavior.
- Updated Fantrax credential copy from `league secret` to `Personal/Profile Secret ID` while preserving the internal storage key for compatibility.
- Added `Launch Scout.bat` as a simple double-click Windows launcher.
- Added `Stop Scout Port 8765.bat` to terminate stale local Scout listeners when needed.
- Added `Tools/build_scout_exe.py` for optional PyInstaller-based executable packaging.
- Fixed `Tools/launch_scout.py` version reporting to use `ATHENA_VERSION` and `SCOUT_VERSION` instead of the removed `VERSION` symbol.

## Validation

- `Scout/app.py` compiles.
- `launch.py` compiles.
- `Scout/run_scout.py` compiles.
- `Tools/launch_scout.py` compiles.
- `Tools/build_scout_exe.py` compiles.
- Embedded Scout HTML no longer contains the fallback `alert(JSON.stringify(...))` path.
- Native Scout event bindings remain present for Ask, Sync, Save/Test, Export, Connect Fantrax, and Ctrl/Cmd+Enter.

## Notes

This patch does not change Athena reasoning, knowledge, or intelligence outputs. It only repairs the Scout runtime/UI layer and adds easier local launch options.
