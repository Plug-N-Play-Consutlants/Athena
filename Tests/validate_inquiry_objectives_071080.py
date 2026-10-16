"""Hermetic objective ledger regression; no NHL network access."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Athena.inquiry_objectives import decompose_inquiry, assess_objective_coverage
from Athena.completion_assessment import assess_completion
from Tools.doctor_release_hygiene import build_report
for question, required in [
    ('What are the Leafs biggest roster needs, and how much flexibility do they have?', {'assessment','mechanism'}),
    ('How could Toronto improve its roster while staying within the cap?', {'mechanism','feasibility','economics'}),
    ('Why trade for a player after waivers when at the 50-contract limit?', {'explanation','mechanism','economics'}),
    ('How did our fantasy league change last week?', {'mechanism','change'}),
]:
    plan = decompose_inquiry(question)
    assert required.issubset({o['id'] for o in plan['objectives']}), (question,plan)
    coverage = assess_objective_coverage(plan, {'missing':['cap_ledger']}, {'inquiry_completion': {'state':'complete'}})
    assert not coverage['independently_verified']
    assert all('cap_ledger' in o['evidence_blockers'] for o in coverage['objectives'])
    assessment = assess_completion({'inquiry_completion': {'state':'complete', 'requirements':[{'name':'answer','state':'supported'}]}}, question=question)
    assert not assessment['inquiry_answered_verified']
assert any(c['name'] == 'distribution metadata matches runtime' and c['status'] == 'PASS' for c in build_report()['checks'])
print('PASS inquiry objective ledger')
