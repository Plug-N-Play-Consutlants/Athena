# Athena v0.5.0-drop4e11 — Scout Provider Visibility + League Routing

## Changes
- Hides Fantrax connection panel unless Fantasy League mode is selected.
- Keeps Public Sports clean and provider-neutral by default.
- Allows browser/password manager autocomplete for Fantrax League ID and Personal/Profile Secret ID.
- Hides manual Cookie header behind an advanced fallback panel.
- Adds visible authentication state: browser session detected, cookie limited, or limited mode.
- Routes league/team/draft/weakness prompts before player lookup so `Analyze my league` no longer fails as a player query.
- Adds no-silent-failure fallback so Scout responds with guidance or a clarifying prompt.
- Preserves player prompt normalization from drop4e10.

## Validation
- Python syntax check passes for Scout app/router and Core version.
