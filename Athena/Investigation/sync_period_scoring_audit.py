"""Reusable, bounded history-wide fantasy scoring audit for Sync League.

A valid Fantrax team-period total and NHL G+A agreement establish numeric
agreement; neither a historical roster snapshot nor a matching total proves
which skaters Fantrax credited at each puck drop. Keep eligibility distinct.

Only authentic elapsed calendar periods are eligible. Missing sources produce
explicit per-period exceptions and never fake a zero-point reconciliation.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import sys
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.project_paths import OUTPUT_DIR, RAW_DIR
from Athena.workspace import get_workspace_value
from Athena.Investigation.fantrax_period_calendar import resolve_unified_period
from Athena.Investigation.historical_roster_attribution import acquire_period_rosters, reconcile_period_points
from Athena.Investigation.nhl_period_production import acquire_nhl_period_production
from Athena.Investigation.standings_archive import compare_archived
from Athena.Investigation.standings_acquisition import ensure_period_snapshots


def audit_path(output: Path, league_id: str, season: Any, period: int) -> Path:
    if not str(league_id).isalnum() or not str(season).isdigit() or type(period) is not int or period < 1:
        raise ValueError('Invalid period scoring audit identity')
    return Path(output)/'PeriodScoringAudit'/str(league_id)/str(season)/f'period_{period:03d}.json'


def _save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def write_period_audit(output: Path, league_id: str, season: Any, period: int,
                       attribution: dict, *, clock: datetime | None = None) -> Path:
    """Save Scout-originated audits as well as Sync-produced audits."""
    if attribution.get('period') != period or not isinstance(attribution.get('teams'), list):
        raise ValueError('Cannot archive incomplete or wrong-period scoring attribution')
    path = audit_path(output, league_id, season, period)
    payload = {**attribution, 'league_id': str(league_id), 'season': str(season),
               'audited_at': (clock or datetime.now(timezone.utc)).isoformat()}
    if path.exists():
        try:
            previous = json.loads(path.read_text(encoding='utf-8'))
            if (previous.get('teams') != payload['teams'] or
                previous.get('eligibility_evidence') != payload.get('eligibility_evidence')):
                # Retroactive Fantrax corrections and improved NHL identities
                # should be reviewable instead of silently overwriting history.
                revisions = path.parent/'revisions'
                revisions.mkdir(exist_ok=True)
                index = 1
                while (revisions/f'{path.stem}_revision_{index:03d}.json').exists():
                    index += 1
                _save_json(revisions/f'{path.stem}_revision_{index:03d}.json', previous)
        except (ValueError, OSError, TypeError):
            # A corrupt old archive cannot establish prior verified evidence.
            pass
    _save_json(path, payload)
    return path


def run(*, league_info: dict | None = None, league_id: str | None = None,
        season: int | str | None = None, expected_teams: int | None = None,
        client_factory=None, nhl_client_factory=None,
        output_dir: Path | None = None, raw_dir: Path | None = None,
        clock: datetime | None = None, max_periods: int = 4,
        nhl_acquirer: Callable[..., dict] | None = None,
        requested_periods: list[int] | None = None) -> dict:
    now = clock or datetime.now(timezone.utc)
    target = Path(output_dir) if output_dir is not None else OUTPUT_DIR
    raw = Path(raw_dir) if raw_dir is not None else RAW_DIR
    manifest_path = target/'PeriodScoringAudit'/('request_manifest.json' if requested_periods is not None else 'sync_manifest.json')
    league = str(league_id or get_workspace_value('league_id') or '')
    year = season if season is not None else get_workspace_value('season')
    team_count = expected_teams if expected_teams is not None else get_workspace_value('team_count')
    manifest = {'schema': 'athena.period_scoring_audit_manifest.v1',
                'league_id': league, 'season': str(year or ''),
                'status': 'unavailable', 'periods': {}, 'attempted_count': 0,
                'numeric_complete_periods': 0, 'fully_identity_complete_periods': 0,
                'audited_at': now.isoformat(),
                'audit_scope': 'explicit_request' if requested_periods is not None else 'sync_recent_completed',
                'interpretation': 'Numeric comparison only; period roster ACTIVE designation does not prove game-effective Fantrax credit'}
    try:
        if now.tzinfo is None or type(max_periods) is not int or not 1 <= max_periods <= 8:
            raise ValueError('Aware clock and bounded period range required')
        if not league.isalnum() or not str(year).isdigit():
            raise ValueError('Missing valid Fantrax league ID or season')
        if team_count is not None:
            team_count = int(team_count)
            if team_count < 1:
                raise ValueError('Expected team count must be positive')
        if league_info is None:
            league_info = json.loads((raw/'league_info.json').read_text(encoding='utf-8'))
        # Use provider timestamps where possible. A test clock is converted to
        # a date-only resolver only when explicitly injected; no period is
        # treated as complete merely because an archive exists.
        calendar = resolve_unified_period(league_info, at=now)
        if calendar.get('status') != 'calendar_closed' or type(calendar.get('period')) is not int:
            raise ValueError('No authenticated elapsed Fantrax period calendar')
        if calendar.get('boundary_kind') not in ('points_based_roster_period', 'scoring'):
            raise ValueError('Roster calendar alone cannot establish a scoring period')
        last = calendar['period']
        # Period one has no independent season-start baseline unless one is
        # provided; run only periods with verifiable prior snapshots.
        if requested_periods is not None:
            if (not isinstance(requested_periods, list) or not requested_periods
                or len(requested_periods) > 8 or any(type(p) is not int or p < 1 for p in requested_periods)):
                raise ValueError('Invalid bounded requested scoring periods')
            periods = sorted(set(requested_periods))
        else:
            periods = list(range(max(2, last-max_periods+1), last+1))
        if not periods:
            raise ValueError('No period with a preceding official standings baseline')
        manifest['attempted_count'] = len(periods)
        # Authentication is optional. Archived snapshots remain usable offline.
        if client_factory is None:
            from Providers.Fantrax.fantrax_client import FantraxClient
            client_factory = FantraxClient
        client = None
        fetch_standings = None
        try:
            client = client_factory(league_id=league, season=year)
            if bool(getattr(client, 'has_cookie_auth', lambda: False)()):
                fetch_standings = lambda period: client.get_standings(period)
        except (ValueError, OSError, TypeError):
            pass
        for period in periods:
            entry = {'status': 'source_unavailable', 'numeric_matched_teams': 0,
                     'identity_complete_teams': 0, 'team_count': 0,
                     'unmatched_active_ids': [], 'point_discrepancies': [], 'reason': ''}
            try:
                if period < 2:
                    raise ValueError('Period one has no verified preceding standings baseline')
                if period > last:
                    raise ValueError('Requested period has not closed on the provider calendar')
                bounds = calendar.get('schedule', {}).get(period) or {}
                if not bounds.get('start_at') or not bounds.get('end_at'):
                    raise ValueError('Period has no precise verified start/end instants')
                snapshot = acquire_period_rosters(
                    league_id=league, season=year, period=period,
                    expected_teams=team_count, output_dir=target,
                    client_factory=client_factory, clock=now,
                    max_cache_age=timedelta(days=2))
                if not snapshot.get('verified'):
                    raise ValueError('Period roster: '+str(snapshot.get('reason') or snapshot.get('status')))
                ensure_period_snapshots(target, league_id=league, season=int(year),
                    period=period, expected_teams=team_count, fetch=fetch_standings)
                standings = compare_archived(target, league, year, period)
                if standings.get('status') != 'compared':
                    raise ValueError('Cumulative standings baseline missing or invalid')
                boundary = {'status': 'verified_boundary',
                            'boundary_kind': calendar['boundary_kind'],
                            'start_at': bounds['start_at'], 'end_at': bounds['end_at']}
                fetch_nhl = nhl_acquirer or acquire_nhl_period_production
                nhl = fetch_nhl(league_id=league, season=year, period=period,
                                boundary=boundary, period_rosters=snapshot,
                                client_factory=nhl_client_factory,
                                output_dir=target, clock=now)
                if not nhl.get('verified'):
                    raise ValueError('NHL period production: '+str(nhl.get('reason') or nhl.get('status')))
                attribution = reconcile_period_points(snapshot, nhl, standings)
                if not attribution.get('teams'):
                    raise ValueError('Scoring attribution unavailable: '+str(attribution.get('reason')))
                write_period_audit(target, league, year, period, attribution, clock=now)
                entry.update(status='numeric_complete' if attribution['numeric_matched_teams'] == len(attribution['teams']) else 'partial',
                             numeric_matched_teams=attribution['numeric_matched_teams'],
                             identity_complete_teams=attribution['fully_reconciled_teams'],
                             team_count=attribution['team_count'],
                             unmatched_active_ids=attribution.get('unmatched_active_ids', []),
                             point_discrepancies=[{'team_id':t['team_id'], 'team_name':t['team_name'],
                                                   'difference':t['difference'],
                                                   'unmatched_active_ids':t['unmatched_active_ids']}
                                                  for t in attribution['teams'] if t['status'] == 'discrepancy'])
                if attribution['numeric_matched_teams'] == len(attribution['teams']):
                    manifest['numeric_complete_periods'] += 1
                if attribution['fully_reconciled_teams'] == len(attribution['teams']):
                    manifest['fully_identity_complete_periods'] += 1
            except (ValueError, KeyError, OSError, TypeError) as exc:
                entry['reason'] = str(exc)[:240]
            except Exception as exc:
                entry['reason'] = f'{type(exc).__name__} verifying scoring evidence'
            manifest['periods'][str(period)] = entry
        statuses = {p['status'] for p in manifest['periods'].values()}
        manifest['status'] = ('numeric_complete' if statuses == {'numeric_complete'}
                              else 'partial' if any(s in ('numeric_complete', 'partial') for s in statuses)
                              else 'source_unavailable')
    except (ValueError, OSError, KeyError, TypeError) as exc:
        manifest['reason'] = str(exc)[:240]
    except Exception as exc:
        manifest['reason'] = f'{type(exc).__name__} configuring period scoring audit'
    _save_json(manifest_path, manifest)
    return manifest


if __name__ == '__main__':
    m = run()
    print(f"Period scoring audits: {m['status']} "
          f"({m['numeric_complete_periods']}/{m['attempted_count']} numerically complete)")
