"""Scout Build 001 validation."""
from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def validate_reasoning_composer():
    from Intelligence.Player.player_intelligence import evaluate_player
    from Reasoning.adapters.player_evidence_adapter import build_player_profile_from_evaluation
    from Reasoning.reasoning_engine import ReasoningEngine
    from Reasoning.composition.executive_brief import ExecutiveBriefComposer

    evaluation = evaluate_player("Analyze Auston Matthews", mode="fantasy", project_root=PROJECT_ROOT)
    assert evaluation.get("status") == "available", evaluation

    profile = build_player_profile_from_evaluation(evaluation, fallback_name="Auston Matthews")
    assessment = ReasoningEngine().reason_about_player(profile, evaluation)
    brief = ExecutiveBriefComposer().build_player_brief(assessment, evaluation=evaluation, question="Analyze Auston Matthews")

    assert "Auston Matthews" in brief.get("title", "")
    assert brief.get("sections")
    assert "Executive Summary" in [s.get("heading") for s in brief.get("sections", [])]
    assert "Current Value" in [s.get("heading") for s in brief.get("sections", [])]
    assert brief.get("confidence", 0) > 0.5
    assert "Confidence:" in brief.get("natural_language_response", "")


def validate_scout_route():
    # Import package first so hotfix wrapper is applied to router.route_question.
    import Scout.conversation  # noqa: F401
    from Scout.conversation.router import route_question

    answer = route_question("Analyze Auston Matthews")
    actual_intent = answer.get("intent")
    assert actual_intent == "player_analysis", f"Expected player_analysis, got {actual_intent}. Answer={answer}"
    assert answer.get("confidence", 0) > 0.5, answer

    text = answer.get("natural_language_response", "") or answer.get("engine_conclusion", "")
    assert "Executive Summary" in text, text
    assert "Current Value" in text, text
    assert "Auston Matthews" in text, text

    dev = answer.get("developer", {})
    assert "executive_brief" in dev, dev
    assert "reasoning_engine" in dev.get("intelligence_used", []), dev


def main():
    print("Scout Build 001 Validation")
    print("==========================")
    tests = [
        ("Reasoning composer", validate_reasoning_composer),
        ("Scout player route", validate_scout_route),
    ]
    passed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"[PASS] {name}")
            passed += 1
        except Exception as ex:
            print(f"[FAIL] {name}: {ex}")
            raise
    print()
    print(f"Passed: {passed}")
    print("SCOUT BUILD 001 VALIDATION PASS")


if __name__ == "__main__":
    main()
