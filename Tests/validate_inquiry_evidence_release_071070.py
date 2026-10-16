"""Hermetic regression for v0.7.10.7.0 evidence and release integrity."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Athena.completion_assessment import assess_completion
from Athena.evidence_reconciliation import reconcile_evidence
from Tools.doctor_release_hygiene import build_report

assert not assess_completion({'inquiry_completion': {'state': 'complete', 'requirements': [{'state': 'supported', 'name': 'answer'}]}}, question='How and why?')['inquiry_answered_verified']
bundle = {'status': 'not_required', 'sources': [], 'missing': []}
answer = {'developer': {'team_performance_evidence': {'team': 'TOR', 'season': 20262027, 'sources': ['nhl_club_stats_season', 'made_up_source'], 'missing': ['verified_roster_deployment_and_needs']}}}
result = reconcile_evidence(bundle, answer)
assert result['sources'] == ['nhl_club_stats_season']
assert 'verified_roster_deployment_and_needs' in result['missing']
assert 'made_up_source' not in result['sources']
report = build_report()
assert any(x['name'] == 'distribution metadata matches runtime' and x['status'] == 'PASS' for x in report['checks'])
print('PASS inquiry evidence and release integrity')
