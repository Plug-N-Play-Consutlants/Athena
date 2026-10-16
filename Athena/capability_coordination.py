"""Execute only subject-matched supporting capabilities with shared evidence."""
from __future__ import annotations
from typing import Any
from Athena.execution_registry import SPECIALISTS

SUPPORTING_ROUTES = {
    "economics": ("public_nhl_cap_reasoning",),
}

def coordinate_capabilities(plan: dict[str, Any], primary_route: str | None, mode: str) -> dict[str, Any]:
    """Account for relevant candidates without invoking mismatched specialists."""
    primary = str(primary_route or "")
    selected_mode = str(mode or "public").lower()
    objectives = [item.get("id") for item in plan.get("objectives", []) if isinstance(item, dict)]
    candidates: list[dict[str, str]] = []
    seen = {primary}
    compatible_primary = (
        selected_mode == "public"
        and primary == "public_current_season_team_investigation"
    )
    for objective in (objectives if compatible_primary else ()):
        for route in SUPPORTING_ROUTES.get(objective, ()):
            if route in seen or route not in SPECIALISTS:
                continue
            seen.add(route)
            spec = SPECIALISTS[route]
            eligibility = "gated" if spec.mode == "fantasy" and selected_mode != "fantasy" else "candidate_only"
            candidates.append({"route": route, "objective": objective, "eligibility": eligibility,
                               "execution": "not_invoked", "reason": "awaiting_subject_and_evidence_validation"})
    return {"schema": "athena.capability_coordination.v1", "primary_route": primary,
            "primary_execution": "handled_by_request_boundary", "objectives": objectives,
            "supporting_candidates": candidates, "supporting_executed": 0,
            "non_executable_objectives": [
                {"objective": objective, "state": "kept_in_primary_analysis",
                 "reason": "no_subject_and_evidence_compatible_secondary_contract"}
                for objective in objectives
                if objective != "economics" or not compatible_primary
            ],
            "multi_capability_synthesis_verified": False,
            "policy": "never_execute_secondary_specialists_without_compatible_subject_and_evidence_contract"}


