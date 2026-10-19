"""Regression: contract salary, waiver and cap charge are distinct."""
from Reasoning.Cap.roster_move_assessment import assess_roster_move
from Reasoning.Cap.cba_obligation_calculator import CapRuleContext
from Reasoning.Cap.cap_inquiry_execution import execute_cap_inquiry
r=assess_roster_move(dict(action='assign_to_minors',player_id='nhl:7',verified_aav=1500000,aav_source='fixture:contract',nhl_salary=900000,minor_salary=85000),minor_league_exemption=1200000)
assert r.annual_cap_delta == -1200000 and r.permissible is None
assert 'eligibility' in r.scout_summary()
assert 'Two-way' in r.scout_summary()
r2=assess_roster_move(dict(action='recall_to_nhl',player_id='nhl:7',verified_aav=1500000,aav_source='fixture:contract',eligibility_verified=True,waiver_clearance_or_exemption=True,roster_limit_compliance=True,contract_assignment_or_recall_permitted=True),minor_league_exemption=1200000)
assert r2.annual_cap_delta==1200000 and r2.permissible is True
r3=assess_roster_move(dict(action='assign_to_minors',player_id='nhl:7',verified_aav=1500000,aav_source='fixture:contract',eligibility_verified=True,waiver_clearance_or_exemption=False,roster_limit_compliance=True,contract_assignment_or_recall_permitted=True),minor_league_exemption=1200000)
assert r3.permissible is False
assert assess_roster_move(dict(action='recall_to_nhl',player_id='nhl:8',verified_aav=900000,aav_source='fixture:contract'),minor_league_exemption=1200000).annual_cap_delta==900000
rules=CapRuleContext('2026-27','2026-07-01','2027-06-30','fixture:rule',1200000)
result=execute_cap_inquiry(dict(team_id='TOR',as_of='2026-10-17',snapshot_id='fixture:tor',sources=[dict(id='fixture-source',retrieved_at='2026-10-17T15:00:00Z')],roster_verified=False,obligations=[],proposed_roster_moves=[dict(action='assign_to_minors',player_id='nhl:7',verified_aav=1500000,aav_source='fixture:contract')]),cba_rules=rules,cap_ceiling=104000000)
assert len(result.roster_moves)==1 and 'Roster scenarios:' in result.scout_answer()
assert result.review.verified_space is None
print('PASS bounded roster move integration and waiver independence')
