"""Offline regression: evidence accountability and conservative conclusions."""
from Athena.evidence_sufficiency import audit_team_evidence
from Athena.team_comparative_evaluation import evaluate_team, narrative

def run():
    evidence = {'sources': ['nhl_club_stats_season', 'nhl_official_current_standings', 'canonical_team_economic_state'],
                'missing': ['verified_recent_completed_games', 'complete_verified_team_cap_ledger'],
                'economics': {'contract_coverage': 1, 'aggregate_permitted': False}}
    audit = audit_team_evidence(evidence)
    assert audit['stages']['complete_contract_ledger']['state'] == 'incomplete'
    assert audit['stages']['complete_contract_ledger']['covered_contract_count'] == 1
    assert audit['stages']['recent_games']['state'] == 'not_acquired'
    assert not audit['causal_diagnosis_verified'] and not audit['contract_completeness_verified']
    x = evaluate_team({'standings': {'gamesPlayed': 8, 'goalFor': 28, 'goalAgainst': 28},
                       'recent_games': [{'for': 1, 'against': 3}] * 3})
    assert next(s for s in x['signals'] if s['id'] == 'sample_consistency')['interpretation'] == 'direction_diverges'
    assert 'Recent results differ' in narrative(x)
    assert x['verified_roster_weakness'] is None
    print('PASS: evidence sufficiency and cross-sample comparison')

if __name__ == '__main__': run()
