# Sports Intelligence Engine v0.2.2

## Type

Cleanup and consolidation release.

## Summary

This release removes obsolete Fantrax provider paths from the active engine, consolidates validation around the canonical provider flow, and fixes compatibility outputs so downstream Knowledge and Intelligence modules continue to consume stable files.

## Changed

- Archived legacy Fantrax fetch modules that called invalid `fxea` endpoints.
- Updated `fetch_all.py` to run only active canonical Fantrax fetches.
- Updated `FantraxEndpoints` to expose only active endpoint defaults.
- Removed `players`, `rosters`, and `draft_picks` from active config defaults.
- Updated `Tests/validate_fantrax_provider.py` to validate only active provider paths.
- Rebuilt `player_master.py` to derive from `player_pool_master.py` instead of retired raw files.
- Updated `player_pool_master.py` to supplement live player IDs with local Fantrax CSV identity metadata when available.
- Updated `transaction_master.py` to parse actual Fantrax `table.rows` transaction payloads.
- Archived historical patch notes and root-level duplicate scripts.
- Removed Python bytecode/cache files from the release tree.
- Removed local secrets from the deliverable ZIP.

## Active Canonical Fantrax Fetches

- League
- Player Pool
- Transactions

## Validation

Local compile check passed:

`python -m compileall -q .`

Local non-network tests passed:

- `Tests/core_self_test.py`
- `Tests/test_asset_registry.py`
- `Tests/test_team_profile.py`
- `Tests/test_team_direction.py`

Build smoke test passed for:

- `Providers/Fantrax/build/player_pool_master.py`
- `Providers/Fantrax/build/player_master.py`
- `Providers/Fantrax/build/transaction_master.py`

Authenticated provider validation must be rerun locally after recreating `Configuration/secrets.local.json`.

## Known Issues

- Live future draft-pick endpoint is not currently part of the active Fantrax provider path. Existing draft-pick output remains historical until a valid current endpoint or transaction-derived draft-pick pipeline is implemented.
- `fetch_player_stats.py` remains a discovery-style optional fetch and is not part of canonical `fetch_all.py`.
