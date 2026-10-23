"""Evidence-grounded JHLPAA sports column written by Scout, not Athena.

Consumes Athena's structured findings only. Humour belongs to observed results,
not invented manager psychology. No fake quotations, grudges, or predicted outcomes.
"""
from __future__ import annotations

from datetime import date


def _n(value):
    return f"{value:g}" if type(value) in (int, float) else "an unverified total"


def _rank(value):
    return f"No. {value}" if type(value) is int else "the standings"


def _fixture(f):
    kind = f.get("kind")
    team = f.get("team")
    points = f.get("period_points")
    move = f.get("rank_change")
    rank = f.get("rank")
    if kind == "surge":
        if type(move) is not int or move <= 0:
            return None
        climb = f"{move} {'spot' if move == 1 else 'spots'}"
        if f.get("top_score"):
            return f"{team} led the scoring parade with {_n(points)} points and jumped {climb} to {_rank(rank)}. That's one way to make an entrance."
        return f"{team} delivered {_n(points)} points and climbed {climb} to {_rank(rank)}. The standings noticed."
    if kind == "scoring_leader":
        return f"{team} piled up {_n(points)} points. That's a number worth circling."
    if kind == "slide":
        if type(move) is not int or move >= 0:
            return None
        return f"{team} dropped {abs(move)} {'place' if abs(move) == 1 else 'places'} to {_rank(rank)} despite {_n(points)} points. The table is getting crowded; the cause of that slide isn't established by the scoreboard alone."
    if kind == "climb":
        if type(move) is not int or move <= 0:
            return None
        return f"{team} moved up {move} {'position' if move == 1 else 'positions'} to {_rank(rank)} on {_n(points)} points."
    if kind in ("trade", "trade_cluster"):
        count = f.get("trade_count", 0)
        exchanges = []
        for trade in f.get("exchanges") or []:
            if isinstance(trade, dict):
                received = trade.get("received") or {}
                if isinstance(received, dict):
                    exchanges += [f"{club} received {', '.join(map(str, assets))}" for club, assets in received.items() if assets]
        if kind == "trade_cluster" and team:
            intro = f"{team} wasn't waiting around: {count} confirmed trades put it at the centre of the transaction wire."
        else:
            intro = f"The league recorded {count} confirmed {'trade' if count == 1 else 'trades'} this week."
        if exchanges:
            intro += " " + "; ".join(exchanges) + "."
        return intro + " The pieces have moved; whether those deals pay off is a story for another week."
    if kind == "secondary_market":
        examples = [str(x) for x in f.get("examples") or [] if x]
        intro = f"Away from the headline deals, {f.get('transaction_count', 0)} other recorded transactions kept the wire busy."
        return intro + (" Among them: " + "; ".join(examples[:2]) + "." if examples else "")
    if kind == "market":
        return f"There were {f.get('transaction_count', 0)} recorded transactions in this period."
    if kind == "quiet_success":
        return f"{team} put up {_n(points)} points without a recorded transaction across the two observed weeks. Sometimes the best move is letting the roster play."
    if kind == "quiet_watch":
        teams = f.get("teams") or []
        weeks = f.get("observed_weeks") or []
        if not teams or len(weeks) != 2:
            return None
        names = ", ".join(map(str, teams[:3]))
        suffix = " and others" if len(teams) > 3 else ""
        return (f"No recorded transactions for {names}{suffix} across Weeks {weeks[0]} and {weeks[1]}. "
                "Maybe they're happy with the roster. Either way, the rest of the league isn't standing still.")
    return None


def _scope(research):
    week = research.get("period")
    label = f"Week {week}" if isinstance(week, int) else "The latest period"
    bounds = research.get("period_calendar") or {}
    if isinstance(bounds, dict) and bounds.get("start") and bounds.get("end"):
        try:
            start = date.fromisoformat(bounds["start"])
            end = date.fromisoformat(bounds["end"])
            label += f" ({start.strftime('%B')} {start.day}-{end.day}, {end.year})"
        except (ValueError, TypeError):
            pass
    return label


