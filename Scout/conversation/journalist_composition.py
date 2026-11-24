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
            label += (f" ({start.strftime('%B')} {start.day}–" + (f"{end.strftime('%B')} " if start.month != end.month or start.year != end.year else '') + f"{end.day}, {end.year})")
        except (ValueError, TypeError):
            pass
    return label


def _continuity(research, findings):
    """Use authenticated cross-week signals before single-period movement."""
    serial = research.get("storyline_continuity") or {}
    if serial.get("status") == "verified" and serial.get("source") == "canonical_period_standings":
        leading = (serial.get("signals") or [])[:3]
        stories = []
        for item in leading:
            periods = item.get("periods") or []
            if len(periods) != 3 or not item.get('team_name'):
                continue
            movement = item.get("overall_rank_change")
            if type(movement) is not int:
                continue
            direction = item.get("direction")
            if direction in ("climb", "slide") and movement:
                verb = "climbed" if movement > 0 else "slipped"
                stories.append(f"{item['team_name']} has {verb} {abs(movement)} standings "
                               f"{'place' if abs(movement) == 1 else 'places'} over two consecutive "
                               f"periods (Weeks {periods[0]}–{periods[2]})")
            elif direction == "reversal":
                moves = item.get('movements') or []
                if len(moves) == 2 and all(type(m) is int and m for m in moves) and moves[0] * moves[1] < 0:
                    earlier = 'rose' if moves[0] > 0 else 'fell'
                    latter = 'recovered' if moves[1] > 0 else 'gave back ground'
                    stories.append(f"{item['team_name']} {earlier} {abs(moves[0])} "
                                   f"{'place' if abs(moves[0]) == 1 else 'places'} in Week {periods[1]}, "
                                   f"then {latter} by {abs(moves[1])} in Week {periods[2]}")
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


def _newsroom_market(research):
    from Athena.Investigation.editorial_newsroom import transaction_inventory
    inventory = transaction_inventory(research)
    parts = []
    for event in inventory['trades']:
        sides = [f"{club} received {', '.join(players)}" for club, players in sorted(event['received'].items())]
        parts.append('; '.join(sides) + '.')
    secondary = next((f for f in research.get('findings') or [] if f.get('kind') == 'secondary_market'), None)
    extra = ''
    if secondary:
        count = secondary.get('transaction_count', 0)
        examples = [str(x) for x in secondary.get('examples') or [] if x]
        prefix = (f"Outside the trades, {count} other recorded moves" if parts else f"The league recorded {count} roster moves")
        extra = prefix + (f" including {'; '.join(examples[:2])}." if examples else ' this period.')
    if not parts and not extra: return '', inventory
    opener = f"The league recorded {len(parts)} confirmed {'trade' if len(parts) == 1 else 'trades'} this period." if parts else ''
    return ' '.join(x for x in [opener, ' '.join(parts), extra] if x), inventory


def _briefing_sections(briefing: dict, featured: str | None) -> list[str]:
    """Render Athena's verified complete standings comparison without changing scores."""
    if briefing.get('status') != 'verified' or briefing.get('source') != 'canonical_period_standings':
        return []
    leaders = briefing['leaders']
    top = briefing['weekly_top_points']
    lead = leaders[0]
    parts = [f"{lead['name']} set the weekly pace with {_n(top)} points"]
    other = [x for x in leaders if x['name'] != lead['name']]
    if other:
        parts.append('The other leading totals came from ' + '; '.join(
            f"{x['name']} ({_n(x['period_points'])})" for x in other))
    if lead['rank'] != 1:
        parts.append(f"The week's highest scorer finished at {_rank(lead['rank'])} in the cumulative standings, rather than first overall")
    else:
        parts.append('The weekly scoring leader also occupies first place overall')
    sections = ['Around the league', '. '.join(parts) + '.']
    climbers = briefing['climbers']
    fallers = briefing['fallers']
    movement = []
    if climbers:
        movement.append('Moving up: ' + '; '.join(
            f"{x['name']} +{x['rank_change']} to {_rank(x['rank'])} ({_n(x['period_points'])} points)" for x in climbers))
    if fallers:
        movement.append('Moving down: ' + '; '.join(
            f"{x['name']} {x['rank_change']} to {_rank(x['rank'])} ({_n(x['period_points'])} points)" for x in fallers))
    if not movement:
        movement.append('No teams changed standings position this period')
    sections.extend(['Standings movement', '. '.join(movement) + '.'])
    stable = briefing['unchanged']
    gaps = briefing['gaps_to_first']
    context = []
    if stable:
        context.append(f"{len(stable)} of {briefing['team_count']} teams held their standings positions, "
                       'even though the weekly points continued to accumulate')
    if gaps:
        closest = gaps[0]
        context.append(f"{closest['team']} sits {_n(closest['points_behind'])} cumulative points behind the "
                       f"first-place points total at {_rank(closest['rank'])}")
    if context:
        sections.extend(['The competitive picture', '. '.join(context) + '.'])
    return sections



