# Athena v0.5.0-drop4e24 — Studio Phase 2 + PIF-1 Build 002

## Summary
Adds the next incremental Athena Studio observability pass and the first expanded Public Entity Registry / Identity Graph seed for PIF-1.

## Engine changes
- Expanded `Knowledge.Intelligence.Entities.entity_registry` from the compact seed to 18 public entities.
- Added richer public identity fields: draft context, status, summary, aliases, and metadata.
- Added `Knowledge.Intelligence.Entities.identity_graph` with registry/graph summary helpers.
- Added public-domain routing guardrails in `request_router`:
  - public player comparisons block fantasy owner data by default;
  - draft/prospect routes block rulebook/CBA retrieval unless explicitly relevant;
  - route output now includes allowed domains, blocked domains, and routing notes.
- Strengthened typo coverage for `Auston Mathtwes` and related Matthews variants.
- Preserved Sebastian Aho disambiguation as two distinct public player identities.

## Studio changes
- Added Studio buttons:
  - PIF Coverage
  - Knowledge Dashboard
  - Provider Dashboard
- Enhanced PIF Prompt Inspector with:
  - allowed domains;
  - blocked domains;
  - routing notes.
- Updated Studio validation/doctor dispatch to prefer Build 002 checks when available.

## New validation / doctor scripts
- `Tests/validate_pif1_build002.py`
- `Tools/doctor_pif1_build002.py`
- `Tests/validate_athena_studio_phase2.py`
- `Tools/doctor_athena_studio_phase2.py`

## Validation status
PASS:
- `python Tests/validate_pif1_build001.py`
- `python Tools/doctor_pif1_build001.py`
- `python Tests/validate_pif1_build002.py`
- `python Tools/doctor_pif1_build002.py`
- `python Tests/validate_athena_studio_phase2.py`
- `python Tools/doctor_athena_studio_phase2.py`

## Extraction target
This ZIP contains a top-level `Athena/` folder. Extract to:

`F:\Development`

Do not extract into `F:\Development\Athena`.
