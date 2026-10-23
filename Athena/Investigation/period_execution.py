"""Authoritative Athena-owned execution of the fantasy league period investigation.

Scout dispatches the request and presents the structured result; it must not
select sources, acquire standings, reconcile evidence or assert completeness.
"""
from __future__ import annotations

from datetime import date, datetime
import re
from typing import Any


_DATE_RANGE = re.compile(
    r"\b(?P<month>January|February|March|April|May|June|July|August|September|October|November|December|"
    r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s+"
    r"(?P<start>\d{1,2})\s*(?:to|through|[-\u2013\u2014])\s*"
    r"(?P<end>\d{1,2})(?:,?\s+(?P<year>\d{4}))?\b",
    re.IGNORECASE,
)
_ISO_DATE_RANGE = re.compile(
    r"\b(?P<start>\d{4}-\d{2}-\d{2})\s*(?:to|through|[-\u2013\u2014])\s*"
    r"(?P<end>\d{4}-\d{2}-\d{2})\b",
    re.IGNORECASE,
)


def _requested_periods(question: str) -> list[int]:
    """Read explicit lists/ranges: 'Weeks 2 and 3', 'Week 2 and Week 3'.

    Do not infer a scoring week from bare dates or arbitrary numbers. This is
    limited to 8 periods; a longer request must be handled deliberately.
    """
    token = re.compile(r"\b(?:weeks?|periods?)\s*(\d{1,3})\b", re.IGNORECASE)
    connector = re.compile(
        r"\s*(,|and|&|to|through|[-\u2013\u2014])\s*"
        r"(?:(?:weeks?|periods?)\s*)?(\d{1,3})\b", re.IGNORECASE)
    values = []
    covered_until = 0
    for match in token.finditer(question):
        if match.start() < covered_until:
            continue
        values.append(int(match.group(1)))
        tail = match.end()
        while part := connector.match(question, tail):
            next_number = int(part.group(2))
            delimiter = part.group(1).lower()
            if delimiter in ('to', 'through', '-', '\u2013', '\u2014'):
                previous = values[-1]
                if next_number >= previous and next_number - previous < 8:
                    values.extend(range(previous + 1, next_number + 1))
                else:
                    raise ValueError('Invalid or excessive scoring period range')
            else:
                values.append(next_number)
            tail = part.end()
        covered_until = tail
    unique = sorted(set(values))
    if len(unique) > 8 or any(value < 1 for value in unique):
        raise ValueError('Scoring period request exceeds the supported 8-period range')
    return unique


def _explicit_period_request(question: str) -> tuple[int | None, tuple[date, date] | None, str | None, bool]:
    numbered = re.search(r"\b(?:week|period)\s*(\d+)\b", question, re.IGNORECASE)
    if numbered:
        return int(numbered.group(1)), None, f"Period {numbered.group(1)}", False
    iso = _ISO_DATE_RANGE.search(question)
    if iso:
        try:
            start, end = date.fromisoformat(iso.group("start")), date.fromisoformat(iso.group("end"))
        except ValueError:
            return None, None, "Invalid requested date range", False
        return None, (start, end), f"{start.isoformat()} through {end.isoformat()}", False
    named = _DATE_RANGE.search(question)
    if named:
        month = named.group("month")
        year = int(named.group("year")) if named.group("year") else None
        try:
            start = datetime.strptime(f"{month} {named.group('start')} {year or 2000}", "%B %d %Y").date()
        except ValueError:
            try:
                start = datetime.strptime(f"{month} {named.group('start')} {year or 2000}", "%b %d %Y").date()
            except ValueError:
                return None, None, "Invalid requested date range", False
        try:
            end = start.replace(day=int(named.group("end")))
        except ValueError:
            return None, None, "Invalid requested date range", False
        if end < start:
            return None, None, "Invalid requested date range", False
        label = (f"{start.isoformat()} through {end.isoformat()}" if year
                 else f"{month} {start.day}-{end.day} (year unspecified)")
        return None, (start, end), label, year is None
    return None, None, None, False


