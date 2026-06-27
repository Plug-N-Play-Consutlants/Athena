"""Scout Build 004 doctor."""
from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main():
    print("Scout Build 004 Doctor")
    print("======================")

    import Scout.conversation  # noqa: F401
    from Scout.conversation.router import route_question

    answer = route_question("Analyze Auston Matthews")
    text = answer.get("natural_language_response", "")

    checks = [
        ("Scout route", answer.get("intent") == "player_analysis"),
        ("Franchise Superstar tier", "Franchise Superstar" in text),
        ("Core fantasy role retained", "Core Fantasy Asset" in text),
        ("No duplicate career summary", text.count("better classified from a career-profile lens") == 1),
        ("Career baselines retained", "Career Baselines" in text and "1.172" in text),
    ]

    for label, ok in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {label}")

    print()
    print("Preview:")
    print(text[:2600])

    if not all(ok for _, ok in checks):
        raise RuntimeError("Scout Build 004 doctor failed.")

    print()
    print("STATUS: PASS")


if __name__ == "__main__":
    main()
