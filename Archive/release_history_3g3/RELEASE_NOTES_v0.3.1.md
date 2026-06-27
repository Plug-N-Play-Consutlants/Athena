# Sports Intelligence Engine v0.3.1 — Intelligence Refinement

## Purpose

Refine the v0.3.0 canonical transaction intelligence outputs so they are clearer, more explainable, and financially accurate in their provenance.

This release does **not** add the official Fantrax finance-page pipeline. It prepares the intelligence outputs for that future source by separating observed transaction-history fee fields from official league financial balances.

## Changes

### Transaction History Knowledge

- Renamed team-level transaction fee aggregation to `observed_transaction_fee_total`.
- Added `financial_provenance` metadata explaining that transaction-history fee fields are observed activity signals only.
- Updated transaction timeline records to use `observed_transaction_fee_total`.
- Explicitly identifies the Fantrax finance page under the team menu as the future official finance source.

### Manager Behavior Intelligence

- Reorganized each manager record into:
  - `observed_facts`
  - `inferred_profile`
  - `limitations`
- Added richer deterministic tendencies, including:
  - `aggressive_roster_manager`
  - `free_agent_streamer`
  - `waiver_opportunist`
  - `high_roster_churn`
  - `roster_pruner`
  - `high_observed_fee_activity`
- Replaced misleading `non_trade_activity` interpretation with `insufficient_trade_evidence` when no trades are present in the available transaction history.
- Renamed ambiguous fee output to `observed_transaction_fee_total`.

### League Market Intelligence

- Replaced simple market liquidity string with an explainable object:
  - `classification`
  - `score`
  - `confidence`
  - `drivers`
  - `limitations`
- Added financial provenance warning that official balances must come from the Fantrax finance page.
- Renamed league fee aggregation to `observed_transaction_fee_total`.

## Validation

Transaction pipeline validation passed.

- Raw transaction rows: 134
- Canonical transactions: 92
- Asset movements: 134
- Managers analyzed: 12
- League market liquidity: liquid, score 73, confidence 0.80

## Known limitation

Official league finance values are not yet fetched directly. The next finance-specific release should add:

```text
Providers/Fantrax/fetch/fetch_finances.py
Providers/Fantrax/build/finance_master.py
Knowledge/finance_profile.py
```

The finance page is the authoritative money source.
