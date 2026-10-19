"""Conservative Cap Freeze -> NHL roster -> independent SPC evidence bridge.

An observed publisher cap hit is NOT a verified SPC AAV. Verification requires
an independently sourced contract record with a stable NHL player ID and an
explicitly verified cap-accounting status. No automatic source trust escalation.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Mapping
import re
import unicodedata

from Knowledge.Contracts.capfreeze_observations import CapFreezeObservation
from Knowledge.Contracts.nhl_roster_evidence import NHLRosterEvidence
from Knowledge.Contracts.contract_obligation_acquisition import ingest_contract_obligations
from Reasoning.Cap.cba_obligation_calculator import CapRuleContext


def _name(value: str) -> str:
    normalized = unicodedata.normalize('NFKD', value)
    normalized = ''.join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r'[^a-z0-9]+', '', normalized.casefold())


@dataclass(frozen=True)
class ContractVerification:
    team_id: str
    season: str
    matched: tuple[tuple[str, str, int], ...]  # NHL id, player, verified AAV
    unmatched_observations: tuple[str, ...]
    roster_without_observation: tuple[str, ...]
    discrepancies: tuple[str, ...]
    obligations: tuple[dict, ...]
    ledger_complete: bool = False


def verify_contract_observations(observed: CapFreezeObservation,
                                 roster: NHLRosterEvidence,
                                 independent_contracts: list[Mapping[str, Any]],
                                 *, as_of: str) -> ContractVerification:
    """Corroborate *active roster* observations, without certifying cap coverage.

    Independent contracts must explicitly identify an NHL player, the original
    evidence, verified AAV and roster/SPC status. A publisher's estimate alone
    never qualifies. Name collisions and ambiguous identity matches fail closed.
    """
    day = date.fromisoformat(as_of)
    if observed.team_id != roster.team_id or not observed.season.startswith(str(day.year)) and not (day.month <= 6 and observed.season.startswith(str(day.year - 1))):
        raise ValueError('Team or season mismatch')
    if day < date.fromisoformat(observed.source_as_of):
        raise ValueError('Cannot verify before publisher snapshot date')
    roster_by_name: dict[str, list[tuple[str, str]]] = {}
    for nhl_id, name, _ in roster.players:
        roster_by_name.setdefault(_name(name), []).append((nhl_id, name))
    by_id: dict[str, Mapping[str, Any]] = {}
    for record in independent_contracts:
        if not isinstance(record, Mapping):
            raise ValueError('Contract record must be an object')
        identifier = record.get('nhl_player_id')
        if type(identifier) is not int or identifier <= 0 or str(identifier) in by_id:
            raise ValueError('Missing or duplicate independent NHL contract ID')
        by_id[str(identifier)] = record
    matched, unmatched, discrepancies, obligations = [], [], [], []
    observed_ids = set()
    for row in observed.contracts:
        if row.category != 'active_roster_observation':
            continue
        candidates = roster_by_name.get(_name(row.player), [])
        if len(candidates) != 1:
            unmatched.append(row.player)
            continue
        nhl_id, roster_name = candidates[0]
        if nhl_id in observed_ids:
            raise ValueError('Duplicate publisher observations for NHL identity')
        observed_ids.add(nhl_id)
        record = by_id.get(nhl_id)
        if not record:
            unmatched.append(row.player)
            continue
        if record.get('team_id') != observed.team_id or _name(str(record.get('player_name', ''))) != _name(roster_name):
            discrepancies.append(f'{row.player}: independent identity/team disagreement')
            continue
        if record.get('contract_verified') is not True or record.get('status_verified') is not True or record.get('roster_status_verified') is not True:
            discrepancies.append(f'{row.player}: unverified contract or roster status')
            continue
        aav = record.get('aav')
        if type(aav) is not int or aav < 0:
            raise ValueError('Independent AAV must be nonnegative integer dollars')
        if not all(isinstance(record.get(key), str) and record[key].strip() for key in ('source_id', 'provenance', 'rule_reference', 'effective_from', 'effective_to')):
            raise ValueError('Missing independent contract provenance or rule')
        if not date.fromisoformat(record['effective_from']) <= day <= date.fromisoformat(record['effective_to']):
            discrepancies.append(f'{row.player}: independent contract not effective on evaluation date')
            continue
        if row.season_cap_hit is None or row.season_cap_hit != aav:
            discrepancies.append(f'{row.player}: publisher cap hit differs from independent AAV')
            continue
        matched.append((nhl_id, roster_name, aav))
        obligations.append(dict(team_id=observed.team_id, nhl_player_id=int(nhl_id),
                                subject_id=f'nhl:{nhl_id}', evidence_id=f'spc:{observed.team_id}:{nhl_id}:{as_of}',
                                source_id=record['source_id'], provenance=record['provenance'],
                                rule_reference=record['rule_reference'],
                                effective_from=record['effective_from'], effective_to=record['effective_to'],
                                aav=aav, status='active_roster_spc', contract_verified=True,
                                status_verified=True, roster_status_verified=True))
    return ContractVerification(observed.team_id, observed.season, tuple(matched),
                                tuple(unmatched), tuple(name for nhl_id, name, _ in roster.players if nhl_id not in observed_ids),
                                tuple(discrepancies), tuple(obligations))


def ingest_verified_contract_subset(result: ContractVerification, *, as_of: str,
                                    cba_rules: CapRuleContext | None = None):
    """Ingest corroborated contracts; intentionally remains a partial ledger."""
    return ingest_contract_obligations(dict(team_id=result.team_id, as_of=as_of,
        snapshot_id=f'verified-subset:{result.team_id}:{as_of}',
        sources=[{'id': source_id, 'retrieved_at': datetime.now(timezone.utc).isoformat()} for source_id in sorted({row['source_id'] for row in result.obligations})],
        roster_verified=False, obligations=list(result.obligations)), cba_rules=cba_rules)
