# Athena v0.5.0-drop4e22a — Runtime Cleanup

## Purpose
Locks the canonical runtime root and removes the nested `Athena/Athena` confusion path that caused earlier patches to land outside the active runtime.

## Changes
- Version bumped to `0.5.0-drop4e22a`.
- Added `Tools/runtime_cleanup.py`.
- Added `Tools/doctor_runtime_cleanup.py`.
- Added `Tests/validate_runtime_cleanup.py`.
- Updated `Clean Athena Runtime.bat` to run canonical cleanup/quarantine logic.
- Updated Athena Studio Clean Runtime and Runtime Audit to use the cleanup module.
- Added a Studio `Doctor Runtime` button.

## Canonical extraction target
This ZIP contains a top-level `Athena` folder. Extract to:

`F:\Development`

not `F:\Development\Athena`.

## After extracting
Run:

```cmd
cd F:\Development\Athena
"Clean Athena Runtime.bat"
python Tests\validate_runtime_cleanup.py
python Tools\doctor_runtime_cleanup.py
"Athena Studio.bat"
```

## Expected result
- `Core/version.py` reports `0.5.0-drop4e22a`.
- Studio Runtime Audit reports no nested Athena folder after cleanup.
- Runtime doctor passes or warns only before cleanup.
