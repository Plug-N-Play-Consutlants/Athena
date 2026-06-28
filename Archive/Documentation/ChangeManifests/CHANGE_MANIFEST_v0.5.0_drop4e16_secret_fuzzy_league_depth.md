# Athena v0.5.0-drop4e16 — Secret Persistence, Fuzzy Player Matching, League Depth

## Purpose
Improve the version-capable Scout/Fantasy League experience without changing the core architecture.

## Changes
- Advanced Scout to `v0.5.0-drop4e16`.
- Improved Fantrax Personal/Profile Secret ID form semantics for browser/password-manager persistence.
- Added fuzzy player matching for common spelling mistakes such as `Austin Mathtwes` -> `Auston Matthews`.
- Added ambiguous-player handling so name-only collisions can ask for clarification instead of merging identities when duplicate player names are present in Athena outputs.
- Improved League Analysis with league type, scoring model, keeper/contract model, lineup model, asset classes, manager activity coverage, average transactions, draft-pick availability, and league-history ID visibility.
- Added raw league-info context to Scout.
- Updated Manager Behavior builder to include teams with zero observed transactions so coverage can reach all league teams while preserving the distinction between "no observed activity" and "inactive owner".

## Files Changed
- Core/version.py
- Scout/app.py
- Scout/conversation/context.py
- Scout/conversation/router.py
- Intelligence/Player/player_intelligence.py
- Intelligence/manager_behavior.py

## Validation
- Python compilation passed for changed files.
- `Analyze my league` routes to League Analysis.
- `Austin Mathtwes` resolves to Auston Matthews in the current data set.
- Manager Behavior builder produces 14 manager/team records after rebuild for the current 14-team league.

## Notes
Run Sync League after applying this patch to regenerate manager behavior and league market outputs with the zero-activity managers included.
