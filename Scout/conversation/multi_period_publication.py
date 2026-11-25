"""Scout's evidence-bounded prose composition for Athena's cross-period decisions.

Athena owns selection and numerical findings. Scout owns readability: the lead
is published once, supporting developments are non-redundant, and temporal
coincidence is never presented as causal evidence.
"""
from __future__ import annotations


def _number(value):
    return f'{value:g}' if type(value) in (int, float) else '?'


def _count(noun, n):
    return f'{n} {noun}' + ('' if n == 1 else 's')


def _event_description(event):
    if 'trade' in event.get('type', '').lower():
        received = event.get('received') or {}
        if received:
            directions = [f"{team} received {', '.join(map(str, assets))}"
                          for team, assets in sorted(received.items()) if assets]
            if directions:
                return 'Trade: ' + '; '.join(directions)
        participants = [p for p in event.get('participants', []) if p]
        return ('Trade between ' + ' and '.join(participants) + ' (asset destinations unverified)'
                if len(participants) >= 2 else 'Trade recorded; participants or asset destinations unverified')
    return event.get('summary') or event.get('type') or 'Recorded transaction'


def _scoring_context(team, weeks):
    if team.get('window_points') is None:
        return ''
    return f" with {_number(team['window_points'])} points across Weeks {weeks[0]}–{weeks[-1]}"


def _leader_and_challenger(data, weeks):
    race = data.get('race') or {}
    synthesis = data.get('synthesis') or {}
    featured = synthesis.get('featured') or []
    if race.get('status') != 'verified':
        return None, None, ''
    leaders = race.get('leaders') or []
    if not leaders:
        return None, None, ''
    leader = ', '.join(leaders)
    lead = (f"{leader} {'share the points lead' if len(leaders)>1 else 'holds the points lead'} with "
            f"{_number(race['leader_points'])} points after Week {weeks[-1]}.")
    challenger = next((x for x in featured if x.get('kind') == 'closing_challenger'), None)
    if not challenger:
        challenger = next((x for x in race.get('closing_gap', []) if x.get('team') not in leaders), None)
    if challenger:
        gain = challenger.get('gap_closed')
        deficit = challenger.get('end_gap')
        if isinstance(gain, (int, float)) and isinstance(deficit, (int, float)):
            lead += (f" {challenger['team']} has closed {_number(gain)} points of the gap "
                     f"and is now {_number(deficit)} points behind")
            lead += _scoring_context(challenger, weeks)
            lead += '.'
            swing = challenger.get('largest_swing')
            if swing and abs(swing[2]) >= 15:
                direction = 'dropped' if swing[2] < 0 else 'jumped'
                lead += (f" But that charge has not been steady: production {direction} "
                         f"from Week {swing[0]} to Week {swing[1]} by "
                         f"{_number(abs(swing[2]))} points.")
        else:
            challenger = None
    if not race.get('includes_first_requested_week'):
        lead += (f" Gap movement is measured from {race['comparison_from']}, "
                 f"not from the start of Week {weeks[0]}.")
    return leader, challenger, lead


