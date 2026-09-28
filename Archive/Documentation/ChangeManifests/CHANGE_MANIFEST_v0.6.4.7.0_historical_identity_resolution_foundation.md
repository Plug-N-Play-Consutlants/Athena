# v0.6.4.7.0 — Historical Identity Resolution Foundation

## Purpose
Add season-scoped historical identity enrichment without mutating canonical historical draft evidence.

## Evidence contracts
- `league_info.teamInfo`: provider team ID and same-season team name.
- `player_pool.rosters.rosterItems`: provider player ID, same-season roster membership/status and position context.
- `transactions.table.rows.scorer`: provider player ID, player name, position eligibility and available same-season NHL context when present.
- `draft_results_canonical.json`: remains authoritative for exercised draft team/player IDs and selection facts.

## Resolution semantics
- Explicit `resolved`, `ambiguous`, and `unresolved` player identity states.
- Multi-position eligibility is resolved position context, not ambiguity.
- Manager/person identity is unresolved when no authoritative same-season evidence establishes it.
- Cross-season franchise continuity is unresolved; team-name similarity is not sufficient evidence.
- Provider team slot, fantasy team, franchise, team name, and manager/person remain distinct concepts.

## New generated artifacts
Historical League Sweep now writes, per season:
- `Output/Historical/<season>/historical_identity_resolution.json`
- `Output/Historical/<season>/draft_observations_enriched.json`

These are derived enrichment artifacts. Existing `draft_results_canonical.json` is not modified by identity enrichment.

## Scout
The existing longitudinal draft route discovers identity-enriched evidence automatically. It reports supported identity/position coverage and retains unresolved manager/franchise limitations without adding a question-specific route.
