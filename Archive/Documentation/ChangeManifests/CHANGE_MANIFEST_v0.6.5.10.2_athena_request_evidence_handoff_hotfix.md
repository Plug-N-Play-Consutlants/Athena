# v0.6.5.10.2 — Athena Request Evidence Handoff Hotfix

## Scope
Repair the request-boundary evidence handoff identified by the v0.6.5.10.1 pathway trace. This is a pathway repair, not a salary-cap calculator or new public-data feature.

## Changes
- Added `Athena/evidence_bundle.py` as the question-scoped evidence acquisition boundary.
- `Athena.request_execution` now acquires and attaches request evidence before specialist execution and records readiness in developer trace output.
- Public player investigations can consume official NHL player records and dated identity-matched news from Athena's request bundle instead of defaulting to the seeded profile alone.
- Salary-cap inquiries acquire governing NHL/MOU evidence once at the Athena boundary and explicitly record the missing current payroll/roster-cap inputs.
- Scout's public hockey rule surface consumes Athena's bundled cap evidence when present rather than independently reacquiring the same rule evidence.

## Boundaries preserved
- No cap number is inferred without a canonical current payroll/cap ledger.
- No unrelated news item substitutes for player-specific current evidence.
- Sebastian Aho disambiguation remains upstream of player evidence acquisition.
- Existing specialist routing and Scout presentation contracts remain intact.
