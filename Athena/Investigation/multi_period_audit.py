"""Athena-owned, cross-period audit evidence for explicit league inquiries.

Re-executes the common verified scoring audit for the requested periods, rather
than trusting a single Scout rendering or treating historical roster snapshots
as game-effective fantasy scoring credit. Missing sources remain missing.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from Athena.Investigation.sync_period_scoring_audit import audit_path, run as run_scoring_audit


def investigate_requested_periods(*, output_dir: Path, league_id: str | None,
                                  season: int | str | None, periods: list[int],
                                  expected_teams: int | None = None,
                                  runner: Callable[..., dict] = run_scoring_audit) -> dict:
    """Return bounded per-team evidence for EVERY explicit requested period.

    A request-stage manifest is independent of the sync-stage manifest, so
    diagnostics cannot overwrite the actual Sync League execution status.
    """
    requested = sorted(set(periods))
    summary: dict[str, Any] = {
        'schema': 'athena.multi_period_scoring_inquiry.v1',
        'status': 'source_unavailable', 'requested_periods': requested,
        'audited_periods': 0, 'unavailable_periods': len(requested), 'periods': [],
        'interpretation': 'Numeric scoring agreement is not game-effective fantasy lineup proof',
    }
    if (not league_id or not str(league_id).isalnum() or not str(season or '').isdigit()
        or not requested or len(requested) > 8
        or any(type(p) is not int or p < 1 for p in requested)):
        summary['reason'] = 'Verified league, season and bounded scoring periods required'
        return summary
    manifest = runner(league_id=str(league_id), season=season,
                      expected_teams=expected_teams, output_dir=Path(output_dir),
                      requested_periods=requested)
    if not isinstance(manifest, dict):
        summary['reason'] = 'Period audit returned no verified manifest'
        return summary
    # Identity enrichment is diagnostic only: never infer or change credited
    # points from a player's name or a candidate NHL identifier.
    identity_by_id = {}
    try:
        mapped = json.loads((Path(output_dir) / 'player_identity_map.json').read_text(encoding='utf-8'))
        if isinstance(mapped, list):
            identity_by_id = {str(row['fantrax_player_id']): row for row in mapped
                              if isinstance(row, dict) and row.get('fantrax_player_id')}
    except (ValueError, OSError, TypeError):
        pass

    def detail(fid):
        item = identity_by_id.get(str(fid)) or {}
        return {'fantrax_player_id': str(fid),
                'player_name': item.get('canonical_player_name') or item.get('fantrax_player_name') or '',
                'resolution_status': item.get('resolution_status') or 'not_in_identity_map',
                'match_method': item.get('match_method') or 'not_indexed',
                'fantrax_position': item.get('fantrax_position') or '',
                'identity_sources': item.get('identity_sources') or []}

    for number in requested:
        entry = (manifest.get('periods') or {}).get(str(number)) or {}
        result = {'period': number, 'status': entry.get('status', 'source_unavailable'),
                  'reason': str(entry.get('reason') or manifest.get('reason') or '')[:240],
                  'numeric_matched_teams': 0, 'identity_complete_teams': 0,
                  'team_count': 0, 'unmatched_active_ids': [], 'unmatched_active_details': [],
                  'reserve_nhl_points_excluded': 0, 'teams': []}
        if entry.get('status') in ('partial', 'numeric_complete'):
            try:
                archive = json.loads(audit_path(Path(output_dir), str(league_id), season, number)
                                     .read_text(encoding='utf-8'))
                if (archive.get('schema') != 'athena.period_attribution.v1'
                    or archive.get('period') != number
                    or str(archive.get('league_id')) != str(league_id)
                    or str(archive.get('season')) != str(season)
                    or not isinstance(archive.get('teams'), list)
                    or len(archive['teams']) != entry.get('team_count')
                    or (expected_teams and len(archive['teams']) != int(expected_teams))):
                    raise ValueError('Archived scoring evidence source or team count does not match request')
                # Source-bound fields; no team/player credit is manufactured.
                result.update({
                    'numeric_matched_teams': archive.get('numeric_matched_teams', 0),
                    'identity_complete_teams': archive.get('fully_reconciled_teams', 0),
                    'team_count': len(archive['teams']),
                    'unmatched_active_ids': archive.get('unmatched_active_ids') or [],
                    'unmatched_active_details': [detail(fid) for fid in archive.get('unmatched_active_ids') or []],
                    'reserve_nhl_points_excluded': archive.get('reserve_nhl_points_excluded') or 0,
                    'teams': [{key: team.get(key) for key in (
                        'team_id', 'team_name', 'status', 'difference', 'fantrax_points',
                        'identified_active_nhl_points', 'unmatched_active_ids',
                        'reserve_nhl_points_excluded', 'lineup_eligibility')}
                        for team in archive['teams']],
                })
                for team in result['teams']:
                    team['unmatched_active_details'] = [detail(fid) for fid in team.get('unmatched_active_ids') or []]
                summary['audited_periods'] += 1
            except (ValueError, TypeError, KeyError, OSError) as exc:
                result['status'] = 'source_unavailable'
                result['reason'] = f'Archived scoring evidence unavailable: {type(exc).__name__}: {exc}'[:240]
        summary['periods'].append(result)
    summary['unavailable_periods'] = len(requested) - summary['audited_periods']
    summary['status'] = ('audited' if not summary['unavailable_periods']
                         else 'partial' if summary['audited_periods']
                         else 'source_unavailable')
    return summary
