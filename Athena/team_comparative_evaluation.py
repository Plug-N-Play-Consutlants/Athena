"""Evidence-bounded team assessment, independent of transaction speculation."""
from __future__ import annotations
from typing import Any


def evaluate_team(evidence: dict[str, Any]) -> dict[str, Any]:
    """Rank observable concerns; do not infer positions, injuries, or trade targets."""
    standings = evidence.get('standings') or {}
    if not isinstance(standings, dict):
        standings = {}
    gp, gf, ga = (standings.get(k) for k in ('gamesPlayed', 'goalFor', 'goalAgainst'))
    signals: list[dict[str, Any]] = []
    if all(type(v) is int and v >= 0 for v in (gp, gf, ga)) and gp:
        gfpg, gapg = gf / gp, ga / gp
        # Relative comparison is internal (for vs against), NOT league ranking.
        signals.append({'id': 'team_goal_balance', 'evidence': 'nhl_official_current_standings',
                        'games': gp, 'goals_for_per_game': round(gfpg, 2),
                        'goals_against_per_game': round(gapg, 2),
                        'goal_differential_per_game': round(gfpg-gapg, 2),
                        'interpretation': ('goals_against_exceed_goals_for' if ga > gf else
                                           'goals_balanced' if ga == gf else 'goals_for_exceed_goals_against'),
                        'sample': 'early_small_sample' if gp < 20 else 'observed_season_sample'})
    recent = evidence.get('recent_games') or []
    if isinstance(recent, list) and len(recent) >= 3 and all(isinstance(g, dict) and type(g.get('for')) is int and type(g.get('against')) is int for g in recent):
        diff = sum(g['for']-g['against'] for g in recent)
        signals.append({'id': 'recent_goal_balance', 'evidence': 'nhl_official_completed_games',
                        'games': len(recent), 'goal_differential': diff,
                        'interpretation': 'recent_negative' if diff < 0 else 'recent_positive' if diff > 0 else 'recent_even'})
    limitations = ['Goals for/against do not isolate goaltending, defensive structure, special teams or shot quality.',
                   'Roster membership and position codes do not establish deployment, injury cover or positional need.']
    if gp and gp < 20:
        limitations.append(f'Only {gp} completed games are reflected in season standings; trends are provisional.')
    economics = evidence.get('economics') or {}
    if isinstance(economics, dict) and not economics.get('aggregate_permitted', False):
        limitations.append('Contract evidence is incomplete; no exact cap headroom or acquisition feasibility can be inferred.')
    priority = 'unresolved'
    if signals:
        season = signals[0]
        if season['interpretation'] == 'goals_against_exceed_goals_for':
            priority = 'investigate_goal_prevention'
        elif season['interpretation'] == 'goals_for_exceed_goals_against':
            priority = 'investigate_sustainability_and_specific_deployment'
        else:
            priority = 'investigate_goal_creation_and_prevention'
    return {'signals': signals, 'investigation_priority': priority, 'limitations': limitations,
            'verified_roster_weakness': None, 'verified_transaction_target': None,
            'conclusion_status': 'provisional_observed_signals_not_causal_diagnosis'}


def narrative(evaluation: dict[str, Any]) -> str:
    signals = evaluation['signals']
    if not signals:
        return 'Assessment: There is not enough verified team-level performance evidence to rank roster weaknesses.'
    season = signals[0]
    gp = season['games']
    if season['interpretation'] == 'goals_against_exceed_goals_for':
        conclusion = 'Goal prevention is the first area to investigate, because the club has conceded more than it has scored.'
    elif season['interpretation'] == 'goals_for_exceed_goals_against':
        conclusion = 'The observed goal balance is positive; a specific roster weakness cannot be ranked from results alone. Investigate whether that advantage is sustainable before recommending an addition.'
    else:
        conclusion = 'Scoring and conceding are balanced; neither a scoring nor prevention deficit is established by aggregate results.'
    qualifier = f' This is a provisional {gp}-game observation, not a league-relative ranking or a diagnosis of individual players.'
    recent = next((s for s in signals if s['id'] == 'recent_goal_balance'), None)
    if recent:
        qualifier += f" The last {recent['games']} completed games have a {recent['goal_differential']:+d} goal differential; this is context, not proof of a trend."
    return 'Assessment: ' + conclusion + qualifier + ' Next evidence to reconcile: five-on-five and special-teams performance, shot quality, goaltending, injuries, and deployment.'
