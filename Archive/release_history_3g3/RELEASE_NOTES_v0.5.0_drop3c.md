# v0.5.0 Drop 3C — Scout Foreground Launcher Fix

This corrective drop stabilizes Scout local launching in Spyder.

## Fixed
- Replaced hidden subprocess launching with a foreground launcher.
- `Scout/app.py` now honors `SCOUT_PORT` and `SCOUT_VERSION`.
- Added `/api/version` and `/api/health`.
- Added visible `Scout Alpha v0.5.0 Drop 3C` badge.
- Added optional Windows stale-process helper.

## Why
The previous launcher selected an available port but `Scout/app.py` still bound to its internal default port in the active repo. This caused the browser to open one port while Scout listened on another, or to hit stale servers.
