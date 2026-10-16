"""Offline bounded synthesis contract checks."""
from Athena.capability_coordination import synthesize_supporting_findings

def run():
    item = {'route':'public_nhl_cap_reasoning','objective':'economics',
            'state':'evidence_available','subject':'TOR','presentation_merged':False,
            'finding':{'team_id':'nhl.team.tor','status':'indeterminate_incomplete_ledger',
                       'headroom':None,'explanation':'Complete payroll evidence is missing.'}}
    answer = {'natural_language_response':'Toronto needs further investigation.',
              'known_limitations':[]}
    report = {'supporting_results':[item], 'multi_capability_synthesis_verified':False}
    result = synthesize_supporting_findings(answer,report,"How could Toronto improve its roster while staying within the salary cap?")
    assert result['merged'] and item['presentation_merged']
    assert 'Complete payroll evidence is missing.' in answer['natural_language_response']
    assert any('Exact cap space' in x for x in answer['known_limitations'])
    assert not report['multi_capability_synthesis_verified']
    assert not synthesize_supporting_findings(answer,report,"How could Toronto improve its roster while staying within the salary cap?")['merged']
    for key,value in [('subject','BOS'),('state','failed')]:
        altered = dict(item, **{key:value}, presentation_merged=False)
        untouched = {'natural_language_response':'Original.'}
        assert not synthesize_supporting_findings(untouched,{'supporting_results':[altered]},'What is Toronto salary cap?')['merged']
        assert untouched['natural_language_response']=='Original.'
    malformed = dict(item, finding=dict(item['finding'],headroom=1000000))
    assert not synthesize_supporting_findings({'natural_language_response':'Original.'},
                    {'supporting_results':[malformed]},'How could Toronto improve its roster within the salary cap?')['merged']
    print('PASS bounded synthesis, provenance and missing-ledger safety')

if __name__ == '__main__':
    run()
