# Fantrax player-period acquisition — v0.7.10.67.24

## Status

**Contract discovery, not credited-point ingestion.** The authenticated `getPlayerStats` payload has a `fpts` column and reports a season `..._BY_PERIOD` selector. Neither fact establishes which scoring period is returned or that FPts were actually credited to the player on a team's active roster. Do not replace provider FPts with NHL G+A or treat YTD values as weekly fantasy points.

## Run on the authenticated Windows installation

From the AthenaEngine root, with Studio/Scout stopped or using the same authenticated workspace:

```powershell
python Tools/fantrax_period_probe.py --season 2026 --period 8 --output Output/fantrax_period_probe_2026_p08.json
```

This is a read-only diagnostic. It submits the verified `getPlayerStats` request and, if uniquely discoverable, the selected `seasonOrProjection` code for the requested season. It does not send unverified `period` parameters, alter workspace settings, or persist raw player data. Its JSON output is limited to schema/selector metadata, omitting players, league IDs, cookies and tokens.

## Remaining acceptance gate

Identify the real period-selection request shape from a period-filtered Fantrax UI session, not guesswork. Verify server confirmation of season and period, scoring basis (period-specific credited FPts, not projected/YTD totals), historical owner/team attribution and complete pagination. Only then normalize and save to the existing `Output/PeriodFantasyPoints/fantrax/<league>/<season>/period_NNN.json` contract. `provider_fantasy_points.py` already enforces strict ledger identity/provenance and Scout already consumes the verified records.

If this probe returns `period_identity_unverified`, that is expected until the provider's selected-period contract is proven. Do not mark it `verified` merely to unblock an editorial test.
