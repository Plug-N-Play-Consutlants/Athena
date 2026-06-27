# Canonical Transaction Engine

Version: v0.3.0

## Purpose

The canonical transaction engine converts raw provider transaction history into provider-neutral transaction, asset, and asset-movement records.

This supports the three product lines that consume the shared engine:

- Fantasy Sports Intelligence
- Public Sports Intelligence
- AI Content Platform

The engine remains deterministic-first. AI explains outputs later; it does not invent transaction facts.

## Pipeline

```text
Raw/transactions.json
↓
Providers/Fantrax/build/transaction_master.py
↓
Output/transaction_master.json
↓
Knowledge/transaction_history.py
↓
Output/transaction_history.json
↓
Intelligence/manager_behavior.py
Intelligence/league_market.py
```

## Canonical transaction record

Each transaction record contains:

- `transaction_id`
- `schema_version`
- `timestamp`
- `season_week`
- `transaction_type`
- `status`
- `summary`
- `participants`
- `assets`
- `asset_movements`
- `fees`
- `fee_total`
- `provider_reference`
- `provider_metadata`

## Fantrax row grouping

Fantrax returns UI table rows. Related rows share `txSetId`.

Example:

- CLAIM row
- DROP row

Both rows may represent one claim/drop transaction. The builder groups rows by `txSetId` and creates one canonical transaction with multiple asset movements.

## Asset movement model

Each asset movement describes what moved and the direction:

- `asset_type`
- `asset_id`
- `asset_name`
- `movement`
- `from_participant_id`
- `to_participant_id`

Current supported asset type:

- `player`

Future supported asset types:

- draft pick
- prospect
- contract
- rights
- cash/fee
- waiver priority
- future consideration

## Knowledge outputs

`Knowledge/transaction_history.py` derives:

- transaction timeline
- team/manager transaction history
- player movement history
- asset movement history
- transaction type distribution
- fee totals

## Intelligence outputs

`Intelligence/manager_behavior.py` derives:

- activity band
- dominant transaction type
- transaction style
- trade posture
- asset movement volume
- fee activity

`Intelligence/league_market.py` derives:

- market liquidity
- league activity distribution
- manager activity distribution
- transaction style distribution
- fee activity
- most active managers

## Boundary rules

- Fetch saves raw provider payloads only.
- Build parses provider payloads and creates canonical objects.
- Knowledge uses only canonical outputs.
- Intelligence uses only Knowledge outputs.
- AI explains later and does not create facts.
