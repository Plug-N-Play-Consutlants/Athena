from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from Reasoning.Significance import assess_asset_significance, assess_organizational_significance, significance_sort_key
from Reasoning.Decisions import assess_transaction_decision

mc={"name":"Gavin McKenna","age":18,"position":"C","draft":{"overall_pick":1},"relationship":"prospect","rights_state":{"control_status":"controlled","transaction_status":"transaction_eligible_subject_to_restrictions"}}
cowan={"name":"Easton Cowan","age":20,"position":"RW","draft":{"overall_pick":28},"relationship":"prospect","rights_state":{"control_status":"controlled","transaction_status":"transaction_eligible_subject_to_restrictions"}}
for x in (mc,cowan):
    x["asset_significance"]=assess_asset_significance(x);x["organizational_significance"]=assess_organizational_significance(x,organization="Toronto Maple Leafs")
assert significance_sort_key(mc)>significance_sort_key(cowan)
assert any(d["dimension"]=="pedigree_rarity" and d["state"]=="established" for d in mc["asset_significance"]["dimensions"])
assert any(d["dimension"]=="current_performance_trajectory" and d["state"]=="unresolved" for d in mc["asset_significance"]["dimensions"])
dq=assess_transaction_decision(target_name="Connor McDavid",outgoing_assets=[mc,cowan],protected_assets=["Auston Matthews"],seller_name="Edmonton")
assert dq["decision_confidence"]=="bounded" and dq["outcome_confidence"]=="not_assessed"
assert any(x["alternative"]=="retain_assets" for x in dq["alternatives"])
assert "does not by itself prove" in dq["principle"]

transaction=(ROOT/'Athena/Investigation/nhl_transaction.py').read_text()
composition=(ROOT/'Scout/conversation/composition.py').read_text()
assert 'analytical_study_v2' in transaction and 'decision_quality' in transaction
assert 'first-overall pedigree and exceptional future-value cost' not in composition
assert 'young control/upside profile' not in composition
assert 'Opportunity Cost' in composition and 'Credible Alternatives' in composition

from Athena.intent_planner import plan_capability
from Athena.Inquiry.state import build_inquiry_state
route_q="Why would the Maple Leafs be more reluctant to trade Gavin McKenna than Easton Cowan or Luke Haymes? Don't just rank them; explain what makes each asset differently significant to Toronto."
assert plan_capability(route_q,"public").route=="public_nhl_organizational_assets"
scenario_q="If the Leafs could acquire Connor McDavid for Gavin McKenna, Easton Cowan and Luke Haymes without trading Auston Matthews, should they do it? Consider not only what they gain and give up, but what else Toronto could potentially do with those assets and whether a bad eventual outcome would necessarily make it a bad decision today."
inquiry=build_inquiry_state(scenario_q,"public")
assert inquiry.named_outgoing_assets==["Gavin McKenna","Easton Cowan","Luke Haymes"]
assert "Auston Matthews" in inquiry.protected_assets
assert 'scenario_locked' in transaction and 'named_outgoing_assets' in transaction
assert 'Decision Quality vs. Outcome' in composition
assert 'Comparative significance is an analytical clause' in composition
assert 'scenario_assets' in composition
assert 'availability_assumed_by_user' in transaction
dq_assumed=assess_transaction_decision(target_name="Connor McDavid",outgoing_assets=[mc,cowan],protected_assets=["Auston Matthews"],seller_name="Edmonton",availability_assumed=True)
assert dq_assumed["verdict"].startswith("Yes.")
assert "does not override the availability assumption" in dq_assumed["verdict"]

print('PASS: analytical significance, scenario authority, decision completion, and outcome-quality separation contracts.')
