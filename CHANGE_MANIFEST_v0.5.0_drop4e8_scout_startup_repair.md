# Athena v0.5.0-drop4e8 / Scout Startup Repair

## Purpose
Stabilizes Scout launch after the button-binding hotfix and makes startup failure visible instead of silently producing browser `ERR_CONNECTION_REFUSED`.

## Changes
- Added `Scout.bat` as the primary Windows entry point.
- Updated `Launch Scout.bat` to mirror `Scout.bat`.
- Added automatic stale-listener cleanup for ports 8765-8794 before launch.
- Updated `Stop Scout Port 8765.bat` to support non-interactive cleanup.
- Updated `launch.py` to write startup failures to `Logs/scout_launch_error.txt`.
- Fixed Scout header version interpolation.
- Fixed remaining JavaScript string escaping issue around `Athena's`.
- Advanced Scout/Core metadata to drop4e8.

## Validation
- `python launch.py` starts Scout successfully in foreground mode in the patched tree.
- Scout remains available over localhost while the foreground process is alive.
