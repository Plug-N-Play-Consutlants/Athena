# Player Pool Master Correction

This patch restores the locked layer boundary.

## Corrected Flow

```text
Raw/fantrax_player_pool.json
    ↓
Providers/Fantrax/build/player_pool_master.py
    ↓
Output/player_pool_master.json
    ↓
Knowledge/player_status.py
Knowledge/player_contracts.py
```

## Why

Fantrax-specific shapes such as:

```json
{
  "contract": {
    "smallId": "3",
    "name": "2027"
  }
}
```

belong in the Fantrax Build layer, not Knowledge.

The build layer now normalizes that into:

```json
{
  "contract_expiry_year": 2027,
  "contract_years_remaining": 3,
  "contract_band": "full_runway",
  "contract_is_verified": true
}
```

Knowledge modules now consume only the canonical `Output/player_pool_master.json`.

## Run Order

```python
runfile('F:/Development/Sports_Intelligence_Engine_2.0/Providers/Fantrax/build/player_pool_master.py', wdir='F:/Development/Sports_Intelligence_Engine_2.0')
runfile('F:/Development/Sports_Intelligence_Engine_2.0/Knowledge/player_status.py', wdir='F:/Development/Sports_Intelligence_Engine_2.0')
runfile('F:/Development/Sports_Intelligence_Engine_2.0/Knowledge/player_contracts.py', wdir='F:/Development/Sports_Intelligence_Engine_2.0')
```

Then rerun valuation, team profile, team direction, and readiness.
