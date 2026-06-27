"""Validate v0.5.0-drop4e39 Team Reasoning Engine."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_VERSION, SCOUT_VERSION, ATHENA_BUILD  # noqa: E402
from Tests.version_compat import is_recognized_athena_version, is_recognized_build, is_recognized_scout_version  # noqa: E402
from Knowledge.Intelligence.Public.public_team_profiles import get_public_team_profile  # noqa: E402
from Reasoning.team_reasoning_engine import TeamReasoningEngine  # noqa: E402
from Scout.conversation.router import route_question  # noqa: E402


class Report:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.lines: list[str] = []

    def check(self, condition: bool, name: str, detail: str = "") -> None:
        if condition:
            self.passed += 1
            self.lines.append(f"[PASS] {name}: {detail}".rstrip())
        else:
            self.failed += 1
            self.lines.append(f"[FAIL] {name}: {detail}".rstrip())

    def emit(self) -> int:
        print("Team Reasoning Engine Validation Report")
        print("=" * 48)
        print(f"Overall status: {'PASS' if self.failed == 0 else 'FAIL'}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print()
        for line in self.lines:
            print(line)
        return 0 if self.failed == 0 else 1


def main() -> int:
    report = Report()
    report.check(is_recognized_athena_version(ATHENA_VERSION), "athena_version", ATHENA_VERSION)
    report.check(is_recognized_scout_version(SCOUT_VERSION, ATHENA_VERSION), "scout_version", SCOUT_VERSION)
    report.check(is_recognized_build(ATHENA_BUILD, ATHENA_VERSION), "athena_build", ATHENA_BUILD)

    profile = get_public_team_profile("nhl.team.toronto_maple_leafs")
    report.check(profile is not None, "seed_team_profile_available", "Toronto Maple Leafs")
    assessment = TeamReasoningEngine().reason_about_public_team(profile, "Tell me about the Leafs")
    data = assessment.to_dict()
    required = ["executive_summary", "historical_context", "organizational_identity", "strengths", "weaknesses", "current_direction", "future_outlook"]
    report.check(all(data.get(key) for key in required), "assessment_sections_complete", ", ".join(required))
    report.check("fantasy" not in "\n".join(str(data.get(key, "")) for key in required).lower(), "assessment_no_fantasy_leakage")
    report.check(assessment.confidence >= 0.7, "assessment_confidence", str(assessment.confidence))

    answer = route_question("Tell me about the Toronto Maple Leafs", mode="public")
    text = "\n".join([
        str(answer.get("natural_language_response", "")),
        str(answer.get("engine_conclusion", "")),
        "\n".join(map(str, answer.get("observed_facts") or [])),
    ]).lower()
    dev = answer.get("developer") or {}
    report.check(answer.get("intent") == "public_team_profile", "scout_public_team_route", str(answer.get("intent")))
    expected_public_sections = [
        "competitive identity",
        "core players",
        "why they can be good",
        "what can hold them back",
        "analytical lens",
        "roster read",
    ]
    for heading in expected_public_sections:
        report.check(heading in text, f"rendered_section_{heading.replace(' ', '_')}")
    report.check("team_reasoning_engine" in (dev.get("intelligence_used") or []), "developer_intelligence_used_team_reasoning")
    report.check("team_reasoning_assessment" in dev, "developer_team_reasoning_assessment_attached")
    report.check("fantasy" not in text, "public_team_answer_no_fantasy_leakage")

    return report.emit()


if __name__ == "__main__":
    raise SystemExit(main())
