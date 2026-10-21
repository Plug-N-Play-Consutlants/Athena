"""Targeted period inquiry routing and diagnostic regression tests."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Athena.entry_policy import select_entry_route

def test_public_mode_period_boundary_route():
    decision = select_entry_route('What was the most recently completed JHLPAA scoring period? Give me its exact dates.', 'public')
    assert decision.route == 'league_scoring_period_boundary'

def test_public_mode_player_period_route():
    decision = select_entry_route('Who were the top 10 point-producing players in the most recently completed JHLPAA scoring period?', 'public')
    assert decision.route == 'league_player_period_leaders'

def test_public_mode_editorial_access():
    assert select_entry_route('Give me the latest JHLPAA weekly report', 'public').route == 'league_recap'

def test_no_cross_domain_hijack():
    assert select_entry_route('Who are the Maple Leafs?', 'public').route == ''

def test_diagnostic_trace_contract():
    src = (ROOT / 'Athena/Investigation/league_period_questions.py').read_text()
    assert "'source_attempts'" in src and "'rejected_evidence'" in src
    assert "'terminal_reason'" in src and "'archive_is_completion_proof': False" in src

def test_period_acquisition_preserved():
    src = (ROOT / 'Athena/Investigation/period_evidence_acquisition.py').read_text()
    assert 'period_filter_status' in src and 'unverified_period' in src
