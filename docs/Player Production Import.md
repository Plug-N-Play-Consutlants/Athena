# Player Production Import

`Knowledge/player_production.py` normalizes player production into canonical Knowledge outputs.

## Preferred input

Place a CSV at:

```text
Raw/player_production.csv
```

Minimum useful columns:

```text
player_id,player_name,season,games_played,goals,assists,points,games_with_points
```

The module accepts common aliases such as:

```text
gp, games, g, a, pts, fantasy_points, gamesWithPoints, scoring_games
```

## Outputs

```text
Output/player_production.json
Output/player_production.csv
```

If no source file exists, the module creates:

```text
Output/player_production_import_template.csv
```

Use that template as the starting point for a manual CSV import.

## Notes

- In this league, `points` means NHL player points: goals + assists.
- If `points` is missing but goals/assists exist, points are calculated as `goals + assists`.
- `points_per_game` is calculated as `points / games_played`.
- `scoring_frequency` is calculated only when `games_with_points` is provided.
- This is Knowledge, not Intelligence. It does not rank, recommend, or infer player value.
