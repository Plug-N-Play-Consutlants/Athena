"""
Epic 4E.2 completion validation.

Validates that Reasoning can produce a contextual player assessment and that
Scout routes player questions through the new assessment path.
"""
from __future__ import annotations

import os
import sys
import traceback

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def check(name, fn):
    try:
        fn()
        print(f"[PASS] {name}")
        return True
    except Exception as ex:
        print(f"[FAIL] {name}: {ex}")
        traceback.print_exc(limit=1)
        return False


def validate_reasoning_player_assessment():
    from Reasoning.reasoning_engine import ReasoningEngine

    assessment = ReasoningEngine().reason_about_player("Analyze Auston Matthews", mode="fantasy")

    assert assessment.summary
    assert "Auston Matthews" in assessment.summary
    assert assessment.confidence > 0
    assert assessment.value_drivers or assessment.strengths
    assert assessment.evidence_used
    assert hasattr(assessment, "to_dict")


def validate_reasoning_request_route():
    from Reasoning.reasoning_engine import ReasoningEngine
    from Reasoning.reasoning_request import ReasoningRequest

    request = ReasoningRequest(
        reasoning_type="player_assessment",
        subject="Analyze Auston Matthews",
        mode="fantasy",
    )
    assessment = ReasoningEngine().reason(request)

    assert assessment.summary
    assert assessment.confidence > 0


def validate_scout_player_route():
    from Scout.conversation.context import load_context
    from Scout.conversation.router import route_question

    answer = route_question("Analyze Auston Matthews", ctx=load_context(), mode="fantasy")

    assert answer.get("intent") in {"player_assessment", "player_analysis"}
    assert answer.get("natural_language_response")
    assert answer.get("confidence", 0) > 0
    assert "assessment" in answer or "player_evaluation" in answer.get("developer", {})


def validate_existing_4e2_regression():
    from Reasoning.models.player_profile import PlayerProfile
    from Reasoning.primitives.player_assessor import PlayerAssessor

    class MockEvidence:
        source_type = "historical"
        category = "historical"
        summary = "Elite multi-season production"
        confidence = 0.95

    profile = PlayerProfile(entity_id="34", name="Auston Matthews")
    assessment = PlayerAssessor().assess(profile, [MockEvidence()])

    assert assessment.summary
    assert assessment.confidence > 0


def main():
    print("Epic 4E.2 Completion Validation")
    print("================================")
    print("Project Root:", PROJECT_ROOT)

    tests = [
        ("Reasoning player assessment", validate_reasoning_player_assessment),
        ("ReasoningRequest route", validate_reasoning_request_route),
        ("Scout player route", validate_scout_player_route),
        ("Existing 4E.2 regression", validate_existing_4e2_regression),
    ]

    passed = 0
    for name, fn in tests:
        if check(name, fn):
            passed += 1

    print()
    print("================================")
    print(f"Passed : {passed}")
    print(f"Failed : {len(tests) - passed}")

    if passed != len(tests):
        raise RuntimeError("Epic 4E.2 completion validation failed.")

    print("\nEPIC 4E.2 COMPLETION VALIDATION PASS")


if __name__ == "__main__":
    main()
