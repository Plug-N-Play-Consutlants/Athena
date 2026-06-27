"""Validate v0.5.0-drop4e38 Scout renderer cleanup.

This validation focuses on rendered answer hygiene, not new intelligence.
It verifies that public answers avoid provider/fantasy leakage, avoid title
repetition inside the body, and expose concise observed facts instead of
repeating the full executive brief a second time.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_VERSION, SCOUT_VERSION, ATHENA_BUILD  # noqa: E402
from Tests.version_compat import is_recognized_athena_version, is_recognized_build, is_recognized_scout_version  # noqa: E402
from Scout.conversation.router import route_question  # noqa: E402


class Report:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.lines: list[str] = []

    def pass_(self, name: str, detail: str = "") -> None:
        self.passed += 1
        self.lines.append(f"[PASS] {name}: {detail}".rstrip())

    def fail(self, name: str, detail: str = "") -> None:
        self.failed += 1
        self.lines.append(f"[FAIL] {name}: {detail}".rstrip())

    def check(self, condition: bool, name: str, detail: str = "") -> None:
        self.pass_(name, detail) if condition else self.fail(name, detail)

    def emit(self) -> int:
        print("Scout Renderer Cleanup Validation Report")
        print("=" * 48)
        print(f"Overall status: {'PASS' if self.failed == 0 else 'FAIL'}")
        print(f"Passed: {self.passed}")
        print(f"Warnings: {self.warnings}")
        print(f"Failed: {self.failed}")
        print()
        for line in self.lines:
            print(line)
        return 0 if self.failed == 0 else 1


def combined_answer_text(answer: dict, *, include_cards: bool = True) -> str:
    parts: list[str] = []
    for key in ("title", "natural_language_response", "engine_conclusion"):
        value = answer.get(key)
        if value:
            parts.append(str(value))
    for key in ("observed_facts", "known_limitations"):
        for item in answer.get(key) or []:
            parts.append(str(item))
    if include_cards:
        for card in answer.get("cards") or []:
            parts.append(str(card.get("label", "")))
            parts.append(str(card.get("value", "")))
    return "\n".join(parts)


def main() -> int:
    report = Report()

    report.check(is_recognized_athena_version(ATHENA_VERSION), "athena_version", ATHENA_VERSION)
    report.check(is_recognized_scout_version(SCOUT_VERSION, ATHENA_VERSION), "scout_version", SCOUT_VERSION)
    report.check(is_recognized_build(ATHENA_BUILD, ATHENA_VERSION), "athena_build", ATHENA_BUILD)

    player = route_question("Tell me about Auston Matthews", mode="public")
    player_text = combined_answer_text(player).lower()
    report.check(player.get("intent") == "public_player_profile", "public_player_route", str(player.get("intent")))
    report.check("fantasy" not in player_text, "public_player_no_fantasy_leakage")
    report.check(not (player.get("natural_language_response") or "").startswith(str(player.get("title"))), "public_player_no_body_title_duplication")
    report.check(len(player.get("observed_facts") or []) <= 6, "public_player_concise_observed_facts", f"facts={len(player.get('observed_facts') or [])}")
    report.check("Executive Summary:" not in "\n".join(player.get("observed_facts") or []), "public_player_facts_do_not_repeat_brief")

    team = route_question("Tell me about the Toronto Maple Leafs", mode="public")
    team_text = combined_answer_text(team).lower()
    report.check(team.get("intent") == "public_team_profile", "public_team_route", str(team.get("intent")))
    report.check("fantasy" not in team_text, "public_team_no_fantasy_leakage")

    comparison = route_question("Compare Auston Matthews and Connor McDavid", mode="public")
    comparison_text = combined_answer_text(comparison, include_cards=False).lower()
    fantasy_cards = [card for card in comparison.get("cards") or [] if str(card.get("label", "")).lower() == "fantasy"]
    report.check(comparison.get("intent") == "public_player_comparison", "public_comparison_route", str(comparison.get("intent")))
    report.check("fantasy" not in comparison_text, "public_comparison_no_body_fantasy_leakage")
    report.check(any(str(card.get("value", "")).lower() == "skipped" for card in fantasy_cards), "public_comparison_fantasy_skipped_card")
    report.check(not (comparison.get("natural_language_response") or "").startswith(str(comparison.get("title"))), "public_comparison_no_body_title_duplication")

    app_text = (PROJECT_ROOT / "Scout" / "app.py").read_text(encoding="utf-8")
    report.check("displayText" in app_text and "diagnosticBlock" in app_text and "const publicText" in app_text, "scout_frontend_redundant_conclusion_guard")

    return report.emit()


if __name__ == "__main__":
    raise SystemExit(main())
