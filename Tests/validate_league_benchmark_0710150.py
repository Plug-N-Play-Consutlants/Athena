"""Offline regression for reconciled league-relative comparison."""
from Athena.team_comparative_evaluation import evaluate_team, narrative

def run():
    x = evaluate_team({'standings': {'gamesPlayed': 8, 'goalFor': 28, 'goalAgainst': 28},
                       'league_benchmark': {'teams': 32, 'gfpg': 3.0, 'gapg': 3.0},
                       'goalie_observations': [{'name': 'Sample Goalie', 'games': 5, 'savePctg': .912}],
                       'recent_games': [{'for': 2, 'against': 3}]*3})
    ids = [v['id'] for v in x['signals']]
    assert 'league_relative_goal_rates' in ids and 'recent_goal_balance' in ids and 'sample_consistency' in ids
    assert '3.50 goals/game versus 3.00' in narrative(x)
    assert 'Sample Goalie' in narrative(x)
    y = evaluate_team({'standings': {'gamesPlayed': 8, 'goalFor': 28, 'goalAgainst': 28}, 'league_benchmark': {'teams': 2, 'gfpg': 3, 'gapg': 3}})
    assert 'league_relative_goal_rates' not in [v['id'] for v in y['signals']]
    print('PASS: league benchmark, recent signal isolation, goalie evidence, coverage gate')
if __name__ == '__main__': run()
