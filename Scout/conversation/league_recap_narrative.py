"""Scout-owned narrative: consumes analytical findings; does not investigate."""

from datetime import date


def _points(value):
    return f"{value:g}" if isinstance(value, (int, float)) else "unverified"


def _describe(f):
    kind, team = f["kind"], f.get("team")
    change, rank, points = f.get("rank_change"), f.get("rank"), f.get("period_points")
    movement = f"{abs(change)} {'place' if abs(change) == 1 else 'places'}" if isinstance(change, int) else ""
    if kind == "trade_cluster":
        exchanges = []
        for exchange in f.get("exchanges", []):
            received = exchange.get("received") if isinstance(exchange.get("received"), dict) else {}
            parts = [f"{club} acquired {', '.join(assets)}" for club, assets in received.items() if assets]
            if parts:
                exchanges.append("; ".join(parts))
        detail = ". ".join(exchanges)
        return (f"{team} completed {f['trade_count']} separate trades, making it the week's busiest trading team. "
                + (detail + ". " if detail else "")
                + "The exchanges are confirmed; their competitive impact remains to be seen.")
    if kind == "trade":
        exchanges = []
        for exchange in f.get("exchanges", []):
            received = exchange.get("received") if isinstance(exchange.get("received"), dict) else {}
            details = [f"{team} acquired {', '.join(assets)}" for team, assets in received.items() if assets]
            if details:
                exchanges.extend(details)
        count = f["trade_count"]
        trade_word = "trade" if count == 1 else "trades"
        detail = " Verified movement: " + "; ".join(exchanges) + "." if exchanges else ""
        return (f"The league recorded {count} {trade_word} this period.{detail} "
                "Competitive impact remains to be established.")
    if kind == "surge":
        return f"{team} put up {_points(points)} points, {'the highest verified total' if f.get('top_score') else 'one of the top totals'} of the week, and climbed {movement} to rank {rank}."
    if kind == "scoring_leader":
        return f"{team} posted {_points(points)} points, among the week's leading performances."
    if kind == "slide":
        return f"{team} slipped {movement} to rank {rank}, with {_points(points)} points this week. The scoring record alone doesn't explain the cause."
    if kind == "climb":
        return f"{team} moved up {movement} to rank {rank}, scoring {_points(points)} points."
    if kind == "secondary_market":
        examples = "; ".join(f.get("examples", []))
        return f"Beyond the trades, {f['transaction_count']} other transactions were recorded." + (f" For example: {examples}." if examples else "")
    if kind == "market":
        return f"The league recorded {f['transaction_count']} transactions in the selected period."
    if kind == "quiet_success":
        return f"{team} scored {_points(points)} points without a recorded transaction across the two observed weeks. Sometimes the scoreboard does the talking."
    if kind == "quiet_watch":
        names = ", ".join(f.get("teams", [])[:3])
        return f"No transactions were recorded for {names}{' and others' if len(f.get('teams', [])) > 3 else ''} across the two observed weeks. Who makes the next move?"
    raise ValueError(f"Unsupported Athena research finding: {kind}")


def _evidence_gaps(research):
    coverage = research.get("coverage") if isinstance(research.get("coverage"), dict) else {}
    labels = {
        "period_standings": "Period standings and movement",
        "player_period_production": "Individual player production",
        "roster_and_keeper_context": "Historical period lineup context",
        "injury_context": "Period-specific injury and lineup impact",
        "draft_asset_context": "Dated draft-asset movement",
        "fantasy_point_attribution": "Fantrax credited team-point reconciliation",
    }
    attribution = research.get("historical_roster_attribution") or {}
    unresolved = []
    for key, label in labels.items():
        status = coverage.get(key)
        if status in (None, "available", "verified", "reconciled"):
            continue
        if status == "historical_period_lineup":
            continue  # Historical lineup is acquired; keeper contract audit is separate.
        if status == "snapshot_context_only":
            description = "current snapshot only; not period history"
        elif status == "ir_designations_only":
            description = "roster designation only; medical timing is unverified"
        elif status == "future_ownership_snapshot_only":
            description = "current ownership snapshot; no dated movement link"
        elif status == "verified_nhl_window_only":
            # Official NHL game-level G+A IS available. A successful numeric
            # comparison does not require this redundant generic gap warning.
            if attribution.get("teams"):
                continue
            description = "NHL G+A available; Fantrax team credit not independently established"
        elif key == "fantasy_point_attribution":
            teams = attribution.get("teams") or []
            if teams:
                differences = [t for t in teams if t.get("status") == "discrepancy"]
                identity_gaps = [t for t in teams if t.get("unmatched_active_ids")]
                if not differences and not identity_gaps:
                    continue
                description = (f"{len(differences)} of {len(teams)} team totals differ; "
                               f"{len(identity_gaps)} have unresolved ACTIVE identities; "
                               "game-effective lineup credit remains unverified")
            else:
                description = "team-period attribution not independently established"
        elif status == "unverified_period":
            description = "the provider did not confirm the requested season and period"
        elif status in {"not_attempted", "not_acquired", "not_reconciled", "incomplete"}:
            description = "not available as verified period evidence"
        else:
            description = "not verified for this period"
        unresolved.append(f"{label}: {description}")
    return unresolved


