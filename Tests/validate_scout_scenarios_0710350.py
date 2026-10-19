from Core.milestone_intelligence import MILESTONES, milestone_checklist, assess_milestone
from Reasoning.Cap.roster_move_assessment import assess_roster_sequence


def test_milestone_breadth():
    prompts = MILESTONES['0.7.10.34.0']
    assert len(prompts) >= 9
    assert all(mode == 'public' for mode, _ in prompts)
    assert 'NOT YET IMPLEMENTED' in milestone_checklist('0.7.10.34.0')
    assert assess_milestone('0.7.10.34.0', {}).status != 'PASS'


def test_sequenced_cap_effect_is_not_compliance_certificate():
    moves = [dict(action='recall_to_nhl', player_id='a', verified_aav=1500000, aav_source='fixture'),
             dict(action='assign_to_minors', player_id='b', verified_aav=2000000, aav_source='fixture')]
    result = assess_roster_sequence(moves, minor_league_exemption=1150000)
    assert result.annual_cap_delta == 0
    assert result.executable is None
    assert 'Intermediate daily cap' in result.unresolved[0]


def test_blocked_step_prevents_sequence_permission():
    moves = [dict(action='recall_to_nhl', player_id='a', verified_aav=1500000, aav_source='fixture',
                  eligibility_verified=True, waiver_clearance_or_exemption=False,
                  roster_limit_compliance=True, contract_assignment_or_recall_permitted=True)]
    assert assess_roster_sequence(moves, minor_league_exemption=1150000).executable is False
