# v0.6.5.0.2 — Fantrax League Context & Scout Integration Hotfix

- Makes Athena workspace/server state authoritative for active Fantrax league identity; removes browser-local league ID persistence.
- Explicit valid league IDs supplied during connect/save override stale persisted state for that user action.
- Routes Fantrax league-name normalization through the canonical identity resolver so account email cannot become canonical league identity.
- Restores useful league reading after successful Sync League.
- Connects general league analysis to available canonical historical draft coverage.
- Removes duplicate Observed Facts from session text logs and obsolete Alpha-era league-analysis limitations.
- Hardens prior regression validators so later releases validate preserved behavior rather than exact release metadata.
- Preserves v0.6.5.0.0 transaction evidence acquisition and normalization.
