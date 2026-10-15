"""Authoritative Athena-owned execution of the fantasy league period investigation.

Scout dispatches the request and presents the structured result; it must not
select sources, acquire standings, reconcile evidence or assert completeness.
"""
from __future__ import annotations

import re
from typing import Any


def execute_league_period(*, ctx: Any, question: str, inquiry: Any, profile: dict) -> dict:
        # Stable, exportable execution trace. This records real execution outcomes,
        # not inferred availability from the existence of an implementation.
        investigation_trace = []
        def trace(stage, status, detail):
            investigation_trace.append({"stage": stage, "status": status, "detail": str(detail)})
        trace("scout.route", "selected", "analyze_league: period recap")
        from Athena.Inquiry.execution import summarize_recent_league_activity
        explicit_week = re.search(r"\bweek\s*(\d+)\b", question, re.IGNORECASE)
        # Resolve the standings period before transaction selection.  An archived
        # period is available evidence, not proof that its scoring window closed.
        from Athena.Investigation.league_recap import resolve_archived_period, research_period
        from Core.project_paths import OUTPUT_DIR
        from Athena.Investigation.standings_acquisition import resolve_league_context
        try:
            archive_league, archive_season = resolve_league_context(ctx.league_profile, ctx.standings_archive)
        except ValueError:
            archive_league, archive_season = None, None
        selected_period = int(explicit_week.group(1)) if explicit_week else resolve_archived_period(OUTPUT_DIR, archive_league, archive_season)
        activity = summarize_recent_league_activity(ctx.transaction_history or {}, days=7,
            period=selected_period if selected_period is not None else None)
        highlights = activity.get("highlights") or []
        trace("athena.transactions", "executed", f"period={selected_period}; count={activity.get('transaction_count', 0)}; scope={activity.get('scope_method', 'unknown')}")
        from Athena.Investigation.league_editorial import investigate_league_period
        editorial = investigate_league_period(ctx.transaction_history or {}, selected_period) if selected_period is not None else None
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
        facts = [
            f"Time scope: {inquiry.temporal_scope.label}; " + (f"canonical season week {explicit_week.group(1)}." if explicit_week else "rolling seven calendar days; league-period alignment unverified."),
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
            conclusion = (f"For {'season week '+explicit_week.group(1) if explicit_week else inquiry.temporal_scope.label}, Athena found {activity.get('transaction_count', 0)} canonical transaction(s) "
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
        from Core.project_paths import OUTPUT_DIR
        if archive_league and archive_season:
            if standings_period is None:
                archive_dir = OUTPUT_DIR / "Standings" / str(archive_league) / str(archive_season)
                archived = sorted(int(p.stem.split("_")[-1]) for p in archive_dir.glob("period_*.json")
                                  if p.stem.split("_")[-1].isdigit())
                # An archive is evidence of availability, not proof a period has closed.
                standings_period = max(archived) if archived else None
            if standings_period is not None:
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
                if not explicit_week:
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
            facts.append("Player-period response schema inspection: " +
                         _json.dumps(inspection, sort_keys=True, separators=(",", ":")) + ".")
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
        if roster_context.get("status") == "current_snapshot_context_only":
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
        trace("athena.roster_context", roster_context.get("status"), "snapshot only; no period lineup claim")
        trace("athena.injury_context", ir_context.get("status"), "IR designation only; no medical claim")
        trace("athena.draft_context", picks_context.get("status"), "future ownership only; no transaction causality")
        # Coverage is an explicit investigation artifact, not an inflated confidence
        # score.  Unresolved requirements remain visible to Doctor and callers.
        evidence_coverage = {
            "transactions": "available" if activity.get("transaction_count") else "no_events_verified",
            "period_standings": "available" if standings_comparison and standings_comparison.get("status") == "compared" else "incomplete",
            "player_period_production": player_production["status"],
            "roster_and_keeper_context": ("snapshot_context_only" if roster_context.get("status") == "current_snapshot_context_only" else "not_reconciled"),
            "injury_context": ("ir_designations_only" if ir_context.get("status") == "roster_ir_only_not_medical_verification" else "not_acquired"),
            "draft_asset_context": ("future_ownership_snapshot_only" if picks_context.get("status") == "future_ownership_snapshot" else "not_reconciled"),
            "trading_block": "not_attempted",
        }
        from Athena.Investigation.recap_evidence_plan import audit_recap_evidence
        acquisition_audit = audit_recap_evidence(OUTPUT_DIR, selected_period)
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
        trace("athena.research", "synthesized_partial" if any(v in {"not_attempted", "not_acquired", "incomplete", "not_reconciled", "failed", "source_error", "wrong_period", "invalid_schema"} for v in evidence_coverage.values()) else "synthesized", f"findings={len(athena_research['findings'])}; structured contract v1")
        return {
            "selected_period": selected_period, "standings_period": standings_period,
            "activity": activity, "editorial": editorial, "dossier": dossier,
            "facts": facts, "highlights": highlights,
            "standings_comparison": standings_comparison, "standings_summary": standings_summary,
            "recap_context": recap_context, "evidence_coverage": evidence_coverage,
            "acquisition_audit": acquisition_audit, "player_production_acquisition": player_production,
            "athena_research": athena_research,
            "investigation_trace": investigation_trace, "explicit_week": bool(explicit_week),
        }
