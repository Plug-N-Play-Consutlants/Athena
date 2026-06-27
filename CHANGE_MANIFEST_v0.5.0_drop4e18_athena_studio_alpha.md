# Athena v0.5.0-drop4e18 — Athena Studio Alpha

## Purpose
Introduces Athena Studio Alpha as a local development control surface so Scout, runtime cleaning, validation, doctor checks, logs, and runtime audits can be managed from one place.

## Added
- `Tools/athena_studio.py`
- `Athena Studio.bat`
- `Athena Studio.ps1`
- `Tools/doctor_athena_studio.py`
- `Tests/validate_athena_studio.py`

## Updated
- `Core/version.py` advanced to `0.5.0-drop4e18`.

## Notes
- Scout remains the presentation layer.
- Athena Studio is a developer/local runtime control surface, not the public product UI.
- This is intentionally standard-library only and does not require packaging dependencies.

## Canonical extraction
This patch contains a top-level `Athena/` folder. Extract to `F:\Development`, not `F:\Development\Athena`.
