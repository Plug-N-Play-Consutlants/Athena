"""Offline regression for reconciled league-relative comparison."""
from Athena.team_comparative_evaluation import evaluate_team, narrative
from Athena.public_team_performance import _complete_league_team_benchmark
from Knowledge.Identity.registry import SEED_IDENTITY_ENTITIES

def run():
    teams = [
        entity.entity_id.rsplit(".", 1)[-1].upper()
        for entity in SEED_IDENTITY_ENTITIES
        if entity.entity_type == "team" and entity.league == "NHL"
    ]
    rows = [
        {"teamAbbrev": {"default": team}, "gamesPlayed": 8, "goalFor": 28, "goalAgainst": 24}
        for team in teams
    ]
    assert _complete_league_team_benchmark(rows, "20262027")["teams"] == len(teams)
    assert _complete_league_team_benchmark(rows[:-1], "20262027") is None
    assert _complete_league_team_benchmark(rows + rows[:1], "20262027")["teams"] == len(teams)

    x = evaluate_team({'standings': {'gamesPlayed': 8, 'goalFor': 28, 'goalAgainst': 28},
                       'league_benchmark': {'teams': 32, 'gfpg': 3.0, 'gapg': 3.0},
                       'team_goalie_save_percentage': {'saves': 912, 'shots_against': 1000, 'save_percentage': .912},
                       'league_goalie_benchmark': {'qualified_goalies': 100, 'saves': 91000, 'shots_against': 100000, 'save_percentage': .91},
                       'goalie_observations': [{'name': 'Sample Goalie', 'games': 5, 'savePctg': .912}],
                       'recent_games': [{'for': 2, 'against': 3}]*3})
    ids = [v['id'] for v in x['signals']]
    assert 'league_relative_goal_rates' in ids and 'league_relative_goalie_save_percentage' in ids
    assert 'recent_goal_balance' in ids and 'sample_consistency' in ids
    assert x['investigation_priority'] == 'investigate_goal_prevention'
    assert '3.50 goals/game versus 3.00' in narrative(x)
    assert '0.912' in narrative(x) and '0.910' in narrative(x)
    assert 'Sample Goalie' in narrative(x)
    y = evaluate_team({'standings': {'gamesPlayed': 8, 'goalFor': 28, 'goalAgainst': 28}, 'league_benchmark': {'teams': 2, 'gfpg': 3, 'gapg': 3}})
    assert 'league_relative_goal_rates' not in [v['id'] for v in y['signals']]
    assert 'investigate_goal_prevention' not in y['investigation_priority']
    print('PASS: league benchmark, recent signal isolation, goalie evidence, coverage gate')
if __name__ == '__main__': run()
