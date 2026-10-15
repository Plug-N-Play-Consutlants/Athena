"""Source boundary and decision regressions: no network or league credentials."""
from pathlib import Path
import sys
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Athena.entry_policy import select_entry_route
from Athena.Investigation.league_standings_inquiry import investigate_period_standings
from types import SimpleNamespace

cases = [
 ('Compare JHLPAA standings for weeks 1-3', 'public', 'league_period_standings'),
 ('JHLPAA weekly report for week 2', 'fantasy', 'league_recap'),
 ('Analyze the JHLPAA trade implications', 'public', 'league_recap'),
 ('Explain my league trade implications', 'fantasy', 'fantasy_trade_investigation'),
 ('How are the Maple Leafs performing this season?', 'public', ''),
 ('How has William Nylander performed?', 'public', ''),
]
for question, mode, expected in cases:
    decision = select_entry_route(question, mode)
    assert decision.route == expected, (question, decision)

router = (ROOT/'Scout/conversation/router.py').read_text(encoding='utf-8')
standings = router.split('def _league_standings_inquiry(',1)[1].split('def route_question(',1)[0]
assert 'FantraxClient' not in standings
assert 'ensure_period_snapshots' not in standings
assert 'investigate_period_standings(ctx, question)' in standings
assert 'select_entry_route(raw_question, selected_mode)' in router
assert 'league_standings =' not in router.split('def route_question(',1)[1].split('    # Prompt semantics',1)[0]
ctx = SimpleNamespace(standings_archive={}, league_profile={})
with patch('Athena.Investigation.standings_acquisition.resolve_league_context', side_effect=ValueError('missing context')):
    outcome = investigate_period_standings(ctx, 'JHLPAA standings weeks 1-3')
assert outcome['periods'] == [1,2,3]
assert outcome['state'] == 'evidence_unavailable'
assert outcome['acquisition'] is None
assert outcome['limitations']
print('Athena entry ownership and standings boundary PASS')
