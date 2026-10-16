"""Bounded inquiry capability coordination, without speculative execution.

A capability candidate is not a claim that evidence was acquired or used.
Only the primary route executes until specialists declare compatible evidence
contracts; this ledger exposes possible supporting routes for future orchestration.
"""
from __future__ import annotations
from typing import Any
from Athena.execution_registry import SPECIALISTS

SUPPORTING_ROUTES = {
    "economics": ("public_nhl_team_economic_state", "public_nhl_cap_reasoning"),
    "feasibility": ("public_nhl_transaction_scenario", "public_nhl_organizational_plausibility"),
    "assessment": ("public_current_season_team_investigation",),
    "change": ("public_team_window",),
    "comparison": ("public_player_comparison",),
}

def coordinate_capabilities(plan: dict[str, Any], primary_route: str | None, mode: str) -> dict[str, Any]:
    """Account for relevant candidates without invoking mismatched specialists."""
    primary = str(primary_route or "")
    selected_mode = str(mode or "public").lower()
    objectives = [item.get("id") for item in plan.get("objectives", []) if isinstance(item, dict)]
    candidates: list[dict[str, str]] = []
    seen = {primary}
    for objective in objectives:
        for route in SUPPORTING_ROUTES.get(objective, ()):
            if route in seen or route not in SPECIALISTS:
                continue
            seen.add(route)
            spec = SPECIALISTS[route]
            eligibility = "gated" if spec.mode == "fantasy" and selected_mode != "fantasy" else "candidate_only"
            candidates.append({"route": route, "objective": objective, "eligibility": eligibility,
                               "execution": "not_invoked", "reason": "no_shared_subject_and_evidence_contract"})
    return {"schema": "athena.capability_coordination.v1", "primary_route": primary,
            "primary_execution": "handled_by_request_boundary", "objectives": objectives,
            "supporting_candidates": candidates, "supporting_executed": 0,
            "multi_capability_synthesis_verified": False,
            "policy": "never_execute_secondary_specialists_without_compatible_subject_and_evidence_contract"}


# Operational secondary execution is deliberately narrower than candidate discovery.
# At present only the Toronto canonical cap determination has a reviewed
# subject-specific contract. Never execute the transaction-scenario specialist
# on a broad improvement question: it requires a named target and can assume one.
def execute_compatible_support(plan: dict[str, Any], primary_route: str | None,
                               mode: str, question: str, context: Any,
                               primary_answer: dict[str, Any],
                               *, executor: Any = None) -> dict[str, Any]:
    """Execute one bounded secondary capability; preserve independent provenance.

    Returns diagnostic evidence, not an alternate user-facing answer. An
    exception or missing canonical inputs must never replace the primary answer.
    """
    import re
    from Athena.execution_registry import execute_specialist
    report = coordinate_capabilities(plan, primary_route, mode)
    report['schema'] = 'athena.capability_coordination.v2'
    report['supporting_results'] = []
    if mode != 'public' or primary_route != 'public_current_season_team_investigation':
        report['execution_policy'] = 'no_reviewed_primary_contract'
        return report
    ids = set(report['objectives'])
    if 'economics' not in ids:
        report['execution_policy'] = 'economic_objective_not_requested'
        return report
    # Do not infer a team from the specialist route, question continuation,
    # or an untrusted answer paragraph. Require matching structured identity.
    detail = primary_answer.get('developer') if isinstance(primary_answer.get('developer'), dict) else {}
    team = detail.get('team_performance_evidence') if isinstance(detail.get('team_performance_evidence'), dict) else {}
    if team.get('team') != 'TOR' or not re.search(r'\b(?:Toronto|Maple Leafs|Leafs)\b', question, re.I):
        report['execution_policy'] = 'subject_contract_not_verified'
        return report
    route = 'public_nhl_cap_reasoning'
    candidate = next((c for c in report['supporting_candidates'] if c['route'] == route), None)
    if candidate is None:
        report['execution_policy'] = 'capability_not_selected'
        return report
    if executor is None:
        executor = execute_specialist
    try:
        result = executor(route, context, question, mode=mode)
        if not isinstance(result, dict):
            raise TypeError('unstructured_support_result')
        developer = result.get('developer') if isinstance(result.get('developer'), dict) else {}
        state = developer.get('team_economic_state')
        determination = developer.get('cap_determination')
        # A successful handler invocation is not proof of usable evidence.
        validated = isinstance(state, dict) and isinstance(determination, dict)
        report['supporting_results'].append({
            'route': route, 'objective': 'economics',
            'state': 'evidence_available' if validated else 'insufficient_evidence',
            'evidence_contract': 'canonical_team_economic_state_and_cap_determination',
            'subject': 'TOR',
            'determination_status': str(determination.get('status', 'unknown')) if validated else None,
            'missing': list(developer.get('missing') or []) if isinstance(developer.get('missing'), list) else [],
            'provenance': ['canonical_team_economic_state', 'league_season_context'] if validated else [],
            'presentation_merged': False,
            'finding': {
                'team_id': determination.get('team_id'),
                'status': determination.get('status'),
                'explanation': determination.get('explanation'),
                'headroom': determination.get('headroom'),
                'unresolved_inputs': list(determination.get('unresolved_inputs') or []),
            } if validated and determination.get('team_id') == 'nhl.team.tor'
                and isinstance(determination.get('explanation'), str) else None,
        })
        candidate['execution'] = 'invoked'
        candidate['eligibility'] = 'reviewed_subject_contract'
        candidate['reason'] = 'explicit_toronto_subject_and_economic_objective'
        report['supporting_executed'] = 1
        report['execution_policy'] = 'bounded_supporting_execution'
    except Exception as exc:
        report['supporting_results'].append({'route': route, 'objective': 'economics',
            'state': 'failed', 'error_type': type(exc).__name__, 'presentation_merged': False})
        candidate['execution'] = 'failed'
        report['execution_policy'] = 'support_failure_isolated'
    # Evidence gathering is not verified multi-capability synthesis.
    report['multi_capability_synthesis_verified'] = False
    return report


