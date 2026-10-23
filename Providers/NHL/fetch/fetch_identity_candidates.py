"""Optional current-season NHL identity candidates for Fantrax identity resolution.

Do not replace the older season skater summary (used by other analytical
paths). Reuse a persisted identity snapshot if the public source is offline.
Network failures are a clearly reported optional capability gap.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Athena.workspace import get_workspace_value
from Core.project_paths import RAW_DIR, OUTPUT_DIR


def _season_id(value) -> str:
    season = str(value or '').strip()
    if re.fullmatch(r'20\d{6}', season):
        first, second = int(season[:4]), int(season[4:])
        if second == first + 1:
            return season
    if re.fullmatch(r'20\d{2}', season):
        return season + str(int(season) + 1)
    raise ValueError('Unsupported workspace season for NHL identity refresh')


def run(*, season=None, client_factory=None, raw_dir: Path | None = None,
        output_dir: Path | None = None, clock: datetime | None = None,
        seasons_back: int = 0) -> dict:
    now = clock or datetime.now(timezone.utc)
    raw = Path(raw_dir) if raw_dir is not None else RAW_DIR
    output = Path(output_dir) if output_dir is not None else OUTPUT_DIR
    source = raw / 'nhl_identity_candidates.json'
    manifest = output / 'nhl_identity_refresh_status.json'
    result = {'schema': 'athena.nhl_identity_refresh.v1', 'status': 'unavailable',
              'season_id': '', 'records': 0, 'refreshed_at': now.isoformat(), 'reason': ''}
    try:
        season_id = _season_id(season if season is not None else get_workspace_value('season'))
        result['season_id'] = season_id
        if client_factory is None:
            from Providers.NHL.nhl_client import NHLClient
            client_factory = NHLClient
        if type(seasons_back) is not int or not 0 <= seasons_back <= 3:
            raise ValueError('Historical identity source depth must be 0..3 NHL seasons')
        client = client_factory()
        current_start = int(season_id[:4])
        seasons = [f'{year}{year+1}' for year in range(current_start-seasons_back,current_start+1)]
        rows, counts = [], {}
        # Oldest -> latest. The resolver deduplicates permanent NHL IDs and
        # prefers the most recent club/name metadata without equating club to ID.
        for candidate_season in seasons:
            payload = client.get_skater_summary(candidate_season, game_type_id=2, limit=-1)
            if not isinstance(payload, dict) or not isinstance(payload.get('data'), list):
                raise ValueError(f'NHL identity candidates missing for season {candidate_season}')
            data = payload['data']
            if not data or (type(payload.get('total')) is int and payload['total'] != len(data)):
                raise ValueError(f'NHL candidate response incomplete for season {candidate_season}')
            for row in data:
                if not isinstance(row, dict) or not str(row.get('playerId') or '').isdigit():
                    raise ValueError('NHL identity candidate lacks permanent player ID')
                if row.get('seasonId') is not None and str(row['seasonId']) != candidate_season:
                    raise ValueError(f'NHL returned candidates from wrong season {candidate_season}')
            counts[candidate_season] = len(data)
            rows.extend(data)
        candidate = {'schema': 'athena.nhl_identity_candidates.v2', 'season_id': season_id,
                     'source_seasons': seasons, 'source_counts': counts,
                     'fetched_at': now.isoformat(), 'total': len(rows), 'data': rows}
        source.parent.mkdir(parents=True, exist_ok=True)
        temp = source.with_suffix('.tmp')
        temp.write_text(json.dumps(candidate, ensure_ascii=False), encoding='utf-8')
        temp.replace(source)
        result.update(status='verified', records=len(rows), source_seasons=seasons, unique_nhl_players=len({str(r['playerId']) for r in rows}))
    except (OSError, ValueError, TypeError, KeyError, ImportError) as exc:
        result['reason'] = str(exc)[:180]
    except Exception as exc:
        # Do not expose private provider URLs/tokens in diagnostics.
        result['reason'] = f'{type(exc).__name__} refreshing NHL identity candidates'
    manifest.parent.mkdir(parents=True, exist_ok=True)
    temp = manifest.with_suffix('.tmp')
    temp.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(manifest)
    return result


if __name__ == '__main__':
    status = run(seasons_back=2)
    print(f"NHL identity candidate refresh: {status['status']} ({status['records']} identities)")
