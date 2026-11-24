"""Athena editorial selection: evidence-backed leads and complete transaction inventory.

This is an editorial ranking, not a new sports-data source. Only verified
research fields may influence a lead. Missing history is not inferred.
"""
from __future__ import annotations


def rank_stories(research: dict) -> list[dict]:
    findings = [f for f in research.get('findings', []) if isinstance(f, dict)]
    continuity = (research.get('storyline_continuity') or {}).get('signals') or []
    arcs = {str(x.get('team_name')): x for x in continuity
            if isinstance(x, dict) and isinstance(x.get('overall_rank_change'), int)
            and x.get('direction') in {'climb', 'slide'}}
    candidates = []
    for f in findings:
        kind, team = f.get('kind'), f.get('team')
        if kind not in {'surge', 'climb', 'slide', 'scoring_leader', 'trade_cluster', 'trade'}:
            continue
        points = f.get('period_points')
        change = f.get('rank_change')
        score = {'surge': 82, 'scoring_leader': 80, 'climb': 62,
                 'slide': 61, 'trade_cluster': 65, 'trade': 44}[kind]
        if f.get('top_score') is True: score += 18
        if kind in {'surge', 'climb', 'slide'} and type(change) is int:
            score += min(14, abs(change) * 3)
        if kind == 'trade_cluster': score += min(17, max(0, int(f.get('trade_count') or 0)) * 4)
        if team in arcs and kind in {'surge', 'climb', 'slide', 'scoring_leader'}:
            arc = arcs[team]
            if (arc['overall_rank_change'] > 0 and kind != 'slide') or (arc['overall_rank_change'] < 0 and kind == 'slide'):
                score += min(15, abs(arc['overall_rank_change']) * 2)
        candidates.append({'finding': f, 'score': score,
                           'reason': 'verified_period_standings' if kind not in {'trade','trade_cluster'} else 'canonical_trade_events'})
    return sorted(candidates, key=lambda x: (-x['score'], str(x['finding'].get('team') or ''), str(x['finding'].get('kind'))))


def transaction_inventory(research: dict) -> dict:
    """Use ALL canonical trades, not a lead-team cluster or duplicated summaries."""
    editor = research.get('editorial') or {}
    verified = editor.get('trades')
    if isinstance(verified, list):
        source = [x for x in verified if isinstance(x, dict)]
        source_type = 'canonical_editorial'
    else:
        source_type = 'finding_fallback'
        source = []
        for finding in research.get('findings') or []:
            if finding.get('kind') not in {'trade', 'trade_cluster'}: continue
            source.extend(x for x in finding.get('exchanges') or [] if isinstance(x, dict))
    seen, result = set(), []
    for idx, trade in enumerate(source):
        received = trade.get('received') or {}
        if not isinstance(received, dict): continue
        normalized = {str(team): [str(v) for v in assets if str(v).strip()]
                      for team, assets in received.items() if isinstance(assets, list) and assets}
        if not normalized: continue
        event_id = str(trade.get('transaction_id') or '').strip()
        identity = ('id', event_id) if event_id else ('assets', tuple(sorted((team, tuple(sorted(assets))) for team, assets in normalized.items())))
        if identity in seen: continue
        seen.add(identity)
        result.append({'transaction_id': event_id or None, 'received': normalized})
    return {'source': source_type, 'count': len(result), 'trades': result,
            'expected_count': editor.get('trade_count') if source_type == 'canonical_editorial' else None}


def historical_trade_continuity(history: dict, period: int) -> dict:
    """Count canonical trade participation across the last two periods.

    Only identified, completed trades with explicit week attribution contribute.
    Missing period metadata cannot be interpreted as an inactive manager.
    """
    if type(period) is not int or period < 2:
        return {'status': 'unavailable', 'signals': []}
    from Athena.Investigation.league_editorial import investigate_league_period
    from collections import Counter
    per_period = {}
    for week in (period - 1, period):
        editorial = investigate_league_period(history, week)
        events = editorial.get('trades') or []
        counts = Counter()
        for event in events:
            for team in set(event.get('participants') or []) | set((event.get('received') or {}).keys()):
                if team: counts[str(team)] += 1
        per_period[week] = counts
    signals = []
    for team in set(per_period[period - 1]) | set(per_period[period]):
        count_before, count_now = per_period[period - 1][team], per_period[period][team]
        if count_before and count_now and count_before + count_now >= 3:
            signals.append({'team': team, 'periods': [period-1, period],
                            'trade_counts': [count_before,count_now],
                            'total_trades': count_before+count_now,
                            'source': 'canonical_period_trade_history'})
    signals.sort(key=lambda x:(-x['total_trades'],x['team']))
    return {'status': 'verified' if signals else 'no_repeated_trade_cluster', 'signals': signals}