def _continuity(research, findings):
    """Use authenticated cross-week signals before single-period movement."""
    serial = research.get("storyline_continuity") or {}
    if serial.get("status") == "verified" and serial.get("source") == "canonical_period_standings":
        leading = (serial.get("signals") or [])[:2]
        stories = []
        for item in leading:
            periods = item.get("periods") or []
            if len(periods) != 3 or item.get("direction") not in ("climb", "slide"):
                continue
            movement = item.get("overall_rank_change")
            if type(movement) is not int or not movement:
                continue
            verb = "climbed" if movement > 0 else "slipped"
            stories.append(f"{item['team_name']} has {verb} {abs(movement)} standings "
                           f"{'place' if abs(movement) == 1 else 'places'} over two consecutive "
                           f"periods (Weeks {periods[0]}–{periods[2]})")
        if stories:
            return "; ".join(stories) + ". Those are verified arcs in the standings, not explanations of what caused them."
    comparison = research.get("comparison") or {}
    if comparison.get("status") != "compared":
        return None
    rows = [r for r in comparison.get("teams") or [] if isinstance(r, dict)]
    biggest = sorted((r for r in rows if type(r.get("rank_change")) is int and r["rank_change"] != 0),
                     key=lambda row: (abs(row["rank_change"]), str(row.get("team_id") or "")), reverse=True)
    if not biggest:
        return "The verified standings show no positional movement from the preceding period. The points still count; the pecking order hasn't budged."
    leader = biggest[0]
    move = leader["rank_change"]
    team = leader.get("name") or leader.get("team_id")
    before_period = comparison.get("baseline_period")
    after_period = comparison.get("period")
    qualifier = (f" between Weeks {before_period} and {after_period}" if type(before_period) is int and type(after_period) is int else " against the verified baseline")
    return (f"One of the biggest verified standings swings{qualifier}: {team} "
            f"{'climbed' if move > 0 else 'fell'} {abs(move)} {'place' if abs(move) == 1 else 'places'}. "
            "That's a standings trend to follow, not proof of what caused it.")


def _clause_for_move(finding: dict) -> str | None:
    team = finding.get("team")
    move = finding.get("rank_change")
    points = finding.get("period_points")
    rank = finding.get("rank")
    if not team or type(move) is not int or not move:
        return None
    direction = (f"rose {move}" if move > 0 else f"fell {abs(move)}")
    places = "place" if abs(move) == 1 else "places"
    score = f" on {_n(points)} points" if type(points) in (float, int) else ""
    ending = f", now {_rank(rank)}" if type(rank) is int else ""
    return f"{team} {direction} {places}{score}{ending}"


def _story_lead(headline: dict | None, findings: list[dict], continuity: dict) -> str:
    if not headline:
        return "The numbers are in, but no single verified development dominates the week."
    kind, team = headline.get("kind"), headline.get("team")
    points = headline.get("period_points")
    move = headline.get("rank_change")
    if kind in ("surge", "climb") and team and type(move) is int and move > 0:
        lead = (f"{team} is climbing the table: {_n(points)} points in the period "
                f"and {move} {'place' if move == 1 else 'places'} gained, taking the club to {_rank(headline.get('rank'))}.")
        leaders = sorted((f for f in findings if f.get("kind") == "scoring_leader" and
                          type(f.get("period_points")) in (int, float) and f.get("team") != team),
                         key=lambda f: -f["period_points"])
        if leaders and type(points) in (int, float) and leaders[0]["period_points"] > points:
            top = leaders[0]
            lead += (f" {top['team']} scored more this week ({_n(top['period_points'])}); "
                     f"the rise of {team} is the standings story.")
        return lead
    if kind == "scoring_leader" and team:
        return f"{team} owned the scoring spotlight with {_n(points)} points. Whether the standings followed is a separate question."
    if kind == "slide" and team and type(move) is int and move < 0:
        return (f"It was a difficult week in the standings for {team}: {_n(points)} points, "
                f"yet a drop of {abs(move)} {'place' if abs(move) == 1 else 'places'} to {_rank(headline.get('rank'))}. "
                "The table moved faster than the team's result.")
    return _fixture(headline) or "The results are verified, but the week's lead remains open to interpretation."


