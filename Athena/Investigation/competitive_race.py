"""Evidence-bounded competitive race signals from cumulative standings.

Pure analysis; no provider calls or presentation wording. Gap movement compares
end-of-period standings. Full requested-week changes require the prior baseline.
"""
from __future__ import annotations


def analyze_race(teams: list[dict], periods: list[int], *, baseline: dict | None = None) -> dict:
    if not teams or not periods:
        return {'status': 'unavailable', 'signals': []}
    n = len(periods)
    if any(len(t.get('cumulative_points', [])) != n for t in teams):
        return {'status': 'incomplete', 'signals': []}
    start = {str(t.get('team_id')): t for t in (baseline or {}).get('teams', [])} if baseline else {}
    has_baseline = bool(start) and set(start) == {str(t['team_id']) for t in teams}
    windows = []
    if has_baseline:
        windows.append({'label': f'after Week {periods[0]-1}', 'points': {tid: float(t['points']) for tid,t in start.items()}})
    for i,p in enumerate(periods):
        windows.append({'label': f'after Week {p}', 'points': {t['team_id']: float(t['cumulative_points'][i]) for t in teams}})
    first,last=windows[0],windows[-1]
    first_best=max(first['points'].values())
    last_best=max(last['points'].values())
    by_id={t['team_id']: t for t in teams}
    leader_ids=[tid for tid,p in last['points'].items() if abs(p-last_best)<1e-7]
    signals=[]
    for tid,t in by_id.items():
        start_gap=round(first_best-first['points'][tid],5)
        end_gap=round(last_best-last['points'][tid],5)
        gained=round(start_gap-end_gap,5)
        signals.append({'team_id':tid,'team':t['name'], 'rank':t['ranks'][-1],
                        'start_gap':start_gap,'end_gap':end_gap,
                        'gap_closed':gained,
                        'direction':'closed' if gained>1e-7 else 'widened' if gained < -1e-7 else 'unchanged'})
    # The lead group is defined by verified points; multiple tied leaders are valid.
    challengers=sorted((s for s in signals if s['end_gap']>1e-7),key=lambda s:(s['end_gap'],s['rank'],s['team']))
    closing=sorted((s for s in signals if s['gap_closed']>1e-7 and s['end_gap']>1e-7),key=lambda s:(-s['gap_closed'],s['end_gap'],s['team']))
    fading=sorted((s for s in signals if s['gap_closed']< -1e-7),key=lambda s:(s['gap_closed'],s['team']))
    return {'status':'verified','comparison_from': first['label'], 'comparison_to':last['label'],
            'includes_first_requested_week':has_baseline,
            'leader_points':last_best, 'leaders':[by_id[x]['name'] for x in leader_ids],
            'closest_challengers':challengers[:2], 'closing_gap':closing[:3], 'losing_ground':fading[:2],
            'team_signals':signals, 'teams_analyzed':len(signals)}
