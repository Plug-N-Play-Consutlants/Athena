"""Offline identity, conditional reasoning, source integrity and regression tests."""
from Athena.public_team_performance import resolve_nhl_team_subject, team_investigation_target
from Athena.capability_coordination import synthesize_supporting_findings
from Athena.intent_resolution import select_executable_route

def run():
    for prompt, code in [
        ('What are the Boston Bruins\' biggest roster weaknesses?', 'BOS'),
        ('What are the Toronto Maple Leafs\' biggest roster needs?', 'TOR'),
        ('How should Edmonton Oilers improve their roster?', 'EDM'),
        ('Where could Carolina Hurricanes improve their lineup?', 'CAR'),
    ]:
        assert team_investigation_target(prompt)[0] == code, prompt
        assert select_executable_route(prompt, 'public')[0] == 'public_current_season_team_investigation', prompt
    assert resolve_nhl_team_subject('What should New York do?') is None
    assert resolve_nhl_team_subject('Compare Boston Bruins and Toronto Maple Leafs') is None
    assert team_investigation_target('How are the Boston Bruins playing?') is None
    q = 'How could Toronto improve its roster while staying within the salary cap?'
    finding = {'team_id':'nhl.team.tor','status':'indeterminate_incomplete_ledger',
               'headroom':None,'explanation':'Verified complete payroll is unavailable.'}
    result = {'route':'public_nhl_cap_reasoning','objective':'economics','state':'evidence_available',
              'subject':'TOR','finding':finding}
    report = {'supporting_results':[result]}
    answer = {'natural_language_response':'Toronto recorded a level goal differential.',
              'developer':{'team_performance_evidence':{'team':'TOR'}}, 'known_limitations':[]}
    merged = synthesize_supporting_findings(answer,report,q)
    assert merged['merged'] and merged['conditional'] and not merged['completion_verified']
    assert 'salary-neutral exchange' in answer['natural_language_response']
    assert 'Verified complete payroll is unavailable.' in answer['natural_language_response']
    assert '\n\n' in answer['natural_language_response'] and '\\n' not in answer['natural_language_response']
    assert answer['engine_conclusion'] == answer['natural_language_response']
    assert not synthesize_supporting_findings(answer,report,q)['merged']
    other = {'natural_language_response':'Boston facts.', 'developer':{'team_performance_evidence':{'team':'BOS'}}}
    assert not synthesize_supporting_findings(other,report,'What should Boston Bruins improve?')['merged']
    scenario = {'natural_language_response':'Toronto ledger is incomplete.', 'known_limitations':[]}
    out = synthesize_supporting_findings(scenario,{'supporting_results':[]},
       'Why would Toronto trade two players for Aatu Räty instead of claiming him on waivers, and what difference would that make to its contract limits?')
    assert out['conditional'] and 'two-SPC-out' in scenario['natural_language_response']
    assert 'management intent' in ';'.join(out['unresolved'])
    unsafe = {'natural_language_response':'Original', 'known_limitations':[]}
    bad = dict(result, finding=dict(finding, headroom=12345))
    assert not synthesize_supporting_findings(unsafe, {'supporting_results':[bad]},q)['merged']
    assert unsafe['natural_language_response'] == 'Original'
    # The Public fantasy domain must not be captured by NHL team resolution.
    assert team_investigation_target('What happened in the JHLPAA this week?') is None
    print('PASS: identity, subject isolation, bounded interpretation, cap safety, fantasy routing')

if __name__ == '__main__':
    run()
