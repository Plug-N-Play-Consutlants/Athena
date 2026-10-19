"""Provider-neutral ingestion of dated NHL cap evidence into canonical ledger.

Only explicitly certified domains become verified. A published aggregate is a
reconciliation reference, never a substitute for itemized cap accounting.
Source adapters must supply their own licensed/authorized acquisition mechanism.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping

from Reasoning.Cap.canonical_ledger import (
    CapCharge, LedgerReconciliation, REQUIRED_RECONCILIATION,
)


@dataclass(frozen=True)
class CapEvidenceImport:
    ledger: LedgerReconciliation
    published_total: int | None
    discrepancy: int | None
    source_count: int


def _nonnegative_dollars(value: Any, field: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field} must be nonnegative integer dollars")
    return value


def ingest_cap_snapshot(payload: Mapping[str, Any]) -> CapEvidenceImport:
    """Normalize an acquired, itemized snapshot without inventing missing facts.

    Required snapshot keys: team_id, as_of, snapshot_id, sources, charges,
    verified_domains, roster_verified. Each charge requires evidence_id,
    subject_id, charge_class, amount, effective_from/to, provenance,
    rule_reference. `verified_domains` must be explicitly certified by the
    acquisition/reconciliation process, not inferred from nonempty records.
    """
    team_id = str(payload['team_id']).strip()
    as_of = str(payload['as_of'])
    date.fromisoformat(as_of)
    snapshot_id = str(payload['snapshot_id']).strip()
    sources = payload['sources']
    if not team_id or not snapshot_id or not isinstance(sources, list) or not sources:
        raise ValueError('Team, snapshot ID and at least one documented source are required')
    source_ids = set()
    for source in sources:
        if not isinstance(source, Mapping) or not str(source.get('id', '')).strip() or not str(source.get('retrieved_at', '')).strip():
            raise ValueError('Sources require id and retrieved_at')
        source_ids.add(str(source['id']))
    if len(source_ids) != len(sources):
        raise ValueError('Duplicate source IDs')
    rows = payload['charges']
    if not isinstance(rows, list):
        raise ValueError('Charges must be an itemized list')
    charges = []
    for row in rows:
        if not isinstance(row, Mapping) or str(row.get('source_id', '')) not in source_ids:
            raise ValueError('Each charge must reference a documented source')
        charges.append(CapCharge(
            evidence_id=str(row['evidence_id']), subject_id=str(row['subject_id']),
            charge_class=str(row['charge_class']), amount=_nonnegative_dollars(row['amount'], 'amount'),
            effective_from=str(row['effective_from']), effective_to=str(row['effective_to']),
            provenance=f"{row['source_id']}:{row['provenance']}", rule_reference=str(row['rule_reference']),
        ))
    domains = payload['verified_domains']
    if not isinstance(domains, list) or len(set(domains)) != len(domains):
        raise ValueError('Verified domains must be a unique list')
    if any(x not in REQUIRED_RECONCILIATION for x in domains):
        raise ValueError('Unknown verified domain')
    if type(payload['roster_verified']) is not bool:
        raise ValueError('Roster verification must be explicit boolean')
    relief = payload.get('verified_ltir_relief')
    if relief is not None:
        relief = _nonnegative_dollars(relief, 'verified_ltir_relief')
    ledger = LedgerReconciliation(
        team_id=team_id, as_of=as_of, charges=tuple(charges),
        verified_domains=tuple(domains), roster_verified=payload['roster_verified'],
        source_snapshot=snapshot_id, verified_ltir_relief=relief,
    )
    published = payload.get('published_cap_charge_total')
    if published is not None:
        published = _nonnegative_dollars(published, 'published_cap_charge_total')
    discrepancy = ledger.reconcile(published) if published is not None else None
    return CapEvidenceImport(ledger, published, discrepancy, len(sources))
