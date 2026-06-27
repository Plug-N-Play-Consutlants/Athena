"""Scout Build 001 doctor."""
from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main():
    print("Scout Build 001 Doctor")
    print("======================")

    import Scout.conversation  # noqa: F401
    from Scout.conversation.router import route_question

    answer = route_question("Analyze Auston Matthews")
    dev = answer.get("developer", {})
    brief = dev.get("executive_brief", {})
    sections = brief.get("sections", []) if isinstance(brief, dict) else []

    checks = [
        ("Scout route", answer.get("intent") == "player_analysis"),
        ("Confidence", answer.get("confidence", 0) > 0.5),
        ("Executive brief", bool(brief)),
        ("Sections", len(sections) >= 5),
        ("Reasoning assessment", bool(dev.get("reasoning_assessment"))),
    ]

    for label, ok in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {label}")

    print()
    print("Intent:", answer.get("intent"))
    print("Title:", answer.get("title"))
    print("Confidence:", answer.get("confidence"))
    print("Sections:", ", ".join(s.get("heading", "?") for s in sections[:10]))
    print()
    print("Preview:")
    print((answer.get("natural_language_response") or answer.get("engine_conclusion") or "")[:1200])

    if not all(ok for _, ok in checks):
        raise RuntimeError("Scout Build 001 doctor failed.")

    print()
    print("STATUS: PASS")


if __name__ == "__main__":
    main()
