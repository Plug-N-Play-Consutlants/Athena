"""Evidence inventory for historical stature; deliberately not a player-tier oracle.

Only observed statistics and awards produce claims. Era comparison, defensive
completeness and injury causality require separately sourced evidence.
"""
from __future__ import annotations
from typing import Any


def stature_evidence(evidence: dict[str, Any], series: list[dict[str, Any]],
                     career: dict[str, Any]) -> dict[str, Any]:
    observations: list[str] = []
    questions: list[str] = []
    awards = [a for a in evidence.get('awards', []) if isinstance(a, dict) and a.get('trophy')]
    for award in awards:
        trophy = str(award['trophy'])
        count = award.get('count')
        if isinstance(count, int) and count > 0:
            observations.append(f"Recorded NHL honour: {trophy}, {count} time(s).")
        else:
            observations.append(f"Recorded NHL honour: {trophy}; award count unverified.")
    completed = [s for s in series if isinstance(s.get('gp'), (int, float)) and s['gp'] > 0]
    goal_peak = max(completed, key=lambda s: s.get('goals') or 0, default=None)
    if goal_peak and isinstance(goal_peak.get('goals'), (int, float)):
        observations.append(f"Highest observed season goal total: {goal_peak['goals']} in {goal_peak['gp']} games ({goal_peak.get('season', 'season unknown')}).")
    if len(completed) >= 2:
        rates = [s['points']/s['gp'] for s in completed if isinstance(s.get('points'), (int, float))]
        if rates:
            observations.append(f"Observed season points-per-game range: {min(rates):.3f} to {max(rates):.3f} across {len(rates)} recorded seasons.")
    questions.extend([
        'Era-adjusted peer distributions and contemporaneous scoring ranks are not established by individual season totals.',
        'Defensive completeness and two-way impact require verified deployment and defensive evidence.',
        'Injury-related production suppression and recovery probabilities require dated medical context and a comparable historical cohort.',
        'Generational status cannot be inferred from a single award, scoring cutoff or prospect reputation.',
    ])
    return {
        'classification': 'not_determined',
        'status': 'evidence_inventory_only',
        'supporting_observations': observations,
        'unresolved_tests': questions,
        'counterevidence': [],
        'reconsideration': 'Reassess after adding era-adjusted peers, sustained impact, position-specific two-way evidence and documented health context.',
    }
