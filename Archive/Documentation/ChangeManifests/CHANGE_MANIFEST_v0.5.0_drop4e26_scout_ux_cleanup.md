# Athena v0.5.0-drop4e26 — Scout UX Cleanup

## Purpose
Clean up Scout demo/runtime UX without changing the reasoning engine.

## Changes
- Preserves Fantasy League mode during Fantrax Save/Test Connection.
- Prevents Fantrax form submission from reloading the page or reverting provider state.
- Improves password-manager compatibility for Fantrax Personal/Profile Secret ID.
- Adds local browser restore fallback for League ID and Personal/Profile Secret ID.
- Collapses long raw/natural reasoning text behind a Developer / Raw Reasoning Output disclosure panel.
- Keeps formatted cards, conclusions, observed facts, limitations, and Developer Mode JSON available.

## Validation
- `python Tests/validate_scout_ux_cleanup.py`
- `python Tools/doctor_scout_ux_cleanup.py`
