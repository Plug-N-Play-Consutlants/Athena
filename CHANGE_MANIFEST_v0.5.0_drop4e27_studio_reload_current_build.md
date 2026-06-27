# Athena v0.5.0-drop4e27 — Studio Reload Current Build

## Purpose
Fix Studio runtime reload behavior after applying patches. Studio should be able to stop Scout, clear stale runtime data, re-read the current build metadata, and launch Scout from the current patched source without requiring a Studio restart for Scout reloads.

## Changes
- Added Studio **Reload Patched Build** workflow.
- Made Studio version display dynamic by re-reading `Core/version.py` during runtime operations.
- Made Restart Scout use the same full reload workflow instead of delayed stop/launch.
- Added synchronous Scout stop and port-clear wait before launching.
- Added Python cache purge for `__pycache__` and `.pyc` before managed Scout reload.
- Added strict-port managed launch so Studio does not silently launch Scout on a different port while the browser opens the old instance.
- Added build/version cache-busting to browser URL.
- Added reload workflow validator and doctor.
- Updated runtime cleanup semantics: `Athena/` is an expected engine package unless it contains runtime duplicates such as `Athena/Core` or `Athena/Scout`.

## Validation
- `Tests/validate_studio_reload_workflow.py` PASS
- `Tools/doctor_studio_reload_workflow.py` PASS
- `Tests/validate_athena_studio_phase2.py` PASS
- `Tools/doctor_runtime_cleanup.py` PASS
