# Player Production NHL Enrichment

This patch updates the production enrichment path so the engine no longer expects manual CSV entry as the primary workflow.

## Canonical Flow

```text
Raw/nhl_skater_summary.json
+ Output/player_identity_map.json
→ Knowledge/player_production.py
→ Output/player_production.json / .csv
```

Then:

```text
Output/player_profiles.json
+ Output/player_production.json
→ Intelligence/valuation_engine.py
→ Output/player_values.json / .csv
```

Then:

```text
Output/player_values.json
→ Knowledge/team_profile.py
→ Output/team_profiles.json / .csv
```

## Provider Responsibility

Fantrax remains responsible for fantasy league structure: owners, rosters, contracts, draft picks, transactions, and league rules.

NHL is responsible for public NHL production: games played, goals, assists, points, points per game, shots, special-teams production, and time on ice.

## Notes

The CSV import fallback remains available for emergency/manual imports but is no longer the intended primary production path.