def _competitive_story(briefing: dict) -> str | None:
    """Write a bounded narrative from verified Athena contrasts, not imagined motives.

    A separate narrative paragraph complements the exhaustive standings inventory:
    it explains *why the observed combination is interesting*, without reciting
    every row or assigning fantasy points to individuals.
    """
    if briefing.get('status') != 'verified' or briefing.get('source') != 'canonical_period_standings':
        return None
    signals = briefing.get('narrative_signals') or []
    if not isinstance(signals, list):
        return None
    stories = []
    seen_kinds = set()
    for signal in signals:
        if not isinstance(signal, dict):
            continue
        kind = signal.get('kind')
        if kind in seen_kinds:
            continue
        if kind == 'weekly_vs_overall':
            if not all(k in signal for k in ('weekly_team', 'weekly_points', 'weekly_rank', 'overall_team', 'overall_rank')):
                continue
            story = (f"The week's scoring crown belongs to {signal['weekly_team']} "
                     f"({_n(signal['weekly_points'])} points), but the overall lead still belongs to "
                     f"{signal['overall_team']}. A weekly win and first place in the season race "
                     "are two different prizes.")
        elif kind == 'leader_under_pressure':
            if not all(k in signal for k in ('team', 'period_points', 'weekly_best')):
                continue
            story = (f"{signal['team']} still sets the overall pace, despite scoring "
                     f"{_n(signal['period_points'])} against a weekly best of "
                     f"{_n(signal['weekly_best'])}. Nobody gets to coast just because the table says first.")
        elif kind == 'scored_but_slipped':
            if not all(k in signal for k in ('team', 'period_points', 'rank_change', 'rank')):
                continue
            story = (f"{signal['team']} delivered {_n(signal['period_points'])} points and still "
                     f"slipped {abs(signal['rank_change'])} "
                     f"{'place' if abs(signal['rank_change']) == 1 else 'places'} "
                     f"to {_rank(signal['rank'])}. Good production doesn't guarantee a climb "
                     "when the field is moving too.")
        elif kind == 'movement_vs_scoring':
            if not all(k in signal for k in ('team', 'period_points', 'rank_change', 'rank', 'weekly_team')):
                continue
            story = (f"{signal['team']} climbed {signal['rank_change']} "
                     f"{'place' if signal['rank_change'] == 1 else 'places'} "
                     f"on {_n(signal['period_points'])} points, even without owning the week's "
                     f"top score. {signal['weekly_team']} supplied the fireworks; "
                     f"{signal['team']} gained ground in the standings.")
        else:
            continue
        stories.append(story)
        seen_kinds.add(kind)
        if len(stories) == 2:
            break
    return ' '.join(stories) if stories else None


