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
    benchmark = evidence.get('league_benchmark') or {}
    if signals and isinstance(benchmark, dict) and benchmark.get('teams', 0) >= 20 and all(type(benchmark.get(k)) in (int, float) and benchmark[k] >= 0 for k in ('gfpg', 'gapg')):
        season = signals[0]
        signals.append({'id': 'league_relative_goal_rates', 'evidence': 'nhl_official_current_standings',
                        'teams': benchmark['teams'], 'team_gfpg': season['goals_for_per_game'],
                        'team_gapg': season['goals_against_per_game'], 'league_gfpg': benchmark['gfpg'],
                        'league_gapg': benchmark['gapg'], 'offense_delta': round(season['goals_for_per_game']-benchmark['gfpg'], 2),
                        'prevention_delta': round(season['goals_against_per_game']-benchmark['gapg'], 2),
                        'causal_inference_permitted': False})
    recent = evidence.get('recent_games') or []
    if isinstance(recent, list) and len(recent) >= 3 and all(isinstance(g, dict) and type(g.get('for')) is int and type(g.get('against')) is int for g in recent):
        diff = sum(g['for']-g['against'] for g in recent)
        signals.append({'id': 'recent_goal_balance', 'evidence': 'nhl_official_completed_games',
                        'games': len(recent), 'goal_differential': diff,
                        'interpretation': 'recent_negative' if diff < 0 else 'recent_positive' if diff > 0 else 'recent_even'})
    # A small number of recent results cannot establish a causal roster weakness.
    # Surface whether recent form confirms or challenges the season-level signal.
    if any(s['id'] == 'recent_goal_balance' for s in signals):
        season_sign = (gf > ga) - (gf < ga)
        recent_sign = (next(s['goal_differential'] for s in signals if s['id'] == 'recent_goal_balance') > 0) - (next(s['goal_differential'] for s in signals if s['id'] == 'recent_goal_balance') < 0)
        signals.append({'id': 'sample_consistency', 'evidence': 'comparison_of_observed_results',
                        'interpretation': 'direction_agrees' if season_sign == recent_sign else 'direction_diverges',
                        'causal_inference_permitted': False})
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
            'goalie_observations': evidence.get('goalie_observations', []), 'conclusion_status': 'provisional_observed_signals_not_causal_diagnosis'}


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
    consistency = next((s for s in signals if s['id'] == 'sample_consistency'), None)
    if consistency and consistency['interpretation'] == 'direction_diverges':
        qualifier += ' Recent results differ in direction from the season goal balance; a simple trend extrapolation is unwarranted.'
    league = next((s for s in signals if s['id'] == 'league_relative_goal_rates'), None)
    if league:
        qualifier += (f" Against {league['teams']} teams in the same official standings snapshot, "
                      f"the club scores {league['team_gfpg']:.2f} goals/game versus {league['league_gfpg']:.2f} league average "
                      f"and concedes {league['team_gapg']:.2f} versus {league['league_gapg']:.2f}. "
                      "These are league-relative results, not a diagnosis of roster causation.")
    goalies = evaluation.get('goalie_observations') or []
    if goalies:
        qualifier += ' Verified goalie season observations: ' + '; '.join(
            f"{g['name']} ({g['games']} GP" + (f", SV% {g['savePctg']:.3f}" if 'savePctg' in g else '') + ')'
            for g in goalies[:3]) + '. These do not isolate defensive shot quality.'
    return 'Assessment: ' + conclusion + qualifier + ' Next evidence to reconcile: five-on-five and special-teams performance, shot quality, goaltending, injuries, and deployment.' 
