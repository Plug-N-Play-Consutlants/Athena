# v0.5.0 Drop 3D — Athena Sync Stabilization

## Purpose
Stabilize Athena sync so it acts as a thin orchestrator over the existing validated pipeline instead of reporting successful zero-output syncs.

## Changes
- Replaced `Athena/sync.py` with a staged orchestrator that calls existing Fetch, Build, Knowledge, and Intelligence scripts.
- Added per-step validation after each pipeline stage.
- Sync now fails loudly if Fantrax transactions return an auth/pageError or if required outputs contain zero records.
- Updated Athena version to `0.5.0-drop3d`.
- Included the foreground Scout launcher/app port behavior from Drop 3C.
- Updated sync validation script.

## Expected behavior
With a valid Fantrax transaction cookie, Scout Sync League should produce non-zero transaction, asset movement, manager behavior, and league market outputs.

If the cookie is expired/incomplete, Scout should report a failed sync instead of showing `completed` with zero managers/transactions.
