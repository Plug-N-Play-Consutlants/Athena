"""Regression: Scout compatibility recap must carry truthful Athena route metadata."""
from pathlib import Path
from Athena.entry_policy import select_entry_route

def test_public_recap_policy():
    assert select_entry_route("Give me the latest JHLPAA weekly report", "public").route == "league_recap"

def test_scout_recap_metadata_contract():
    source = (Path(__file__).resolve().parents[1] / "Scout/conversation/router.py").read_text()
    assert 'answer["developer"]["athena_request"]' in source
    assert '"selected_route": "league_recap"' in source
    assert '"execution_owner": "scout_compatibility_adapter"' in source
