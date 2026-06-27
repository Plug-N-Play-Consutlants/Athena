"""Scout Build 003 validation."""
from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def validate_baselines():
    from Reasoning.career import CareerDataProvider, BaselineEngine

    career = CareerDataProvider(PROJECT_ROOT).load_player("Auston Matthews")
    assert career is not None
    baselines = BaselineEngine().compute(career["season_history"])
    r3 = baselines["rolling_3"]
    assert r3["points"] == 245
    assert r3["games"] == 209
    assert round(r3["ppg"], 3) == 1.172
    assert baselines["peak_goals"]["goals"] == 69


def validate_scout_output():
    import Scout.conversation  # applies player-route hotfix
    from Scout.conversation.router import route_question

    answer = route_question("Analyze Auston Matthews")
    text = answer.get("natural_language_response", "") or ""
    assert answer.get("intent") == "player_analysis", answer
    assert "Career Identity" in text, text
    assert "Career Legacy" in text, text
    assert "Career Baselines" in text, text
    assert "1.172" in text, text
    assert "69 goals" in text, text
    assert "captain" in text.lower(), text
    assert "Rocket" in text, text


def main():
    print("Scout Build 003 Validation")
    print("==========================")
    tests = [
        ("Career baselines", validate_baselines),
        ("Scout enriched output", validate_scout_output),
    ]
    passed = 0
    for name, fn in tests:
        fn()
        print(f"[PASS] {name}")
        passed += 1
    print()
    print(f"Passed: {passed}")
    print("SCOUT BUILD 003 VALIDATION PASS")


if __name__ == "__main__":
    main()
