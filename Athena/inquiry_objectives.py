"""Conservative, inspectable question-objective ledger.

This is an objective detector, not an answer generator or evidence verifier.
It never treats keyword matches as proof that a question was answered.
"""
from __future__ import annotations
import re
from typing import Any

OBJECTIVES = (
    ("explanation", r"\b(?:why|explain|reason|how come)\b", "causal explanation"),
    ("mechanism", r"\b(?:how|waiver|claim|contract limit|assign|eligib|rule)\b", "mechanism and constraints"),
    ("assessment", r"\b(?:biggest|need|weakness|strength|assess|evaluate|outlook)\b", "evidence-grounded assessment"),
    ("feasibility", r"\b(?:could|can|feasib|possible|option|improv|trade target)\b", "feasible options and tradeoffs"),
    ("economics", r"\b(?:cap|salary|payroll|contract|ltir|retention)\b", "economic or contract constraints"),
    ("comparison", r"\b(?:compar|versus|\bvs\b|relative|better|worse)\b", "contextual comparison"),
    ("change", r"\b(?:chang|mov|since|last week|trend|recent)\b", "change over time"),
)

def decompose_inquiry(question: str) -> dict[str, Any]:
    original = str(question or '').strip()
    clauses = [part.strip(' ,;:.?!') for part in re.split(r"[?!;]+|(?<=,)\s+(?=(?:and|but)\s)", original, flags=re.I) if part.strip(' ,;:.?!')]
    objectives = []
    for key, pattern, requirement in OBJECTIVES:
        if re.search(pattern, original, re.I):
            objectives.append({'id': key, 'requirement': requirement, 'state': 'not_independently_verified'})
    if original and not objectives:
        objectives.append({'id': 'response', 'requirement': 'answer the original inquiry', 'state': 'not_independently_verified'})
    return {'schema': 'athena.inquiry_objectives.v1', 'clauses': clauses, 'objectives': objectives,
            'verification_policy': 'objectives_are_requirements_not_proof'}

def assess_objective_coverage(plan: dict[str, Any], evidence: Any, result: Any) -> dict[str, Any]:
    """Surface candidate coverage and explicit blockers; never certify correctness."""
    missing = evidence.get('missing', []) if isinstance(evidence, dict) else []
    missing = [str(x) for x in missing] if isinstance(missing, list) else []
    declared = result.get('inquiry_completion') if isinstance(result, dict) else None
    declared = declared if isinstance(declared, dict) else {}
    return {'schema': 'athena.objective_coverage.v1',
            'objectives': [{**objective, 'evidence_blockers': list(missing),
                            'specialist_declared_state': declared.get('state', 'unverified')}
                           for objective in plan.get('objectives', [])],
            'independently_verified': False,
            'reason': 'no_claim_level_evidence_to_objective_provenance_contract'}
