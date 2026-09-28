"""Regression checks for subject-bound follow-ups and visible rule explanations."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

os.environ["ATHENA_NHL_PLAYER_NETWORK"] = "0"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from Athena.request_execution import AthenaRequest, execute_request


def ask(question, entity=None):
    continuation = {"origin_intent": "public_player_profile", "subject_entity_id": entity} if entity else None
    return execute_request(AthenaRequest(question, mode="public", context=SimpleNamespace(files_loaded=[]), continuation=continuation))


def main():
    baseline = "How does Sebastian Aho's current production compare with his recent career baseline?"
    finnish = ask(baseline, "nhl.player.sebastian_aho_car")
    swedish = ask(baseline, "nhl.player.sebastian_aho_swe")
    assert finnish["intent"] == swedish["intent"] == "public_player_temporal_comparison"
    assert finnish["developer"]["subject_entity_id"] == "nhl.player.sebastian_aho_car"
    assert swedish["developer"]["subject_entity_id"] == "nhl.player.sebastian_aho_swe"
    assert "80 points" not in swedish["public_comment"]
    camp = ask("What has Sidney Crosby shown in camp and preseason, and does it change the outlook for his early-season form or deployment?", "nhl.player.sidney_crosby")
    assert camp["intent"] == "public_player_investigation" and "Sidney Crosby" in camp["public_comment"]
    icing = ask("What is icing")
    assert icing["intent"] == "public_hockey_knowledge" and "puck" in icing["public_comment"].lower()
    assert "Relevant public hockey evidence:" not in icing["public_comment"]
    print("Public inquiry pathways: PASS")


if __name__ == "__main__":
    main()
