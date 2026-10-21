"""Athena-owned, evidence-first league recap synthesis.

Narrative significance is inferred from verified comparisons and transaction
movements; neither teams nor weekly outcomes are hardcoded.
"""
from __future__ import annotations
from pathlib import Path


def resolve_archived_period(output, league_id, season):
    if not league_id or not season:
        return None
    archive = Path(output) / "Standings" / str(league_id) / str(season)
    periods = [int(p.stem.rsplit("_", 1)[-1]) for p in archive.glob("period_*.json")
               if p.stem.rsplit("_", 1)[-1].isdigit()]
    return max(periods) if periods else None


def _team(row):
    return str(row.get("name") or row.get("team_id") or "Unknown team")


def _points(row):
    return f"{row['period_points']:g}" if isinstance(row.get("period_points"), (int, float)) else None


def _activity_context(history, period, comparison):
    """Bounded league activity signals, never judgments about manager effort.

    A quiet week means no *recorded transactions*, not an inactive manager.
    Multiple weeks are only comparable when the source actually contains rows
    from both periods; absence of historical records is not proof of silence.
    """
    records = (history.get("records") or []) if isinstance(history, dict) else []
    if not isinstance(records, list) or not isinstance(period, int) or period < 2:
        return {}
    observed = set()
    per_team = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        try:
            week = int(record.get("season_week") or record.get("period"))
        except (ValueError, TypeError):
            continue
        observed.add(week)
        names = set()
        for participant in record.get("participants") or []:
            if isinstance(participant, dict):
                name = participant.get("participant_name") or participant.get("team_name")
                if name:
                    names.add(str(name))
        for name in names:
            per_team.setdefault(name, set()).add(week)
    # We cannot establish completeness from sparse transaction observations.
    # Even when both weeks appear, the conclusion is about recorded trades/moves.
    if not {period, period - 1}.issubset(observed):
        return {}
    rows = comparison.get("teams", []) if isinstance(comparison, dict) else []
    quiet = []
    for row in rows:
        if not isinstance(row, dict) or not row.get("name"):
            continue
        name = str(row["name"])
        if not ({period, period - 1} & per_team.get(name, set())):
            quiet.append(name)
    return {"quiet_teams": quiet, "observed_weeks": [period - 1, period]}


