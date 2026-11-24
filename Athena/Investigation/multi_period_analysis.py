"""Bounded multi-period analysis: Athena investigates; Scout renders contract.

Explicit multi-week questions may not silently collapse to an opening/latest
standings comparison. Missing transactions remain an explicit coverage gap.
"""
from __future__ import annotations

from Athena.Investigation.period_execution import _requested_periods
from Athena.Investigation.competitive_race import analyze_race
from Athena.Investigation.storyline_synthesis import synthesize_storylines
from Athena.Investigation.league_competitive_dynamics import analyze_competitive_dynamics
from Athena.Investigation.league_editorial import _movements
from Athena.Investigation.standings_acquisition import resolve_league_context
from Athena.Investigation.standings_archive import load_snapshot
from Core.project_paths import OUTPUT_DIR


def analyze_snapshots(snapshots: list[dict], periods: list[int]) -> dict:
    ordered = {s['period']: {str(t['team_id']): t for t in s['teams']} for s in snapshots}
    if sorted(ordered) != periods:
        return {'status': 'missing_periods', 'missing_periods': sorted(set(periods)-set(ordered))}
    ids = [set(ordered[p]) for p in periods]
    if any(ids[0] != group for group in ids[1:]):
        return {'status': 'identity_membership_changed'}
    stories = []
    for tid in sorted(ids[0]):
        rows = [ordered[p][tid] for p in periods]
        deltas = [round(rows[i]['points']-rows[i-1]['points'], 5) for i in range(1,len(rows))]
        ranks = [r['rank'] for r in rows]
        if any(x < -1e-7 for x in deltas):
            return {'status': 'decreasing_cumulative_points', 'team_id': tid}
        stories.append({'team_id':tid,'name':rows[-1].get('name') or tid,
                        'ranks':ranks,'cumulative_points':[r['points'] for r in rows],
                        'interval_points':deltas,'rank_change':ranks[0]-ranks[-1]})
    return {'status':'verified','periods':periods,'teams':stories}


