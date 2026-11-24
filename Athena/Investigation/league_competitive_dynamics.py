"""Local competitive races across the standings, without invented postseason cutoffs.

A standings position is not a playoff qualification rule. Likewise poor current
results are not evidence of rebuilding, and a trade is not proof of player impact.
"""
from __future__ import annotations


def analyze_competitive_dynamics(teams: list[dict], periods: list[int], *, baseline: dict | None = None) -> dict:
    if not teams or not periods or any(len(t.get('cumulative_points') or []) != len(periods) for t in teams):
        return {'status': 'unavailable', 'groups': [], 'team_count': 0}
    initial = {str(t['team_id']): t for t in (baseline or {}).get('teams', [])}
    full_baseline = bool(initial) and set(initial) == {str(t['team_id']) for t in teams}
    # Sort by final actual points; never reinterpret ordinal provider ranks as a
    # verified playoff threshold or claim the third/halfway rank is a cutoff.
    ordered = sorted(teams, key=lambda x: (-x['cumulative_points'][-1], x['name']))
    size = len(ordered)
    upper_end = (size + 2) // 3
    middle_end = (2 * size + 2) // 3
    bins = [('upper_table', ordered[:upper_end]), ('middle_table', ordered[upper_end:middle_end]),
            ('lower_table', ordered[middle_end:])]
    result = []
    for category, rows in bins:
        if not rows:
            continue
        signals = []
        for team in rows:
            index = next(i for i, r in enumerate(ordered) if r['team_id'] == team['team_id'])
            higher = ordered[index-1] if index else None
            current_gap = round(higher['cumulative_points'][-1] - team['cumulative_points'][-1], 5) if higher else 0
            previous_gap = None
            if higher and full_baseline:
                previous_gap = round(float(initial[str(higher['team_id'])]['points']) - float(initial[str(team['team_id'])]['points']), 5)
            # Signed gap delta is a *specific-neighbor* observation, not gain
            # on the original or current league leader.
            gap_change = round(previous_gap - current_gap, 5) if previous_gap is not None else None
            signals.append({'team_id': team['team_id'], 'team': team['name'],
                            'rank': team['ranks'][-1], 'points': team['cumulative_points'][-1],
                            'neighbor_above': higher['name'] if higher else None,
                            'gap_to_neighbor': current_gap, 'gap_change_to_neighbor': gap_change,
                            'window_points': team.get('window_points')})
        # Prioritize movement locally, but do not infer manager motives.
        candidates = [s for s in signals if s['neighbor_above']]
        if full_baseline:
            spotlight = max(candidates, key=lambda s: (s['gap_change_to_neighbor'], -s['gap_to_neighbor'], s['team']), default=None)
        else:
            spotlight = min(candidates, key=lambda s: (s['gap_to_neighbor'], s['team']), default=None)
        result.append({'category': category, 'team_count': len(rows), 'teams': signals,
                       'spotlight': spotlight, 'position_only': True})
    return {'status': 'verified', 'groups': result, 'team_count': size,
            'baseline_verified': full_baseline, 'scope': periods,
            'classification': 'descriptive_standings_thirds_not_playoff_or_rebuild_status',
            'strategy_attribution': 'unverified_without_asset_and_motive_evidence'}
