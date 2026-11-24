"""Evidence-bounded period production attribution with historical roster identity.

NHL period G+A is not Fantrax credited scoring until active historical
lineups reconcile against the official team-period standings difference.
Transaction approval and roster eligibility are separate; this layer never
retroactively transfers player production based on the current owner.
"""
from __future__ import annotations

import json
from pathlib import Path


def _load(root, kind, league, season, period):
    path = (Path(root) / kind / str(league) / str(season) /
            f'period_{period:03d}.json')
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, ValueError):
        return None
    if not isinstance(value, dict) or value.get('verified') is not True:
        return None
    if str(value.get('league_id')) != str(league) or str(value.get('season')) != str(season):
        return None
    if value.get('period') != period:
        return None
    return value


def _period(production, roster, standings_delta):
    if production is None or roster is None:
        return {'status': 'missing_verified_player_or_roster_snapshot'}
    if (production.get('roster_basis') != 'verified_historical_period'
            or production.get('roster_scope') is None
            or production.get('status') != 'verified_nhl_window'
            or roster.get('status') != 'verified_period_rosters'):
        return {'status': 'unverified_historical_ownership_or_production'}
    p_rows = production.get('records')
    r_rows = roster.get('records')
    if not isinstance(p_rows, list) or not isinstance(r_rows, list):
        return {'status': 'invalid_record_schema'}
    players = {}
    duplicate_ids = set()
    for row in p_rows:
        if not isinstance(row, dict):
            return {'status': 'invalid_player_production'}
        pid = str(row.get('fantrax_player_id') or '')
        points = row.get('points')
        if not pid or type(points) not in (int, float) or points < 0:
            return {'status': 'invalid_player_production'}
        if pid in players:
            duplicate_ids.add(pid)
        players[pid] = row
    if duplicate_ids:
        return {'status': 'duplicate_player_production_ids'}
    teams = {}
    seen_roster_ids = set()
    for row in r_rows:
        if not isinstance(row, dict):
            return {'status': 'invalid_historical_roster'}
        pid = str(row.get('player_id') or '')
        tid = str(row.get('owner_team_id') or '')
        if not pid or not tid or pid in seen_roster_ids:
            return {'status': 'ambiguous_historical_roster_membership'}
        seen_roster_ids.add(pid)
        team = teams.setdefault(tid, {'team': str(row.get('owner_team') or tid), 'observed_nhl_points': 0,
                                      'matched_active': [], 'unmatched_active': []})
        if row.get('active_for_period') is not True:
            continue
        matched = players.get(pid)
        if matched is None:
            team['unmatched_active'].append(pid)
            continue
        amount = matched['points']
        team['observed_nhl_points'] += amount
        if amount > 0:
            team['matched_active'].append({'player_id': pid, 'name': matched.get('player_name') or pid,
                                            'goals': matched.get('goals'), 'assists': matched.get('assists'),
                                            'nhl_points': amount})
    for tid, team in teams.items():
        observed = round(team['observed_nhl_points'], 5)
        official = standings_delta.get(tid)
        team['observed_nhl_points'] = observed
        team['official_period_points'] = official
        team['matched_active'].sort(key=lambda r: (-r['nhl_points'], r['name']))
        team['top_contributors'] = team.pop('matched_active')[:5]
        unmatched = len(team.pop('unmatched_active'))
        team['unmatched_active_count'] = unmatched
        # A matching total with missing players does not prove a complete
        # attribution (a missing player's zero is not independently verified).
        team['status'] = ('reconciled_active_nhl_points' if unmatched == 0
                          and type(official) in (int, float)
                          and abs(official-observed) < 1e-5 else
                          'partial_nhl_evidence_not_fantasy_credit')
        team['game_effective_eligibility_verified'] = False
        team['credited_fantasy_points_verified'] = False
    return {'status':'verified_historical_input', 'game_effective_eligibility_verified':False, 'teams': teams,
            'matched_teams':sum(t['status']=='reconciled_active_nhl_points' for t in teams.values())}


def analyze_player_attribution(root, league, season, periods, standings):
    """standings: {period: {team_id: cumulative_points}} including baseline."""
    if not periods:
        return {'status': 'no_reporting_periods', 'periods': []}
    results = []
    for period in periods:
        previous = standings.get(period - 1, {})
        current = standings.get(period, {})
        delta = {tid: round(score - previous[tid],5)
                 for tid, score in current.items()
                 if tid in previous and type(score) in (int,float)
                 and type(previous[tid]) in (int,float) and score >= previous[tid]}
        production = _load(root, 'PeriodPlayerProduction', league, season, period)
        roster = _load(root, 'PeriodRosters', league, season, period)
        report = _period(production, roster, delta)
        report['period'] = period
        results.append(report)
    return {'status':'period_evidence_assessed','periods':results,
            'complete_periods':[r['period'] for r in results if r['status']=='verified_historical_input'],
            'missing_periods':[r['period'] for r in results if r['status']!='verified_historical_input']}


def assess_trade_production(trades, attribution):
    """Only summarize post-effective NHL production; not value gained or causality."""
    periods = {p['period']:p for p in attribution.get('periods',[]) if p.get('teams')}
    findings=[]
    for trade in trades or []:
        if 'trade' not in str(trade.get('type','')).lower():
            continue
        effective=trade.get('roster_effective_period')
        if type(effective) is not int:
            findings.append({'trade_id':trade.get('id'), 'status':'roster_effectiveness_unverified'})
            continue
        available=sorted(p for p in periods if p>=effective)
        if not available:
            findings.append({'trade_id':trade.get('id'),'status':'awaiting_roster_effective_period',
                             'effective_period':effective})
            continue
        # Destination-player identity matching requires immutable Fantrax IDs,
        # not player names or currently-held roster names. The transaction
        # summary contract currently contains only display names.
        findings.append({'trade_id':trade.get('id'),'status':'requires_transaction_player_id_crosswalk',
                         'effective_period':effective,'observed_post_effective_periods':available})
    return findings
