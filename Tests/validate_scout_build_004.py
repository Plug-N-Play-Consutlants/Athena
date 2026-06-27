"""Scout Build 004 validation."""
from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main():
    print("Scout Build 004 Validation")
    print("==========================")

    import Scout.conversation  # noqa: F401
    from Scout.conversation.router import route_question

    answer = route_question("Analyze Auston Matthews")
    text = answer.get("natural_language_response", "")
    assert answer.get("intent") == "player_analysis", answer
    assert "Franchise Superstar" in text, text
    assert "Fantasy Role: Core Fantasy Asset" in text, text
    assert "that label is narrower than his full career value" in text, text
    assert text.count("better classified from a career-profile lens") == 1, text
    assert "Career Baselines" in text
    assert "1.172" in text

    print("[PASS] Scout route")
    print("[PASS] Asset tier polish")
    print("[PASS] Executive summary dedupe")
    print("[PASS] Career baseline preserved")
    print()
    print("SCOUT BUILD 004 VALIDATION PASS")


if __name__ == "__main__":
    main()
