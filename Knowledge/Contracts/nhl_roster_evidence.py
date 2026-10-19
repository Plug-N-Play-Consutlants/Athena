"""Read-only NHL roster acquisition and independent identity reconciliation.

The NHL roster endpoint does not provide contract AAV, LTIR relief, retained
salary or a cap accounting ledger. Roster membership is not cap-roster status.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
from typing import Any, Mapping

from Knowledge.Contracts.cap_snapshot_acquisition import MAX_SNAPSHOT_BYTES

_NHL_ORIGIN = 'https://api-web.nhle.com'
_TEAM = re.compile(r'^[A-Z]{3}$')
_GROUPS = ('forwards', 'defensemen', 'goalies')


@dataclass(frozen=True)
class NHLRosterEvidence:
    team_id: str
    endpoint: str
    acquired_at: str
    players: tuple[tuple[str, str, str], ...]  # NHL id, name, roster grouping

    @property
    def player_ids(self) -> frozenset[str]:
        return frozenset(p[0] for p in self.players)


def parse_nhl_roster(payload: Mapping[str, Any], *, team_id: str,
                     acquired_at: str, endpoint: str) -> NHLRosterEvidence:
    if not isinstance(payload, Mapping):
        raise ValueError('NHL roster must be a JSON object')
    seen = set()
    players = []
    for group in _GROUPS:
        entries = payload.get(group)
        if not isinstance(entries, list):
            raise ValueError(f'NHL roster missing {group} list')
        for entry in entries:
            if not isinstance(entry, Mapping) or type(entry.get('id')) is not int or entry['id'] <= 0:
                raise ValueError('NHL roster contains invalid player identity')
            player_id = str(entry['id'])
            if player_id in seen:
                raise ValueError('NHL roster contains duplicate player ID')
            seen.add(player_id)
            def name(part):
                value = entry.get(part)
                if isinstance(value, Mapping):
                    return str(value.get('default') or '').strip()
                return str(value or '').strip()
            full_name = ' '.join(filter(None, (name('firstName'), name('lastName'))))
            if not full_name:
                raise ValueError('NHL roster player lacks name')
            players.append((player_id, full_name, group))
    return NHLRosterEvidence(team_id, endpoint, acquired_at, tuple(players))


def acquire_nhl_roster(team_id: str, *, transport=None,
                       acquired_at: str | None = None) -> NHLRosterEvidence:
    """Acquire a public NHL roster, with a fixed host and strict team code.

    This endpoint is an unofficially documented NHL website API; availability
    and permitted usage must be evaluated in the deployment environment.
    """
    if not isinstance(team_id, str) or not _TEAM.fullmatch(team_id):
        raise ValueError('NHL team must be an uppercase three-letter code')
    endpoint = f'{_NHL_ORIGIN}/v1/roster/{team_id}/current'
    if transport is None:
        import requests
        transport = requests.get
    response = transport(endpoint, timeout=15, allow_redirects=False,
                         headers={'Accept': 'application/json', 'User-Agent': 'AthenaEngine-roster-evidence/1'})
    if response.status_code != 200:
        raise ValueError(f'NHL roster HTTP {response.status_code}')
    if len(response.content) > MAX_SNAPSHOT_BYTES:
        raise ValueError('NHL roster response exceeds size limit')
    try:
        payload = json.loads(response.content)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError('Invalid NHL roster JSON') from exc
    acquired_at = acquired_at or datetime.now(timezone.utc).isoformat()
    return parse_nhl_roster(payload, team_id=team_id, acquired_at=acquired_at, endpoint=endpoint)


def reconcile_contract_roster(obligations: Mapping[str, Any], roster: NHLRosterEvidence) -> dict:
    """Cross-check NHL IDs, never infer cap completeness from a roster match.

    A feed must explicitly supply `nhl_player_id` for active-roster SPC rows.
    An NHL roster does not certify cap accounting status, AAV or completeness.
    """
    if obligations.get('team_id') != roster.team_id:
        raise ValueError('Cross-team roster reconciliation forbidden')
    rows = obligations.get('obligations')
    if not isinstance(rows, list):
        raise ValueError('Missing itemized contract obligations')
    claimed = set()
    unknown = []
    missing_ids = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError('Invalid obligation row')
        if row.get('status') != 'active_roster_spc':
            continue
        identifier = row.get('nhl_player_id')
        if type(identifier) is not int or identifier <= 0:
            missing_ids.append(str(row.get('subject_id', 'unknown')))
            continue
        player_id = str(identifier)
        if player_id in claimed:
            raise ValueError('Duplicate active-roster SPC NHL player ID')
        claimed.add(player_id)
        if player_id not in roster.player_ids:
            unknown.append(player_id)
    return {'team_id': roster.team_id, 'roster_count': len(roster.players),
            'matched_count': len(claimed & roster.player_ids),
            'roster_without_active_spc': sorted(roster.player_ids - claimed),
            'spc_not_on_roster': sorted(unknown),
            'spc_missing_nhl_id': sorted(missing_ids),
            'cap_ledger_complete': False,
            'note': 'Roster comparison cannot certify cap obligations, LTIR or contract status.'}
