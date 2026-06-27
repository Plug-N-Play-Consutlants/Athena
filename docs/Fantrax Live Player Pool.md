# Fantrax Live Player Pool

## Purpose

The Fantrax player pool is the source of truth for league-specific player state:

- fantasy ownership
- rostered/free-agent/waiver status
- contract expiry year
- player availability in the fantasy league
- Fantrax player ID
- league-specific position/status fields

This data must be treated differently from NHL production data. NHL production can come from the NHL provider, but ownership/status/contracts are fantasy-league facts and must come from Fantrax or a Fantrax export.

## Source Priority

The engine now uses this priority order:

```text
1. Live Fantrax player-pool endpoint/export URL
2. Raw/fantrax_player_pool.json generated from a live source
3. Raw/player_contracts.csv manual override
4. Raw/Fantrax-Players*.csv snapshot fallback
```

CSV exports are valid for development and recovery, but they are snapshots. They are not live and can become stale after drops, claims, waiver clearances, free-agent purchases, or contract resets.

## New Fetch Module

```text
Providers/Fantrax/fetch/fetch_player_pool.py
```

Outputs:

```text
Raw/fantrax_player_pool.json
Logs/fantrax_player_pool_fetch.json
```

The raw payload includes:

```json
{
  "source": "fantrax",
  "source_type": "fantrax_live_player_pool_json",
  "source_reference": "...",
  "is_live": true,
  "fetched_at": "...",
  "record_count": 0,
  "records": []
}
```

If no live source is configured, the fetcher falls back to `Raw/Fantrax-Players*.csv` and marks:

```json
{
  "source_type": "fantrax_player_export_snapshot",
  "is_live": false
}
```

## Configuration

Add one of these to `Configuration/config.json` once the correct Fantrax player-pool/export URL is known:

```json
{
  "provider": {
    "endpoints": {
      "player_pool": "relative/fantrax/endpoint"
    }
  }
}
```

or:

```json
{
  "provider": {
    "player_pool_export_url": "https://www.fantrax.com/..."
  }
}
```

The value may be either a relative endpoint under `provider.base_url` or a full URL.

## New Knowledge Module

```text
Knowledge/player_status.py
```

Outputs:

```text
Output/player_status.json
Output/player_status.csv
```

Canonical fields include:

```text
player_id
player_name
position
nhl_team
fantasy_team
status_label
availability_status
source_type
source_is_live
match_method
evidence_completeness
```

## Contract Integration

`Knowledge/player_contracts.py` now prefers `Raw/fantrax_player_pool.json` before manual CSV inputs.

The contract field is parsed as an expiry year:

```text
2025 = expiring / 1 year remaining
2026 = stable / 2 years remaining
2027 = full_runway / 3 years remaining
```

Derived formula:

```text
years_remaining = expiry_year - active_season + 1
```

For the unresolved 2025 season:

```text
2025 -> 1
2026 -> 2
2027 -> 3
```

## Recommended Run Order

```python
runfile(
    'F:/Development/Sports_Intelligence_Engine_2.0/Providers/Fantrax/fetch/fetch_player_pool.py',
    wdir='F:/Development/Sports_Intelligence_Engine_2.0'
)

runfile(
    'F:/Development/Sports_Intelligence_Engine_2.0/Knowledge/player_status.py',
    wdir='F:/Development/Sports_Intelligence_Engine_2.0'
)

runfile(
    'F:/Development/Sports_Intelligence_Engine_2.0/Knowledge/player_contracts.py',
    wdir='F:/Development/Sports_Intelligence_Engine_2.0'
)
```

Then rerun valuation/team/readiness.

## Important Safeguard

When `source_is_live` is false, the engine may still use the data for development and backfill, but any decision support should treat the status/contract information as stale-risk. Live state is required for waiver/free-agent decisions.
