"""Hermetic regression for canonical evidence and natural league recap routing."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Athena.entry_policy import select_entry_route
from Knowledge.Intelligence.Public.player_evidence import authoritative_statistical_view

for prompt in ('What happened in the JHLPAA this week?', 'What changed in the JHLPAA last week?', 'JHLPAA weekly report for week 2'):
    assert select_entry_route(prompt, 'fantasy').route == 'league_recap', prompt
assert select_entry_route('How do I join the JHLPAA?', 'fantasy').route == ''

from unittest.mock import patch
from types import SimpleNamespace
from Athena.public_identity import execute_public_player_investigation

class Profile:
    display_name = 'William Nylander'
    team = 'Toronto Maple Leafs'
    def to_dict(self): return {'display_name': self.display_name}
class Match:
    entity = object()
    def to_dict(self): return {'status': 'qualified_resolved'}

assessment = {'kind':'current_evidence', 'facts':[], 'limitations':['Current-season production unverified'], 'conclusion':'No verified current production', 'confidence':0.4}
ctx = SimpleNamespace(request_evidence={'player':{'official_player_record':{}, 'dated_news':[{'title':'Relevant player report','published_at':'2026-10-15'}]}}, files_loaded=[])
club = {'season':'20262027','gp':7,'points':12,'goals':4,'assists':8}
with patch('Athena.public_identity.resolve_public_player', return_value=Match()), \
     patch('Knowledge.Intelligence.Public.public_player_profiles.profile_for_entity', return_value=Profile()), \
     patch('Reasoning.public_player_questions.assess_player_question', return_value=assessment), \
     patch('Athena.public_team_performance.official_team_player_row', return_value=club):
    result = execute_public_player_investigation(ctx, 'How has William Nylander performed this season?')
conclusion = result['engine_conclusion']
assert '12 points' in conclusion and '7 games' in conclusion, conclusion
assert 'no verified' not in conclusion.casefold(), conclusion
assert 'Relevant player report' in str(result['observed_facts'])
view = authoritative_statistical_view(ctx.request_evidence['player']['official_player_record'])
assert view['authority'] == 'canonical_statistical_evidence', view
assert view['season_series'][0]['points'] == 12
assert view['target_season'] == '20262027'
print('PASS: natural fantasy routing and player evidence-to-conclusion continuity')
