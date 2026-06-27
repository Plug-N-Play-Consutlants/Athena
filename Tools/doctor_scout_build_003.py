"""Scout Build 003 doctor."""
from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main():
    print("Scout Build 003 Doctor")
    print("======================")

    from Reasoning.career import CareerDataProvider, BaselineEngine
    import Scout.conversation  # noqa
    from Scout.conversation.router import route_question

    career = CareerDataProvider(PROJECT_ROOT).load_player("Auston Matthews")
    baselines = BaselineEngine().compute(career["season_history"]) if career else {}

    print("[PASS] Career seed pack" if career else "[FAIL] Career seed pack")
    if baselines:
        print(f"[PASS] 3-year PPG: {baselines['rolling_3']['ppg']:.3f}")
        print(f"[PASS] Peak goals: {baselines['peak_goals']['goals']}")

    answer = route_question("Analyze Auston Matthews")
    text = answer.get("natural_language_response", "")

    checks = [
        ("Scout route", answer.get("intent") == "player_analysis"),
        ("Career Identity section", "Career Identity" in text),
        ("Career Legacy section", "Career Legacy" in text),
        ("Career Baselines section", "Career Baselines" in text),
        ("Captain context", "captain" in text.lower()),
        ("Award context", "Rocket" in text),
    ]

    for label, ok in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {label}")

    print()
    print("Preview:")
    print(text[:2200])

    if not career or not all(ok for _, ok in checks):
        raise RuntimeError("Scout Build 003 doctor failed.")

    print()
    print("STATUS: PASS")


if __name__ == "__main__":
    main()
