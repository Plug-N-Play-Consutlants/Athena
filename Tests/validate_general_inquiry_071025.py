"""Focused v0.7.10.2.5 inquiry ownership and temporal baseline regression."""
from Athena.intent_planner import plan_capability
from Athena.Investigation.period_standings import compare_periods


def run():
    player = plan_capability('How has William Nylander performed this season, and what does that tell us about his contribution to the Maple Leafs?', 'public')
    assert player and player.route == 'public_player_investigation', player
    roster = plan_capability("What are the Maple Leafs' biggest roster needs, and how much flexibility do they have to address them?", 'public')
    assert roster and roster.route == 'public_nhl_team_economic_state', roster
    first = {'period': 1, 'teams': [{'team_id':'a','name':'A','rank':3,'points':10},{'team_id':'b','name':'B','rank':1,'points':15}]}
    second = {'period': 2, 'teams': [{'team_id':'a','name':'A','rank':2,'points':20},{'team_id':'b','name':'B','rank':1,'points':25}]}
    latest = {'period': 3, 'teams': [{'team_id':'a','name':'A','rank':1,'points':40},{'team_id':'b','name':'B','rank':2,'points':35}]}
    result = compare_periods([first,second,latest], requested_period=3, season_to_date=True)
    assert result['baseline_period'] == 1 and result['teams'][0]['rank_change'] == 2, result
    weekly = compare_periods([first,second,latest], requested_period=3)
    assert weekly['baseline_period'] == 2 and weekly['teams'][0]['rank_change'] == 1, weekly
    print('PASS: player ownership, roster economic ownership, season baseline, weekly baseline')

if __name__ == '__main__':
    run()
