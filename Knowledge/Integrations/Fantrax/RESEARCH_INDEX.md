# Fantrax Integration Research Index

Reviewed: 2026-10-14. Source-reviewed does not mean Studio-verified. This is a research-only knowledge overlay; it does not alter runtime or version.

## Standing rule

Before exploratory builds: search official docs and mature public implementations; read actual source; distinguish sport-specific assumptions; record request/response contract, evidence, limitations and security; reuse existing patterns; use Studio only for unresolved facts. Revisit this index before modifying Fantrax providers.

## Public implementation registry

### FAN-001 — meisnate12/FantraxAPI
Source: https://github.com/meisnate12/FantraxAPI
Topics: period-calendar,league-model,authenticated-session. Status: source-reviewed.
Evidence: Community library; scoring period number/start/end and results; authenticated cookie workaround.
Limitation: NHL-specific weekly player G+A not demonstrated.

### FAN-002 — tjoerdie/fantrax-toolkit
Source: https://github.com/tjoerdie/fantrax-toolkit
Topics: player-statistics,headers,views,projections,pagination. Status: source-reviewed.
Evidence: fxpa/req getPlayerStats, STATS view, position-dependent category columns; some pagination caveats.
Limitation: EPL implementation; NHL period selectors and complete pagination unverified.

### FAN-003 — sprx97/FantraxCapfriendly
Source: https://github.com/sprx97/FantraxCapfriendly/blob/main/fantrax.py
Topics: csv-export,timeframe,auth. Status: source-reviewed.
Evidence: fxpa/downloadPlayerStats; seasonOrProjection, timeframeTypeCode, transactionPeriod, timeStartType, scoringCategoryType, view.
Limitation: Captured parameters not proof that transactionPeriod equals NHL scoring period.

### FAN-004 — pmurley/go-fantrax
Source: https://github.com/pmurley/go-fantrax
Topics: public-beta,rosters,period,league,draft. Status: source-reviewed.
Evidence: fxea/general API; NHL supported; getTeamRosters optional period; getStandings lacks individual stats.
Limitation: Public beta incomplete; repository README has inconsistent draft-results URL label.

### FAN-005 — gabrielmeir53/federation-fantasy-dashboard
Source: https://github.com/gabrielmeir53/federation-fantasy-dashboard
Topics: nhl,transactions,standings,rate-limits. Status: source-reviewed.
Evidence: fxpa/req getTransactionDetailsHistory and getStandings view=SCHEDULE; sequential requests and conservative throttle guidance.
Limitation: Rate limits anecdotal; public-league visibility may not match JHLPAA.

### FAN-006 — butterflyskies/fantrax-mcp issue 34
Source: https://github.com/butterflyskies/fantrax-mcp/issues/34
Topics: public-api-limitations,category-scoring. Status: source-reviewed.
Evidence: Public beta standings and rosters lack per-category/player stat details; internal methods discussed.
Limitation: Issue discussion not proof of internal method support for NHL.

### FAN-007 — Abcmsaj/FantraxBot
Source: https://github.com/Abcmsaj/FantraxBot
Topics: discord,posting,chatbot. Status: source-reviewed.
Evidence: Discord bot posts Fantrax standings screenshots and chat responses.
Limitation: External Discord integration, not native Fantrax message posting.

### FAN-008 — maestor/node-fantrax-stats-parser
Source: https://github.com/maestor/node-fantrax-stats-parser
Topics: hockey,history,csv,api. Status: source-reviewed.
Evidence: Hockey-specific import of Fantrax CSV and history into database/API.
Limitation: Not evidence of direct weekly authenticated player stats endpoint.

### FAN-009 — FantraxAPI scoring period source
Source: https://fantraxapi.metamanager.wiki/en/stable/_modules/fantraxapi/objs/scoring_period.html
Topics: period-completion,dates. Status: source-reviewed.
Evidence: ScoringPeriodResult exposes period number/start/end and computed complete/current/future flags.
Limitation: Completion is library date logic, not a server-confirmed finalization flag.

## Athena Studio evidence

v0.7.10.0.39: authenticated `fxpa/req` `getPlayerStats` returned `statsTable` (500 rows), `tableHeader.cells` (10), `seasonOrProjections` (81), `posOrGroupList` (5), `statusOrTeamList` (65), and `paginatedResultSet` with `pageNumber` and `maxResultsPerPage`. Only GP recognized by existing parser. Period-specific G+A unverified. Session export working.

## Next implementation research priorities

1. Read the toolkit source implementation for `view`, `positionOrGroup`, `miscDisplayType`, category header key parsing and page controls; do not assume EPL identifiers match NHL.
2. Use FantraxAPI scoring-period objects for league period date mapping, while separately verifying official league finalization.
3. Evaluate `downloadPlayerStats` timeframe parameters as a fallback; distinguish `transactionPeriod` from scoring period.
4. Require period attribution, G+A column mapping, full pagination, player ID matching and reconciliation against archived team totals before promoting to canonical weekly evidence.
5. Native Fantrax messages/cards/chatbot: no supported write/embedding contract established in this research. Discord companion bot is a demonstrated alternative, not a native integration.

## Operational safeguards

- No raw cookies, auth headers, user secrets or private payloads in logs.
- Conservative sequential requests; handle 429 with backoff; no unsupported rate-limit guarantees.
- Keep authenticated internal API separate from public beta API.
- Do not import third-party code without checking its license.
- Research index is a navigation and provenance layer, not an executable provider contract.


## Studio-confirmed response metadata, v0.7.10.0.39
The authenticated NHL response has ten tableHeader.cells objects with key/name/shortName metadata, 500 rows each containing ten cells, 81 seasonOrProjections options with code/name/shortName, and paginatedResultSet pageNumber/maxResultsPerPage. These field structures are Studio-verified. The actual codes, column labels, weekly timeframe semantics, and whether 500 rows represent a complete set are NOT verified. v0.7.10.0.40 records only safe, bounded column and selector metadata and numeric pagination fields, preserving the existing unverified-period gate.

## v0.7.10.0.41 contract decision
Studio v0.7.10.0.40 identified `SEASON_31n_BY_PERIOD` for 2026-27 and a `Pt` (Goals + Assists) column. The provider request now selects BY_PERIOD for recognized 2026-27 season labels, but no scoring-period-number argument has been independently verified. Therefore the acquisition remains `unverified_period` and must not be treated as verified weekly player production. The 500-row page was full; complete pagination and row normalization remain outstanding.
