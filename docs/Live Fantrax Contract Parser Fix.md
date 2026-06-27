# Live Fantrax Contract Parser Fix

This patch updates `Knowledge/player_contracts.py` so it reads live Fantrax roster contract objects from:

`Raw/fantrax_player_pool.json`

The live route returns contract data as:

```json
{
  "contract": {
    "smallId": "3",
    "name": "2027"
  }
}
```

Parser rules:

- `contract.name` = contract expiry year
- `contract.smallId` = Fantrax runway indicator
- `years_remaining = expiry_year - active_season + 1`

For active season `2025`:

- `2025` = 1 year remaining / expiring
- `2026` = 2 years remaining / stable
- `2027` = 3 years remaining / full runway

Run:

```python
runfile('F:/Development/Sports_Intelligence_Engine_2.0/Knowledge/player_contracts.py', wdir='F:/Development/Sports_Intelligence_Engine_2.0')
```

Then rerun valuation/team/readiness.


## v2

Adds compatibility imports for the project's existing `Core.json_utils` helper names.