def synthesize_supporting_findings(answer: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    """Merge only a verified, subject-matched cap determination.

    The primary specialist retains ownership of its answer. Missing ledger data
    must never become invented headroom or a claim that roster options are feasible.
    """
    results = report.get('supporting_results', [])
    if not isinstance(results, list):
        return {'state': 'not_available', 'merged': False}
    eligible = [r for r in results if isinstance(r, dict)
                and r.get('route') == 'public_nhl_cap_reasoning'
                and r.get('objective') == 'economics'
                and r.get('state') == 'evidence_available'
                and r.get('subject') == 'TOR'
                and isinstance(r.get('finding'), dict)]
    if len(eligible) != 1:
        return {'state': 'not_available', 'merged': False}
    item = eligible[0]
    finding = item['finding']
    if finding.get('team_id') != 'nhl.team.tor':
        return {'state': 'subject_mismatch', 'merged': False}
    explanation = finding.get('explanation')
    status = finding.get('status')
    if not isinstance(explanation, str) or not explanation.strip() or not isinstance(status, str):
        return {'state': 'invalid_finding', 'merged': False}
    # Numeric claims require a determinate finding, not just a numeric field.
    if status == 'indeterminate_incomplete_ledger':
        if finding.get('headroom') is not None:
            return {'state': 'inconsistent_cap_finding', 'merged': False}
    elif status not in {'within_team_payroll_range', 'above_upper_limit', 'below_lower_limit'}:
        return {'state': 'unsupported_cap_status', 'merged': False}
    base = answer.get('natural_language_response')
    if not isinstance(base, str) or not base.strip():
        return {'state': 'missing_primary_narrative', 'merged': False}
    if explanation.strip() in base:
        return {'state': 'already_present', 'merged': False}
    answer['natural_language_response'] = base.rstrip() + '\\n\\nSalary-cap assessment: ' + explanation.strip()
    limitations = answer.get('known_limitations')
    if not isinstance(limitations, list):
        limitations = []
        answer['known_limitations'] = limitations
    if status == 'indeterminate_incomplete_ledger':
        note = 'Exact cap space and transaction feasibility remain unverified until the complete payroll and adjustment ledger is available.'
        if note not in limitations:
            limitations.append(note)
    item['presentation_merged'] = True
    report['multi_capability_synthesis_verified'] = False
    return {'state': 'bounded_cap_finding_merged', 'merged': True,
            'objective': 'economics', 'source_route': item['route'],
            'completion_verified': False}
