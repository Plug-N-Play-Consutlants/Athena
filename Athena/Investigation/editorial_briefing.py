"""Verified league-wide editorial briefing for Scout's journalist surface.

Athena owns observations and comparisons, not phrasing. No player-specific
fantasy credit, owner motive, or participation judgement is inferred here.
"""
from __future__ import annotations


def _number(value):
    return type(value) in (int, float) and not isinstance(value, bool)


def build_editorial_briefing(research: dict) -> dict:
    comparison = research.get('comparison') or {}
    if comparison.get('status') != 'compared' or comparison.get('source') not in (None, 'canonical_period_standings'):
        return {'status': 'unavailable', 'reason': 'verified_period_comparison_missing'}
    teams = comparison.get('teams') or []
    if not isinstance(teams, list) or not teams or any(not isinstance(t, dict) or not t.get('name') or
                         type(t.get('rank')) is not int or not _number(t.get('period_points')) or
                         not _number(t.get('points')) or type(t.get('rank_change')) is not int for t in teams):
        return {'status': 'unavailable', 'reason': 'incomplete_period_comparison'}
    if len({str(t.get('team_id') or t['name']) for t in teams}) != len(teams):
        return {'status': 'unavailable', 'reason': 'duplicate_team_identity'}
    by_score = sorted(teams, key=lambda t: (-t['period_points'], t['name']))
    score_cutoff = by_score[min(2, len(by_score)-1)]['period_points']
    leaders = [t for t in by_score if t['period_points'] >= score_cutoff]
    ascending = sorted(teams, key=lambda t: (-t['rank_change'], t['name']))
    climbing = [t for t in ascending if t['rank_change'] > 0]
    falling = [t for t in reversed(ascending) if t['rank_change'] < 0]
    unchanged = [t for t in teams if t['rank_change'] == 0]
    leaders_in_rank = [t for t in teams if t['rank'] == min(x['rank'] for x in teams)]
    best_score = by_score[0]['period_points']
    top_scoring_rank = min(t['rank'] for t in teams if t['period_points'] == best_score)
    # Rank measures are standings positions only; point gaps are taken from
    # cumulative verified source totals and do not imply a tie-break winner.
    first_points = max(t['points'] for t in leaders_in_rank)
    gaps = [dict(team=t['name'], points_behind=first_points-t['points'], rank=t['rank'])
            for t in teams if t['rank'] > min(x['rank'] for x in teams) and first_points >= t['points']]
    gaps.sort(key=lambda t: (t['points_behind'], t['rank'], t['team']))
    # Athena selects evidence-backed editorial contrasts; Scout owns the voice.
    # These observations make no claim about owner motive or player credit.
    signals = []
    weekly_winner = by_score[0]
    first_rank = min(t['rank'] for t in teams)
    overall_leader = sorted(leaders_in_rank, key=lambda t: (-t['points'], t['name']))[0]
    if weekly_winner['rank'] != first_rank:
        signals.append({'kind': 'weekly_vs_overall', 'weekly_team': weekly_winner['name'],
                        'weekly_points': weekly_winner['period_points'],
                        'weekly_rank': weekly_winner['rank'],
                        'overall_team': overall_leader['name'],
                        'overall_rank': overall_leader['rank'],
                        'overall_points': overall_leader['points']})
    if overall_leader['name'] != weekly_winner['name']:
        signals.append({'kind': 'leader_under_pressure', 'team': overall_leader['name'],
                        'period_points': overall_leader['period_points'],
                        'weekly_best': weekly_winner['period_points'],
                        'rank': overall_leader['rank']})
    productive_slides = [t for t in teams if t['rank_change'] < 0 and t['period_points'] >= score_cutoff]
    for t in sorted(productive_slides, key=lambda r: (r['rank_change'], -r['period_points'], r['name']))[:2]:
        signals.append({'kind': 'scored_but_slipped', 'team': t['name'],
                        'period_points': t['period_points'], 'rank_change': t['rank_change'],
                        'rank': t['rank']})
    if climbing:
        fastest = climbing[0]
        if fastest['name'] != weekly_winner['name']:
            signals.append({'kind': 'movement_vs_scoring', 'team': fastest['name'],
                            'period_points': fastest['period_points'], 'rank_change': fastest['rank_change'],
                            'rank': fastest['rank'], 'weekly_team': weekly_winner['name'],
                            'weekly_points': weekly_winner['period_points']})
    if _number(best_score) and _number(by_score[-1]['period_points']) and len(teams) > 1:
        signals.append({'kind': 'scoring_spread', 'highest': best_score,
                        'lowest': by_score[-1]['period_points'],
                        'difference': best_score - by_score[-1]['period_points']})
    return {
        'status': 'verified', 'source': 'canonical_period_standings',
        'period': comparison.get('period'), 'baseline_period': comparison.get('baseline_period'),
        'team_count': len(teams), 'leaders': leaders, 'climbers': climbing,
        'fallers': falling, 'unchanged': unchanged, 'weekly_top_points': best_score,
        'weekly_top_rank': top_scoring_rank, 'front_runners': leaders_in_rank,
        'gaps_to_first': gaps, 'low_scorers': list(reversed(by_score))[:2],
        'narrative_signals': signals,
    }