def _market_paragraph(findings: list[dict]) -> str:
    primary = next((f for f in findings if f.get("kind") in ("trade_cluster", "trade")), None)
    secondary = next((f for f in findings if f.get("kind") == "secondary_market"), None)
    parts = []
    if primary:
        count = primary.get("trade_count", 0)
        parties = []
        for trade in primary.get("exchanges") or []:
            if not isinstance(trade, dict):
                continue
            for club, assets in (trade.get("received") or {}).items():
                if assets:
                    parties.append(f"{club} added {', '.join(map(str, assets))}")
        opening = (f"{primary.get('team')} was involved in {count} confirmed trades" if
                   primary.get("kind") == "trade_cluster" and primary.get("team") else
                   f"The league recorded {count} confirmed {'trade' if count == 1 else 'trades'}")
        detail = "; ".join(parties)
        parts.append(opening + (f": {detail}." if detail else ".") +
                     " That's a change in personnel, not yet a verified change in competitive value.")
    if secondary:
        examples = [str(item) for item in secondary.get("examples") or [] if item]
        count = secondary.get("transaction_count", 0)
        if examples:
            parts.append(f"Beyond the trades, {count} other recorded moves included " + "; ".join(examples[:2]) + ".")
        else:
            parts.append(f"There were also {count} other recorded transactions.")
    if not parts:
        other = next((f for f in findings if f.get('kind') == 'market'), None)
        if other:
            return f"The league recorded {other.get('transaction_count', 0)} transactions this period; individual significance needs more evidence."
    return " ".join(parts)


