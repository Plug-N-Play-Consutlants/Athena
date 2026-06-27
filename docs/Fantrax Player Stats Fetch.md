# Fantrax Player Stats Fetch

This patch adds an automated production-data path. Manual CSV import remains only a fallback.

## New Fetch module

```text
Providers/Fantrax/fetch/fetch_player_stats.py
```

It attempts to fetch Fantrax player production and saves the first valid non-error payload to:

```text
Raw/player_stats.json
```

If no endpoint works, it writes diagnostics to:

```text
Logs/fantrax_player_stats_discovery.json
```

and does not overwrite `Raw/player_stats.json`.

## Optional config

If discovery does not find the correct endpoint, add the endpoint to `Configuration/config.json`:

```json
{
  "provider": {
    "endpoints": {
      "player_stats": "players/getPlayerStats"
    }
  }
}
```

The exact endpoint can be changed without affecting Knowledge or Intelligence.

## Knowledge path

`Knowledge/player_production.py` now checks sources in this order:

1. `Raw/player_production.csv` manual fallback
2. `Raw/player_production.json` generic JSON fallback
3. `Raw/player_stats.json` Fantrax automated fetch

It produces:

```text
Output/player_production.json
Output/player_production.csv
```

## Run order

```python
runfile(
    'F:/Development/Sports_Intelligence_Engine_2.0/Providers/Fantrax/fetch/fetch_player_stats.py',
    wdir='F:/Development/Sports_Intelligence_Engine_2.0'
)
```

Then:

```python
runfile(
    'F:/Development/Sports_Intelligence_Engine_2.0/Knowledge/player_production.py',
    wdir='F:/Development/Sports_Intelligence_Engine_2.0'
)
```
