"""Provider-authoritative player fantasy scoring for period editorial.

NHL points and fantasy points are independent concepts.  A fantasy provider
owns scoring and official results for its league; this module consumes only a
period-attributed provider ledger, never NHL G+A or inferred roster scoring.

Adapters must normalize their own responses to PeriodFantasyPoints/v1 and may
persist the verified record at the documented path.  No league-specific point
weights or speculative Fantrax API arguments are applied here.
"""
from __future__ import annotations

import json
import math
from pathlib import Path


def _nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def _points(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def normalize_provider_period(payload: dict, *, provider: str, league: str,
                              season: int | str, period: int) -> dict:
    """Fail closed if a purported credited ledger has ambiguous provenance."""
    if not _nonempty(provider) or not _nonempty(str(league)) or type(period) is not int or period < 1:
        raise ValueError('Invalid provider ledger request identity')
    if not isinstance(payload, dict) or payload.get('schema') != 'athena.provider_period_fantasy_points.v1':
        raise ValueError('Not a normalized provider fantasy-points ledger')
    expected = {'provider': provider, 'league_id': str(league), 'season': str(season), 'period': period}
    for key, value in expected.items():
        if payload.get(key) != value:
            raise ValueError(f'Provider fantasy ledger {key} mismatch')
    if payload.get('verified') is not True or payload.get('status') != 'provider_credited_period':
        raise ValueError('Provider-period fantasy credit has not been verified')
    if not _nonempty(payload.get('source')):
        raise ValueError('Provider source provenance missing')
    records = payload.get('records')
    if not isinstance(records, list) or not records:
        raise ValueError('No provider player scoring records')
    seen, normalized = set(), []
    for row in records:
        if not isinstance(row, dict):
            raise ValueError('Invalid provider player scoring record')
        pid, team_id = str(row.get('player_id') or ''), str(row.get('team_id') or '')
        name, team = row.get('player_name'), row.get('team_name')
        if not pid or not team_id or not _nonempty(name) or not _nonempty(team):
            raise ValueError('Provider player or historical team identity missing')
        if pid in seen:
            raise ValueError('Ambiguous duplicate player-period fantasy credit')
        seen.add(pid)
        if not _points(row.get('fantasy_points')):
            raise ValueError('Invalid provider fantasy-points value')
        # Player production and team credit are only equivalent when the
        # source contract explicitly declares credited (not season YTD) FPts.
        if row.get('credit_basis') != 'provider_period_credited':
            raise ValueError('Player point measure is not proven credited period FPts')
        normalized.append({'player_id': pid, 'player_name': name.strip(),
                           'team_id': team_id, 'team_name': team.strip(),
                           'fantasy_points': row['fantasy_points']})
    normalized.sort(key=lambda x: (-x['fantasy_points'], x['player_name']))
    return {'status': 'provider_credited_period', 'provider': provider,
            'period': period, 'source': payload['source'], 'records': normalized}


def load_provider_period(root: Path, provider: str, league: str,
                         season: int | str, period: int) -> dict:
    """Use a recorded league-scoped provider ledger, never a raw NHL artifact."""
    if not _nonempty(provider) or not provider.replace('_', '').replace('-', '').isalnum():
        return {'status': 'provider_not_configured', 'period': period}
    if not str(league).isalnum() or not str(season).replace('-', '').isalnum() or type(period) is not int or not 1 <= period <= 999:
        return {'status': 'invalid_identity', 'period': period}
    path = Path(root) / 'PeriodFantasyPoints' / provider / str(league) / str(season) / f'period_{period:03d}.json'
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError, UnicodeError):
        return {'status': 'provider_period_unavailable', 'period': period}
    try:
        return normalize_provider_period(payload, provider=provider, league=league, season=season, period=period)
    except ValueError:
        return {'status': 'provider_period_unverified', 'period': period}


def analyze_provider_points(root: Path, *, provider: str, league: str,
                            season: int | str, periods: list[int], team_ids: set[str]) -> dict:
    reports = []
    for period in periods:
        report = load_provider_period(root, provider, league, season, period)
        if report['status'] == 'provider_credited_period':
            # Provider-owned player ledger can contain only teams with scoring
            # observations; it cannot fabricate owners absent from standings.
            if any(r['team_id'] not in team_ids for r in report['records']):
                report = {'status': 'unknown_historical_team', 'period': period}
            else:
                report['leaders'] = [r for r in report['records'] if r['fantasy_points'] > 0][:5]
        reports.append(report)
    return {'status': 'provider_scoring_assessed', 'provider': provider, 'periods': reports,
            'available_periods': [r['period'] for r in reports if r['status'] == 'provider_credited_period'],
            'unavailable_periods': [r['period'] for r in reports if r['status'] != 'provider_credited_period']}
