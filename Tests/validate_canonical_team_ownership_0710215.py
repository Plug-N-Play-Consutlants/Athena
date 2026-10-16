"""Deliverable 2: canonical team ownership across Athena and Scout (offline)."""
from __future__ import annotations
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Athena.intent_resolution import select_executable_route
from Athena.request_execution import AthenaRequest, execute_request
from Athena.public_team_performance import team_investigation_target
from Scout.conversation import router

PROMPTS = (
    "What are the Leafs' biggest roster needs, and how much flexibility do they have?",
    "How could Toronto improve its roster while staying within the cap?",
)
FAKE = {"conclusion": "Verified bounded team evidence", "confidence": .55,
        "evidence": {"season": 20262027, "sources": ["nhl_club_stats_season"],
                     "missing": ["verified_roster_deployment_and_needs"], "leaders": []}}


def run():
    # The local archival snapshot predates Athena/inquiry_execution.py. A
    # boundary adapter here delegates Scout's real call into execute_request;
    # Studio uses the actual installed adapter instead.
    adapter = ModuleType("Athena.inquiry_execution")
    adapter.answer = lambda question, ctx, mode="public": execute_request(AthenaRequest(question, mode=mode, context=ctx))
    with patch.dict(sys.modules, {"Athena.inquiry_execution": adapter}), \
         patch("Athena.public_team_performance.assess_team_performance", return_value=FAKE) as assessor, \
         patch("Athena.evidence_bundle.build_request_evidence", return_value={"status": "not_required", "sources": [], "missing": []}):
        for prompt in PROMPTS:
            assert team_investigation_target(prompt) == ("TOR", "Toronto Maple Leafs")
            route, source = select_executable_route(prompt, "public")
            assert (route, source) == ("public_current_season_team_investigation", "canonical_nhl_team_investigation")
            context = SimpleNamespace(files_loaded=[])
            direct = execute_request(AthenaRequest(prompt, mode="public", context=context))
            with patch.object(router, "_public_analytical_answer", side_effect=AssertionError("Scout preempted Athena")):
                scout = router.route_question(prompt, ctx=SimpleNamespace(files_loaded=[]), mode="public")
            for answer in (direct, scout):
                assert answer["intent"] == "public_current_season_team_investigation"
                assert answer["engine_conclusion"] == "Verified bounded team evidence"
                assert answer["developer"]["athena_request"]["execution_owner"] == "athena_registered_specialist"
                assert answer["developer"]["athena_request"]["selected_route"] == route
                assert answer["known_limitations"] == FAKE["evidence"]["missing"]
            assert assessor.call_count >= 2
            print("[PASS] canonical ownership:", prompt)
    for prompt in ("What is Toronto's salary cap space?", "What is the Maple Leafs' cap usage?"):
        route, _ = select_executable_route(prompt, "public")
        assert route != "public_current_season_team_investigation", (prompt, route)
        assert team_investigation_target(prompt) is None
    print("[PASS] cap-only boundary retained")


if __name__ == "__main__":
    run()
