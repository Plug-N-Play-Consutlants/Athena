"""Read-only period evidence diagnostics; no absence, match or hypothesis becomes proof.

The archived audit explicitly distinguishes numeric reconciliation from game-time
Fantrax eligibility. A points sum alone never verifies *credited* player points.
"""
from __future__ import annotations
import json
from pathlib import Path


def _verified_archive(root, kind, league, season, period):
    path = Path(root)/kind/str(league)/str(season)/f'period_{period:03d}.json'
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, ValueError):
        return None
    if (not isinstance(data, dict) or data.get('verified') is not True
            or str(data.get('league_id')) != str(league)
            or str(data.get('season')) != str(season)
            or data.get('period') != period):
        return None
    return data


def diagnose_period_evidence(root, league, season, periods, attribution=None):
    attribution = attribution or {}
    reports = {p.get('period'):p for p in attribution.get('periods', [])}
    results=[]
    for period in periods:
        production = _verified_archive(root,'PeriodPlayerProduction',league,season,period)
        rosters = _verified_archive(root,'PeriodRosters',league,season,period)
        existing = reports.get(period) or {}
        evidence = {'period':period, 'production_available':bool(production),
                    'historical_roster_available':bool(rosters),
                    'status':'unavailable', 'unresolved_active_identity_count':0,
                    'numeric_reconciled_teams':0, 'discrepant_teams':0,
                    'total_absolute_point_difference':0, 'game_effective_eligibility_verified':False,
                    'causes_established':[], 'possible_causes_not_proven':[],
                    'next_action':''}
        if not production or not rosters:
            missing=[]
            if not production: missing.append('NHL player-window production')
            if not rosters: missing.append('historical period rosters')
            evidence['status']='missing_period_evidence'
            evidence['missing_components']=missing
            evidence['next_action']='Run targeted authenticated historical scoring audit for this completed period'
            results.append(evidence)
            continue
        if existing.get('status') != 'verified_historical_input':
            evidence['status']='unverified_join'
            evidence['next_action']='Check source identities and period-specific provenance'
            results.append(evidence)
            continue
        teams=existing.get('teams') or {}
        if not teams:
            evidence['status']='no_team_results'
            results.append(evidence)
            continue
        evidence['numeric_reconciled_teams']=sum(t.get('status')=='reconciled_active_nhl_points' for t in teams.values())
        evidence['discrepant_teams']=len(teams)-evidence['numeric_reconciled_teams']
        evidence['team_count']=len(teams)
        evidence['unresolved_active_identity_count']=sum(t.get('unmatched_active_count',0) for t in teams.values())
        evidence['total_absolute_point_difference']=round(sum(
            abs(t['official_period_points']-t['observed_nhl_points'])
            for t in teams.values() if type(t.get('official_period_points')) in (int,float)),5)
        # These hints do not assert any root cause; game-level Fantrax
        # effective lineup histories must establish actual scoring eligibility.
        evidence['possible_causes_not_proven']=['game-effective lineup/roster locks',
            'scoring-window boundary alignment', 'Fantrax scoring corrections']
        if evidence['unresolved_active_identity_count']:
            evidence['causes_established'].append('some active Fantrax IDs lack matched NHL production records')
        evidence['status']=('numeric_match_not_game_credit_proof'
             if not evidence['discrepant_teams'] else 'partial_numeric_reconciliation')
        evidence['next_action']='Reconcile credited game-level Fantrax lineup and scoring ledger against dated NHL games'
        results.append(evidence)
    return {'status':'diagnosed','periods':results,
            'missing_periods':[p['period'] for p in results if p['status']=='missing_period_evidence'],
            'interpretation':'Numerical active-roster NHL G+A equality does not establish player-specific Fantrax credit'}
