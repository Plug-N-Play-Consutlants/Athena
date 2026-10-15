"""Historical stature requires observable coverage, not a success-shaped verdict."""
from pathlib import Path
import sys
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Athena.historical_stature_specialist import execute_historical_stature
from Athena.inquiry_execution import _completion
from types import SimpleNamespace
profile = SimpleNamespace(display_name="Test Player", team="TOR", position="C")
match = SimpleNamespace(entity="verified")
with patch("Athena.public_identity.resolve_public_player", return_value=match), \
     patch("Knowledge.Intelligence.Public.public_player_profiles.profile_for_entity", return_value=profile), \
     patch("Knowledge.Intelligence.Public.player_evidence.player_evidence", return_value={"position":"C"}), \
     patch("Athena.player_assessment.assess_player", return_value={"historical_stature":{"supporting_observations":["Verified honour"],"unresolved_tests":["Peer data unavailable"]}, "current_tier":"Star", "career_legacy":"Career Star"}):
    result = execute_historical_stature(SimpleNamespace(files_loaded=[]), "Is Test Player generational?")
    completion = _completion(result, "executed")
    assert completion["state"] == "partial"
    assert len(completion["requirements"]) == 6
    assert completion["requirements"][0]["state"] == "supported"
    assert len(completion["unresolved"]) == 5
    assert "not determined" in result["engine_conclusion"] or "cannot complete" in result["engine_conclusion"]
print("Historical stature clause coverage PASS")
