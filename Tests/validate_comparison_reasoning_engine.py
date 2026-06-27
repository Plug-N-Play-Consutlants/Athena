"""Validate v0.5.0-drop4e40 Comparison Intelligence Engine."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_VERSION, SCOUT_VERSION, ATHENA_BUILD  # noqa: E402
from Tests.version_compat import is_recognized_athena_version, is_recognized_build, is_recognized_scout_version  # noqa: E402
from Knowledge.Intelligence.Entities.entity_registry import find_by_id  # noqa: E402
from Knowledge.Intelligence.Public.public_player_profiles import profile_for_entity  # noqa: E402
from Knowledge.Intelligence.Public.public_team_profiles import profile_for_team_entity  # noqa: E402
from Reasoning.comparison_reasoning_engine import ComparisonReasoningEngine  # noqa: E402
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
        print("Comparison Intelligence Engine Validation Report")
        print("=" * 56)
        print(f"Overall status: {'PASS' if self.failed == 0 else 'FAIL'}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print()
        for line in self.lines:
            print(line)
        return 0 if self.failed == 0 else 1


def _text(answer: dict) -> str:
    return "\n".join([
        str(answer.get("natural_language_response", "")),
        str(answer.get("engine_conclusion", "")),
        "\n".join(map(str, answer.get("observed_facts") or [])),
    ]).lower()


def main() -> int:
    report = Report()
    report.check(is_recognized_athena_version(ATHENA_VERSION), "athena_version", ATHENA_VERSION)
    report.check(is_recognized_scout_version(SCOUT_VERSION, ATHENA_VERSION), "scout_version", SCOUT_VERSION)
    report.check(is_recognized_build(ATHENA_BUILD, ATHENA_VERSION), "athena_build", ATHENA_BUILD)

    matthews = profile_for_entity(find_by_id("nhl.player.auston_matthews"))
    mcdavid = profile_for_entity(find_by_id("nhl.player.connor_mcdavid"))
    report.check(matthews is not None and mcdavid is not None, "player_profiles_available", "Matthews and McDavid")
    assessment = ComparisonReasoningEngine().compare_public_players(matthews, mcdavid, "Compare Matthews and McDavid")
    data = assessment.to_dict()
    required = ["executive_comparison", "strengths", "weaknesses", "historical_comparison", "prime_comparison", "future_outlook", "athena_conclusion"]
    report.check(all(data.get(key) for key in required), "player_assessment_sections_complete", ", ".join(required))
    report.check(assessment.confidence >= 0.75, "player_assessment_confidence", str(assessment.confidence))
    report.check("goal" in assessment.athena_conclusion.lower() and "creation" in assessment.athena_conclusion.lower(), "player_conclusion_is_comparative", assessment.athena_conclusion)

    answer = route_question("Compare Matthews and McDavid", mode="public")
    text = _text(answer)
    report.check(answer.get("intent") == "public_player_comparison", "scout_public_player_comparison_route", str(answer.get("intent")))
    for heading in ["executive comparison", "strengths", "weaknesses", "historical comparison", "prime comparison", "future outlook", "athena conclusion"]:
        report.check(heading in text, f"rendered_player_section_{heading.replace(' ', '_')}")
    dev = answer.get("developer") or {}
    report.check("comparison_reasoning_engine" in (dev.get("intelligence_used") or []), "developer_intelligence_used_comparison_engine")
    report.check("comparison_assessment" in dev, "developer_comparison_assessment_attached")
    report.check(any(str(card.get("label")).lower() == "fantasy" and str(card.get("value")).lower() == "skipped" for card in answer.get("cards", [])), "public_player_comparison_skips_fantasy")
    report.check("owner" not in text and "fantrax" not in text, "public_player_comparison_no_provider_leakage")

    leafs = profile_for_team_entity(find_by_id("nhl.team.toronto_maple_leafs"))
    canes = profile_for_team_entity(find_by_id("nhl.team.carolina_hurricanes"))
    report.check(leafs is not None and canes is not None, "team_profiles_available", "Leafs and Hurricanes")
    team_assessment = ComparisonReasoningEngine().compare_public_teams(leafs, canes, "Compare Leafs and Hurricanes")
    report.check(team_assessment.comparison_type == "public_team_comparison", "team_assessment_type", team_assessment.comparison_type)
    report.check(team_assessment.confidence >= 0.70, "team_assessment_confidence", str(team_assessment.confidence))

    team_answer = route_question("Compare Leafs and Hurricanes", mode="public")
    team_text = _text(team_answer)
    report.check(team_answer.get("intent") == "public_team_comparison", "scout_public_team_comparison_route", str(team_answer.get("intent")))
    for heading in ["executive comparison", "strengths", "weaknesses", "historical comparison", "prime comparison", "future outlook", "athena conclusion"]:
        report.check(heading in team_text, f"rendered_team_section_{heading.replace(' ', '_')}")
    team_dev = team_answer.get("developer") or {}
    report.check("comparison_reasoning_engine" in (team_dev.get("intelligence_used") or []), "developer_team_comparison_engine")
    report.check("comparison_assessment" in team_dev, "developer_team_comparison_assessment_attached")
    report.check(any(str(card.get("label")).lower() == "fantasy" and str(card.get("value")).lower() == "skipped" for card in team_answer.get("cards", [])), "public_team_comparison_skips_fantasy")
    report.check("owner" not in team_text and "fantrax" not in team_text, "public_team_comparison_no_provider_leakage")

    return report.emit()


if __name__ == "__main__":
    raise SystemExit(main())
