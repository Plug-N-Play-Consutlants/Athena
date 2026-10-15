"""Period standings acquisition using the configured Fantrax workspace.

Transport and canonicalization are separate. Unknown provider shapes are not
silently coerced into league standings; the error identifies the contract gap.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from Athena.Investigation.standings_archive import load_snapshot, save_snapshot, validate_snapshot
from Athena.Investigation.period_standings import required_periods


def resolve_league_context(profile: dict | None, index: dict | None = None) -> tuple[str, int]:
    profile, index = profile or {}, index or {}
    league_id = str(profile.get('league_id') or index.get('league_id') or '').strip()
    season = profile.get('season') or index.get('season')
    if not league_id or not league_id.isalnum() or not str(season or '').isdigit():
        raise ValueError('canonical league profile lacks a valid league ID or season')
    if index.get('league_id') and str(index['league_id']) != league_id:
        raise ValueError('standings archive league ID conflicts with canonical league profile')
    if index.get('season') and int(index['season']) != int(season):
        raise ValueError('standings archive season conflicts with canonical league profile')
    return league_id, int(season)


def normalize_standings(payload: Any, *, league_id: str, season: int, period: int,
                        expected_teams: int | None = None) -> dict:
    """Accept only explicit team IDs, ranks and numeric cumulative points.

    Live Fantrax response layouts must be verified before adding adapters for
    other schemas. In particular, do not infer identity from display names.
    """
    if not isinstance(payload, dict):
        raise ValueError('unrecognized Fantrax standings response: expected object')
    if payload.get('league_id') not in (None, league_id) or payload.get('leagueId') not in (None, league_id):
        raise ValueError('standings response league mismatch')
    if payload.get('period') not in (None, period) or payload.get('scoringPeriod') not in (None, period, str(period)):
        raise ValueError('standings response period mismatch')
    if payload.get('timeframe') not in (None, 'FROM_SEASON_START') or payload.get('timeframeSpan') not in (None, 'FROM_SEASON_START'):
        raise ValueError('standings response is not cumulative')
    # The authenticated API exposes tableList[0].header.cells and rows.
    # Its cells are positional: match their column keys before reading scores.
    # Support the pre-normalized canonical shape for existing integrations.
    rows = payload.get('teams')
    teams = []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError('invalid standings team row')
            team_id = row.get('team_id', row.get('teamId'))
            rank, points = row.get('rank'), row.get('points')
            if team_id in (None, '') or type(rank) is not int or type(points) not in (int, float):
                raise ValueError('unverified standings row: stable team ID, integer rank and numeric points required')
            teams.append({'team_id': str(team_id), 'name': str(row.get('name') or row.get('teamName') or ''),
                          'rank': rank, 'points': points})
    else:
        # A transport may return nested data or a single FXPA response wrapper.
        body = payload
        for _ in range(3):
            if isinstance(body, dict) and isinstance(body.get('tableList'), list):
                break
            if isinstance(body, dict) and isinstance(body.get('responses'), list) and len(body['responses']) == 1:
                body = body['responses'][0]
            elif isinstance(body, dict) and isinstance(body.get('data'), dict):
                body = body['data']
            else:
                break
        tables = body.get('tableList') if isinstance(body, dict) else None
        if not isinstance(tables, list) or not tables or not isinstance(tables[0], dict):
            keys = sorted(str(k) for k in payload.keys())
            raise ValueError(f'unrecognized Fantrax standings response: no tableList/team rows; top-level keys={keys[:12]}')
        table = tables[0]
        headers = (table.get('header') or {}).get('cells')
        table_rows = table.get('rows')
        if not isinstance(headers, list) or not isinstance(table_rows, list):
            raise ValueError('Fantrax standings table lacks header.cells or rows')
        keys = [str(c.get('key') or '') if isinstance(c, dict) else '' for c in headers]
        # Points and pointsFor have different semantics in H2H leagues.
        # Require the explicit standings points column; no silent substitution.
        score_candidates = [key for key in ('fantasyPoints', 'points') if key in keys]
        if not score_candidates:
            raise ValueError(f'Fantrax standings score column unresolved; available keys={keys}')
        # Fantrax points-based fantasy standings expose fantasyPoints; legacy
        # league formats may instead expose points. Never use per-game,
        # points-behind-leader or ordering fields as cumulative scores.
        score_key = score_candidates[0]
        score_index = keys.index(score_key)

        def numeric(value):
            if isinstance(value, dict):
                value = value.get('value', value.get('content'))
            if isinstance(value, str):
                value = value.strip().replace(',', '')
                try:
                    return float(value)
                except ValueError:
                    return None
            return value if type(value) in (int, float) else None

        for row in table_rows:
            if not isinstance(row, dict):
                raise ValueError('invalid Fantrax standings table row')
            fixed = row.get('fixedCells')
            cells = row.get('cells')
            if not isinstance(fixed, list) or len(fixed) < 2 or not isinstance(cells, list):
                raise ValueError('Fantrax standings row lacks fixedCells/team ID or cells')
            first, second = fixed[0], fixed[1]
            if not isinstance(first, dict) or not isinstance(second, dict):
                raise ValueError('Fantrax standings fixed cell is invalid')
            team_id = second.get('teamId')
            raw_rank = first.get('content')
            if isinstance(raw_rank, dict):
                raw_rank = raw_rank.get('content', raw_rank.get('value'))
            try:
                rank = int(str(raw_rank).strip().rstrip('.'))
            except (ValueError, TypeError):
                raise ValueError(f'Fantrax standings rank is not numeric at row {len(teams) + 1}: {str(raw_rank)[:30]!r}') from None
            if not team_id or score_index >= len(cells):
                raise ValueError(f'Fantrax standings row {len(teams) + 1} missing team ID or points column')
            points = numeric(cells[score_index])
            if points is None:
                raise ValueError('Fantrax standings points value is not numeric')
            name = second.get('content', second.get('name', ''))
            if isinstance(name, dict):
                name = name.get('content', name.get('name', ''))
            teams.append({'team_id': str(team_id), 'name': str(name or ''), 'rank': rank, 'points': points})
    if expected_teams and len(teams) != expected_teams:
        raise ValueError(f'incomplete standings: expected {expected_teams} teams, received {len(teams)}')
    return validate_snapshot({'league_id': league_id, 'season': season, 'period': period,
                              'source': 'fantrax_authenticated', 'timeframe': 'FROM_SEASON_START',
                              'complete': True, 'score_column': score_key if not isinstance(rows, list) else 'points', 'teams': teams})


def ensure_period_snapshots(output: Path, *, league_id: str, season: int, period: int,
                            expected_teams: int | None = None, season_to_date: bool = False,
                            fetch: Callable[[int], Any] | None = None) -> dict:
    """Use archived evidence first; acquire only missing periods when a fetcher exists."""
    needed = required_periods(period, season_to_date=season_to_date)
    obtained, missing, errors = [], [], {}
    for p in needed:
        try:
            snapshot = load_snapshot(output, league_id, season, p)
            if expected_teams and len(snapshot['teams']) != expected_teams:
                raise ValueError('archived snapshot team count conflicts with canonical league')
            obtained.append(p)
            continue
        except (OSError, ValueError, KeyError, TypeError) as exc:
            archive_error = str(exc)
        if fetch is None:
            missing.append(p)
            errors[p] = f'archive unavailable: {archive_error}'
            continue
        try:
            snapshot = normalize_standings(fetch(p), league_id=league_id, season=season,
                                           period=p, expected_teams=expected_teams)
            save_snapshot(output, snapshot)
            obtained.append(p)
        except Exception as exc:
            missing.append(p)
            errors[p] = f'{type(exc).__name__}: {exc}'
    return {'requested_periods': needed, 'available_periods': obtained,
            'missing_periods': missing, 'errors': errors}
