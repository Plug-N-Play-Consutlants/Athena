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
    ("assessment", r"\b(?:biggest|need|weakness|strength|assess|evaluate|outlook|investigat|priority)\b", "evidence-grounded assessment"),
    ("feasibility", r"\b(?:could|can|feasib|possible|option|improv|trade target)\b", "feasible options and tradeoffs"),
    ("economics", r"\b(?:cap|salary|payroll|contract|ltir|retention)\b", "economic or contract constraints"),
    ("comparison", r"\b(?:compar\w*|versus|\bvs\b|relative|better|worse)\b", "contextual comparison"),
    ("change", r"\b(?:chang|mov|since|last week|trend|recent)\b", "change over time"),
    ("roster", r"\b(?:roster|lineup|depth|call[ -]?up|recall|assign(?:ment)?|two[ -]?way|waivers?)\b", "roster roles, assignments and eligibility"),
    ("market", r"\b(?:free agent|sign(?:ing)?|acqui(?:re|sition)|trade|available players?|market)\b", "player availability and acquisition cost"),
    ("strategy", r"\b(?:don't trade|do not trade|protect|untouchable|prioriti[sz]|prefer|long[ -]?term|future picks?|gm plan)\b", "decision-maker objectives and organizational impact"),
    ("historical_intent", r"\b(?:why did|why would|gm's plan|management intent|at the time|hindsight)\b", "contemporaneous evidence versus inferred management intent"),
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
    synthesis = (result.get('developer') or {}).get('supporting_synthesis') if isinstance(result, dict) and isinstance(result.get('developer'), dict) else None
    synthesis = synthesis if isinstance(synthesis, dict) else {}
    developer = result.get('developer') if isinstance(result, dict) and isinstance(result.get('developer'), dict) else {}
    team = developer.get('team_performance_evidence') if isinstance(developer.get('team_performance_evidence'), dict) else {}
    evaluation = team.get('comparative_evaluation') if isinstance(team.get('comparative_evaluation'), dict) else {}
    signal_ids = {
        signal.get('id')
        for signal in evaluation.get('signals', [])
        if isinstance(signal, dict) and isinstance(signal.get('id'), str)
    }
    coordination = developer.get('capability_coordination') if isinstance(developer.get('capability_coordination'), dict) else {}
    support_results = coordination.get('supporting_results') if isinstance(coordination.get('supporting_results'), list) else []
    question_text = str(evidence.get('question') or '').casefold() if isinstance(evidence, dict) else ''

    def coverage_for(objective_id: str) -> tuple[str, list[str], list[str]]:
        refs: list[str] = []
        blockers: list[str] = []
        if objective_id == 'assessment':
            if 'team_goal_balance' in signal_ids:
                refs.extend(['team_goal_balance', 'investigation_priority'])
            else:
                blockers.append('verified_current_team_standings')
        elif objective_id == 'comparison':
            required = ['league_relative_goal_rates']
            if any(term in question_text for term in ('goaltend', 'goalie', 'save percentage', 'save%')):
                required.append('league_relative_goalie_save_percentage')
            refs.extend(signal for signal in required if signal in signal_ids)
            blockers.extend(
                requirement for requirement in (
                    'complete_current_nhl_standings_benchmark',
                    'league_goalie_comparison',
                )
                if requirement in missing
                and (
                    requirement != 'league_goalie_comparison'
                    or 'league_relative_goalie_save_percentage' in required
                )
            )
            if not refs:
                blockers.append('league_comparative_signals_unavailable')
        elif objective_id == 'change':
            if 'recent_goal_balance' in signal_ids:
                refs.append('recent_goal_balance')
            else:
                blockers.append('verified_recent_completed_games')
        elif objective_id == 'economics':
            supported = next((
                item for item in support_results
                if isinstance(item, dict)
                and item.get('objective') == 'economics'
                and item.get('state') == 'evidence_available'
            ), None)
            if supported:
                refs.extend(str(source) for source in supported.get('provenance', []) if isinstance(source, str))
                blockers.extend(
                    item for item in supported.get('missing', [])
                    if isinstance(item, str)
                )
                if supported.get('determination_status') == 'indeterminate_incomplete_ledger':
                    blockers.append('complete_verified_team_cap_ledger')
            else:
                blockers.extend(
                    item for item in support_results
                    if isinstance(item, dict) and item.get('objective') == 'economics'
                    for item in item.get('missing', []) if isinstance(item, str)
                )
                blockers.extend(
                    item for item in missing
                    if any(term in item.casefold() for term in ('cap', 'economic', 'ledger', 'salary'))
                )
                if not blockers:
                    blockers.append('canonical_team_economic_state')
        elif objective_id in {'roster', 'market', 'strategy', 'historical_intent'}:
            # A keyword or conditional explanation is never player-specific proof.
            blockers.append({
                'roster': 'verified_player_eligibility_and_roster_state',
                'market': 'verified_player_market_and_transaction_terms',
                'strategy': 'stated_objective_and_comparable_scenario_evidence',
                'historical_intent': 'dated_contemporaneous_decision_evidence',
            }[objective_id])
        elif objective_id in {'mechanism', 'feasibility'}:
            if synthesis.get('conditional'):
                refs.append('general_transaction_mechanism_conditional_not_transaction_evidence')
                return 'conditional_only', refs, ['verified_transaction_terms_and_eligibility']
            blockers.append('subject_specific_feasibility_evidence')
        else:
            blockers.extend(missing)
        if refs and blockers:
            return 'partially_available', refs, blockers
        if refs:
            return 'observations_available', refs, []
        return 'not_supported', [], blockers

    coverage_objectives = []
    for objective in plan.get('objectives', []):
        state, refs, blockers = coverage_for(str(objective.get('id') or ''))
        coverage_objectives.append({
            **objective,
            'evidence_coverage': state,
            'evidence_refs': refs,
            'evidence_blockers': blockers,
            'specialist_declared_state': declared.get('state', 'unverified'),
            'synthesis_state': 'conditional_mechanism_only' if synthesis.get('conditional') and objective.get('id') in {'mechanism', 'feasibility', 'explanation'} else 'not_independently_verified',
        })
    return {'schema': 'athena.objective_coverage.v2',
            'objectives': coverage_objectives,
            'evidence_missing': missing,
            'independently_verified': False,
            'reason': 'no_claim_level_evidence_to_objective_provenance_contract'}