def execute_compatible_support(plan: dict[str, Any], primary_route: str | None,
                               mode: str, question: str, context: Any,
                               primary_answer: dict[str, Any],
                               *, executor: Any = None) -> dict[str, Any]:
    """Execute one bounded secondary capability; preserve independent provenance.

    Returns diagnostic evidence, not an alternate user-facing answer. An
    exception or missing canonical inputs must never replace the primary answer.
    """
    from Athena.execution_registry import execute_specialist
    report = coordinate_capabilities(plan, primary_route, mode)
    report['schema'] = 'athena.capability_coordination.v2'
    report['supporting_results'] = []
    if mode != 'public' or primary_route != 'public_current_season_team_investigation':
        report['execution_policy'] = 'no_compatible_primary_contract'
        return report
    ids = set(report['objectives'])
    if 'economics' not in ids:
        report['execution_policy'] = 'economic_objective_not_requested'
        return report
    detail = primary_answer.get('developer') if isinstance(primary_answer.get('developer'), dict) else {}
    team = detail.get('team_performance_evidence') if isinstance(detail.get('team_performance_evidence'), dict) else {}
    from Athena.public_team_performance import resolve_nhl_team_subject
    subject = resolve_nhl_team_subject(question)
    if subject is None or team.get('team') != subject[0]:
        report['execution_policy'] = 'subject_contract_not_verified'
        return report
    route = 'public_nhl_cap_reasoning'
    candidate = next((c for c in report['supporting_candidates'] if c['route'] == route), None)
    if candidate is None:
        report['execution_policy'] = 'capability_not_selected'
        return report
    request_evidence = getattr(context, "request_evidence", None)
    state = request_evidence.get("team_economic_state") if isinstance(request_evidence, dict) else None
    league_context = request_evidence.get("league_season_context") if isinstance(request_evidence, dict) else None
    if (
        not isinstance(request_evidence, dict)
        or request_evidence.get("team") != subject[0]
        or request_evidence.get("route") != primary_route
        or getattr(state, "team_id", None) != "nhl.team." + subject[0].lower()
        or getattr(league_context, "league_year", None) != getattr(state, "league_year", None)
    ):
        candidate.update({
            "eligibility": "evidence_missing",
            "execution": "blocked",
            "reason": "matching_shared_canonical_economic_state_unavailable",
        })
        report['supporting_results'].append({
            "route": route,
            "objective": "economics",
            "state": "blocked",
            "subject": subject[0],
            "missing": ["matching_shared_canonical_economic_state"],
            "presentation_merged": False,
        })
        report['execution_policy'] = 'support_blocked_by_missing_evidence'
        return report
    if executor is None:
        executor = execute_specialist
    try:
        result = executor(route, context, question, mode=mode)
        if not isinstance(result, dict):
            raise TypeError('unstructured_support_result')
        developer = result.get('developer') if isinstance(result.get('developer'), dict) else {}
        state_result = developer.get('team_economic_state')
        determination = developer.get('cap_determination')
        validated = (
            isinstance(state_result, dict)
            and isinstance(determination, dict)
            and state_result.get("team_id") == "nhl.team." + subject[0].lower()
            and determination.get("team_id") == "nhl.team." + subject[0].lower()
        )
        report['supporting_results'].append({
            'route': route, 'objective': 'economics',
            'state': 'evidence_available' if validated else 'insufficient_evidence',
            'evidence_contract': 'canonical_team_economic_state_and_cap_determination',
            'subject': subject[0],
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
            } if validated
                and isinstance(determination.get('explanation'), str) else None,
        })
        candidate['execution'] = 'executed' if validated else 'insufficient_evidence'
        candidate['eligibility'] = 'shared_subject_evidence_contract'
        candidate['reason'] = 'explicit_subject_and_economic_objective'
        report['supporting_executed'] = int(validated)
        report['execution_policy'] = 'bounded_supporting_execution'
    except Exception as exc:
        report['supporting_results'].append({'route': route, 'objective': 'economics',
            'state': 'failed', 'error_type': type(exc).__name__, 'presentation_merged': False})
        candidate['execution'] = 'failed'
        report['execution_policy'] = 'support_failure_isolated'
    return report


def _conditional_mechanisms(question: str, objectives: set[str], *, team: str) -> tuple[list[str], list[str]]:
    """Explicitly hypothetical mechanisms; never a recommendation or verified eligibility."""
    import re
    text = question.casefold()
    clauses: list[str] = []
    unresolved: list[str] = []
    if 'waiver' in text and ('trade' in text or 'claim' in text):
        clauses.append('Transaction mechanisms: A waiver claim, if the player is eligible and available and the club has claim priority, generally adds the claimed SPC without sending another SPC away. A trade can exchange existing SPCs; a two-SPC-out, one-SPC-in trade would reduce the acquiring club’s SPC count by one if all three are qualifying SPCs and no other contracts enter the transaction. This is a conditional count comparison, not evidence that such a trade occurred or that a claim was available.')
        clauses.append('Roster and cap effects are separate: contract-slot count, active-roster limits, assignment/waiver eligibility, and the net cap-hit change must each be checked. Two outgoing players do not automatically create two active roster openings or a specific amount of cap space.')
        unresolved.extend(['player waiver status and claim availability', 'actual SPC status of each player', 'verified transaction terms and cap hits', 'club contract count and roster constraints', 'management intent'])
    elif 'feasibility' in objectives and ('improv' in text or 'option' in text or 'upgrade' in text):
        clauses.append('Conditional improvement pathways: An internal lineup or deployment adjustment may be explored without acquiring an additional contract, but its effectiveness depends on verified usage and player performance. A salary-neutral exchange could change roster composition without increasing aggregate nominal cap hits, subject to retention, bonuses, buried charges and other accounting. A net salary addition requires verified cap room or a separately validated compliant mechanism. These are mechanisms to investigate, not endorsed targets or confirmed feasible moves.')
        unresolved.extend(['verified positional/deployment need', 'complete cap ledger and adjustments', 'candidate player availability and transaction terms'])
    return clauses, unresolved


