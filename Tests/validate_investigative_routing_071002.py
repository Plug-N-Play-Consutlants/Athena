"""Guard against specialist-route hijacking of fantasy investigations."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from Athena.Inquiry.execution import summarize_recent_league_activity,reconstruct_league_trade
from Scout.conversation.router import route_question
from Scout.conversation.context import load_context
from Core.version import ATHENA_VERSION
assert tuple(map(int,ATHENA_VERSION.split('.'))) >= (0,7,10,0,2)
h=json.loads((ROOT/'Output/transaction_history.json').read_text(encoding='utf-8'))
week=summarize_recent_league_activity(h,period='2')
assert week['transaction_count'] >= 1 and week['team_count'] >= 1
assert reconstruct_league_trade(h,team_names=['Unrecorded Team','Protect Hronek'])['matched_count']==0
ctx=load_context()
r=route_question('Write an Around the JHLPAA report covering Week 2',ctx,'fantasy')
assert r['intent']=='analyze_league' and 'season week 2' in r['engine_conclusion']
r=route_question('Analyze the JHLPAA trade between Bubba’s Bruisers and Protect Hronek involving Jack Eichel and future draft picks',ctx,'fantasy')
assert r['intent']=='fantasy_trade_investigation' and 'No canonical trade matches' in r['engine_conclusion']
print('PASS | fantasy weekly period, canonical participants, route precedence and no false trade reconstruction')
