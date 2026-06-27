"""
Athena Sports Intelligence Platform
Epic 4E.2 Player Reasoning Validation
"""
from __future__ import annotations

import os
import sys
import traceback

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def validate(name, func):
    try:
        func()
        print(f"[PASS] {name}")
        return True
    except Exception as ex:
        print(f"[FAIL] {name}")
        print(f"       {ex}")
        traceback.print_exc(limit=1)
        return False


def validate_project_root():
    assert os.path.isdir(os.path.join(PROJECT_ROOT, "Reasoning")), (
        "Reasoning package not found at " + os.path.join(PROJECT_ROOT, "Reasoning")
    )


def validate_models():
    from Reasoning.models.player_profile import PlayerProfile
    from Reasoning.models.player_assessment import PlayerAssessment

    profile = PlayerProfile(entity_id="34", name="Auston Matthews")
    assessment = PlayerAssessment()

    assert profile.name == "Auston Matthews"
    assert assessment is not None


def validate_interpreter():
    from Reasoning.primitives.player_evidence_interpreter import PlayerEvidenceInterpreter

    class MockEvidence:
        source_type = "historical"
        summary = "Elite multi-season production"
        confidence = 0.95

    findings = PlayerEvidenceInterpreter().interpret([MockEvidence()])

    assert len(findings) == 1
    assert findings[0]["confidence"] > 0


def validate_assessor():
    from Reasoning.models.player_profile import PlayerProfile
    from Reasoning.primitives.player_assessor import PlayerAssessor

    class MockEvidence:
        source_type = "historical"
        summary = "Elite multi-season production"
        confidence = 0.95

    profile = PlayerProfile(entity_id="34", name="Auston Matthews")
    assessment = PlayerAssessor().assess(profile, [MockEvidence()])

    assert assessment.summary
    assert assessment.confidence > 0


def validate_reasoning_engine():
    from Reasoning.reasoning_engine import ReasoningEngine
    from Reasoning.reasoning_request import ReasoningRequest
    from Reasoning.models.player_profile import PlayerProfile

    class MockEvidence:
        source_type = "historical"
        summary = "Elite multi-season production"
        confidence = 0.95

    profile = PlayerProfile(entity_id="34", name="Auston Matthews")
    request = ReasoningRequest(
        reasoning_type="player_assessment",
        subject=profile,
        evidence_bundle=[MockEvidence()],
    )

    result = ReasoningEngine().reason(request)

    assert result.summary
    assert result.confidence > 0


def validate_context():
    from Reasoning.primitives.player_context_builder import PlayerContextBuilder

    findings = [
        {"type": "historical", "statement": "Historical finding", "confidence": 0.95},
        {"type": "temporal", "statement": "Temporal finding", "confidence": 0.90},
    ]

    context = PlayerContextBuilder().build(findings)

    assert len(context["historical"]) == 1
    assert len(context["temporal"]) == 1


def validate_generic_reasoning_pipeline():
    from Reasoning.reasoning_engine import ReasoningEngine

    result = ReasoningEngine().reason_about_asset([])

    assert isinstance(result, dict)
    assert "summary" in result
    assert "key_findings" in result
    assert "overall_confidence" in result


def main():
    print("Epic 4E.2 Player Reasoning Validation")
    print("=====================================")
    print("Project Root:", PROJECT_ROOT)

    tests = [
        ("Project Root", validate_project_root),
        ("Models", validate_models),
        ("Evidence Interpreter", validate_interpreter),
        ("Player Assessor", validate_assessor),
        ("Reasoning Engine", validate_reasoning_engine),
        ("Context Builder", validate_context),
        ("Generic Reasoning Pipeline", validate_generic_reasoning_pipeline),
    ]

    passed = 0
    for name, fn in tests:
        if validate(name, fn):
            passed += 1

    print()
    print("=====================================")
    print(f"Passed : {passed}")
    print(f"Failed : {len(tests) - passed}")

    if passed == len(tests):
        print("\nEPIC 4E.2 VALIDATION PASS")
    else:
        raise RuntimeError("One or more validations failed.")


if __name__ == "__main__":
    main()