def publish_multi_period(data: dict) -> str:
    weeks = data.get('periods') or []
    scope = ', '.join(f'Week {w}' for w in weeks)
    if data.get('status') != 'verified' or not weeks:
        missing = data.get('missing_periods') or []
        detail = (' Missing canonical standings for ' + ', '.join(f'Period {p}' for p in missing) + '.'
                  if missing else '')
        return (f'JHLPAA | {scope}\n\nThe requested cumulative standings could not be reconciled.'
                + detail + ' No comparative performance conclusion is supported by this evidence.')

    lines = [f'Around the JHLPAA | Weeks {weeks[0]}–{weeks[-1]}']
    synthesis = data.get('synthesis') or {}
    stories = data.get('stories') or []
    race = data.get('race') or {}
    leader, challenger, lead_text = _leader_and_challenger(data, weeks)
    used = set()
    if lead_text:
        lines.extend(['The competitive storyline — The race for first', lead_text])
        if challenger:
            used.add(challenger['team'])
        used.update(race.get('leaders') or [])
    else:
        lines.extend(['The competitive storyline — The race for first',
                      f"Athena compared {data.get('teams_analyzed')} teams across "
                      f"{len(weeks)} verified standings snapshots. The competitive "
                      'picture is limited to what those snapshots establish.'])

    # Report the scoring leader exactly once. If the lead already covers that
    # team, its weekly breakdown is useful evidence, not a second headline.
    pace = next((s for s in stories if s.get('kind') == 'scoring_pace'), None)
    if pace:
        if pace.get('scope') == 'full_window':
            weekly = ', '.join(f"Week {w}: {_number(n)}" for w, n in sorted(pace.get('weekly_points', {}).items()))
            detail = f"{pace['team']} led the three-week scoring table with {_number(pace['points'])} points ({weekly})."
            if pace['team'] in used:
                detail = f"The week-by-week breakdown for {pace['team']} was {weekly}."
        else:
            detail = (f"{pace['team']} led scoring between the ends of Weeks {weeks[0]} and {weeks[-1]} "
                      f"with {_number(pace['points'])} points. Week {weeks[0]} production remains unverified, "
                      'so this is not a full-window total.')
        lines.extend(['How the charge unfolded' if pace['team'] in used else 'The scoring pace', detail])
        used.add(pace['team'])

    supporting = []
    # Athena has already selected the top three competitive signals. Scout
    # gives each a distinct role and avoids a second leader/challenger summary.
    if synthesis.get('status') == 'verified':
        for item in synthesis.get('featured', []):
            if item['team'] in used:
                continue
            if item.get('kind') == 'losing_ground' and isinstance(item.get('gap_closed'), (int, float)):
                supporting.append(
                    (f"By contrast, {item['team']}" if not supporting else f"{item['team']}")
                    + f" has fallen {_number(abs(item['gap_closed']))} "
                    + f"points farther behind first{_scoring_context(item, weeks)}."
                )
                used.add(item['team'])
            elif item.get('kind') == 'closing_challenger' and isinstance(item.get('gap_closed'), (int, float)):
                supporting.append(f"{item['team']} also gained {_number(item['gap_closed'])} "
                                  f"points on the leader{_scoring_context(item, weeks)}.")
                used.add(item['team'])
            if len(supporting) >= 2:
                break

    # Choose just one new swing or reversal, never reintroducing the lead team.
    for story in stories:
        if len(supporting) >= 3:
            break
        if story.get('team') in used:
            continue
        if story.get('kind') == 'scoring_swing':
            change = story['change']
            direction = 'rebounded' if change > 0 else 'fell back'
            supporting.append(f"{story['team']} {direction} from {_number(story['from_points'])} "
                              f"points in Week {story['from_week']} to {_number(story['to_points'])} "
                              f"in Week {story['to_week']}.")
        elif story.get('kind') == 'rank_reversal':
            supporting.append(f"{story['team']} changed direction in the standings "
                              f"({' → '.join(map(str, story['ranks']))}) rather than sustaining a climb or slide.")
        else:
            continue
        used.add(story['team'])
    if supporting:
        lines.extend(['Elsewhere in the race', ' '.join(supporting)])

    # Different standings neighborhoods have different competitive stories.
    # These are positional descriptions, not invented playoff/bubble cutoffs.
    dynamics = data.get('competitive_dynamics') or {}
    if dynamics.get('status') == 'verified':
        for group in dynamics.get('groups', []):
            if group.get('category') not in ('middle_table','lower_table'):
                continue
            team = group.get('spotlight')
            if not team:
                continue
            name = 'The middle-table contest' if group['category'] == 'middle_table' else 'The lower-table contest'
            gap = team.get('gap_to_neighbor')
            neighbor = team.get('neighbor_above')
            change = team.get('gap_change_to_neighbor')
            passage = f"{team['team']} sits {_number(gap)} {'point' if gap == 1 else 'points'} behind {neighbor} in the standings"
            if isinstance(change, (int, float)):
                if change > 0:
                    passage += f", having gained {_number(change)} points relative to that team across the reporting window"
                elif change < 0:
                    passage += f", with that gap growing by {_number(abs(change))} points across the reporting window"
                else:
                    passage += ', with the gap unchanged over the reporting window'
            passage += '. '
            passage += ('These mid-table positions do not establish a playoff cutoff.'
                        if group['category'] == 'middle_table' else
                        'A lower-table position alone does not establish whether a manager is rebuilding.')
            lines.extend([name, passage])

    transactions = data.get('transactions') or []
    spotlight = data.get('transaction_spotlights') or []
    if transactions:
        counts = '; '.join(f"Week {t['week']}: {t['count']} recorded "
                           f"{'event' if t['count']==1 else 'events'}" for t in transactions)
        # Major verified exchanges take priority over first-in-archive trades.
        # Their approval belongs to event chronology, while the acquired roster
        # may first be eligible in a later period.
        selected = spotlight[:3]
        if not selected:
            selected = [{**event, 'event_period': t['week']} for t in transactions
                        for event in t.get('events', [])
                        if 'trade' in event.get('type', '').lower()][:3]
        details = []
        for event in selected:
            desc = _event_description(event)
            if event.get('player_count', 0) >= 8:
                desc = f"Major {event['player_count']}-player exchange: " + desc.removeprefix('Trade: ')
            desc = f"Week {event['event_period']}: {desc}"
            if event.get('roster_effective_period') and event['event_period'] != event['roster_effective_period']:
                desc += (f". Fantrax labels roster effectiveness as Period {event['roster_effective_period']}; "
                         "this does not change the trade's earlier approval date")
            if event.get('asset_market_note'):
                desc += '. ' + event['asset_market_note']
            details.append(desc + '.')
        if not details:
            details = [f"Week {t['week']}: {_event_description(event)}."
                       for t in transactions for event in t.get('events', [])
                       if event.get('summary')][:2]
        parts = [counts + '.']
        if details:
            parts.append(' '.join(details))
        if any(t['count'] == 0 for t in transactions):
            parts.append('No recorded events in a week does not establish that every manager was inactive.')
        lines.extend(['The transaction wire', ' '.join(parts)])

    # Official fantasy-player points, when the provider supplied period and
    # historical-owner attribution. Never substitute NHL G+A for missing FPts.
    provider_points = data.get('provider_fantasy_points') or {}
    provider_leaders = []
    for period in provider_points.get('periods', []):
        if period.get('status') != 'provider_credited_period':
            continue
        for person in period.get('leaders', []):
            provider_leaders.append((person['fantasy_points'], period['period'],
                                     person['team_name'], person['player_name']))
    if provider_leaders:
        provider_leaders.sort(key=lambda row: (-row[0], row[1], row[3]))
        passages = [f"In Period {period}, {name} earned {_number(points)} provider-credited "
                    f"fantasy points for {team}."
                    for points, period, team, name in provider_leaders[:3]]
        lines.extend(['Players behind the results', ' '.join(passages)])

    trade_results = data.get('trade_production') or []
    if any(t.get('status') == 'awaiting_roster_effective_period' for t in trade_results):
        lines.extend(['The next roster test',
                      'The major trade is recorded in this reporting window, but its acquired '
                      'players do not become roster-effective until a subsequent period; '
                      'their contribution cannot be backdated to the approval week.'])

    # Give the reader a concrete forward-looking tension, with one concise
    # evidence boundary instead of attaching caveats to each team and trade.
    if challenger:
        watch = (f"Can {challenger['team']} sustain its pursuit of {leader}, "
                 f"or will the next scoring period restore the gap?")
    elif leader:
        watch = f"Can anyone make a sustained move on {leader} in the next verified period?"
    else:
        watch = 'The next verified period will show which performance changes persist.'
    watch += (' Recorded trades establish roster activity, not what caused the change '
              'in scoring. Provider-reported player production and period-effective ownership can reveal what followed.')
    lines.extend(['What to watch', watch])
    return '\n\n'.join(lines)
