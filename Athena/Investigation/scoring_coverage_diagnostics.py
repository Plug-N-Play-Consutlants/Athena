"""Classify completed-period score attribution, without relaxing reconciliation.

Partial disagreement may be snapshot lineup timing, official game coverage,
identity, or standings source differences. Categorization is evidence, not a
root-cause diagnosis or a claim about which feed is erroneous.
"""
from __future__ import annotations


def summarize_attribution_coverage(attribution: dict) -> dict:
    if not isinstance(attribution, dict):
        attribution = {}
    rows = [r for r in attribution.get('teams', []) if isinstance(r, dict)]
    total = len(rows)
    matched = [r for r in rows if r.get('status') == 'reconciled' and
               r.get('numeric_match') is True and r.get('identity_complete') is True]
    exceptions = []
    for row in rows:
        if row in matched:
            continue
        reasons = []
        if row.get('unmatched_active_ids'):
            reasons.append('unresolved_active_identity')
        if type(row.get('difference')) in (int, float) and row['difference'] != 0:
            reasons.append('numeric_difference')
        if row.get('difference') is None:
            reasons.append('unavailable_score')
        if not reasons:
            reasons.append('unclassified_attribution_gap')
        exceptions.append({'team_id': row.get('team_id'), 'team_name': row.get('team_name'),
                           'difference': row.get('difference'), 'reasons': reasons,
                           'reserve_nhl_points_excluded': row.get('reserve_nhl_points_excluded'),
                           'active_ids_without_nhl_game_rows': len(row.get('active_ids_without_nhl_game_rows') or [])})
    status = 'complete' if total and len(matched) == total else 'partial' if total else 'unavailable'
    return {'status': status, 'period': attribution.get('period'), 'team_count': total,
            'reconciled_teams': len(matched), 'unreconciled_teams': total - len(matched),
            'point_discrepancy_teams': sum('numeric_difference' in e['reasons'] for e in exceptions),
            'identity_gap_teams': sum('unresolved_active_identity' in e['reasons'] for e in exceptions),
            'unavailable_score_teams': sum('unavailable_score' in e['reasons'] for e in exceptions),
            'exceptions': exceptions,
            'interpretation': 'Team-level historical ACTIVE roster vs NHL G+A numeric check; partial results are not a complete scoring credit ledger'}
