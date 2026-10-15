from Reasoning.Boosters.league_player_comparison import apply_league_player_comparison
from types import SimpleNamespace
league={"league_name":"JHLPAA","scoring_detail":"points_only","competition_model":"total_points","keeper_count":11,"lineup_slots":[{"position":"C","active_slots":3}]}
profiles=[SimpleNamespace(display_name="Connor McDavid"),SimpleNamespace(display_name="Auston Matthews")]
series={"Connor McDavid":[{"gp":82,"points":138}],"Auston Matthews":[{"gp":60,"points":53}]}
a={"intent":"public_player_comparison","title":"comparison","natural_language_response":"Shared NHL analysis","developer":{"intelligence_used":[]},"observed_facts":[],"known_limitations":[]}
b=apply_league_player_comparison(a,league,profiles,series)
assert b['intent']=='league_player_comparison'
assert 'Connor McDavid has the stronger historical production case' in b['natural_language_response']
assert '11 keeper slots' in b['natural_language_response']
assert 'Shared NHL analysis' in b['natural_language_response']
c=apply_league_player_comparison({"developer":{}}, {**league,"scoring_detail":"categories","competition_model":"head_to_head"}, profiles, series)
assert 'cannot determine the league-specific winner' in c['engine_conclusion']
print('[PASS] shared comparison booster: verified scoring, keeper limits, unknown scoring guardrail')
