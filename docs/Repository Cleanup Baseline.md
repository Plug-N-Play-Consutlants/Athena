# Repository Cleanup Baseline

Date: 2026-06-18
Release: v0.2.2 cleanup baseline

## Purpose

This cleanup pass consolidates the Sports Intelligence Engine around the current canonical provider path and removes or archives files that were still wired to obsolete Fantrax endpoint assumptions.

The locked architecture is unchanged:

Fetch -> Build -> Knowledge -> Intelligence -> AI

## Canonical Fantrax Fetch Path

Active fetch modules:

- `Providers/Fantrax/fetch/fetch_league.py`
- `Providers/Fantrax/fetch/fetch_player_pool.py`
- `Providers/Fantrax/fetch/fetch_transactions.py`
- `Providers/Fantrax/fetch/fetch_all.py`

`fetch_all.py` now runs only the active canonical Fantrax fetches.

## Retired Fantrax Fetches

The following modules were removed from the active provider path because their configured `fxea` endpoints returned provider errors and were not the canonical source for current engine data:

- `fetch_players.py`
- `fetch_rosters.py`
- `fetch_draft_picks.py`

They were moved to:

`Archive/retired_fantrax_legacy_endpoints_20260618/`

Archived raw error payloads were moved there as well:

- `player_ids.json`
- `team_rosters.json`
- `draft_picks.json`

## Current Player Source

The canonical live player/roster/contract source is:

`Raw/fantrax_player_pool.json`

built by:

`Providers/Fantrax/fetch/fetch_player_pool.py`

normalized by:

`Providers/Fantrax/build/player_pool_master.py`

Compatibility output:

`Providers/Fantrax/build/player_master.py` now builds `Output/player_master.*` from `Output/player_pool_master.json`, not from retired raw files.

## Transaction Source

The canonical transaction source is:

`Raw/transactions.json`

fetched by:

`Providers/Fantrax/fetch/fetch_transactions.py`

normalized by:

`Providers/Fantrax/build/transaction_master.py`

`transaction_master.py` now supports the actual Fantrax transaction payload shape: `table.rows`.

## Validation Harness

`Tests/validate_fantrax_provider.py` now validates the active provider path only:

- configuration
- client initialization
- provider diagnostics
- league fetch
- player pool fetch
- transaction fetch

It no longer fails against retired legacy endpoint scripts.

## Local Secrets

`Configuration/secrets.local.json` is not included in this release ZIP. Recreate it locally from `Configuration/secrets.example.json` and paste the Fantrax browser cookie there when validating authenticated transaction fetches.
