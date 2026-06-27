# Player Contract Enrichment

## Purpose

`Knowledge/player_contracts.py` normalizes fantasy contract data into canonical contract facts used by the valuation engine, team profiles, keeper planning, and future trade analysis.

This is a Knowledge module. It does not fetch provider data and does not make recommendations.

## Current Source Strategy

Fantrax contract data is not yet available through a reliable provider endpoint. Until it is, contracts are imported from:

```text
Raw/player_contracts.csv
```

If that file does not exist, the module creates:

```text
Output/player_contracts_import_template.csv
```

The template is pre-filled with known player identity, fantasy team, position, and NHL team fields so contract data can be filled/exported without manually rebuilding the roster list.

## Supported Input Columns

Minimum useful fields:

```text
player_id
player_name
fantasy_team
contract_years_remaining
keeper_eligible
```

Optional fields:

```text
position
nhl_team
contract_expiry_year
contract_status
season
notes
```

The builder matches by `player_id` first, then name + fantasy team, then unique player name when safe.

## Output

```text
Output/player_contracts.json
Output/player_contracts.csv
```

Each record includes:

```text
player_id
player_name
fantasy_team
contract_years_remaining
contract_status
contract_score
keeper_eligible
evidence_completeness
evidence
```

## Contract Score

Contract score is deterministic and tuned for the current contract dynasty model:

```text
3 years remaining -> maximum runway
2 years remaining -> stable runway
1 year remaining  -> contract cliff risk
0 years remaining -> expired/unprotected risk
unknown           -> neutral placeholder
```

This score is not a recommendation. It is one valuation dimension used by the canonical valuation engine.

## Future Provider Upgrade

When Fantrax contract data becomes available through API, export, or network reverse engineering, provider-specific logic should be added under:

```text
Providers/Fantrax/fetch/
Providers/Fantrax/build/
```

The canonical output should remain `Output/player_contracts.json` so downstream Intelligence modules do not change.
