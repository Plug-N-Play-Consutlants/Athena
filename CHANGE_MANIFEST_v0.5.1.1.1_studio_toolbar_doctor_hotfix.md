# Change Manifest - 0.5.1.1.1 Studio Toolbar Doctor Hotfix

## Scope

Hotfix for 0.5.1.1.0. This release repairs the Studio Toolbar Doctor diagnostic output only.

## Changes

- Updated `Core/version.py` to `0.5.1.1.1`.
- Updated `Tools/doctor_athena_studio_toolbar.py` to print Unicode toolbar markers using ASCII-safe escaped labels while still validating the actual Unicode strings in `Tools/athena_studio.py`.
- Updated `CHANGELOG.md`.

## Non-Changes

- No Event Intelligence behavior changes.
- No model/schema changes.
- No Scout rendering changes.
- No provider changes.

## Validation Target

Run in Athena Studio:

```text
Doctor Everything
Validate Everything
```

Expected result: PASS.
