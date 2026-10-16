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
    from Knowledge.Identity.registry import SEED_IDENTITY_ENTITIES
    expected_team_count = sum(
        entity.entity_type == "team" and entity.league == "NHL"
        for entity in SEED_IDENTITY_ENTITIES
    )
    if signals and isinstance(benchmark, dict) and benchmark.get('teams') == expected_team_count and all(type(benchmark.get(k)) in (int, float) and benchmark[k] >= 0 for k in ('gfpg', 'gapg')):
        season = signals[0]
        signals.append({'id': 'league_relative_goal_rates', 'evidence': 'nhl_official_current_standings',
                        'teams': benchmark['teams'], 'team_gfpg': season['goals_for_per_game'],
                        'team_gapg': season['goals_against_per_game'], 'league_gfpg': benchmark['gfpg'],
                        'league_gapg': benchmark['gapg'], 'offense_delta': round(season['goals_for_per_game']-benchmark['gfpg'], 2),
                        'prevention_delta': round(season['goals_against_per_game']-benchmark['gapg'], 2),
                        'causal_inference_permitted': False})
    goalie = evidence.get('team_goalie_save_percentage')
    goalie_benchmark = evidence.get('league_goalie_benchmark')
    if (
        isinstance(goalie, dict)
        and isinstance(goalie_benchmark, dict)
        and type(goalie.get('save_percentage')) in (int, float)
        and type(goalie_benchmark.get('save_percentage')) in (int, float)
        and type(goalie.get('shots_against')) is int
        and type(goalie_benchmark.get('shots_against')) is int
        and goalie.get('shots_against', 0) > 0
        and goalie_benchmark.get('shots_against', 0) > 0
    ):
        signals.append({
            'id': 'league_relative_goalie_save_percentage',
            'evidence': 'nhl_official_goalie_summary',
            'team_save_percentage': round(goalie['save_percentage'], 3),
            'team_shots_against': goalie['shots_against'],
            'league_save_percentage': round(goalie_benchmark['save_percentage'], 3),
            'league_shots_against': goalie_benchmark['shots_against'],
            'qualified_league_goalies': goalie_benchmark.get('qualified_goalies'),
            'delta': round(goalie['save_percentage'] - goalie_benchmark['save_percentage'], 3),
            'causal_inference_permitted': False,
        })
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
    limitations = ['Goals for/against do not isolate defensive structure, special teams or shot quality.',
                   'Roster membership and position codes do not establish deployment, injury cover or positional need.']
    if gp and gp < 20:
        limitations.append(f'Only {gp} completed games are reflected in season standings; trends are provisional.')
    if not any(s['id'] == 'league_relative_goalie_save_percentage' for s in signals):
        limitations.append('A comparable league-wide goalie save-percentage benchmark was not acquired; individual goalie results cannot be ranked against the league.')
    economics = evidence.get('economics') or {}
    if isinstance(economics, dict) and not economics.get('aggregate_permitted', False):
        limitations.append('Contract evidence is incomplete; no exact cap headroom or acquisition feasibility can be inferred.')
    relative_rates = next((s for s in signals if s['id'] == 'league_relative_goal_rates'), None)
    goalie_rate = next((s for s in signals if s['id'] == 'league_relative_goalie_save_percentage'), None)
    priority = 'unresolved'
    if relative_rates and goalie_rate and goalie_rate['delta'] < 0:
        priority = 'investigate_goaltending_and_goal_prevention'
    elif relative_rates and relative_rates['prevention_delta'] > 0:
        priority = 'investigate_goal_prevention'
    elif relative_rates and relative_rates['offense_delta'] < 0:
        priority = 'investigate_goal_creation'
    elif relative_rates:
        priority = 'investigate_sustainability'
    elif goalie_rate and goalie_rate['delta'] < 0:
        priority = 'investigate_goaltending'
    elif signals:
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
    league = next((s for s in signals if s['id'] == 'league_relative_goal_rates'), None)
    goalie_comparison = next((s for s in signals if s['id'] == 'league_relative_goalie_save_percentage'), None)
    if league:
        if goalie_comparison and goalie_comparison['delta'] < 0:
            conclusion = 'Team save percentage is below the league rate; investigate goaltending and shot quality first, without treating this comparison as a causal diagnosis.'
        elif league['prevention_delta'] > 0:
            conclusion = 'The team allows more goals per game than the league rate; investigate goal prevention first, while checking whether scoring also trails the league.'
        elif league['offense_delta'] < 0:
            conclusion = 'The team scores fewer goals per game than the league rate; investigate goal creation first, while checking the underlying shot and special-teams evidence.'
        else:
            conclusion = 'No measured scoring, prevention, or goalie rate is below the league benchmark; investigate sustainability before proposing a roster change.'
    elif goalie_comparison and goalie_comparison['delta'] < 0:
        conclusion = 'Team save percentage is below the available league rate; investigate goaltending and shot quality before drawing a roster conclusion.'
    qualifier = f' This is a provisional {gp}-game observation, not a diagnosis of individual players.'
    recent = next((s for s in signals if s['id'] == 'recent_goal_balance'), None)
    if recent:
        qualifier += f" The last {recent['games']} completed games have a {recent['goal_differential']:+d} goal differential; this is context, not proof of a trend."
    consistency = next((s for s in signals if s['id'] == 'sample_consistency'), None)
    if consistency and consistency['interpretation'] == 'direction_diverges':
        qualifier += ' Recent results differ in direction from the season goal balance; a simple trend extrapolation is unwarranted.'
    if league:
        qualifier += (f" Against {league['teams']} teams in the same official standings snapshot, "
                      f"the club scores {league['team_gfpg']:.2f} goals/game versus {league['league_gfpg']:.2f} league average "
                      f"and concedes {league['team_gapg']:.2f} versus {league['league_gapg']:.2f}. "
                      "These are league-relative results, not a diagnosis of roster causation.")
    if goalie_comparison:
        qualifier += (
            f" Across {goalie_comparison['team_shots_against']} team shots against, the team save percentage is "
            f"{goalie_comparison['team_save_percentage']:.3f}, versus {goalie_comparison['league_save_percentage']:.3f} "
            f"league-wide across {goalie_comparison['league_shots_against']} shots. "
            "This result does not adjust for shot quality or establish goaltender causation."
        )
    else:
        qualifier += (
            " A league-wide goalie save-percentage benchmark was not acquired, so the team cannot "
            "be ranked against league goaltending; scoring and goal-prevention comparisons above "
            "remain supported independently."
        )
    goalies = evaluation.get('goalie_observations') or []
    if goalies:
        qualifier += ' Verified goalie season observations: ' + '; '.join(
            f"{g['name']} ({g['games']} GP" + (f", SV% {g['savePctg']:.3f}" if 'savePctg' in g else '') + ')'
            for g in goalies[:3]) + '. These do not isolate defensive shot quality.'
    return 'Assessment: ' + conclusion + qualifier + ' Next evidence to reconcile: five-on-five and special-teams performance, shot quality, goaltending, injuries, and deployment.' 
