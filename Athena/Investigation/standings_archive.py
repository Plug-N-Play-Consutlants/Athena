"""Validated, provenance-preserving historical league standings archive.

Provider-specific extraction is intentionally separate: never guess at an
unverified Fantrax payload shape or manufacture a complete standings table.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from Athena.Investigation.period_standings import acquire_periods


def validate_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(snapshot, dict):
        raise ValueError('standings snapshot must be an object')
    for field in ('league_id', 'season', 'period', 'source'):
        if snapshot.get(field) in (None, ''):
            raise ValueError(f'missing {field}')
    if type(snapshot['period']) is not int or snapshot['period'] < 1:
        raise ValueError('invalid period')
    if snapshot.get('timeframe') != 'FROM_SEASON_START':
        raise ValueError('only cumulative end-of-period standings are accepted')
    if snapshot.get('complete') is not True:
        raise ValueError('incomplete league standings must not be archived as complete')
    teams = snapshot.get('teams')
    if not isinstance(teams, list) or not teams:
        raise ValueError('missing team rows')
    ids = set()
    ranks = []
    for row_number, row in enumerate(teams, start=1):
        if not isinstance(row, dict):
            raise ValueError(f'invalid team row {row_number}')
        tid = str(row.get('team_id') or '').strip()
        rank, points = row.get('rank'), row.get('points')
        if not tid:
            raise ValueError(f'missing team identity at row {row_number}')
        if tid in ids:
            raise ValueError(f'duplicate team identity at row {row_number}')
        if type(rank) is not int or not 1 <= rank <= len(teams):
            raise ValueError(f'invalid standings rank at row {row_number}: {rank!r}')
        if type(points) not in (int, float) or not __import__('math').isfinite(points):
            raise ValueError(f'invalid points at row {row_number}')
        ids.add(tid)
        ranks.append(rank)
    # Standings may contain legitimate tied positions. Both dense (1,2,2,3)
    # and competition (1,2,2,4) ranking are valid; uniqueness is for team IDs.
    # Reject impossible gaps, but do not require a 1..N permutation.
    rank_counts = {rank: ranks.count(rank) for rank in set(ranks)}
    ordered = sorted(rank_counts)
    if ordered[0] != 1:
        raise ValueError('standings ranking has no first-place team')
    for previous, current in zip(ordered, ordered[1:]):
        if current > previous + rank_counts[previous]:
            raise ValueError(f'standings ranking has an unexplained gap before rank {current}')
    return snapshot


def snapshot_path(output: Path, league_id: str, season: str | int, period: int) -> Path:
    if not str(league_id).isalnum() or not str(season).isdigit() or type(period) is not int or period<1:
        raise ValueError('invalid archive identity')
    return Path(output)/'Standings'/str(league_id)/str(season)/f'period_{period:03d}.json'


def save_snapshot(output: Path, snapshot: dict[str, Any]) -> Path:
    validate_snapshot(snapshot)
    path=snapshot_path(output,str(snapshot['league_id']),snapshot['season'],snapshot['period'])
    path.parent.mkdir(parents=True,exist_ok=True)
    payload=dict(snapshot)
    payload.setdefault('acquired_at',datetime.now(timezone.utc).isoformat())
    # Preserve replaced versions to permit investigation of retroactive corrections.
    if path.exists():
        existing=json.loads(path.read_text(encoding='utf-8'))
        if existing.get('teams') != payload.get('teams'):
            revisions=path.parent/'revisions';revisions.mkdir(exist_ok=True)
            index=1
            while (revisions/f'{path.stem}_revision_{index:03d}.json').exists(): index+=1
            (revisions/f'{path.stem}_revision_{index:03d}.json').write_text(json.dumps(existing,indent=2),encoding='utf-8')
    path.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8')
    return path


def load_snapshot(output: Path, league_id: str, season: str | int, period: int) -> dict[str, Any]:
    path=snapshot_path(output,league_id,season,period)
    snapshot=json.loads(path.read_text(encoding='utf-8'))
    validate_snapshot(snapshot)
    if str(snapshot['league_id'])!=str(league_id) or str(snapshot['season'])!=str(season) or snapshot['period']!=period:
        raise ValueError('snapshot identity mismatch')
    return snapshot


def compare_archived(output: Path, league_id: str, season: str | int, period: int, *, season_to_date: bool=False) -> dict[str, Any]:
    return acquire_periods(period,lambda p: load_snapshot(output,league_id,season,p),season_to_date=season_to_date)
