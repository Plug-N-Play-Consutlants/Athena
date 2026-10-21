# Fantasy weekly intelligence

## Execution path and corrections

A JHLPAA recap now follows the registered route:

`Scout.route_question` -> `Athena.entry_policy.select_entry_route` -> `Athena.intent_resolution.select_executable_route` -> `Athena.request_execution.execute_request` -> `Athena.execution_registry.league_recap` -> `Athena.entry_capabilities.execute_league_recap` -> `Scout.conversation.router.analyze_league` -> `Athena.Investigation.period_execution`.

The current source already prioritizes broad weekly reports over player-leader questions and registers `league_recap` for either presentation mode. The pre-existing regression test checked the classifier only; an end-to-end deterministic test now exercises Public routing, provider-independent evidence acquisition, and final narrative composition.

The reported failure modes have these source-level causes and resolutions:

| Area | Root cause / status |
|---|---|
| Composite routing | The broad-report precedence fix was present but had no regression through the registered Athena request boundary and Scout composer. The acceptance test now covers that path and the exact request shape. |
| Explicit date window | Period execution recognized `Week N` but ignored a user-specified date range and could choose the latest period instead. It now matches a requested date range against the authoritative Fantrax schedule and refuses to substitute a period if there is no exact match. |
| Unresolved period | The activity helper defaulted to a rolling seven-day window when no period was resolved, contradicting the report's stated evidence policy. Weekly reports now omit unattributable transactions instead. |
| Partial evidence | Acquisition results were tracked separately, but the final article did not consistently disclose missing sections. The composer now reports unresolved evidence without suppressing verified standings or transaction findings. |
| Calendar context | Period selection was represented by a small status dictionary with no league/season identity, adjacent periods, or timezone caveat. The execution result now carries those fields from one shared schedule; a calendar boundary is not described as finalized scoring. |
| Release metadata | `Core/version.py` and `pyproject.toml` duplicated version/build literals, so incrementing the runtime version left packaging metadata stale. Package version, build, and release name now point to the runtime constants, and Release Hygiene verifies those source references. |
| Player stats / trading block / historical lineups | Current provider evidence does not validate period-specific player records, authenticated trade-block payload normalization, or archived lineup snapshots. These remain explicit gaps; the pipeline does not substitute season totals or current state. |

## Fantrax capability matrix

“Verified” below means the local request shape or parser is covered by deterministic tests. It does not imply a successful live request for the JHLPAA. Community libraries are implementation references, not an official SDK.

| Capability | Assessment | Local behavior and limitation |
|---|---|---|
| League settings and period calendars | Partially verified | The configured `general/getLeagueInfo` response is read as the source of period boundaries. One valid scoring or roster schedule is sufficient; if both exist and disagree, the resolver reports a conflict. The calendar response's timezone and intraday cutoff are not established. |
| Period standings | Request semantics verified; response contract partial | `get_standings(N, only_period=True)` sends `BY_PERIOD` / `PERIOD_ONLY`; `only_period=False` sends `BY_PERIOD` / `FROM_SEASON_START`. Local snapshot normalization currently accepts cumulative standings and period comparisons subtract cumulative snapshots. A live JHLPAA response has not validated direct period-only normalization, so direct results must not be claimed. |
| Historical rosters | Partial and authentication-dependent | Fantrax's `getTeamRosters?period=N` is a lineup/roster-period endpoint; the Python community library's `team_roster(..., period_number)` uses daily scoring-date indices. Local recap context is only a current snapshot and explicitly does not claim a historical lineup. |
| Transactions | Partial and authentication-dependent | The local FXPA adapter requests claim/drop and trade views separately and preserves canonical transaction IDs. It requests up to 1,000 rows, but does not demonstrate provider pagination completeness or whether timestamps are submission versus effective dates. Period membership uses an explicit period label or the canonical date boundaries, never fetch time. |
| Player G+A by period | Unverified for period attribution | `getPlayerStats` is called through authenticated FXPA with a season selector. The local adapter has no validated individual-period argument/response metadata contract; a season selector or non-empty response is insufficient. Results remain `unverified_period` unless both season and period are explicitly confirmed. |
| Trading block | Authentication-dependent; acquisition not wired | The community Python wrapper exposes `getTradeBlocks` and parses team, last-updated date, comments, offered/wanted players, positions, and stats. Athena has validated snapshot storage/comparison, but no provider adapter has been verified to return a complete authenticated payload in the canonical snapshot schema. |
| Draft picks | Partial | The provider client exposes `general/getDraftPicks`; current ownership is not dated movement evidence and is not attributed to a weekly transaction without an ownership history. |

### Source references

- [Fantrax developer entry point](https://www.fantrax.com/developer) currently presents the developer landing page; it does not publish the FXPA response schemas needed to validate these private-league integrations.
- [meisnate12/FantraxAPI](https://github.com/meisnate12/FantraxAPI) and its [league implementation](https://github.com/meisnate12/FantraxAPI/blob/master/fantraxapi/objs/league.py) show community request semantics for standings, scoring calendars, transactions, rosters, trade blocks, and period results. In that implementation, roster `period_number` denotes a daily scoring-date index.
- [pmurley/go-fantrax](https://github.com/pmurley/go-fantrax) documents the Fantrax beta FXEA endpoints supplied in April 2025, including league info, draft picks, period rosters, and cumulative standings. It does not establish the local authenticated FXPA player-stat response contract.

## Verification boundary

Offline regression fixtures cover routing and composition, exact date-window selection, schedule conflicts, period isolation, and partial player-stat failure. No credentials or live JHLPAA session were available to prove live provider access, response pagination, period-specific G+A, historical roster snapshots, or trading-block completeness. Live integration must be reported as unverified until those checks run with the supported local authentication configuration.
