# Sports Intelligence Engine v0.3.0 — Canonical Transaction Engine

## Summary

This release promotes transaction data from raw Fantrax rows into canonical transaction, asset movement, Knowledge, and Intelligence outputs.

## Added

- `Tests/validate_transaction_pipeline.py`
- `docs/Canonical Transaction Engine.md`
- `RELEASE_NOTES_v0.3.0.md`

## Updated

- `Providers/Fantrax/build/transaction_master.py`
  - Groups Fantrax rows by `txSetId`
  - Produces canonical transaction records
  - Produces asset movement records
  - Preserves provider metadata under provider boundary

- `Knowledge/transaction_history.py`
  - Builds transaction timeline
  - Builds team/manager transaction histories
  - Builds player movement history
  - Builds asset movement records

- `Intelligence/manager_behavior.py`
  - Derives manager activity bands
  - Derives transaction style
  - Derives fee and movement signals

- `Intelligence/league_market.py`
  - Derives market liquidity
  - Derives league activity distributions
  - Derives most active managers

- `Knowledge/knowledge_readiness.py`
  - Recognizes `transaction_master`, `transaction_history`, `manager_behavior`, and `league_market` as current canonical outputs

## Validation

Validation command:

```python
runfile('F:/Development/Sports_Intelligence_Engine_2.0/Tests/validate_transaction_pipeline.py', wdir='F:/Development/Sports_Intelligence_Engine_2.0')
```

Expected outputs:

- `Output/transaction_master.json`
- `Output/transaction_master.csv`
- `Output/transaction_history.json`
- `Output/transaction_history.csv`
- `Output/manager_behavior.json`
- `Output/manager_behavior.csv`
- `Output/league_market.json`
- `Output/league_market.csv`
- `Reports/transaction_pipeline_validation_report.json`
- `Reports/transaction_pipeline_validation_report.txt`

## Known limits

- Current Fantrax transaction fetch is using the Claim/Drop view available in the authenticated payload.
- Trade-specific transaction parsing is scaffolded through canonical transaction types but requires a trade payload sample before final normalization.
- Draft-pick asset movement parsing is designed for the canonical model but requires live draft-pick transaction payloads.
