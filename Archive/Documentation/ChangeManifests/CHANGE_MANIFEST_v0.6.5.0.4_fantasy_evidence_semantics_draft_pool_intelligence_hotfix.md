# v0.6.5.0.4 — Fantasy Evidence Semantics & Draft-Pool Intelligence Hotfix

## Scope
- Separate canonical synchronized player-pool availability from imported Fantrax CSV snapshot semantics.
- Never promote snapshot FA rows into a current best-available player list without live corroboration.
- Add keeper positional retention-pressure evidence and live-availability comparison when canonical live records exist.
- Rebalance league headline cards around roster/contracts/draft capital/history; retain transactions as bounded evidence.
- Replace membership-ambiguous `Managers active` with `Managers with observed moves`.
- Repair common UTF-8 decoded as Windows-1252/Latin-1 mojibake at shared external-text boundaries.
- Preserve v0.6.5.0.3 contextual routing, v0.6.5.0.2 league identity/persistence, and v0.6.5.0.0 transaction evidence architecture.

## Regression controls
- New Fantasy Evidence Semantics & Draft-Pool Intelligence validator.
- Prior contextual-routing validator metadata made release-durable.
- Scout runtime acceptance: 41/41 PASS in candidate workspace.
- Pre-draft, transaction foundation, league-context integration, normal composition, information-flow and release-hygiene validators PASS.