def compose_journalist_report(*, research: dict) -> str:
    """Compose a story with evidence-based context, not one sentence per team."""
    if research.get("schema") != "athena.league_period_research.v2":
        raise ValueError("Scout requires Athena structured research contract v2")
    findings = [f for f in research.get("findings") or [] if isinstance(f, dict)]
    title = f"{research.get('league_name') or 'League'} — {_scope(research)}"
    if not findings:
        return (title + "\n\nThe press box is open, but there isn't enough verified activity "
                "to call a league-wide story this week. A good column can wait for evidence; rumours don't become results.")
    main = [f for f in findings if f.get("kind") in ("surge", "scoring_leader", "slide", "climb")]
    headline = next((f for f in findings if f.get("kind") in
                    ("surge", "scoring_leader", "slide", "climb", "trade_cluster", "trade")), None)
    lead_story = _story_lead(headline, findings, research.get("storyline_continuity") or {})
    featured = headline.get("team") if headline else None
    # Join a relevant personnel story to the featured club without inventing
    # transaction timing, a managerial motive or a causal scoring effect.
    if featured:
        for trade_finding in findings:
            if trade_finding.get("kind") not in ("trade", "trade_cluster"):
                continue
            acquisitions = []
            for exchange in trade_finding.get("exchanges") or []:
                if not isinstance(exchange, dict):
                    continue
                for club, players in (exchange.get("received") or {}).items():
                    if str(club).casefold() == str(featured).casefold() and players:
                        acquisitions.extend(str(p) for p in players)
            if acquisitions:
                lead_story += (f" The club also appears on the transaction wire, acquiring "
                               f"{', '.join(acquisitions[:3])}. The scoring and the deal are both recorded; "
                               "their causal connection is not established.")
                break
    lines = [title, "The headline", lead_story]
    scoring = [f for f in main if f.get("kind") == "scoring_leader" and f.get("team") != featured]
    rising = [f for f in main if f.get("kind") in ("surge", "climb") and f.get("team") != featured]
    falling = [f for f in main if f.get("kind") == "slide" and f.get("team") != featured]
    sides = []
    if scoring:
        scored = sorted(scoring, key=lambda f: f.get("period_points") if type(f.get("period_points")) in (float, int) else -1, reverse=True)
        leader = scored[0]
        if not (headline and featured and type(headline.get("period_points")) in (float, int) and
                type(leader.get("period_points")) in (float, int) and leader["period_points"] > headline["period_points"]
                and headline.get("kind") in ("surge", "climb")):
            sides.append(f"On the scoreboard, {leader.get('team')} produced {_n(leader.get('period_points'))} points.")
        if len(scored) > 1:
            sides.append(f"{scored[1].get('team')} also posted {_n(scored[1].get('period_points'))}, adding pressure near the top of the weekly leaderboard.")
    if rising:
        movements = [_clause_for_move(f) for f in rising[:2]]
        movements = [m for m in movements if m]
        if movements:
            sides.append("There was upward movement elsewhere: " + "; ".join(movements) + ".")
    if falling:
        movements = [_clause_for_move(f) for f in falling[:3]]
        movements = [m for m in movements if m]
        if movements:
            sides.append("The other side of that shuffle: " + "; ".join(movements) +
                         ". Those changes are standings facts, not proof of why each roster struggled.")
    if sides:
        lines.extend(["Around the league", " ".join(sides)])
    market = _market_paragraph(findings)
    if market:
        lines.extend(["The transaction wire", market])
    continuity = _continuity(research, findings)
    if continuity:
        lines.extend(["The developing picture", continuity])
    comparison = research.get("comparison") or {}
    verified_rows = comparison.get("teams") or [] if comparison.get("status") == "compared" else []
    quiet = next((f for f in findings if f.get("kind") == "quiet_watch" and f.get("teams") and
                  len(f.get("observed_weeks") or []) == 2), None)
    success = next((f for f in findings if f.get("kind") == "quiet_success"), None)
    if quiet:
        teams = [str(x) for x in quiet.get("teams") or []]
        weeks = quiet["observed_weeks"]
        focus = sorted((row for row in verified_rows if isinstance(row, dict)
                        and (row.get("name") or row.get("team_id")) in teams
                        and type(row.get("rank_change")) is int and row["rank_change"] < 0),
                       key=lambda row: row["rank_change"])
        if focus:
            row = focus[0]
            line = (f"{row.get('name') or row.get('team_id')} has made no recorded move across Weeks {weeks[0]} and {weeks[1]} "
                    f"while sliding {abs(row['rank_change'])} standings places in the latest comparison. "
                    "That doesn't reveal the manager's reasoning, but it's becoming a story worth watching.")
        else:
            line = (f"No recorded moves for {', '.join(teams[:3])} across Weeks {weeks[0]} and {weeks[1]}. "
                    "Quiet is a roster decision too—whether it's rewarded is another matter.")
        if success and success.get("team") and success.get("team") not in line:
            line += (f" Meanwhile, {success['team']} put up {_n(success.get('period_points'))} "
                     "without recorded activity; standing pat can look rather different when the points arrive.")
        lines.extend(["The quiet corner", line])
    elif success:
        lines.extend(["The quiet corner", _fixture(success)])
    # Spotlight needs a verified period-identity and ACTIVE team join; NHL
    # scoring alone is insufficient to name a JHLPAA team's contributors.
    bridge = research.get("editorial_player_attribution") or {}
    linked = ([r for r in bridge.get("records") or [] if isinstance(r, dict) and
               r.get("fantasy_team") and type(r.get("points")) is int and r["points"] > 0 and
               r.get("attribution_kind") == "historical_active_snapshot_numeric_reconciliation" and
               r.get("credited_points_verified") is False]
              if bridge.get("status") == "reconciled_snapshot" and
                 bridge.get("period") == research.get("period") else [])
    if linked:
        performers = linked[:3]
        mentions = [f"{r['player_name']} ({r['points']} G+A) was on "
                    f"{r['fantasy_team']}'s archived ACTIVE roster" for r in performers]
        spotlight = ("The player-to-team picture is taking shape: " + "; ".join(mentions) +
                     ". Those NHL totals reconcile numerically with their teams' reported weekly scores; "
                     "the period snapshot does not independently prove game-by-game fantasy eligibility.")
        lines.extend(["JHLPAA player spotlight", spotlight])
    else:
        leaders = [r for r in research.get("nhl_player_leaders") or [] if isinstance(r, dict)
                   and type(r.get("points")) is int and r["points"] > 0 and r.get("player_name")]
        if leaders:
            names = [f"{r['player_name']} ({r['points']} G+A)" for r in leaders[:2]]
            spotlight = ("Around the NHL, " + " and ".join(names) + " drew attention. "
                         "These are NHL performances, not independently verified fantasy lineup credit; "
                         "the league-team connection remains to be established before calling them fantasy difference-makers.")
            lines.extend(["NHL spotlight", spotlight])
    if headline and headline.get("team"):
        watch = f"The next test for {headline['team']} is whether this week's result becomes part of a sustained run."
    elif market:
        watch = "The next scoring period will begin to show what those roster moves actually changed."
    else:
        watch = "Next week's results will tell us which movements had staying power."
    lines.extend(["Next on the radar", watch])
    attribution = research.get("historical_roster_attribution") or {}
    gaps = [t for t in attribution.get("teams") or [] if isinstance(t, dict) and
            (t.get("status") == "discrepancy" or t.get("unmatched_active_ids"))]
    if gaps:
        lines.append(f"Scoring note: {len(gaps)} team totals retain an unresolved numerical or identity exception.")
    from Scout.conversation.league_recap_narrative import _evidence_gaps
    missing = _evidence_gaps(research)
    if missing:
        lines.extend(["Reporting limits", "\n".join(missing)])
    return "\n\n".join(lines)
