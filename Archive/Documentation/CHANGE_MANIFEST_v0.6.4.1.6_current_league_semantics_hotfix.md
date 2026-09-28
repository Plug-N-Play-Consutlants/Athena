# Athena v0.6.4.1.6 — Current League Semantics Hotfix

Changed files only.

- Resolves Fantrax league display identity without treating an account email returned in `leagueName` as the league name; uses matching historical league identity when `leagueHistoryId` proves continuity.
- Treats a successfully fetched zero-row current-season transaction feed as an available empty state, not a connection/capability failure.
- Keeps transaction history and league-market outputs valid when the current season legitimately has no transactions.
- Reconciles current player-contract knowledge to the active player-pool population instead of emitting stale historical-only profile rows.
- Reads Knowledge Readiness from its current `summary.overall_readiness_score` schema instead of displaying `None`.
- Adds Studio `Copy Console`, which copies the entire console text buffer to the clipboard.
- Clarifies the Fantrax Personal/Profile Secret ID field location in the connection UI.
- Adds focused validation for the hotfix.
