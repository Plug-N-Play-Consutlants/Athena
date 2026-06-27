# Player Bio Enrichment

## Purpose

Player bio enrichment adds canonical age and physical-profile facts to the Sports Intelligence Engine.

This is important for dynasty and contract-dynasty analysis because current production alone cannot distinguish between:

- a young core asset,
- a prime-age producer,
- an aging veteran,
- a prospect/development asset,
- or a short-term production play.

## Provider Responsibilities

### NHL Provider

Fetches raw public player landing payloads from the NHL API.

Output:

```text
Raw/nhl_player_landing.json
```

### Knowledge Layer

Normalizes the NHL raw payloads into canonical bio facts.

Output:

```text
Output/player_bio.json
Output/player_bio.csv
```

## Inputs

```text
Output/player_identity_map.json
Raw/nhl_player_landing.json
```

## Canonical Fields

Initial fields include:

```text
fantrax_player_id
nhl_player_id
player_name
birth_date
age_as_of_season_start
height_inches
height_centimeters
weight_pounds
weight_kilograms
shoots_catches
birth_country
nhl_team
nhl_position
is_active
evidence_completeness
```

## Age Anchor

The engine uses October 1 of the workspace season as the default fantasy/dynasty age anchor.

Example:

```text
workspace.season = 2025
age_as_of_date = 2025-10-01
```

This prevents age values from changing every day and gives the valuation engine a stable season-level input.

## Downstream Consumers

Player bio will eventually feed:

```text
player_profile.py
valuation_engine.py
team_profile.py
team_direction.py
trade_analysis.py
keeper_value.py
```

## Current Limitations

This module does not yet calculate age curves or dynasty age-adjusted value. It only creates the canonical knowledge required for those future Intelligence modules.
