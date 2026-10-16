"""Offline regression for bounded NHL team evaluation."""
from Athena.team_comparative_evaluation import evaluate_team, narrative

def run():
    x = evaluate_team({'standings': {'gamesPlayed': 7, 'goalFor': 16, 'goalAgainst': 25},
                       'economics': {'aggregate_permitted': False}})
    assert x['investigation_priority'] == 'investigate_goal_prevention'
    assert x['verified_roster_weakness'] is None and x['verified_transaction_target'] is None
    assert 'provisional 7-game' in narrative(x)
    assert any('Contract evidence is incomplete' in s for s in x['limitations'])
    y = evaluate_team({'standings': {'gamesPlayed': 7, 'goalFor': 26, 'goalAgainst': 16},
                       'recent_games': [{'for': 4, 'against': 2}]*3})
    assert y['investigation_priority'] == 'investigate_sustainability_and_specific_deployment'
    assert '+6 goal differential' in narrative(y)
    z = evaluate_team({'standings': {'gamesPlayed': True, 'goalFor': 0, 'goalAgainst': 0}})
    assert z['investigation_priority'] == 'unresolved'
    assert 'not enough verified' in narrative(z)
    print('PASS: comparative evaluation, small-sample caution, cap gate, malformed evidence')

if __name__ == '__main__':
    run()