def audit_publication(research: dict, report: str) -> dict:
    """Publication checks never alter canonical scoring or trade data."""
    from Athena.Investigation.editorial_newsroom import transaction_inventory
    inventory = transaction_inventory(research)
    problems = []
    expected = inventory['expected_count']
    if type(expected) is int and inventory['count'] != expected:
        problems.append('trade_inventory_count_mismatch')
    if inventory['trades'] and 'The transaction wire' not in report:
        problems.append('missing_trade_section')
    for event in inventory['trades']:
        for players in event['received'].values():
            for player in players:
                if player not in report: problems.append('omitted_trade_asset:' + player)
    scoring = research.get('period_scoring_audit') or {}
    if scoring and scoring.get('status') == 'partial':
        if 'These NHL totals reconcile with the team scoring snapshots' in report:
            problems.append('unqualified_partial_scoring_attribution')
        if 'All teams reconciled' in report or '14/14 teams reconciled' in report:
            problems.append('unverified_leaguewide_scoring_claim')
    if 'Reporting limits' in report: problems.append('diagnostics_leaked_into_publication')
    if 'The scoring and the deal are both recorded' in report:
        problems.append('repeated_trade_context')
    return {'status': 'pass' if not problems else 'fail', 'issues': sorted(set(problems)),
            'audited_trades': inventory['count'], 'expected_trades': expected}