def investigate_period_stories(comparison, editorial, activity, history=None, period=None):
    """Rank independent, source-backed developments, retaining inference boundaries."""
    stories = []
    rows = comparison.get("teams", []) if isinstance(comparison, dict) and comparison.get("status") == "compared" else []
    rows = [r for r in rows if isinstance(r, dict)]
    leaders = sorted((r for r in rows if _points(r) is not None),
                     key=lambda r: r["period_points"], reverse=True)
    movers = sorted((r for r in rows if isinstance(r.get("rank_change"), int) and r["rank_change"]),
                    key=lambda r: abs(r["rank_change"]), reverse=True)
    used = set()
    # A high-scoring climb is a stronger supported story than either isolated fact.
    # Include all tied top-three scoring performances; rank alone must not
    # silently remove a joint runner-up from editorial coverage.
    scoring_cutoff = leaders[min(2 if len(leaders) > 3 else 1, len(leaders)-1)]["period_points"] if leaders else None
    scoring_headliners = [r for r in leaders if r["period_points"] >= scoring_cutoff] if scoring_cutoff is not None else []
    for r in scoring_headliners:
        if r.get("rank_change", 0) > 0:
            stories.append({"kind": "surge", "team": _team(r), "score": 100 + r["rank_change"],
                "text": (f"{_team(r)} delivered {_points(r)} points, "
                         f"{'the highest verified weekly total' if r is leaders[0] else 'among the league’s top weekly totals'}, "
                         f"and climbed {r['rank_change']} {"place" if r["rank_change"] == 1 else "places"} to {r.get('rank')}. "
                         "The standings and scoring support the surge; individual player contributions still need verification.")})
            used.add(str(r.get("team_id")))
    # Every scoring headliner gets a story, even without a standings climb.
    for r in scoring_headliners:
        if str(r.get("team_id")) in used:
            continue
        stories.append({"kind": "scoring_leader", "team": _team(r), "score": 94,
            "text": f"{_team(r)} scored {_points(r)} points, placing among the week's leading performances"
                    + (".")})
        used.add(str(r.get("team_id")))
    for r in movers:
        if str(r.get("team_id")) in used:
            continue
        change = r["rank_change"]
        if change < 0:
            context = f" with {_points(r)} weekly points" if _points(r) is not None else ""
            stories.append({"kind": "slide", "team": _team(r), "score": 70 + abs(change),
                "text": f"{_team(r)} fell {abs(change)} {'place' if abs(change) == 1 else 'places'} to rank {r.get('rank')}{context}. "
                        "The drop is clear; the available figures do not establish which roster factors drove it."})
        elif change > 0:
            stories.append({"kind": "climb", "team": _team(r), "score": 60 + change,
                "text": f"{_team(r)} climbed {change} {'place' if change == 1 else 'places'} to rank {r.get('rank')}" +
                        (f" after scoring {_points(r)} points" if _points(r) is not None else "") + "."})
    # Trade/standings relationships are consolidated by team, not emitted as
    # independent sentences for each acquisition. A transaction's date is not
    # evidence that it caused the same-period scoring result.
    trade_context = {}
    if editorial:
        for trade in editorial.get("trades") or []:
            recipients = trade.get("received") or {}
            if not isinstance(recipients, dict):
                continue
            for team, assets in recipients.items():
                if assets:
                    trade_context.setdefault(team, []).extend(str(a) for a in assets)
    for team, assets in trade_context.items():
        row = next((r for r in rows if _team(r) == team), None)
        if row is None:
            continue
        # Enrich the existing team story rather than competing with it.
        for story in stories:
            if story.get("team") == team and story.get("kind") in ("surge", "scoring_leader", "slide", "climb"):
                story["trade_context"] = {"received": list(dict.fromkeys(assets)),
                    "rank": row.get("rank"), "period_points": row.get("period_points")}
                break
    if editorial:
        trades = editorial.get("trades") or []
        multi = editorial.get("multiple_trade_teams") or []
        if multi:
            team, count = multi[0]
            moved_out, received = [], []
            for trade in trades:
                if team not in trade.get("participants", []) and team not in trade.get("received", {}):
                    continue
                received.extend(trade.get("received", {}).get(team, []))
                for other, names in trade.get("received", {}).items():
                    if other != team:
                        moved_out.extend(names)
            exchanges = []
            for trade in trades:
                if team not in trade.get("participants", []) and team not in trade.get("received", {}):
                    continue
                parts = [f"{club} acquired {', '.join(names)}" for club, names in trade.get("received", {}).items() if names]
                if parts:
                    exchanges.append("; ".join(parts))
            detail = (" In the verified exchanges: " + ". ".join(exchanges) + ".") if exchanges else ""
            stories.append({"kind": "trade_cluster", "team": team, "score": 105 + count,
                "text": f"{team} completed {count} separate trades, making its roster overhaul the period's leading transaction story." +
                        detail + " The scale of the exchanges is established, but neither competitive advantage nor managerial intent follows from asset movement alone."})
        elif trades:
            stories.append({"kind": "trade", "team": None, "score": 75,
                "text": f"The period includes {len(trades)} verified trade event(s). " + trades[0]["lead"] +
                        " Their roster impact remains conditional on team and player evidence."})
        other = editorial.get("other_moves") or []
        if other:
            summaries = [m.get("summary") for m in other if m.get("summary")]
            if summaries:
                stories.append({"kind": "secondary_market", "team": None, "score": 25,
                    "text": f"Beyond the headline trades, {len(other)} other recorded transactions show managers adjusting their rosters. "
                            + "For example: " + "; ".join(summaries[:2]) + ". "
                            "These moves are not assigned competitive significance without verified player or roster evidence."})
    elif activity.get("transaction_count"):
        stories.append({"kind": "market", "team": None, "score": 25,
            "text": f"The selected scope includes {activity['transaction_count']} recorded transactions; their individual competitive impact is not yet established."})
    context = _activity_context(history, period, comparison)
    quiet = context.get("quiet_teams", [])
    if quiet:
        thriving = [r for r in rows if _team(r) in quiet and isinstance(r.get("period_points"), (int, float)) and r in leaders[:3] and r.get("period_points", 0) >= leaders[0]["period_points"] * 0.9]
        thriving_names = {_team(r) for r in thriving}
        quiet = [n for n in quiet if n not in thriving_names]
        for r in thriving:
            movement = r.get("rank_change")
            climb = f" and climbed {movement} places" if isinstance(movement, int) and movement > 0 else ""
            stories.append({"kind": "quiet_success", "team": _team(r), "score": 65,
                "text": f"{_team(r)} recorded {_points(r)} points this week{climb}, despite no recorded transactions across the two observed weeks. Strong results make standing pat a different story from a struggling roster; transaction logs cannot establish lineup activity."})
    if quiet:
        names = ", ".join(quiet[:3])
        suffix = " and others" if len(quiet) > 3 else ""
        stories.append({"kind": "quiet_watch", "team": None, "score": 20,
            "text": (f"The transaction record has been quiet for {names}{suffix} across the two observed scoring weeks. "
                     "That doesn't tell us who is setting lineups or discussing deals, but with the league moving around them, "
                     "it will be interesting to see who makes the next move.")})
    return sorted(stories, key=lambda s: s["score"], reverse=True)


