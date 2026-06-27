# Player Identity Resolver

## Purpose

The Player Identity Resolver creates the bridge between fantasy-provider player identities and public sport-provider player identities.

Current first-pass bridge:

```text
Fantrax player_master.json
+
NHL nhl_skater_summary.json
=
player_identity_map.json / player_identity_map.csv
```

## Inputs

```text
Output/player_master.json
Raw/nhl_skater_summary.json
```

## Outputs

```text
Output/player_identity_map.json
Output/player_identity_map.csv
```

## Matching Strategy

The resolver is intentionally conservative:

1. Convert Fantrax names from `Last, First` to `First Last`.
2. Normalize names by removing punctuation, accents, and case differences.
3. Match exact normalized name plus NHL team abbreviation.
4. If unique, match exact normalized name.
5. Use fuzzy matching only when the confidence gap is strong enough.
6. Mark unresolved or ambiguous players explicitly.

The module should not force bad mappings. Ambiguous records are expected and should be reviewed or resolved by future manual override support.

## Why this matters

Fantrax uses internal player IDs. NHL API uses numeric player IDs. The Sports Intelligence Engine needs a canonical bridge so league ownership, contracts, and roster context from Fantrax can be enriched with production, game logs, schedules, and opponent trends from the NHL provider.

## Next Enhancements

- Add manual override support in `Configuration/player_identity_overrides.json`.
- Add support for retired/free-agent players not present in current NHL skater summary.
- Enrich `player_production.py` using this identity map.
- Use NHL game logs for historical player trend analysis.
