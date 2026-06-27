# Retired Fantrax Legacy Endpoint Artifacts

Date retired: 2026-06-18

These files were removed from the canonical provider path because they call Fantrax `fxea` endpoints that now return provider errors:

- `players/getPlayerIds`
- `team/getTeamRosters`
- `draft/getFutureDraftPicks`

Current canonical Fantrax fetch path:

- League: `fetch_league.py`
- Player/roster/contract state: `fetch_player_pool.py` using live `general/getTeamRosters`
- Transactions: `fetch_transactions.py` using authenticated `fxpa/req` method `getTransactionDetailsHistory`

The old raw outputs were archived here only for traceability. They should not be used by Build, Knowledge, or Intelligence.
