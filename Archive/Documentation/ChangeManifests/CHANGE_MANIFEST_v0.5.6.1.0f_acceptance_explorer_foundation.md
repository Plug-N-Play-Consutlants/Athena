# AthenaEngine v0.5.6.1.0f — Acceptance Explorer Foundation

## Purpose
Add a prompt-level Acceptance Explorer that consolidates execution trace, capability participation, evidence audit, and composition audit diagnostics into one Studio-accessible report.

## Scope
- Added `Core/acceptance_explorer.py`.
- Added `Tools/doctor_acceptance_explorer.py`.
- Added `Tests/validate_acceptance_explorer.py`.
- Updated `Tools/athena_studio.py` with Acceptance Explorer operations, doctor, and validator hooks.
- Updated `Core/__init__.py` optional exports.

## Behavior
Observability-only. No Scout routing, reasoning, provider, or response behavior changes.