def compose_journalist_report(*, research: dict) -> str:
    """Evidence-grounded league edition; canonical trade coverage is complete and non-repeating."""
    if research.get('schema') != 'athena.league_period_research.v2':
        raise ValueError('Scout requires Athena structured research contract v2')
    from Athena.Investigation.editorial_newsroom import rank_stories
    findings = [f for f in research.get('findings') or [] if isinstance(f, dict)]
    title = f"{research.get('league_name') or 'League'} — {_scope(research)}"
    if not findings:
        return title + "\n\nNo verified league developments are available for this period."
    ranked = rank_stories(research)
    headline = ranked[0]['finding'] if ranked else None
    featured = headline.get('team') if headline else None
    lead = _story_lead(headline, findings, research.get('storyline_continuity') or {})
    # The headline should introduce a story. Trade details are reported exactly
    # once, under the wire, from Athena's full canonical event list.
    if headline and headline.get('kind') in {'trade_cluster','trade'}:
        count = headline.get('trade_count', 0)
        lead = (f"{featured} has made {count} trades this period, keeping the transaction wire busy."
                if featured else f"The league recorded {count} trades this period.")
    lines = [title, 'The headline', lead]
    briefing = research.get('editorial_briefing') or {}
    # Compatibility path for older structured fixtures and staged integrations;
    # production researches compute this briefing inside Athena.
    sections = _briefing_sections(briefing, featured)
    if sections:
        lines.extend(sections)
        competitive_story = _competitive_story(briefing)
        if competitive_story:
            lines.extend(['Beyond the scores', competitive_story])
    else:
        scoreboard = sorted((f for f in findings if f.get('kind') in {'surge','scoring_leader'}
                             and type(f.get('period_points')) in (int,float)),
                            key=lambda f: (-f['period_points'], str(f.get('team'))))
        scorelines = []
        for f in scoreboard[:3]:
            if f.get('team') != featured:
                scorelines.append(f"{f['team']} posted {_n(f['period_points'])} points")
        if scorelines:
            lines.extend(['Around the league', '. '.join(scorelines) + '.'])
        climbers = sorted((f for f in findings if f.get('kind') in {'surge','climb'} and f.get('team') != featured),
                         key=lambda f: -(f.get('rank_change') or 0))
        slides = sorted((f for f in findings if f.get('kind') == 'slide' and f.get('team') != featured),
                        key=lambda f: (f.get('rank_change') or 0))
        movements = [_clause_for_move(f) for f in climbers[:2] + slides[:2]]
        movements = [x for x in movements if x]
        if movements:
            lines.extend(['Standings movement', '; '.join(movements) + '.'])
    market, inventory = _newsroom_market(research)
    if market: lines.extend(['The transaction wire', market])
    continuity = _continuity(research, findings)
    trade_continuity = research.get('editorial_trade_continuity') or {}
    trade_stories = []
    if trade_continuity.get('status') == 'verified':
        for item in (trade_continuity.get('signals') or [])[:2]:
            weeks = item.get('periods') or []
            if len(weeks) == 2 and type(item.get('total_trades')) is int:
                trade_stories.append(f"{item['team']} has completed {item['total_trades']} trades across Weeks {weeks[0]}–{weeks[1]}")
    if continuity or trade_stories:
        lines.extend(['The developing picture', ' '.join(filter(None, [continuity, '; '.join(trade_stories) + '.' if trade_stories else '']))])
    comparison = research.get('comparison') or {}
    verified_rows = comparison.get('teams') or [] if comparison.get('status') == 'compared' else []
    quiet = next((f for f in findings if f.get('kind') == 'quiet_watch' and len(f.get('observed_weeks') or []) == 2 and f.get('teams')), None)
    success = next((f for f in findings if f.get('kind') == 'quiet_success'), None)
    if quiet:
        weeks = quiet['observed_weeks']; teams = set(map(str, quiet['teams']))
        focus = sorted((r for r in verified_rows if isinstance(r,dict) and (r.get('name') or r.get('team_id')) in teams and type(r.get('rank_change')) is int and r['rank_change'] < 0), key=lambda r:r['rank_change'])
        if focus:
            row = focus[0]; magnitude = abs(row['rank_change'])
            paragraph = f"{row.get('name') or row.get('team_id')} recorded no moves across Weeks {weeks[0]} and {weeks[1]} while slipping {magnitude} {'place' if magnitude == 1 else 'places'} this week. A quiet trade wire is starting to get noticed."
        else:
            paragraph = f"No moves recorded for {', '.join(sorted(teams)[:3])} across Weeks {weeks[0]} and {weeks[1]}. There's no shortage of activity elsewhere."
        if success and success.get('team'):
            paragraph += f" Meanwhile, {success['team']} scored {_n(success.get('period_points'))} without a recorded move. Standing pat can work, too."
        lines.extend(['The quiet corner', paragraph])
    elif success:
        lines.extend(['The quiet corner', _fixture(success)])
    bridge = research.get('editorial_player_attribution') or {}
    linked = [r for r in bridge.get('records') or [] if isinstance(r,dict) and r.get('fantasy_team')
              and type(r.get('points')) is int and r['points'] > 0
              and r.get('attribution_kind') == 'historical_active_snapshot_numeric_reconciliation'
              and r.get('credited_points_verified') is False] if (bridge.get('status') == 'reconciled_snapshot' and bridge.get('period') == research.get('period')) else []
    if linked:
        mentions = [f"{r['player_name']} ({r['points']} G+A) featured on {r['fantasy_team']}'s archived ACTIVE roster" for r in linked[:3]]
        audit = research.get('period_scoring_audit') or {}
        if audit.get('status') == 'partial':
            caveat = ('These players belong to individually reconciled team snapshots, not the entire league; '
                      'game-by-game fantasy eligibility remains unverified.')
        else:
            caveat = 'These team snapshots reconcile numerically; game-by-game eligibility has not independently been confirmed.'
        lines.extend(['JHLPAA player spotlight', '; '.join(mentions) + '. ' + caveat])
    else:
        leaders = [r for r in research.get('nhl_player_leaders') or [] if isinstance(r,dict) and type(r.get('points')) is int and r['points'] > 0 and r.get('player_name')]
        if leaders:
            lines.extend(['NHL spotlight', 'Around the NHL, ' + ' and '.join(f"{r['player_name']} ({r['points']} G+A)" for r in leaders[:2]) + ' stood out. Their JHLPAA team credit has not been verified.'])
    if continuity:
        watch = 'The next period will test whether those emerging standings trends hold.'
    elif inventory['count']:
        watch = 'The next period should give the latest roster exchanges a chance to show their value.'
    else:
        watch = 'Next period will show whether the scoring and standings movement continues.'
    lines.extend(['Next on the radar', watch])
    return '\n\n'.join(lines)


def compose_editorial_publication(*, research: dict) -> dict:
    """Single publication boundary for every Scout journalist surface.

    Both the ordinary sports column and an auditor-requested attached column
    must pass the same evidence gate. This function returns evidence state;
    it never silently substitutes or mutates canonical Athena research.
    """
    draft = compose_journalist_report(research=research)
    publication = audit_publication(research, draft)
    return {"status": publication["status"], "issues": publication["issues"],
            "report": (draft if publication["status"] == "pass" else
                       "Editorial publication held: the verified transaction inventory "
                       "could not be completely represented. The analytical evidence "
                       "remains available, but this column needs correction before publication."),
            "audit": publication}
