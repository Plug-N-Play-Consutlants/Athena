"""Offline contract regression for bounded supporting capability execution."""
from Athena.capability_coordination import execute_compatible_support
from Athena.inquiry_objectives import decompose_inquiry

def run():
    calls = []
    def executor(route, context, question, *, mode):
        calls.append(route)
        return {'developer': {'team_economic_state': {'team': 'TOR'},
                              'cap_determination': {'status': 'unresolved'},
                              'missing': ['complete_roster']}}
    question = 'What are the Toronto Maple Leafs biggest needs and how much cap flexibility do they have?'
    plan = decompose_inquiry(question)
    answer = {'developer': {'team_performance_evidence': {'team': 'TOR'}}}
    out = execute_compatible_support(plan, 'public_current_season_team_investigation', 'public', question, object(), answer, executor=executor)
    assert calls == ['public_nhl_cap_reasoning'], calls
    assert out['supporting_executed'] == 1
    assert out['supporting_results'][0]['state'] == 'evidence_available'
    assert not out['multi_capability_synthesis_verified']
    assert not out['supporting_results'][0]['presentation_merged']
    calls.clear()
    for altered in [
        (question, {'developer': {'team_performance_evidence': {'team': 'BOS'}}}, 'public'),
        ('What are Boston needs and cap flexibility?', answer, 'public'),
        (question, answer, 'fantasy'),
        ('How are the Toronto Maple Leafs playing?', answer, 'public'),
    ]:
        q, a, mode = altered
        r = execute_compatible_support(decompose_inquiry(q), 'public_current_season_team_investigation', mode, q, object(), a, executor=executor)
        assert r['supporting_executed'] == 0
    assert not calls
    def fail(*args, **kwargs):
        raise RuntimeError('provider_offline')
    out = execute_compatible_support(plan, 'public_current_season_team_investigation', 'public', question, object(), answer, executor=fail)
    assert out['supporting_results'][0]['state'] == 'failed'
    print('PASS bounded supporting execution and isolation')

if __name__ == '__main__':
    run()