def compose_period_report(*, league_name, period, comparison, editorial, activity, requested_role="editorial", history=None):
    label = f"Week {period}" if period else "recent activity"
    stories = investigate_period_stories(comparison, editorial, activity, history=history, period=period)
    lines = [f"{league_name} | {label}"]
    # Equal displayed ranks can be valid ties, or conflicting source rankings.
    # Do not silently relabel either team without a verified tie-break rule.
    rows = comparison.get("teams", []) if isinstance(comparison, dict) else []
    ranks = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("rank"), int):
            ranks.setdefault(row["rank"], set()).add(_team(row))
    ambiguous = {rank: names for rank, names in ranks.items() if len(names) > 1}

    if not stories:
        return "\n\n".join(lines + ["The available period evidence is insufficient to identify a verified league-wide development."])
    # The opening earns its place through ranked evidence, rather than a fixed standings section.
    lead = stories[0]
    lines.append("\nThe week's defining development")
    lead_text = lead["text"]
    if lead.get("trade_context"):
        lead_text += " " + str(lead["team"]) + " acquired " + ", ".join(lead["trade_context"]["received"]) + "; its contribution to that result is not established."
    lines.append(lead_text)
    supporting = [s for s in stories[1:] if s["kind"] not in ("secondary_market", "market", "quiet_watch", "quiet_success")]
    if supporting:
        lines.append("\nThe wider picture")
        # Include distinct story types and teams, rather than filling the article
        # with four near-identical standings descriptions.
        selected, seen = [], {lead.get("team")}
        for story in supporting:
            if story.get("team") in seen and story.get("team") is not None and story.get("kind") != "trade_standings_context":
                continue
            selected.append(story)
            seen.add(story.get("team"))
            # No arbitrary six-story cap: retain independently significant teams.
        for story in selected:
            paragraph = story["text"]
            context = story.get("trade_context")
            if context:
                assets = ", ".join(context["received"])
                paragraph += f" {story['team']} acquired {assets} during the period; after a {_points(next(r for r in rows if _team(r) == story['team']))}-point week, the trade's contribution to that result is not established."
            lines.append(paragraph)
    secondary = next((s for s in stories if s["kind"] in ("secondary_market", "market")), None)
    if secondary:
        lines.append("\nAround the league")
        lines.append(secondary["text"])
    successful_quiet = [s for s in stories if s["kind"] == "quiet_success"]
    if successful_quiet:
        lines.append("\nQuiet, but producing")
        covered = {s.get("team") for s in [lead] + selected} if supporting else {lead.get("team")}
        for story in successful_quiet:
            if story.get("team") not in covered:
                lines.append(story["text"])
            else:
                lines.append(f"{story['team']} reached those results without recorded transactions in the two observed weeks; that does not establish lineup inactivity.")
    quiet = next((s for s in stories if s["kind"] == "quiet_watch"), None)
    if quiet:
        lines.append("\nThe quiet corner")
        lines.append(quiet["text"])
    if ambiguous:
        # Ties are allowed by the canonical archive validator. Their presence
        # alone is not an error, nor grounds to invent a tiebreak result.
        lines.append("\nStandings note")
        lines.append("The archived standings display shared positions (" +
                     "; ".join(f"rank {rank}: {', '.join(sorted(names))}" for rank, names in sorted(ambiguous.items())) +
                     "). These may be legitimate ties; no unsupported tiebreak is applied.")
    lines.append("\nWhat to watch")
    lines.append("The next scoring period can establish whether the movement persists. "
                 "Trade returns and roster changes should be reassessed against verified player production, "
                 "lineup construction and keeper context before judging their longer-term value.")
    return "\n\n".join(lines)