def investigate_multi_period(ctx, question: str) -> dict:
    from Scout.conversation.responses import response, developer_info
    from Athena.Investigation.transaction_event_intelligence import resolve_reporting_periods
    try:
        periods = resolve_reporting_periods(question)
    except ValueError:
        periods = []
    findings, limitations = None, []
    race_baseline = None
    period_resolution = {'status':'explicit_request' if periods else 'unresolved', 'last_completed':None, 'active_period':None}
    re = __import__('re')
    rolling = re.search(r'\b(?:last|latest|most recent)\s+(?:three|3)\s+(?:completed\s+)?(?:scoring\s+)?(?:weeks?|periods?)\b', question, re.I)
    if rolling:
        # A parenthesized reporting scope takes precedence over a separate
        # 'Period 5 as baseline' instruction. Reject nonconsecutive or
        # incorrect-length windows rather than silently changing their scope.
        parenthetical = re.search(r'\b(?:weeks?|periods?)\s*\(([^)]{1,65})\)', question, re.I)
        if parenthetical:
            selected = [int(n) for n in re.findall(r'\b\d{1,3}\b', parenthetical.group(1))]
            if len(selected) == 3 and len(set(selected)) == 3 and sorted(selected) == list(range(min(selected), min(selected)+3)):
                periods = sorted(selected)
                period_resolution = {'status':'explicit_completed_window_not_calendar_verified',
                                     'last_completed':max(periods), 'active_period':None,
                                     'standings_finalization':'requires_complete_archives'}
            else:
                periods = []
                period_resolution = {'status':'invalid_requested_window', 'last_completed':None,
                                     'active_period':None}
        else:
            # Standalone baseline references are not reporting weeks.
            periods = []
    if rolling and not periods and period_resolution['status'] != 'invalid_requested_window':
        # Calendar evidence selects the reporting scope. A standings archive
        # cannot establish that a period has ended.
        from Athena.Investigation.fantrax_period_calendar import acquire_unified_period
        try:
            league, season = resolve_league_context(ctx.league_profile, ctx.standings_archive)
            resolved = acquire_unified_period(league, season)
            latest = resolved.get('period')
            if (resolved.get('status') == 'calendar_closed' and resolved.get('boundary_kind') == 'scoring'
                    and type(latest) is int and latest >= 3):
                periods = [latest-2, latest-1, latest]
                period_resolution = {'status':'calendar_closed', 'last_completed':latest,
                                     'active_period':(latest+1 if latest+1 in (resolved.get('schedule') or {}) else None),
                                     'source':resolved.get('source'),
                                     'boundary_kind':resolved.get('boundary_kind'),
                                     'standings_finalization':'requires_complete_archives'}
            else:
                period_resolution = {'status':'unverified', 'last_completed':None,
                                     'active_period':None, 'reason':resolved.get('reason')}
        except (ValueError, KeyError, OSError, TypeError) as exc:
            period_resolution = {'status':'unverified', 'last_completed':None,
                                 'active_period':None, 'reason':type(exc).__name__}

    if len(periods) < 2:
        limitations.append('Two or more bounded, explicit scoring periods are required.')
    else:
        try:
            league, season = resolve_league_context(ctx.league_profile, ctx.standings_archive)
            snapshots, missing = [], []
            for period in periods:
                try:
                    snapshots.append(load_snapshot(OUTPUT_DIR, league, season, period))
                except (ValueError, KeyError, OSError, TypeError):
                    missing.append(period)
            findings = (analyze_snapshots(snapshots, periods) if not missing else
                        {'status':'missing_periods', 'missing_periods':missing})
            if findings.get('status') == 'verified' and periods[0] > 1:
                try:
                    baseline = load_snapshot(OUTPUT_DIR, league, season, periods[0] - 1)
                    before = {str(t['team_id']): t for t in baseline['teams']}
                    if set(before) == {t['team_id'] for t in findings['teams']}:
                        race_baseline = baseline
                        for team in findings['teams']:
                            current = team['cumulative_points'][0]
                            diff = current - before[team['team_id']]['points']
                            team['first_period_points'] = round(diff, 5) if diff >= 0 else None
                except (ValueError, KeyError, OSError, TypeError):
                    pass
        except (ValueError, KeyError, OSError, TypeError) as exc:
            limitations.append(f'Requested period evidence not verified: {exc}')
    scope = ', '.join('Week '+str(p) for p in periods) or 'unresolved weeks'
    structured = {'status': findings.get('status') if findings else 'unavailable',
                  'periods': periods, 'teams_analyzed': 0, 'total_teams': None,
                  'scoring_complete': False, 'missing_periods': findings.get('missing_periods', []) if findings else [],
                  'stories': [], 'race': {'status': 'unavailable'}, 'transactions': [],
                  'transaction_coverage': 'not_requested', 'synthesis': {'status': 'unavailable'},
                  'competitive_dynamics': {'status':'unavailable'}, 'period_resolution':period_resolution}
    if findings and findings.get('status') == 'verified':
        teams = findings['teams']
        structured['teams_analyzed'] = len(teams)
        structured['total_teams'] = len(teams)
        complete = all(type(t.get('first_period_points')) in (int, float) for t in teams)
        structured['scoring_complete'] = complete
        for t in teams:
            weekly = ([t['first_period_points']] if complete else []) + t['interval_points']
            t['weekly_points'] = dict(zip(periods if complete else periods[1:], weekly))
            t['window_points'] = round(sum(weekly), 5) if complete else None
            t['observed_interval_points'] = round(sum(t['interval_points']), 5)
        structured['race'] = analyze_race(teams, periods, baseline=race_baseline)
        structured['competitive_dynamics'] = analyze_competitive_dynamics(teams, periods, baseline=race_baseline)
        if not complete:
            limitations.append('The first requested week is a cumulative baseline; its preceding snapshot is needed to calculate that week’s scoring and full-window totals.')
        # Findings are provider facts and numerical signals, not a writer's guess
        # about injuries, player contribution or management intent.
        ranked = sorted(teams, key=lambda t: (-t['window_points'], t['name'])) if complete else sorted(teams,key=lambda t:(-t['observed_interval_points'],t['name']))
        if ranked:
            t = ranked[0]
            structured['stories'].append({'kind':'scoring_pace','team_id':t['team_id'],'team':t['name'],
                                          'points':t['window_points'] if complete else t['observed_interval_points'],
                                          'scope':'full_window' if complete else 'after_initial_snapshot',
                                          'weekly_points':t['weekly_points']})
        for t in teams:
            weeks=list(t['weekly_points'])
            if len(weeks) >= 2:
                scores=[t['weekly_points'][w] for w in weeks]
                extreme=max(range(1,len(scores)),key=lambda j:abs(scores[j]-scores[j-1]))
                change=round(scores[extreme]-scores[extreme-1],5)
                if abs(change)>=15:
                    structured['stories'].append({'kind':'scoring_swing','team_id':t['team_id'],
                        'team':t['name'],'from_week':weeks[extreme-1], 'to_week':weeks[extreme],
                        'from_points':scores[extreme-1], 'to_points':scores[extreme], 'change':change})
            if len(t['ranks'])>=3:
                moves=[t['ranks'][i-1]-t['ranks'][i] for i in range(1,len(t['ranks']))]
                if any(a*b<0 for a,b in zip(moves,moves[1:])):
                    structured['stories'].append({'kind':'rank_reversal','team_id':t['team_id'],
                        'team':t['name'],'ranks':t['ranks']})
            if t['rank_change']:
                structured['stories'].append({'kind':'rank_movement','team_id':t['team_id'],
                    'team':t['name'],'from_rank':t['ranks'][0], 'to_rank':t['ranks'][-1],
                    'change':t['rank_change']})
        structured['stories'].sort(key=lambda x: (
            {'scoring_pace':100,'scoring_swing':85,'rank_reversal':65,'rank_movement':55}[x['kind']]
            + (min(abs(x.get('change',0)),35) if x['kind']!='rank_movement' else min(abs(x['change'])*6,25))),reverse=True)
    else:
        limitations.append('Requested comparative standings are unverified: '+str(structured['status']))
        if periods:
            limitations.append('Do not publish this requested window until complete canonical standings for every period, including Period 8 when requested, are available.')

    if any(t in question.lower() for t in ('transaction','trade','waiver','add','drop','strateg')):
        from Athena.Investigation.transaction_event_intelligence import investigate_transactions
        history = ctx.transaction_history or {}
        try:
            # Use provider calendar for event-date mapping even with an explicit
            # reporting window. This is separate from standings-window resolution.
            from Athena.Investigation.fantrax_period_calendar import acquire_unified_period
            league, season = resolve_league_context(ctx.league_profile, ctx.standings_archive)
            transaction_calendar = acquire_unified_period(league, season)
        except (ValueError, KeyError, OSError, TypeError):
            transaction_calendar = {'status':'unverified'}
        analysis = investigate_transactions(history, periods, calendar=transaction_calendar)
        structured['transactions'] = analysis['periods']
        structured['transaction_spotlights'] = analysis['spotlights']
        structured['transaction_coverage'] = analysis['coverage']
        if analysis['unresolved_count']:
            limitations.append(f"{analysis['unresolved_count']} transactions lack verified event-period assignment; roster-effective labels were not substituted for event dates.")
        if analysis['event_time_based_count']:
            limitations.append('Transaction event dates are distinct from roster-effective scoring-period labels; player production after an exchange remains unverified.')

    # Historical active-roster joins use archived Fantrax IDs and NHL G+A.
    # Fantasy contribution is described as credited only when official team
    # period totals reconcile exactly and all active identities resolve.
    if findings and findings.get('status') == 'verified' and periods:
        from Athena.Investigation.player_level_attribution import (
            analyze_player_attribution, assess_trade_production)
        try:
            league, season = resolve_league_context(ctx.league_profile, ctx.standings_archive)
            verified_points = {s['period']: {str(t['team_id']):t['points'] for t in s['teams']}
                               for s in snapshots}
            if race_baseline is not None:
                verified_points[race_baseline['period']] = {
                    str(t['team_id']):t['points'] for t in race_baseline['teams']}
            attribution = analyze_player_attribution(OUTPUT_DIR, league, season, periods, verified_points)
            structured['player_attribution'] = attribution
            from Athena.Investigation.period_evidence_diagnostics import diagnose_period_evidence
            structured['period_evidence_diagnostics'] = diagnose_period_evidence(
                OUTPUT_DIR, league, season, periods, attribution)
            structured['trade_production'] = assess_trade_production(
                structured.get('transaction_spotlights'), attribution)
            if attribution['missing_periods']:
                limitations.append('Verified historical player production and active rosters are unavailable for '
                                   + ', '.join(f"Period {p}" for p in attribution['missing_periods']) + '.')
        except (ValueError, KeyError, OSError, TypeError) as exc:
            structured['player_attribution'] = {'status':'attribution_unavailable',
                                                'reason':type(exc).__name__}
    else:
        structured['player_attribution'] = {'status':'comparative_standings_unverified'}

    # Synthesis takes place after scoring, race and transaction acquisition;
    # the complete team cohort remains available even when only three stories
    # are published.
    structured['synthesis'] = synthesize_storylines({**structured, 'teams': findings['teams'] if findings and findings.get('status') == 'verified' else []})

    # Athena exposes structured decisions; Scout composes the article without
    # reaching back into raw provider state or inventing an explanation.
    from Scout.conversation.multi_period_publication import publish_multi_period
    text = publish_multi_period(structured)
    result=response(intent='league_multi_period_analysis',title=f'JHLPAA | Multi-period analysis ({scope})',
                    engine_conclusion=text,natural_language_response=text,
                    observed_facts=[f"Analyzed {structured['teams_analyzed']} teams across {len(periods)} requested periods"],known_limitations=limitations,
                    confidence=.75 if findings and findings['status']=='verified' else .25,
                    developer=developer_info('league_multi_period_analysis', ctx.files_loaded,
                        knowledge_used=['canonical_period_standings'],intelligence_used=['multi_period_analysis', 'evidence_to_editorial', 'player_level_attribution'],
                        files_read=[],missing=['verified_period_transactions'] ))
    result['developer']['requested_periods']=periods
    result['developer']['period_resolution']=period_resolution
    result['developer']['period_analysis']=findings
    result['developer']['multi_period_findings']=structured
    result['developer']['investigation_owner']='Athena.Investigation.multi_period_analysis'
    return result
