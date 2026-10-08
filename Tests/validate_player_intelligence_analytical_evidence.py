from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from Core.version import ATHENA_VERSION,RELEASE_NAME
from Reasoning.Players import build_player_intelligence
from Reasoning.Significance import assess_asset_significance
from Reasoning.Analytics import analytical_finding,assess_applicability
assert ATHENA_VERSION=='0.7.9.0.2'
assert RELEASE_NAME=='Development Inquiry Routing and Evidence Integration Hotfix'
mc={"name":"Gavin McKenna","age":18,"position":"L","games_played":3,"points":2,"draft":{"overall_pick":1},"relationship":"current_roster","development_history":[{"level":"NHL","age":18,"event":"made_roster"},{"level":"NHL","age":18,"role":"top_six_top_nine"}]}
haymes={"name":"Luke Haymes","age":23,"position":"C","games_played":3,"relationship":"current_roster","development_history":[{"level":"NCAA"},{"level":"AHL"},{"level":"AHL"},{"level":"NHL"}]}
mi=build_player_intelligence(mc);hi=build_player_intelligence(haymes)
assert mi['current_impact']['sample_sufficiency']['statistical_sample']=='immature'
assert mi['current_impact']['sample_sufficiency']['contextual_evidence']=='available'
assert hi['development_pathway']['principle'].startswith('Elapsed time is not developmental delay')
assert hi['development_trajectory']['causal_explanations']=='unresolved'
sig=assess_asset_significance(mc)
assert sig['player_intelligence']['player']=='Gavin McKenna'
assert any(d['dimension']=='development_trajectory' for d in sig['dimensions'])
f=analytical_finding(claim='X predicts Y',source='Clear Sight Analytics',methodology='classified observations',population='NHL',period='2025-26',conditions=['5v5'])
a=assess_applicability(f,{"league":"NHL"})
assert set(a['modes'])=={'support','challenge','extend'} and a['relationship']=='test_against_case'
print('PASS: canonical player intelligence, pathway/causation separation, sample sufficiency, significance consumption, and analytical evidence applicability.')

# Integration guard: organizational significance must enrich named assets before canonical significance.
handler=(ROOT/'Athena'/'capability_handlers.py').read_text(encoding='utf-8')
assert 'client.get_player_landing(pid)' in handler
assert handler.index('client.get_player_landing(pid)') < handler.index('asset["asset_significance"]=assess_asset_significance(asset)')
ui=(ROOT/'Scout'/'app.py').read_text(encoding='utf-8')
assert 'answer-copy-heading' in ui and 'color:#f3d77a' in ui and 'renderAnswerCopy(natural)' in ui