def research_period(*, league_name, period, comparison, editorial, activity, history=None, context=None, coverage=None):
    """Rank evidence-derived developments without generating narrative sentences."""
    rows = comparison.get("teams", []) if isinstance(comparison, dict) and comparison.get("status") == "compared" else []
    rows = [r for r in rows if isinstance(r, dict)]
    leaders = sorted((r for r in rows if isinstance(r.get("period_points"), (int, float))), key=lambda r: r["period_points"], reverse=True)
    cutoff = leaders[min(2 if len(leaders) > 3 else 1, len(leaders)-1)]["period_points"] if leaders else None
    findings, covered = [], set()
    for row in leaders:
        if row["period_points"] < cutoff:
            break
        team = _team(row)
        change = row.get("rank_change")
        kind = "surge" if isinstance(change, int) and change > 0 else "scoring_leader"
        findings.append({"kind": kind, "team": team, "significance": (100 + change if kind == "surge" else 94), "rank": row.get("rank"), "rank_change": change, "period_points": row["period_points"], "top_score": row["period_points"] == leaders[0]["period_points"], "evidence": ["period_standings"]})
        covered.add(team)
    for row in sorted(rows, key=lambda r: abs(r.get("rank_change") or 0), reverse=True):
        change = row.get("rank_change")
        team = _team(row)
        if team in covered or not isinstance(change, int) or change == 0:
            continue
        findings.append({"kind": "slide" if change < 0 else "climb", "team": team, "significance": (70 + abs(change) if change < 0 else 60 + change), "rank": row.get("rank"), "rank_change": change, "period_points": row.get("period_points"), "evidence": ["period_standings"]})
    trades = (editorial or {}).get("trades") or []
    trade_receipts = {}
    for trade in trades:
        for team, assets in (trade.get("received") or {}).items():
            trade_receipts.setdefault(team, []).extend(assets or [])
    for finding in findings:
        if finding["team"] in trade_receipts:
            finding["trade_context"] = {"received": list(dict.fromkeys(trade_receipts[finding["team"]]))}
    for team, count in (editorial or {}).get("multiple_trade_teams") or []:
        associated = [t for t in trades if team in (t.get("participants") or []) or team in (t.get("received") or {})]
        findings.append({"kind": "trade_cluster", "team": team, "significance": 105 + count, "trade_count": count, "exchanges": [{"received": t.get("received") or {}} for t in associated], "evidence": ["transactions"]})
    if trades and not any(f["kind"] == "trade_cluster" for f in findings):
        findings.append({"kind": "trade", "team": None, "significance": 75, "trade_count": len(trades), "exchanges": [{"received": t.get("received") or {}} for t in trades], "evidence": ["transactions"]})
    other = (editorial or {}).get("other_moves") or []
    if other:
        findings.append({"kind": "secondary_market", "team": None, "significance": 25, "transaction_count": len(other), "examples": [m.get("summary") for m in other if m.get("summary")][:2], "evidence": ["transactions"]})
    elif not trades and activity.get("transaction_count"):
        findings.append({"kind": "market", "team": None, "significance": 25, "transaction_count": activity["transaction_count"], "evidence": ["transactions"]})
    quiet = _activity_context(history, period, comparison)
    quiet_teams = quiet.get("quiet_teams") or []
    thriving = [r for r in leaders[:3] if _team(r) in quiet_teams and r["period_points"] >= leaders[0]["period_points"] * .9] if leaders else []
    for row in thriving:
        findings.append({"kind": "quiet_success", "team": _team(row), "significance": 65, "period_points": row["period_points"], "rank_change": row.get("rank_change"), "evidence": ["period_standings", "transaction_history"]})
    remaining = [name for name in quiet_teams if name not in {_team(r) for r in thriving}]
    if remaining:
        findings.append({"kind": "quiet_watch", "team": None, "significance": 20, "teams": remaining, "observed_weeks": quiet.get("observed_weeks"), "evidence": ["transaction_history"]})
    return {"schema": "athena.league_period_research.v2", "league_name": league_name, "period": period,
            "findings": sorted(findings, key=lambda f: f["significance"], reverse=True),
            "comparison": comparison, "activity": activity, "quiet_activity": quiet,
            "context": context or {}, "coverage": coverage or {},
            "limitations": [k for k, v in (coverage or {}).items() if v not in ("available", "verified")]}
