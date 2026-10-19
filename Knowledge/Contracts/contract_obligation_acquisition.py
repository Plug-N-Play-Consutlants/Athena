"""Acquire itemized contract/roster observations and derive bounded NHL cap charges.

The upstream feed is an explicitly authorized HTTPS JSON endpoint, not a guessed
NHL/PuckPedia API. This adapter does not certify complete payroll or LTIR relief.
Raw AAV is a cap charge only for explicitly verified standard active-roster SPCs;
all other obligations require a separately verified, rule-derived cap charge.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from Knowledge.Contracts.cap_snapshot_acquisition import CapSnapshotSource, acquire_cap_snapshot
from Knowledge.Contracts.cap_evidence_ingestion import CapEvidenceImport, ingest_cap_snapshot
from Reasoning.Cap.canonical_ledger import CHARGE_CLASSES
from Reasoning.Cap.cba_obligation_calculator import CapRuleContext, calculate_contract_charge


def _dollars(value: Any, field: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f'{field} must be a nonnegative integer-dollar amount')
    return value


def build_cap_snapshot_from_obligations(payload: Mapping[str, Any], *,
                                        cba_rules: CapRuleContext | None = None) -> dict:
    """Transform evidence-backed obligations; never self-certify domain coverage.

    Required: team_id, as_of, snapshot_id, sources, obligations, roster_verified.
    Obligations: evidence_id, subject_id, source_id, provenance, effective_from,
    effective_to, status, aav or verified_cap_charge, rule_reference.

    `active_roster_spc` can use AAV as standard cap charge when both roster and
    contract status are explicitly evidenced. All other statuses require an
    externally rule-verified cap charge and its specific charge_class.
    """
    if not isinstance(payload, Mapping):
        raise ValueError('Contract evidence must be an object')
    team_id, as_of = str(payload['team_id']).strip(), str(payload['as_of'])
    date.fromisoformat(as_of)
    if not team_id or type(payload['roster_verified']) is not bool:
        raise ValueError('Team and explicit roster verification required')
    observations = payload['obligations']
    if not isinstance(observations, list):
        raise ValueError('Obligations must be a list')
    charges = []
    for row in observations:
        if not isinstance(row, Mapping):
            raise ValueError('Obligation must be an object')
        if row.get('team_id') != team_id:
            raise ValueError('Cross-team obligation cannot be included')
        status = row['status']
        if cba_rules is not None and status in ('active_roster_spc', 'retained_salary', 'buried_contract'):
            charge = calculate_contract_charge(row, cba_rules)
            charges.append(dict(evidence_id=charge.evidence_id, subject_id=charge.subject_id,
                                source_id=row['source_id'], provenance=row['provenance'],
                                effective_from=charge.effective_from, effective_to=charge.effective_to,
                                rule_reference=charge.rule_reference, charge_class=charge.charge_class,
                                amount=charge.amount))
            continue
        if status == 'active_roster_spc':
            if row.get('roster_status_verified') is not True or row.get('contract_verified') is not True:
                raise ValueError('AAV charge requires verified roster and SPC status')
            amount = _dollars(row['aav'], 'aav')
            charge_class = 'standard_player_contract'
        else:
            if status not in ('retained_salary', 'buried_contract', 'buyout_or_termination',
                              'bonus_overage', 'other_cap_obligation'):
                raise ValueError('Unsupported obligation status')
            if row.get('cba_charge_verified') is not True:
                raise ValueError('Nonstandard obligations require CBA-verified charges')
            amount = _dollars(row['verified_cap_charge'], 'verified_cap_charge')
            charge_class = {'retained_salary': 'retained_salary',
                            'buried_contract': 'buried_contract_charge',
                            'buyout_or_termination': 'buyout_or_termination_charge',
                            'bonus_overage': 'bonus_overage',
                            'other_cap_obligation': 'other_cap_charge'}[status]
        if charge_class not in CHARGE_CLASSES:
            raise ValueError('Unsupported charge class')
        charges.append({key: row[key] for key in ('evidence_id', 'subject_id', 'source_id',
                       'provenance', 'effective_from', 'effective_to', 'rule_reference')}
                       | {'charge_class': charge_class, 'amount': amount})
    # Ingest as PARTIAL regardless of publisher assertions. A full team cap
    # requires independently verified roster, adjustments, and relief accounting.
    return dict(team_id=team_id, as_of=as_of, snapshot_id=payload['snapshot_id'],
                sources=payload['sources'], charges=charges, verified_domains=[],
                roster_verified=False, published_cap_charge_total=payload.get('published_cap_charge_total'))


def ingest_contract_obligations(payload: Mapping[str, Any], *,
                                cba_rules: CapRuleContext | None = None) -> CapEvidenceImport:
    return ingest_cap_snapshot(build_cap_snapshot_from_obligations(payload, cba_rules=cba_rules))


def acquire_contract_obligations(source: CapSnapshotSource, *, transport=None,
                                 expected_team_id: str | None = None,
                                 expected_as_of: str | None = None,
                                 cba_rules: CapRuleContext | None = None) -> CapEvidenceImport:
    """Fetch a raw-obligation feed using the existing hardened snapshot transport.

    Reuse the existing HTTPS boundary by adapting the fetched raw object at the
    transport boundary. Its normal schema/identity/size checks remain in force.
    """
    import json
    if transport is None:
        import requests
        transport = requests.get

    def transform(url, **kwargs):
        response = transport(url, **kwargs)
        if response.status_code != 200:
            return response
        # Bound response before parsing (same limit as the existing boundary).
        from Knowledge.Contracts.cap_snapshot_acquisition import MAX_SNAPSHOT_BYTES
        if len(response.content) > MAX_SNAPSHOT_BYTES:
            raise ValueError('Contract obligations exceed size limit')
        try:
            raw = json.loads(response.content)
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError('Invalid contract obligations JSON') from exc
        canonical = build_cap_snapshot_from_obligations(raw, cba_rules=cba_rules)
        from types import SimpleNamespace
        return SimpleNamespace(status_code=200, content=json.dumps(canonical).encode('utf-8'))

    return acquire_cap_snapshot(source, transport=transform, expected_team_id=expected_team_id,
                                expected_as_of=expected_as_of)
