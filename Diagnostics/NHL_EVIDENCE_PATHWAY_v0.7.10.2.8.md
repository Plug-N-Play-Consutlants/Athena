# NHL evidence pathway v0.7.10.2.8

- Repairs player performance classification and consumes canonical season statistics only when target-season games exist.
- Reuses NHLClient club-stats endpoint for team scoring evidence; reports acquisition failures and remaining analytical components explicitly.
- Does not infer team strengths, game trends, lineup needs, or cap space from scoring leaders.
- No new provider, no invented data. Studio verification pending.
