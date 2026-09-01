"""Validate Epic 6B Player Experience contract."""
from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_VERSION, RELEASE_NAME, VERSION_SCHEMA
from Experience import EXPERIENCE_LAYER_VERSION
from Experience.player import PLAYER_EXPERIENCE_VERSION
from Scout.conversation.responses import response


def check(label: str, condition: bool, detail: object, failures: list[str]) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}: {detail}")
    if not condition:
        failures.append(label)


def main() -> int:
    failures: list[str] = []
    print("Player Experience Validation")
    print("=" * 64)
    check("version_advanced_to_6b", ATHENA_VERSION >= "0.6.2.0.2", ATHENA_VERSION, failures)
    check("release_name", RELEASE_NAME in {"Experience Layer Foundation", "Player Experience Foundation", "Player Experience Rendering Hotfix", "Player Experience Contract Hotfix", "Scout Orchestration Release Gate Hotfix", "Experience Gate Alignment Hotfix", "Player Experience Content Mapping Hotfix", "Player Experience Refinement", "Foundational Governance and Module Adaptivity", "Foundational Governance Cleanup Tolerance Hotfix", "Adaptive Investigation Strategy Foundation", "Adaptive Investigation Runtime Integration"}, RELEASE_NAME, failures)
    check("version_schema_locked", VERSION_SCHEMA == "major.epic.sprint.patch.hotfix", VERSION_SCHEMA, failures)
    check("experience_layer_version", EXPERIENCE_LAYER_VERSION >= "0.6.2.0.2", EXPERIENCE_LAYER_VERSION, failures)
    check("player_experience_version", PLAYER_EXPERIENCE_VERSION >= "0.6.2.0.2", PLAYER_EXPERIENCE_VERSION, failures)

    payload = response(
        intent="public_player_profile",
        title="Connor McDavid",
        engine_conclusion="Connor McDavid remains an elite franchise center and offensive driver.",
        observed_facts=[
            "Identity: Edmonton Oilers center.",
            "Career trend: elite production remains the defining signal.",
            "Organizational impact: drives roster construction and competitive window analysis.",
            "Risk factors: workload and injury exposure should be considered.",
        ],
        known_limitations=["Offline mode may not include live NHL season feed data."],
        confidence=0.91,
        cards=[
            {"label": "Team", "value": "Edmonton Oilers"},
            {"label": "Position", "value": "C"},
            {"label": "Jersey Number", "value": "97"},
            {"label": "Goals", "value": "32"},
            {"label": "Assists", "value": "75"},
            {"label": "Points", "value": "107"},
            {"label": "P/GP", "value": "1.40"},
            {"label": "+/-", "value": "+25"},
            {"label": "Career Tier", "value": "Elite"},
            {"label": "Prime Window", "value": "Prime"},
            {"label": "Trend Summary", "value": "Last-three-season signal remains elite."},
            {"label": "Outlook", "value": "Franchise-level offensive anchor."},
        ],
    )
    athena_response = payload.get("athena_response") or {}
    sections = athena_response.get("ui_sections") or []
    player_experience = next((s for s in sections if s.get("section_type") == "player_experience"), None)
    check("player_experience_section_present", isinstance(player_experience, dict), player_experience, failures)
    data = (player_experience or {}).get("data") or {}
    identity = data.get("identity") or {}
    check("identity_name", identity.get("full_name") == "Connor McDavid", identity, failures)
    check("identity_jersey_number", identity.get("jersey_number") == "97", identity, failures)
    check("identity_team_position", identity.get("team") == "Edmonton Oilers" and identity.get("position") == "C", identity, failures)
    check("assessment_badges", {"Elite", "Prime Window"}.issubset(set(identity.get("assessment_badges") or [])), identity.get("assessment_badges"), failures)
    stat_labels = {box.get("label") for box in data.get("stat_boxes") or []}
    check("stat_boxes", {"Goals", "Assists", "Points", "P/GP", "+/-"}.issubset(stat_labels), stat_labels, failures)
    tabs = (player_experience or {}).get("children") or []
    tab_titles = [tab.get("title") for tab in tabs]
    check("analysis_and_stats_tabs", tab_titles == ["Analysis", "Stats"], tab_titles, failures)
    analysis = tabs[0] if tabs else {}
    analysis_children = analysis.get("children") or []
    analysis_titles = [child.get("title") for child in analysis_children]
    required = ["Executive Summary", "Playing Style", "Current Season", "Career Trend", "Organizational Impact", "Risk Factors", "Future Outlook"]
    check("analysis_sections", analysis_titles == required, analysis_titles, failures)
    stats = tabs[1] if len(tabs) > 1 else {}
    stats_data = stats.get("data") or {}
    check("stats_tab_story_first", bool(stats_data.get("athena_insight")) and "current_assessment" in stats_data, stats_data, failures)
    evidence_panel = next((s for s in sections if s.get("section_type") == "expandable_evidence_panel"), None)
    check("evidence_panel_preserved", isinstance(evidence_panel, dict) and evidence_panel.get("default_open") is False, evidence_panel, failures)

    print("-" * 64)
    if failures:
        print("Overall status: FAIL")
        print(f"Failed: {len(failures)}")
        return 1
    print("Overall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
