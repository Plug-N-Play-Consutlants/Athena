# Athena v0.5.0-drop4e12 — Scout JS Runtime Cleanup

## Purpose
Recover Scout from the repeated button-binding regression and reduce runtime confusion.

## Changes
- Fixed the JavaScript syntax blocker caused by the unescaped apostrophe in `Athena's`.
- Kept `Scout/app.py` and nested duplicate `Athena/Scout/app.py` aligned for this recovery patch.
- Hid Fantrax controls unless Fantasy League mode is selected.
- Opens the Fantrax panel when Fantasy League mode is selected.
- Hides `Sync League` while Public Sports mode is selected.
- Hides duplicate `Connect Fantrax & Sync` button so only one league sync path is presented.
- Added optional `Clean Athena Runtime Duplicates.bat` to remove duplicate root launch/stop files and the nested duplicate Scout app.

## Canonical Runtime Controls
Keep:
- `Scout.bat`
- `Stop Scout Port 8765.bat`

Optional cleanup removes:
- `Launch Scout.bat`
- `Stop_Scout_8765.bat`
- `Athena/Scout/`

## Validation
- `python -m py_compile Scout/app.py Athena/Scout/app.py`
- `node --check` on extracted inline Scout JavaScript
