# Provider Completion Plan

## Purpose

The Sports Intelligence Engine needs reliable provider feeds before Knowledge and Intelligence can produce meaningful conclusions.

Fantrax should remain the source for fantasy-league-specific data:

- league rules
- fantasy teams/managers
- roster ownership
- draft picks
- transactions
- contracts, if exposed
- league history, if exposed

The public NHL provider should supply real-world hockey data:

- player production
- team stats
- schedules
- game logs
- player landing/profile data
- matchup history
- opponent trends

## Why add NHL provider now?

Fantrax endpoint discovery did not find a direct stats endpoint. NHL production data is public and should not be blocked by Fantrax internals.

## New diagnostic module

```text
Providers/Fantrax/fetch/discover_provider_capabilities.py
```

This probes known/likely Fantrax capabilities and writes:

```text
Logs/fantrax_provider_capabilities.json
```

It does not overwrite Raw files.

## New NHL fetch module

```text
Providers/NHL/fetch/fetch_skater_summary.py
```

This writes:

```text
Raw/nhl_skater_summary.json
```

That file can become a source for:

```text
Knowledge/player_production.py
```

## nhl-api-py note

The `nhl-api-py` package is a useful wrapper around NHL API modules such as teams, schedule, stats, Edge data, standings, game center, and miscellaneous endpoints. The engine can use it later as a convenience dependency, but provider modules should remain stable even if wrapper method names change. Therefore the first NHL provider implementation uses direct public NHL endpoints.

## Run order

```python
runfile(
    'F:/Development/Sports_Intelligence_Engine_2.0/Providers/Fantrax/fetch/discover_provider_capabilities.py',
    wdir='F:/Development/Sports_Intelligence_Engine_2.0'
)
```

Then:

```python
runfile(
    'F:/Development/Sports_Intelligence_Engine_2.0/Providers/NHL/fetch/fetch_skater_summary.py',
    wdir='F:/Development/Sports_Intelligence_Engine_2.0'
)
```