def _match_date_period(schedule: dict, requested: tuple[date, date], *, year_unspecified: bool = False) -> int | None:
    start, end = requested
    matches = []
    for period, bounds in schedule.items():
        try:
            candidate_start = date.fromisoformat(str(bounds["start"]))
            candidate_end = date.fromisoformat(str(bounds["end"]))
            matches_dates = (
                (candidate_start.month, candidate_start.day, candidate_end.month, candidate_end.day)
                == (start.month, start.day, end.month, end.day)
                if year_unspecified
                else candidate_start == start and candidate_end == end
            )
            if matches_dates:
                matches.append(int(period))
        except (KeyError, TypeError, ValueError):
            continue
    return matches[0] if len(matches) == 1 else None


def execute_league_period(*, ctx: Any, question: str, inquiry: Any, profile: dict) -> dict:
        # Stable, exportable execution trace. This records real execution outcomes,
        # not inferred availability from the existence of an implementation.
        investigation_trace = []
        def trace(stage, status, detail):
            investigation_trace.append({"stage": stage, "status": status, "detail": str(detail)})
        trace("scout.route", "selected", "analyze_league: period recap")
        from Athena.Inquiry.execution import summarize_recent_league_activity
        requested_periods = _requested_periods(question)
        explicit_week, requested_dates, explicit_period_label, date_year_unspecified = _explicit_period_request(question)
        if len(requested_periods) > 1:
            # Lead editorial with the latest requested period, not the first
            # regexp match. The complete set is separately audited below.
            explicit_week = requested_periods[-1]
            explicit_period_label = 'Periods ' + ', '.join(str(p) for p in requested_periods)
        # Period/roster-effective ownership cannot be inferred from archived
        # standings alone. The timeline resolver requires verified league rules,
        # eligible puck-drop schedule and effective period end.
        # Resolve the standings period before transaction selection.  An archived
        # period is available evidence, not proof that its scoring window closed.
        from Athena.Investigation.league_recap import resolve_archived_period, research_period
        from Core.project_paths import OUTPUT_DIR
        from Athena.Investigation.standings_acquisition import resolve_league_context
        try:
            archive_league, archive_season = resolve_league_context(ctx.league_profile, ctx.standings_archive)
        except ValueError:
            archive_league, archive_season = None, None
        from Athena.Investigation.fantrax_period_calendar import acquire_unified_period
        unified = acquire_unified_period(archive_league, archive_season)
        trace("provider.fantrax.unified_period", unified.get("status", "unavailable"),
              f"period={unified.get('period')}; source={unified.get('source')}; reason={unified.get('reason')}")
        schedule = unified.get("schedule") or {}
        date_request_unmatched = False
        invalid_date_request = explicit_period_label is not None and explicit_week is None and requested_dates is None
        if invalid_date_request:
            selected_period = None
            date_request_unmatched = True
        elif explicit_week is not None:
            selected_period = explicit_week
        elif requested_dates is not None:
            selected_period = _match_date_period(schedule, requested_dates, year_unspecified=date_year_unspecified)
            date_request_unmatched = selected_period is None
        elif unified.get("status") == "calendar_closed":
            selected_period = unified["period"]
        elif unified.get("status") == "calendar_conflict":
            selected_period = None
        else:
            selected_period = resolve_archived_period(OUTPUT_DIR, archive_league, archive_season)
        explicit_period = explicit_week is not None or requested_dates is not None or explicit_period_label is not None
        archive_period_unverified = not explicit_period and unified.get("status") != "calendar_closed"
        bounds = schedule.get(selected_period) or {}
        period_numbers = sorted(int(number) for number in schedule if str(number).isdigit())
        previous_period = max((number for number in period_numbers if selected_period is not None and number < selected_period), default=None)
        next_period = min((number for number in period_numbers if selected_period is not None and number > selected_period), default=None)
        calendar_closed_through = unified.get("period") if unified.get("status") == "calendar_closed" else None
        period_calendar = {
            "status": "calendar_conflict" if unified.get("status") == "calendar_conflict" else "verified_boundary" if bounds else "unverified",
            "league_id": archive_league, "season": archive_season, "period": selected_period,
            "start": bounds.get("start"), "end": bounds.get("end"),
            "completed": bool(bounds and calendar_closed_through is not None and selected_period <= calendar_closed_through),
            "completion_status": ("calendar_elapsed" if bounds and calendar_closed_through is not None and selected_period <= calendar_closed_through
                                  else "ongoing_or_not_yet_closed" if bounds and calendar_closed_through is not None
                                  else "unverified"),
            "previous_period": previous_period, "next_period": next_period,
            "timezone": ("provider UTC offset in start_at/end_at" if bounds.get("end_at") else "not provided by Fantrax calendar response"),
            "start_at": bounds.get("start_at"), "end_at": bounds.get("end_at"),
            "boundary_kind": unified.get("boundary_kind", "unverified"),
            "boundary_semantics": ("Fantrax season-long POINTS_BASED reporting/roster period; not head-to-head scoringPeriods, and not a verified lineup lock"
                                   if unified.get("boundary_kind") == "points_based_roster_period" else
                                   "provider roster-period timestamp bounds; scoring-window equivalence unverified"
                                   if unified.get("boundary_kind") == "roster_only" else
                                   "provider scoring-period bounds" if bounds else "calendar bounds unavailable"),
            "source": unified.get("source", "none"),
            "verification_status": "provider_calendar_boundary" if bounds else unified.get("status", "unverified"),
            "requested_period_label": explicit_period_label,
            "requested_dates_matched": not date_request_unmatched if requested_dates is not None else None,
        }
        trace("provider.fantrax.period_calendar", period_calendar["status"],
              f"period={selected_period}; source={period_calendar['source']}; completed={period_calendar['completed']}")
        trace("athena.period_timeline", "shared_boundary_verified" if bounds else "awaiting_verified_boundaries",
              f"period={selected_period}; source={period_calendar['source']}")
        activity = summarize_recent_league_activity(ctx.transaction_history or {}, days=7,
            period=selected_period if selected_period is not None else None,
            period_bounds=bounds, allow_rolling=False)
        highlights = activity.get("highlights") or []
        trace("athena.transactions", "executed", f"period={selected_period}; count={activity.get('transaction_count', 0)}; scope={activity.get('scope_method', 'unknown')}")
        from Athena.Investigation.league_editorial import investigate_league_period
        editorial = investigate_league_period(ctx.transaction_history or {}, selected_period, period_bounds=bounds) if selected_period is not None else None
        trace("athena.trade_editorial", "executed" if editorial is not None else "skipped", f"period={selected_period}; trade_count={len((editorial or {}).get('trades') or [])}")
        from Athena.Investigation.evidence_dossier import build_dossier
        dossier = build_dossier(subject=inquiry.temporal_scope.label,
            requirements=["transactions", "standings", "player_performance"],
            evidence={"transactions": activity if activity.get("transaction_count") else None},
            findings=[{"summary": h.get("summary"), "source_id": h.get("transaction_id"),
                       "significance": h.get("significance_score"),
                       "evidence": [h.get("transaction_id")] if h.get("transaction_id") else [],
                       "uncertainty": ["Impact not established without standings and player performance"]}
                      for h in highlights])
        facts = []
        if date_request_unmatched:
            facts.append(f"Requested date window {explicit_period_label} does not match exactly one authoritative Fantrax calendar period; no substitute period was selected.")
        elif archive_period_unverified:
            facts.append("Selected period is an evidence-acquisition target, not independently verified as the latest completed scoring period.")
        elif unified.get("status") == "calendar_closed":
            if unified.get("boundary_kind") == "points_based_roster_period":
                facts.append(f"JHLPAA POINTS_BASED league: Fantrax roster/reporting period {selected_period} elapsed; head-to-head scoringPeriods are not required. Archived standings finalization and scoring eligibility remain separate checks.")
            else:
                facts.append(f"Fantrax {unified.get('boundary_kind', 'period')} calendar identifies period {selected_period} as the latest elapsed period; scoring-window equivalence and standings finalization require separate verification.")
        if period_calendar.get("status") == "verified_boundary":
            facts.append(f"Fantrax {period_calendar['source']} period {selected_period}: "
                         f"{period_calendar['start']} through {period_calendar['end']}; "
                         f"calendar window {'ended' if period_calendar['completed'] else 'ongoing'}. "
                         "Standings finalization and lineup eligibility remain independently unverified.")
        else:
            facts.append("Fantrax shared-period date boundaries not independently verified.")
        facts += [
            f"Time scope: {inquiry.temporal_scope.label}; " + (
                f"explicit {explicit_period_label}." if explicit_period_label else
                "shared league period selected where verified; no rolling-week substitution."
            ),
            f"Canonical transactions in scope: {activity.get('transaction_count', 0)} across {activity.get('team_count', 0)} observed teams.",
        ]
        types = activity.get("transaction_types") or {}
        if types:
            facts.append("Transaction mix: " + ", ".join(f"{k}={v}" for k, v in sorted(types.items())) + ".")
        facts.extend(f"Significant activity: {item.get('summary')}" for item in highlights)
        if editorial and editorial.get("trades"):
            facts.append("Editorial lead: " + editorial["opening"])
            facts.extend(story["lead"] for story in editorial["trades"])
            facts.append(editorial["evidence_boundary"])
        if highlights:
            lead = highlights[0].get("summary")
            scope_label = (f"season week {explicit_week}" if explicit_week is not None
                           else f"date window {explicit_period_label}" if requested_dates is not None
                           else inquiry.temporal_scope.label)
            conclusion = (f"For {scope_label}, Athena found {activity.get('transaction_count', 0)} canonical transaction(s) "
                          f"in the requested window. The strongest transaction signal is: {lead} "
                          "This is a transaction-led briefing, not a complete league report: standings and player-performance evidence have not been reconciled.")
        else:
            conclusion = (f"Athena found no dated canonical transactions inside the requested {inquiry.temporal_scope.label} window. "
                          "It will not substitute season-to-date transaction totals for a weekly recap.")
        if editorial and editorial.get("trades"):
            from Athena.Investigation.league_editorial import compose_league_editorial
            conclusion = compose_league_editorial(editorial, selected_period if selected_period is not None else inquiry.temporal_scope.label)
        standings_comparison = None
        standings_summary = None
        standings_period = selected_period
        from Athena.Investigation.standings_acquisition import ensure_period_snapshots
        from Athena.Investigation.standings_archive import compare_archived
        if archive_league and archive_season:
            if standings_period is None and not explicit_period:
                archive_dir = OUTPUT_DIR / "Standings" / str(archive_league) / str(archive_season)
                archived = sorted(int(p.stem.split("_")[-1]) for p in archive_dir.glob("period_*.json")
                                  if p.stem.split("_")[-1].isdigit())
                # An archive is evidence of availability, not proof a period has closed.
                standings_period = max(archived) if archived else None
            if standings_period is not None:
                # Reconcile the calendar when archive fallback changes the period.
                if standings_period != selected_period:
                    bounds = schedule.get(standings_period) or {}
                    period_calendar.update({
                        "period": standings_period, "start": bounds.get("start"), "end": bounds.get("end"),
                        "status": "verified_boundary" if bounds else "unverified",
                        "completed": bool(bounds and calendar_closed_through is not None and standings_period <= calendar_closed_through),
                        "verification_status": "provider_calendar_boundary" if bounds else "unverified",
                    })
                    trace("provider.fantrax.period_calendar", period_calendar["status"],
                          f"period={standings_period}; source={period_calendar['source']}; reconciled=true")
                    trace("athena.period_timeline",
                          "calendar_boundary_verified" if bounds else "awaiting_verified_boundaries",
                          f"period={standings_period}; reconciled=true")
                    if bounds:
                        facts.append(f"Reconciled Fantrax {period_calendar['source']} period {standings_period}: "
                                     f"{period_calendar['start']} through {period_calendar['end']}.")
                fetcher = None
                try:
                    from Providers.Fantrax.fantrax_client import FantraxClient
                    client = FantraxClient(league_id=archive_league, season=archive_season)
                    if client.has_cookie_auth():
                        fetcher = lambda p: client.get_standings(p)
                except (ImportError, ValueError, OSError) as exc:
                    trace("provider.fantrax.standings", "unavailable", f"{type(exc).__name__}: {exc}")
                trace("provider.fantrax.standings", "authenticated" if fetcher else "no_authenticated_fetcher", f"league={archive_league}; season={archive_season}")
                standings_acquisition = ensure_period_snapshots(OUTPUT_DIR, league_id=archive_league,
                    season=archive_season, period=standings_period,
                    expected_teams=(ctx.league_profile or {}).get("team_count"), fetch=fetcher)
                standings_comparison = compare_archived(OUTPUT_DIR, archive_league, archive_season, standings_period)
                trace("athena.standings", standings_comparison.get("status", "unknown"), f"period={standings_period}; acquisition={standings_acquisition.get('status', 'unknown') if isinstance(standings_acquisition, dict) else type(standings_acquisition).__name__}")
                if standings_comparison.get("status") == "compared":
                    rows = standings_comparison["teams"]
                    movers = sorted((r for r in rows if isinstance(r.get("rank_change"), int) and r["rank_change"] != 0),
                        key=lambda r: abs(r["rank_change"]), reverse=True)
                    leaders = sorted((r for r in rows if isinstance(r.get("period_points"), (int, float))),
                        key=lambda r: r["period_points"], reverse=True)
                    standings_summary = (f"Standings after scoring period {standings_period}: " +
                        "; ".join(f"{r.get('name') or r['team_id']} {'rose' if r['rank_change'] > 0 else 'fell'} "
                        f"{abs(r['rank_change'])} to rank {r['rank']}" for r in movers[:6]) +
                        (". Top period scorers: " + "; ".join(f"{r.get('name') or r['team_id']} {r['period_points']:g}" for r in leaders[:3]) if leaders else ""))
                    facts.append(standings_summary)
                    conclusion += "\n\nStandings and scoring\n\n" + standings_summary
                else:
                    facts.append(f"Standings comparison for period {standings_period} is incomplete; missing verified snapshots.")
                if not explicit_week and archive_period_unverified:
                    facts.append("Latest available archived scoring period is not independently confirmed as the last completed period.")
        # Attempt only a configured, authenticated player-production source.
        # A nonempty response is not verified until its season, period and G+A
        # records pass validation. Never substitute the player master snapshot.
        from Athena.Investigation.period_evidence_acquisition import acquire_player_period_production
        player_production = acquire_player_period_production(
            league_id=archive_league, season=archive_season, period=standings_period)
        trace("provider.fantrax.player_period_production", player_production["status"],
              player_production["reason"] + ("; diagnostic=" + str(player_production["diagnostic"])
                                            if player_production.get("diagnostic") else ""))
        if player_production["verified"]:
            facts.append(f"Verified period {standings_period} player production: "
                         f"{len(player_production['records'])} G+A records acquired.")
        else:
            facts.append("Player-period production acquisition: " + player_production["status"] +
                         " (" + player_production["reason"] + ").")
            # Provider diagnostics are a separate, sanitized fact. Studio's
            # session exporter retains observed_facts but not trace.detail.
            diagnostic = player_production.get("diagnostic") or {}
            if diagnostic:
                diagnostic_parts = [f"{key}={diagnostic[key]}" for key in
                                    ("code", "message", "exception_type") if diagnostic.get(key)]
                if diagnostic_parts:
                    facts.append("Player-period provider diagnostic: " + "; ".join(diagnostic_parts) + ".")
        inspection = player_production.get("schema_inspection") or {}
        if inspection:
            # Only metadata constructed from fixed allowlisted fields.
            import json as _json
            # Diagnostic metadata is for the developer trace, not the league
            # editorial or the user-facing observed-facts feed. Keep a concise
            # acquisition summary; retain bounded schema detail in the trace.
            trace("provider.fantrax.player_stats_schema", "inspected",
                  _json.dumps(inspection, sort_keys=True, separators=(",", ":"))[:2400])
        # Historical period rosters are a documented, separate provider source.
        # getTeamRosters(period=N) includes provider period echo and ACTIVE vs
        # RESERVE designations. Backfill the small recent window in one pass.
        from Athena.Investigation.historical_roster_attribution import (
            backfill_period_rosters, reconcile_period_points,
        )
        historical_backfill = backfill_period_rosters(
            league_id=archive_league, season=archive_season,
            through_period=standings_period,
            expected_teams=(ctx.league_profile or {}).get("team_count"),
        )
        historical_rosters = historical_backfill.get("periods", {}).get(standings_period, {})
        trace("provider.fantrax.historical_rosters", historical_rosters.get("status", "unavailable"),
              f"period={standings_period}; verified_backfill={historical_backfill.get('verified_count', 0)}; "
              f"teams={historical_rosters.get('team_count', 0)}; reason={historical_rosters.get('reason', '')}")
        if historical_rosters.get("verified"):
            facts.append(f"Fantrax historical period {standings_period} roster: "
                         f"{historical_rosters['player_count']} players on {historical_rosters['team_count']} teams; "
                         f"{historical_rosters['active_count']} marked ACTIVE. "
                         "This alone does not establish credited fantasy scoring.")
        else:
            facts.append("Fantrax historical period roster acquisition: " +
                         historical_rosters.get("status", "unavailable") +
                         " (" + historical_rosters.get("reason", "not acquired") + ").")
        # Independent official NHL game results for rostered players. This
        # reports individual NHL G+A, NOT Fantrax credited fantasy points or
        # verified historical owner/lineup eligibility. No player-per-request
        # fan-out; one date-filtered summary and two boundary schedules.
        from Athena.Investigation.nhl_period_production import acquire_nhl_period_production
        nhl_production = acquire_nhl_period_production(
            league_id=archive_league, season=archive_season,
            period=standings_period, boundary=period_calendar,
            period_rosters=historical_rosters if historical_rosters.get("verified") else None)
        trace("provider.nhl.period_game_production", nhl_production.get("status", "unavailable"),
              f"matched_players={nhl_production.get('matched_players', 0)}; reason={nhl_production.get('reason', '')}")
        if nhl_production.get("verified"):
            roster_basis = "historical period" if nhl_production.get("roster_basis") == "verified_historical_period" else "current snapshot"
            facts.append(f"Official NHL game performance: {nhl_production.get('matched_players', 0)} {roster_basis} player identities matched in the reporting window; fantasy point credit requires Fantrax reconciliation.")
        else:
            facts.append("Official NHL period game performance: " + nhl_production.get("status", "unavailable") +
                         " (" + nhl_production.get("reason", "unknown") + ").")
        attribution = reconcile_period_points(historical_rosters, nhl_production,
                                               standings_comparison or {})
        if attribution.get("teams") and archive_league and archive_season and type(standings_period) is int:
            try:
                from Athena.Investigation.sync_period_scoring_audit import write_period_audit
                write_period_audit(OUTPUT_DIR, archive_league, archive_season,
                                   standings_period, attribution)
                trace("athena.period_scoring_archive", "archived", f"period={standings_period}")
            except (ValueError, OSError, TypeError) as exc:
                trace("athena.period_scoring_archive", "unavailable", type(exc).__name__)
        trace("athena.period_point_attribution", attribution.get("status", "unavailable"),
              f"numeric_matches={attribution.get('numeric_matched_teams', 0)}/"
              f"{attribution.get('team_count', 0)}; complete={attribution.get('fully_reconciled_teams', 0)}; "
              f"reason={attribution.get('reason', '')}")
        if attribution.get("teams"):
            facts.append(f"Historical roster NHL-to-Fantrax scoring check: "
                         f"{attribution['numeric_matched_teams']}/{attribution['team_count']} numeric matches; "
                         f"{attribution['fully_reconciled_teams']} with complete active-player identity coverage. "
                         "Unmatched teams are NOT verified fantasy credits.")
        # Report evidence coverage as an actual inspection, not a claim that a
        # player-statistics provider was queried. Player master is identity data.
        player_records = ctx.player_master if isinstance(ctx.player_master, list) else []
        player_stat_records = sum(1 for player in player_records if isinstance(player, dict) and any(
            isinstance(player.get(key), (int, float)) for key in ("season_goals", "season_assists", "weekly_points", "period_points")
        ))
        facts.append(f"Player evidence inspection: {len(player_records)} master records; {player_stat_records} with recognized production fields. Player master records alone cannot establish scoring-period production.")
        # Reconcile existing roster/IR and future-pick artifacts as bounded snapshot
        # context. Neither source establishes a past scoring-period lineup or impact.
        from Athena.Investigation.recap_context import reconcile_recap_context
        recap_context = reconcile_recap_context(
            OUTPUT_DIR, active_season=archive_season, selected_period=standings_period,
            teams=[r.get("name") for r in (standings_comparison or {}).get("teams", []) if r.get("name")],
        )
        roster_context = recap_context["roster"]
        if roster_context.get("status") == "current_snapshot_context_only" and not historical_rosters.get("verified"):
            facts.append(f"Current roster snapshot: {roster_context['player_count']} players across "
                         f"{len(roster_context['teams'])} teams, fetched {roster_context.get('fetched_at')}; "
                         "not a verified scoring-period lineup or keeper selection.")
        ir_context = recap_context["injuries"]
        if ir_context.get("status") == "roster_ir_only_not_medical_verification":
            affected = sum(len(v) for v in ir_context["teams"].values())
            facts.append(f"Roster IR designations: {affected} players in the current snapshot; "
                         "injury diagnoses and Week-specific IR timing not verified.")
        picks_context = recap_context["draft_assets"]
        if picks_context.get("status") == "future_ownership_snapshot":
            facts.append(f"Future draft ownership: {picks_context['pick_count']} source-recorded picks; "
                         "not linked to this week's transactions without dated ownership history.")
        trace("athena.roster_context", "historical_period_lineup" if historical_rosters.get("verified") else roster_context.get("status"), "provider historical roster with ACTIVE/RESERVE; game credits require reconciliation" if historical_rosters.get("verified") else "snapshot only; no period lineup claim")
        trace("athena.injury_context", ir_context.get("status"), "IR designation only; no medical claim")
        trace("athena.draft_context", picks_context.get("status"), "future ownership only; no transaction causality")
        # Coverage is an explicit investigation artifact, not an inflated confidence
        # score.  Unresolved requirements remain visible to Doctor and callers.
        evidence_coverage = {
            "transactions": "available" if activity.get("transaction_count") else "no_events_verified",
            "period_standings": "available" if standings_comparison and standings_comparison.get("status") == "compared" else "incomplete",
            "player_period_production": ("verified" if attribution.get("status") == "reconciled" else
                                         "verified_nhl_window_only" if nhl_production.get("verified") else
                                         player_production["status"]),
            "roster_and_keeper_context": ("historical_period_lineup" if historical_rosters.get("verified") else
                                         "snapshot_context_only" if roster_context.get("status") == "current_snapshot_context_only" else "not_reconciled"),
            "fantasy_point_attribution": ("reconciled" if attribution.get("status") == "reconciled" else
                                          "partial" if attribution.get("teams") else "not_reconciled"),
            "injury_context": ("ir_designations_only" if ir_context.get("status") == "roster_ir_only_not_medical_verification" else "not_acquired"),
            "draft_asset_context": ("future_ownership_snapshot_only" if picks_context.get("status") == "future_ownership_snapshot" else "not_reconciled"),
        }
        from Athena.Investigation.recap_evidence_plan import audit_recap_evidence
        acquisition_audit = audit_recap_evidence(OUTPUT_DIR, selected_period)
        if historical_rosters.get("verified"):
            acquisition_audit["roster"] = {
                "status": "verified_historical_period_lineup",
                "reason": f"Fantrax period {standings_period}: {historical_rosters['team_count']} team rosters, "
                          f"{historical_rosters['active_count']} ACTIVE players; credited points reconciled separately",
                "period": standings_period,
            }
        if nhl_production.get("verified"):
            acquisition_audit["player_production"] = {
                "status": "verified_nhl_game_window",
                "reason": f"Official NHL period {standings_period} G+A; fantasy team credit is a separate audited step",
                "period": standings_period,
            }
        facts.append("Investigation coverage: " + "; ".join(f"{k}={v}" for k,v in evidence_coverage.items()) + ".")
        facts.append("Evidence routing audit: " + "; ".join(
            f"{k}={v['status']} ({v['reason']})" for k,v in acquisition_audit.items()) + ".")
        for kind, evidence in acquisition_audit.items():
            trace(f"evidence.{kind}", evidence.get("status", "unknown"), evidence.get("reason", ""))
        for kind, status in evidence_coverage.items():
            trace(f"coverage.{kind}", status, "Acquisition coverage, not proof of analytical completion")
        # Presentation is downstream of all investigation and evidence checks.
        # This is a sequencing safeguard, not a claim of completed acquisition.
        # Athena synthesizes only after the available evidence has been gathered.
        athena_research = research_period(
            league_name=profile['league_name'], period=standings_period,
            comparison=standings_comparison, editorial=editorial,
            activity=activity, history=ctx.transaction_history or {},
            context=recap_context, coverage=evidence_coverage)
        # Source-backed editorial continuity: never infer a multi-week streak
        # from one period delta, current rosters or an incomplete archive.
        from Athena.Investigation.editorial_storylines import investigate_storyline_continuity
        storyline = investigate_storyline_continuity(OUTPUT_DIR, archive_league,
                                                      archive_season, standings_period)
        athena_research["storyline_continuity"] = storyline
        trace("athena.editorial_storylines", storyline["status"],
              f"verified_signals={len(storyline['signals'])}")
        athena_research["period_calendar"] = period_calendar
        athena_research["historical_roster_attribution"] = attribution
        athena_research["historical_roster_evidence"] = {
            k: v for k, v in historical_rosters.items() if k not in ("records", "teams")
        }
        athena_research["nhl_period_production"] = {
            k: v for k, v in nhl_production.items() if k != "records"
        }
        from Athena.Investigation.editorial_player_attribution import editorial_contributors
        athena_research["editorial_player_attribution"] = editorial_contributors(attribution, nhl_production)
        trace("athena.editorial_player_attribution",
              athena_research["editorial_player_attribution"]["status"],
              f"linked_contributors={len(athena_research['editorial_player_attribution']['records'])}")
        if nhl_production.get("verified"):
            # Keep NHL skater production under its own contract, without
            # representing it as Fantrax roster/lineup scoring.
            athena_research["nhl_player_leaders"] = nhl_production["records"][:12]
        if len(requested_periods) > 1:
            from Athena.Investigation.multi_period_audit import investigate_requested_periods
            multi = investigate_requested_periods(
                output_dir=OUTPUT_DIR, league_id=archive_league,
                season=archive_season, periods=requested_periods,
                expected_teams=(ctx.league_profile or {}).get("team_count"))
            athena_research["multi_period_scoring"] = multi
            trace("athena.multi_period_scoring", multi.get("status", "unavailable"),
                  f"requested={requested_periods}; audited={multi.get('audited_periods', 0)}; "
                  f"unavailable={multi.get('unavailable_periods', 0)}")
            facts.append("Requested scoring periods: " + ", ".join(str(p) for p in requested_periods)
                         + f"; {multi.get('audited_periods', 0)} period audits available; "
                         + f"{multi.get('unavailable_periods', 0)} unavailable. "
                         "Numeric matches are not game-effective fantasy credit proof.")
        trace("athena.research", "synthesized_partial" if any(v in {"not_attempted", "not_acquired", "incomplete", "not_reconciled", "failed", "source_error", "wrong_period", "invalid_schema"} for v in evidence_coverage.values()) else "synthesized", f"findings={len(athena_research['findings'])}; structured contract v1")
        return {
            "selected_period": selected_period, "standings_period": standings_period, "period_calendar": period_calendar,
            "activity": activity, "editorial": editorial, "dossier": dossier,
            "facts": facts, "highlights": highlights,
            "standings_comparison": standings_comparison, "standings_summary": standings_summary,
            "recap_context": recap_context, "evidence_coverage": evidence_coverage,
            "acquisition_audit": acquisition_audit, "player_production_acquisition": player_production,
            "nhl_period_production_acquisition": nhl_production,
            "historical_roster_backfill": historical_backfill,
            "period_point_attribution": attribution,
            "requested_periods": requested_periods,
            "athena_research": athena_research,
            "investigation_trace": investigation_trace, "explicit_week": explicit_period,
        }
