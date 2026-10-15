"""Single bounded inquiry-completion assessment shared by Athena entry points.

Execution success, specialist confidence, and source availability are not proof
that an inquiry was answered. Specialist declarations remain observable; evidence
and explicit limitations can conservatively downgrade a declared complete result.
"""
from __future__ import annotations
from typing import Any

STATES = frozenset({'complete', 'partial', 'blocked', 'unverified'})


def _items(value: Any) -> list[Any]:
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value] if isinstance(value, str) and value.strip() else []


def assess_completion(result: Any, *, status: str = 'executed', evidence: Any = None) -> dict[str, Any]:
    if status != 'executed':
        return {'state': 'not_assessed', 'reason': status, 'requirements': [],
                'unresolved': [], 'unresolved_requirements': [],
                'inquiry_answered_verified': False, 'handler_executed': False}
    if not isinstance(result, dict):
        return {'state': 'unverified', 'reason': 'unstructured_specialist_result',
                'requirements': [], 'unresolved': [], 'unresolved_requirements': [],
                'inquiry_answered_verified': False, 'handler_executed': True}
    declared = result.get('inquiry_completion')
    if not isinstance(declared, dict):
        declared = {}
    state = declared.get('state') if declared.get('state') in STATES else 'unverified'
    requirements = _items(declared.get('requirements'))
    unresolved = _items(declared.get('unresolved'))
    for requirement in requirements:
        if isinstance(requirement, dict) and requirement.get('state') not in {'supported', 'satisfied', 'complete', 'verified'}:
            if not any(item == requirement or (isinstance(item, str) and item == str(requirement.get('dimension') or requirement.get('name') or requirement.get('id') or '')) for item in unresolved):
                unresolved.append(requirement)
    gaps: list[str] = []
    if isinstance(evidence, dict):
        for item in _items(evidence.get('missing')):
            label = str(item).strip()
            if label and label not in gaps:
                gaps.append(label)
    for item in _items(result.get('known_limitations')) + _items(result.get('limitations')):
        label = str(item).strip()
        if label and label not in gaps:
            gaps.append(label)
    for item in unresolved:
        label = str(item.get('requirement') or item.get('name') or item.get('id') or item) if isinstance(item, dict) else str(item)
        if label and label not in gaps:
            gaps.append(label)
    if state == 'complete' and gaps:
        state = 'partial'
        reason = 'declared_complete_with_unresolved_requirements'
    elif state == 'unverified' and gaps:
        state = 'partial'
        reason = 'evidence_requirements_unresolved'
    elif declared.get('state') in STATES:
        reason = 'specialist_declared'
    else:
        reason = 'specialist_did_not_supply_clause_coverage'
    verified = state == 'complete' and not gaps and bool(requirements) and all(
        isinstance(r, dict) and r.get('state') in {'supported', 'satisfied', 'complete', 'verified'} for r in requirements
    )
    return {'state': state, 'reason': reason, 'requirements': requirements,
            'unresolved': unresolved, 'unresolved_requirements': gaps,
            'inquiry_answered_verified': verified, 'handler_executed': True,
            'declared_state': declared.get('state') if declared.get('state') in STATES else None}