def synthesize_supporting_findings(answer: dict[str, Any], report: dict[str, Any],
                                   question: str = '') -> dict[str, Any]:
    """Integrate subject-matched specialist findings and bounded alternatives.

    Does not promote objective completion or claim verified feasibility.
    """
    results = report.get('supporting_results', [])
    if not isinstance(results, list):
        results = []
    developer = answer.get('developer') if isinstance(answer.get('developer'), dict) else {}
    team_evidence = developer.get('team_performance_evidence') if isinstance(developer.get('team_performance_evidence'), dict) else {}
    from Athena.public_team_performance import resolve_nhl_team_subject
    subject = resolve_nhl_team_subject(question) if question else None
    if subject is None:
        return {'state': 'subject_not_verified', 'merged': False, 'completion_verified': False}
    team, name = subject
    if team_evidence and team_evidence.get('team') != team:
        return {'state': 'subject_mismatch', 'merged': False, 'completion_verified': False}
    # For a cap-led economic answer, no fabricated current-season team evidence
    # is introduced. The only allowed addition is a qualified mechanism.
    eligible = [r for r in results if isinstance(r, dict)
                and r.get('route') == 'public_nhl_cap_reasoning'
                and r.get('state') == 'evidence_available'
                and r.get('subject') == team and isinstance(r.get('finding'), dict)]
    finding = eligible[0]['finding'] if len(eligible) == 1 else None
    if finding:
        if finding.get('team_id') != 'nhl.team.' + team.lower():
            return {'state': 'subject_mismatch', 'merged': False, 'completion_verified': False}
        if finding.get('status') == 'indeterminate_incomplete_ledger' and finding.get('headroom') is not None:
            return {'state': 'inconsistent_cap_finding', 'merged': False, 'completion_verified': False}
    base = answer.get('natural_language_response')
    if not isinstance(base, str) or not base.strip():
        return {'state': 'missing_primary_narrative', 'merged': False, 'completion_verified': False}
    from Athena.inquiry_objectives import decompose_inquiry
    objectives = {o['id'] for o in decompose_inquiry(question)['objectives']}
    sections: list[str] = []
    provenance: list[str] = []
    if finding and isinstance(finding.get('explanation'), str):
        explanation = finding['explanation'].strip()
        if explanation and explanation not in base:
            sections.append('Financial constraints: ' + explanation)
            provenance.append('canonical_team_economic_state_and_cap_determination')
            eligible[0]['presentation_merged'] = True
    mechanisms, unresolved = _conditional_mechanisms(question, objectives, team=team)
    # The bounded scenario mechanism is useful for the explicit comparison even
    # if the team specialist returned an economic-state answer.
    for mechanism in mechanisms:
        if mechanism not in base:
            sections.append(mechanism)
    if mechanisms:
        provenance.append('general_transaction_mechanism_conditional_not_transaction_evidence')
    if not sections:
        return {'state': 'no_new_supported_analysis', 'merged': False, 'completion_verified': False}
    if unresolved:
        sections.append('Still requiring verification: ' + '; '.join(unresolved) + '.')
    # Use genuine newlines. Maintain Scout's parallel narrative fields to avoid
    # divergence between the browser and internal execution record.
    unified = base.rstrip() + '\n\n' + '\n\n'.join(sections)
    answer['natural_language_response'] = unified
    answer['internal_narrative'] = unified
    answer['engine_conclusion'] = unified
    limitations = answer.get('known_limitations')
    if not isinstance(limitations, list):
        limitations = []
        answer['known_limitations'] = limitations
    for requirement in unresolved:
        note = 'Unverified: ' + requirement
        if note not in limitations:
            limitations.append(note)
    if finding and finding.get('status') == 'indeterminate_incomplete_ledger':
        note = 'Exact cap space and transaction feasibility remain unverified until the complete payroll and adjustment ledger is available.'
        if note not in limitations:
            limitations.append(note)
    report['multi_capability_synthesis_verified'] = bool(
        finding and eligible[0].get('presentation_merged')
    )
    return {'state': 'bounded_coordinated_interpretation', 'merged': True,
            'source_provenance': provenance, 'conditional': bool(mechanisms),
            'unresolved': unresolved, 'completion_verified': False}
