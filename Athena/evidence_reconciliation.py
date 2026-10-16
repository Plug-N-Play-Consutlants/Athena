"""Reconcile observed specialist acquisitions with the original question-scoped ledger.

Only a supported, specifically identified replacement source can satisfy a missing
requirement. Source failure and missing facts remain distinct in the diagnostic.
"""
from __future__ import annotations
from typing import Any


def _unique(items: Any) -> list[str]:
    if not isinstance(items, (list, tuple)):
        return []
    result: list[str] = []
    for item in items:
        if isinstance(item, str) and item.strip() and item not in result:
            result.append(item)
    return result


def reconcile_evidence(bundle: dict[str, Any], answer: dict[str, Any]) -> dict[str, Any]:
    """Update the attached canonical bundle in place, without trusting prose claims.

    A specialist can acquire official NHL club statistics after the player landing
    record failed. The acquired row is authoritative only when the specialist has
    attached its structured official source record for the same resolved subject.
    """
    original_missing = _unique(bundle.get('missing'))
    original_sources = _unique(bundle.get('sources'))
    resolved: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []
    developer = answer.get('developer') if isinstance(answer.get('developer'), dict) else {}
    detail = developer.get('request_evidence') if isinstance(developer.get('request_evidence'), dict) else {}
    player = bundle.get('player') if isinstance(bundle.get('player'), dict) else None
    if player is not None and detail is player:
        record = player.get('official_player_record')
        fallback = player.get('fallback_source')
        stats = record.get('statistical_evidence') if isinstance(record, dict) else None
        rows = stats.get('season_series') if isinstance(stats, dict) else None
        valid = (fallback == 'official_nhl_club_stats' and isinstance(stats, dict)
                 and stats.get('source') == 'official_nhl_club_stats'
                 and isinstance(rows, list) and any(isinstance(row, dict)
                     and isinstance(row.get('gp'), (int, float)) and not isinstance(row.get('gp'), bool)
                     and row['gp'] > 0 and isinstance(row.get('season'), (int, str))
                     and str(row['season']).strip() for row in rows))
        if valid:
            if 'official_nhl_player_record' in original_missing:
                original_missing.remove('official_nhl_player_record')
                resolved.append({'requirement': 'official_nhl_player_record',
                                 'replacement_source': 'official_nhl_club_stats'})
            if 'official_nhl_club_stats' not in original_sources:
                original_sources.append('official_nhl_club_stats')
            player['missing'] = [m for m in _unique(player.get('missing')) if m != 'official_nhl_player_record']
        if player.get('club_stats_fallback_error'):
            failures.append({'source': 'official_nhl_club_stats',
                             'error_type': str(player['club_stats_fallback_error'])})
    # Team evidence is acquired by the specialist today. Reconcile only the
    # structured acquisition record it actually returns; prose is not proof.
    team = developer.get('team_performance_evidence')
    if isinstance(team, dict) and isinstance(team.get('team'), str) and team.get('team'):
        allowed = {'nhl_club_stats_season', 'nhl_official_current_standings',
                   'nhl_official_completed_games', 'nhl_current_roster',
                   'canonical_team_economic_state', 'canonical_league_season_context'}
        for source in _unique(team.get('sources')):
            if source in allowed and source not in original_sources:
                original_sources.append(source)
        for missing in _unique(team.get('missing')):
            if missing not in original_missing:
                original_missing.append(missing)
        bundle['specialist_evidence'] = {
            'domain': 'team', 'team': team['team'],
            'sources': [s for s in _unique(team.get('sources')) if s in allowed],
            'missing': _unique(team.get('missing')),
            'season': team.get('season'),
            'consumption': 'specialist_structured_evidence_reported',
        }
    bundle['missing'] = original_missing
    bundle['sources'] = original_sources
    if resolved:
        bundle['reconciled_sources'] = resolved
    if failures:
        bundle['acquisition_failures'] = failures
    if resolved and not original_missing:
        bundle['status'] = 'ready'
    elif original_missing and bundle.get('status') in {'ready', 'not_required'}:
        bundle['status'] = 'partial'
    return {'status': bundle.get('status', 'unknown'), 'sources': list(original_sources),
            'missing': list(original_missing), 'resolved': resolved, 'acquisition_failures': failures}
