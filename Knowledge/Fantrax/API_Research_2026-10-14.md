# Fantrax API and public developer workaround research

Research date: 2026-10-14. Purpose: durable evidence inventory for AthenaEngine; not a validated production provider contract.

## Evidence tiers
- **Studio-confirmed (Athena v0.7.10.0.35):** GET `/fxea/players/getPlayerStats` fails with `WARNING: Invalid URL for API service/fxea/players/getPlayerStats`.
- **Studio-confirmed (Athena v0.7.10.0.36):** switching to internal `/fxpa/req` `getPlayerStats` removes the invalid-URL error, but `player_period_production=unverified_period`. This does **not** establish that usable player rows were returned.
- **Developer-captured (soccer league; NOT NHL verified):** `tjoerdie/fantrax-toolkit` documents browser-captured `/fxpa/req` POST with `msgs: [{method: getPlayerStats, data: {view, pageNumber (string), positionOrGroup, seasonOrProjection, miscDisplayType}}]`, outer `uiv`, `refUrl`, `dt`, `at`, `tz`, `v`; response `responses[0].data` with `tableHeader.cells`, `statsTable`, `paginatedResultSet`, `seasonOrProjections`, `posOrGroupList`, `statusOrTeamList`. `statusOrTeamFilter` request spelling is an educated guess according to author. The author reports `miscDisplayType: "1"` necessary for GP, and season YEAR_TO_DATE codes for actual category stats; projection codes may provide only composite score. **Soccer season codes and position codes must NOT be reused for NHL.** https://raw.githubusercontent.com/tjoerdie/fantrax-toolkit/main/src/fantrax_stats.py
- **Developer implementation (multi-sport, API version-specific):** `pmurley/go-fantrax/auth_client` defines `GetPlayerPoolRequest` with `statusOrTeamFilter`, `maxResultsPerPage`, `pageNumber` (string) for `getPlayerStats`; defines `GetTeamRosterInfoRequest` with `period` (string), `teamId`, optional `scoringCategoryType`, `statsType`. Its comments describe per-period year-to-date roster stats. https://pkg.go.dev/github.com/pmurley/go-fantrax/auth_client
- **Fantrax-provided beta docs relayed by developer (April 2025):** `/fxea/general/getPlayerIds?sport=NHL`, `/fxea/general/getLeagueInfo?leagueId=...`, `/fxea/general/getTeamRosters?leagueId=...&period=...`, standings/draft endpoints. The listed beta API does not document period-specific player statistics. https://github.com/pmurley/go-fantrax
- **Developer implementation (NHL library):** `meisnate12/FantraxAPI` includes scoring periods with start/end dates and cookie-based access for private leagues; the author could not establish native login. https://github.com/meisnate12/FantraxAPI ; https://fantraxapi.kometa.wiki/en/stable/league.html
- **Developer CSV workaround:** `sprx97/FantraxCapfriendly` uses GET `/fxpa/downloadPlayerStats` with `leagueId`, `view=STATS`, `seasonOrProjection`, `timeframeTypeCode`, `transactionPeriod`, `miscDisplayType`, `scoringCategoryType`, `timeStartType`, and other filters, plus session cookie. Example `timeframeTypeCode=YEAR_TO_DATE` is NOT evidence of a single JHLPAA week. https://github.com/sprx97/FantraxCapfriendly/blob/main/fantrax.py
- **Independent CSV/website workaround:** `/fxpa/downloadTransactionHistory` and `/fxpa/downloadPlayerStats`, cookie-authenticated `/fxpa/req`; browser network inspection and Selenium cookie persistence. https://wjrm500.com/2025/10/27/fantraxpert-a-fantasy-football-data-dashboard
- **Developer caveat:** Public beta `getTeamRosters` may contain identities/positions but not detailed stats; internal `getTeamRosterInfo` and `getLiveScoringStats` require session auth. This example concerns MLB and must not be treated as NHL verified. https://github.com/butterflyskies/fantrax-mcp/issues/34

## Candidate investigation sequence (not implemented)
1. Preserve current authenticated `/fxpa/req` transport and collect **redacted schema metadata only** for `getPlayerStats`: response envelope keys, data keys, header labels, count of stats rows, pagination and available season/timeframe selectors. Never log cookie, credentials, full raw response, private player data or token.
2. Confirm NHL-specific `seasonOrProjections` and timeframe selectors from actual authenticated response; select the requested season/period via captured UI request contract, not a guessed code.
3. Evaluate `getTeamRosterInfo` with `period` for period attribution, distinguishing YTD cumulative from single-period production.
4. Evaluate `/fxpa/downloadPlayerStats` with a verified single-period filter; parse header-driven G/A columns and reconcile player IDs.
5. Cross-check period G+A with league totals, week boundaries, roster status, and archived standings. Reject absent/ambiguous period evidence rather than treating YTD as week-specific.
6. Implement one canonical provider contract and tests for paging, authentication, no rows, season mismatch, period mismatch, response schema changes and duplicate players.

## Unresolved
- Actual NHL `getPlayerStats` request filters and current season code.
- Whether Fantrax's selected period is scoring period, lineup period, transaction period or date range for the relevant view.
- Whether the existing Athena v0.7.10.0.36 request returns populated `statsTable`.
- How to establish week-specific G+A with direct period response versus differences of YTD snapshots.
- Availability/terms/rate limits for internal API; undocumented internal methods may change.

Security: Do not commit or export session cookies or user-specific league credentials. Cite source repositories rather than copying licensed code.

## Studio inspection v0.7.10.0.37
The bounded response-schema inspector records only recognized structural keys, counts, value types, and allowlisted hockey statistical labels. No raw responses, dynamic values, player identifiers, cookies or league-specific data are exported. Await Studio response before establishing request filters or parsing production.

## Studio observation v0.7.10.0.37 (2026-10-14)
Authenticated getPlayerStats returned a statsTable list of 500 rows, tableHeader.cells of 10, seasonOrProjections of 81, posOrGroupList of 5, statusOrTeamList of 65, and paginatedResultSet as an object. Only GP was recognized by the strict initial header-label inspector. Season/period attribution remains unverified. v0.7.10.0.38 expands safe structural inspection to nested header cells, first-row shape, selector item shapes, boolean selection flags and pagination field shape, without exposing player data or option values.
