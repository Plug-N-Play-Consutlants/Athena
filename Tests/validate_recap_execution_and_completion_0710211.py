"""Network-free execution-boundary regression for recap and completion semantics."""
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Scout.conversation.router import route_question
from Athena.intent_resolution import select_executable_route
from Athena.request_execution import AthenaRequest, execute_request
from Athena.execution_registry import Specialist

question = 'What happened in the JHLPAA this week?'
route, reason = select_executable_route(question, 'fantasy')
assert route == 'league_recap' and reason == 'athena_entry_policy:league_recap', (route, reason)
with patch('Scout.conversation.router.analyze_league', return_value={'intent':'analyze_league','engine_conclusion':'period recap'}) as recap:
    answer = route_question(question, ctx=SimpleNamespace(), mode='fantasy')
assert answer['engine_conclusion'] == 'period recap'
recap.assert_called_once()
source = (ROOT/'Scout/conversation/router.py').read_text(encoding='utf-8')
recap_body = source.split('def analyze_league(', 1)[1].split('def _', 1)[0]
assert 'select_entry_route(question, "fantasy").route == "league_recap"' in recap_body

result = {'intent':'probe','natural_language_response':'Bounded evidence','known_limitations':['Deployment not verified']}
with patch('Athena.intent_resolution.select_executable_route', return_value=('probe','test')), \
     patch('Athena.execution_registry.SPECIALISTS', {'probe':Specialist('probe','test.module','handler','public')}), \
     patch('Athena.execution_registry.execute_specialist', return_value=result), \
     patch('Athena.evidence_bundle.build_request_evidence', return_value={'status':'partial','sources':[],'missing':['current_roster']}):
    response = execute_request(AthenaRequest('Probe', mode='public', context=SimpleNamespace()))
completion = response['developer']['inquiry_completion']
assert completion['state'] == 'partial' and not completion['inquiry_answered_verified']
assert completion['unresolved_requirements'] == ['current_roster','Deployment not verified']
assert response['developer']['inquiry_execution_trace']['result']['completion_state'] == 'partial'
print('PASS: recap ownership reaches Scout adapter; request completion remains evidence-bounded')