def compose_period_report(*, research):
    if research.get("schema") != "athena.league_period_research.v2":
        raise ValueError("Scout requires Athena structured research contract v2")
    label = f"Week {research['period']}" if research.get("period") else "recent activity"
    calendar = research.get("period_calendar") if isinstance(research.get("period_calendar"), dict) else {}
    if calendar.get("start") and calendar.get("end"):
        try:
            start = date.fromisoformat(calendar["start"])
            end = date.fromisoformat(calendar["end"])
            label += f" ({start.strftime('%B')} {start.day}-{end.day}, {end.year})"
        except (TypeError, ValueError):
            pass
    lines = [f"{research['league_name']} | {label}"]
    multi = research.get("multi_period_scoring") or {}
    if multi.get("requested_periods"):
        lines.append("Historical scoring audit — requested periods")
        for period in multi.get("periods") or []:
            number = period["period"]
            if period.get("status") not in ("partial", "numeric_complete"):
                lines.append(f"Week {number}: not audited — {period.get('reason') or 'verified period evidence unavailable'}.")
                continue
            teams = period.get("teams") or []
            lines.append(f"Week {number}: {period['numeric_matched_teams']}/{period['team_count']} numerically matched; "
                         f"{period['identity_complete_teams']} complete ACTIVE identity rosters; "
                         f"{period.get('reserve_nhl_points_excluded', 0):g} NHL reserve points excluded "
                         "(not Fantrax-credit evidence).")
            for team in teams:
                if team.get("difference") is None:
                    scored = "official team total unavailable"
                elif team.get("difference"):
                    scored = (f"{team.get('identified_active_nhl_points', 0):g} NHL ACTIVE vs "
                              f"{team.get('fantrax_points', 0):g} Fantrax "
                              f"(difference {team['difference']:+g})")
                else:
                    scored = f"{team.get('fantrax_points', 0):g}/{team.get('fantrax_points', 0):g} numeric match"
                unresolved = team.get("unmatched_active_ids") or []
                details = team.get("unmatched_active_details") or []
                if unresolved and details:
                    evidence_by_id = {str(row.get('fantrax_player_id')): row for row in details
                                      if isinstance(row, dict)}
                    labels = []
                    for fid in unresolved:
                        item = evidence_by_id.get(str(fid), {})
                        name = item.get('player_name') or 'unidentified player'
                        cause = item.get('match_method') or item.get('resolution_status') or 'unresolved'
                        labels.append(f"{name} [{fid}] ({cause})")
                    note = "; unresolved ACTIVE identities: " + ", ".join(labels)
                else:
                    note = f"; unresolved ACTIVE IDs: {', '.join(map(str, unresolved))}" if unresolved else ""
                lines.append(f"{team.get('team_name') or team.get('team_id')}: {scored}{note}.")
        lines.append("An archived ACTIVE roster is a period snapshot, not proof of game-by-game scoring eligibility.")
    findings = research.get("findings") or []
    if not findings:
        lines.append("There isn't enough verified evidence to identify a league-wide development yet.")
        gaps = _evidence_gaps(research)
        if gaps:
            lines.append("Evidence still missing")
            lines.extend(gaps)
        return "\n\n".join(lines)
    lead = findings[0]
    lines.extend(["The week's defining development", _describe(lead)])
    primary = [f for f in findings[1:] if f["kind"] not in ("secondary_market", "market", "quiet_watch", "quiet_success")]
    if primary:
        lines.append("Around the league")
        lines.extend(_describe(f) for f in primary)
    attribution = research.get("historical_roster_attribution") or {}
    team_audits = attribution.get("teams") or []
    nhl_leaders = research.get("nhl_player_leaders") or []
    if nhl_leaders:
        lines.append("Individual NHL performances (matched players)")
        positive = [r for r in nhl_leaders if isinstance(r, dict) and isinstance(r.get("points"), int) and r["points"] > 0]
        for r in positive[:8]:
            lines.append(f"{r['player_name']}: {r['points']} NHL points ({r['goals']} G, {r['assists']} A) in {r['games_played']} games.")
        detail = research.get("nhl_period_production") or {}
        roster_basis = ("historical period roster" if detail.get("roster_basis") == "verified_historical_period"
                        else "current roster")
        coverage = (f" Matched crosswalk coverage: {detail['roster_crosswalk_resolved']} of {detail['roster_count']} {roster_basis} entries."
                    if isinstance(detail.get("roster_crosswalk_resolved"), int) and isinstance(detail.get("roster_count"), int) else "")
        lineup_note = ("Historical ACTIVE lineup snapshots permit numeric team checks, not independent puck-drop eligibility proof."
                       if team_audits else
                       "They are NOT confirmed fantasy points for the team currently holding the player; historical lineup and transaction-effective period still require reconciliation.")
        lines.append("These are official NHL G+A results for matched players." + coverage + " " + lineup_note)
    if team_audits and not multi.get("requested_periods"):
        lines.append("Historical lineup scoring — team-by-team")
        # All fourteen teams must be visible, not merely the convenient scoring
        # leaders. A mismatch buried in debug-only output defeats acceptance.
        top_ids = {str(r.get("team_id")) for r in ((research.get("comparison") or {}).get("teams") or [])
                   if isinstance(r, dict) and isinstance(r.get("period_points"), (int, float))
                   and r.get("period_points", 0) >= 35}
        prioritized = sorted(team_audits, key=lambda r: (r["team_id"] not in top_ids,
                                                       -(r.get("fantrax_points") or 0), r.get("team_name") or ""))
        for club in prioritized:
            leaders = club.get("contributors") or []
            top = ", ".join(f"{r['name']} ({r['points']})" for r in leaders[:3])
            if not top:
                top = "no confirmed scoring contributors identified"
            if club.get("status") == "reconciled":
                result = f"{club['fantrax_points']:g} Fantrax points numerically matched against historical ACTIVE NHL scoring"
            elif club.get("status") == "reconciled_with_identity_gaps":
                result = f"{club['fantrax_points']:g} Fantrax points numerically matched; some active identities unresolved"
            elif club.get("difference") is not None:
                result = (f"{club['identified_active_nhl_points']:g} identified NHL points versus "
                          f"{club['fantrax_points']:g} Fantrax points (difference {club['difference']:+g}; not reconciled)")
            else:
                result = "Fantrax team-point baseline unavailable"
            lines.append(f"{club.get('team_name')}: {result}. Leading identified ACTIVE skaters: {top}.")
        lines.append(f"Reconciliation: {attribution.get('numeric_matched_teams', 0)} of "
                     f"{attribution.get('team_count', len(prioritized))} team totals numerically matched; "
                     f"{attribution.get('fully_reconciled_teams', 0)} have complete identity coverage. "
                     "Numeric matches do not independently verify game-effective Fantrax credit; remaining differences are not silently assigned.")
    elif team_audits and multi.get("requested_periods"):
        lines.append("Week " + str(research.get('period')) + " live inquiry check: "
                     + f"{attribution.get('numeric_matched_teams', 0)}/{attribution.get('team_count', 0)} "
                     + "numeric team matches. Complete requested-period team audits are above; "
                     + "a matching total does not prove game-effective eligibility.")
    market = [f for f in findings if f["kind"] in ("secondary_market", "market")]
    if market:
        lines.append("On the transaction wire")
        lines.extend(_describe(f) for f in market)
    quiet = [f for f in findings if f["kind"] in ("quiet_success", "quiet_watch")]
    if quiet:
        lines.append("Who's keeping quiet?")
        lines.extend(_describe(f) for f in quiet)
    comparison = research.get("comparison")
    rows = (comparison.get("teams") or []) if isinstance(comparison, dict) else []
    ranks = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("rank"), int):
            ranks.setdefault(row["rank"], set()).add(str(row.get("name") or row.get("team_id")))
    tied = {rank: names for rank, names in ranks.items() if len(names) > 1}
    if tied:
        lines.append("Standings note")
        lines.append("The archive shows shared ranks: " + "; ".join(f"{rank}: {', '.join(sorted(names))}" for rank, names in sorted(tied.items())) + ". No tiebreak is assumed.")
    lines.append("What to watch")
    lines.append("Next week's results will help show which moves stick."
                 + ((f" {sum(t.get('status') == 'discrepancy' for t in team_audits)} team scoring difference(s) remain; "
                       "game-effective lineup credit still requires dated evidence.")
                    if team_audits else " NHL performances are available, but lineup eligibility and trade impact still need verification."
                    if nhl_leaders else " Player-level contributions and trade impact still require verified period-specific evidence."))
    gaps = _evidence_gaps(research)
    if gaps:
        lines.append("Evidence still missing")
        lines.extend(gaps)
    return "\n\n".join(lines)
