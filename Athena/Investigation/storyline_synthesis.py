"""Rank cross-signal league narratives from verified analytical facts only.

This is an Athena decision layer, not Scout copywriting. A trade appearing in
an observed week establishes coexistence, never that it caused scoring changes.
"""
from __future__ import annotations


def _num(value):
    return f'{value:g}' if isinstance(value, (float, int)) and not isinstance(value, bool) else '?'


def synthesize_storylines(findings: dict) -> dict:
    if findings.get('status') != 'verified':
        return {'status': 'insufficient_evidence', 'evaluated_teams': 0, 'ranked': [], 'featured': []}
    race = findings.get('race') or {}
    teams = (findings.get('teams') or [])
    # Teams may only exist in the internal analysis structure; accept the
    # complete period-analysis roster rather than counting featured stories.
    by_id = {str(t['team_id']): t for t in teams if t.get('team_id') is not None}
    if not by_id:
        return {'status': 'insufficient_evidence', 'evaluated_teams': 0, 'ranked': [], 'featured': []}
    race_signals = {str(s['team_id']): s for s in race.get('team_signals', [])}
    trade_associations: dict[str, list[dict]] = {}
    for week in findings.get('transactions', []):
        for e in week.get('events', []):
            if 'trade' not in e.get('type', '').lower():
                continue
            names = set(e.get('participants') or []) | set((e.get('received') or {}).keys())
            for name in names:
                trade_associations.setdefault(name, []).append({'week': week['week'], 'event_id': e.get('id'),
                    'acquired': (e.get('received') or {}).get(name, [])})
    candidates=[]
    for tid, team in by_id.items():
        signal = race_signals.get(tid) or {}
        gap = signal.get('gap_closed')
        gap_end = signal.get('end_gap')
        full = team.get('window_points')
        week_scores = team.get('weekly_points') or {}
        scores = sorted(week_scores.items())
        swing = max(((w0,w1,round(p1-p0,5)) for (w0,p0),(w1,p1) in zip(scores,scores[1:])),
                    key=lambda x:abs(x[2]), default=None)
        trade_context = trade_associations.get(team['name'], [])
        facts=[]
        priority=0
        classification='position_watch'
        if isinstance(gap, (int,float)) and gap>0 and isinstance(gap_end,(int,float)) and gap_end>0:
            priority=60+min(gap,50)*1.5 + max(0, 15-gap_end)*0.25
            classification='closing_challenger'
            facts.append(f"closed {_num(gap)} points of the gap to first; now {_num(gap_end)} behind")
        elif isinstance(gap,(int,float)) and gap<0:
            priority=40+min(abs(gap),60)*0.8
            classification='losing_ground'
            facts.append(f"fell {_num(abs(gap))} points farther behind first")
        elif isinstance(gap_end,(int,float)) and gap_end==0:
            priority=75
            classification='leader'
            facts.append('holds or shares the verified points lead')
        if isinstance(full,(float,int)):
            facts.append(f"scored {_num(full)} over the full requested window")
        elif team.get('observed_interval_points') is not None:
            facts.append(f"scored {_num(team['observed_interval_points'])} after the initial snapshot (partial window)")
        if swing and abs(swing[2])>=15:
            facts.append(f"scoring changed from {_num(week_scores[swing[0]])} in Week {swing[0]} to {_num(week_scores[swing[1]])} in Week {swing[1]}")
            priority+=min(abs(swing[2]),50)*0.35
        if trade_context:
            facts.append(f"participated in {len(trade_context)} recorded trade(s) in the requested weeks")
            priority+=min(len(trade_context),3)*4
        if team.get('rank_change'):
            priority+=min(abs(team['rank_change']),5)*2
        candidates.append({'team_id':tid,'team':team['name'],'kind':classification,
            'priority':round(priority,3),'evidence':facts,'gap_closed':gap,'end_gap':gap_end,
            'window_points':full,'largest_swing':swing,'trade_context':trade_context,
            'causal_attribution':'not_established'})
    ranked=sorted(candidates, key=lambda x:(-x['priority'],x['team']))
    return {'status':'verified','evaluated_teams':len(by_id),'ranked':ranked,
            'featured':ranked[:3], 'causal_attribution':'not_established',
            'comparison_scope':(race.get('comparison_from'),race.get('comparison_to')) if race.get('status')=='verified' else None}
