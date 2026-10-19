"""Regression checks for bounded multi-objective Scout coordination."""
from Athena.inquiry_objectives import decompose_inquiry, assess_objective_coverage
from Athena.capability_coordination import _conditional_mechanisms

def test_implicit_cap_and_roster_objectives():
    ids={x['id'] for x in decompose_inquiry('How can Toronto improve its defense with a free agent or call-up?')['objectives']}
    assert {'mechanism','feasibility','market','roster'} <= ids

def test_executive_constraints_not_turned_into_evidence():
    plan=decompose_inquiry("Don't trade Knies; prioritize long-term depth")
    assert 'strategy' in {x['id'] for x in plan['objectives']}
    report=assess_objective_coverage(plan, {}, {})
    assert not report['independently_verified']
    assert next(x for x in report['objectives'] if x['id']=='strategy')['evidence_coverage']=='not_supported'

def test_ltir_and_signing_have_distinct_requirements():
    ltir, gaps=_conditional_mechanisms('Can Toronto sign a player using LTIR?',{'feasibility','economics','market'},team='TOR')
    assert any('not additional ordinary cap space' in x for x in ltir)
    assert any('eligibility' in x for x in gaps)
    signing, gaps=_conditional_mechanisms('Can Toronto sign a free agent?',{'feasibility','market'},team='TOR')
    assert any('contract slot' in x for x in signing)
    assert any('SPC' in x for x in gaps)

def test_two_way_does_not_imply_waiver_exemption():
    sections,gaps=_conditional_mechanisms('Can Toronto recall a two-way player?',{'roster','mechanism'},team='TOR')
    assert any('not itself waiver exemption' in x for x in sections)
    assert gaps
