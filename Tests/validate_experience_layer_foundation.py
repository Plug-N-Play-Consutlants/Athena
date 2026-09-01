"""Validate Epic 6A Experience Layer foundation."""
from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_VERSION, RELEASE_NAME, VERSION_SCHEMA
from Experience import ATHENA_RESPONSE_SCHEMA_VERSION, EXPERIENCE_LAYER_VERSION
from Experience.renderer import build_athena_response
from Scout.conversation.responses import response


def check(label: str, condition: bool, detail: object, failures: list[str]) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}: {detail}")
    if not condition:
        failures.append(label)


def main() -> int:
    failures: list[str] = []
    print("Experience Layer Foundation Validation")
    print("=" * 64)
    check("version_advanced_to_epic_6", ATHENA_VERSION >= "0.6.1.0.0", ATHENA_VERSION, failures)
    check("release_name", RELEASE_NAME in {"Experience Layer Foundation", "Player Experience Foundation", "Player Experience Rendering Hotfix", "Player Experience Contract Hotfix", "Scout Orchestration Release Gate Hotfix", "Experience Gate Alignment Hotfix", "Player Experience Content Mapping Hotfix", "Player Experience Refinement", "Foundational Governance and Module Adaptivity", "Foundational Governance Cleanup Tolerance Hotfix", "Adaptive Investigation Strategy Foundation", "Adaptive Investigation Runtime Integration"}, RELEASE_NAME, failures)
    check("version_schema_locked", VERSION_SCHEMA == "major.epic.sprint.patch.hotfix", VERSION_SCHEMA, failures)
    check("schema_version", ATHENA_RESPONSE_SCHEMA_VERSION == "athena_response_v1", ATHENA_RESPONSE_SCHEMA_VERSION, failures)
    check("experience_layer_version", EXPERIENCE_LAYER_VERSION >= "0.6.1.0.0", EXPERIENCE_LAYER_VERSION, failures)

    payload = response(
        intent="public_player_profile",
        title="Auston Matthews",
        engine_conclusion="Auston Matthews remains an elite franchise center.",
        observed_facts=["Identity: Toronto Maple Leafs center.", "Current value: elite scoring driver."],
        known_limitations=["Live NHL feed data may be unavailable in offline mode."],
        confidence=0.86,
        cards=[
            {"label": "Team", "value": "Toronto Maple Leafs"},
            {"label": "Position", "value": "C"},
            {"label": "Jersey Number", "value": "34"},
            {"label": "Goals", "value": "42"},
            {"label": "Assists", "value": "39"},
            {"label": "Points", "value": "81"},
            {"label": "P/GP", "value": "1.12"},
            {"label": "+/-", "value": "+18"},
            {"label": "Career Tier", "value": "Elite"},
        ],
    )
    check("scout_payload_has_experience_contract", payload.get("experience_contract") == "athena_response_v1", payload.get("experience_contract"), failures)
    athena_response = payload.get("athena_response") or {}
    check("athena_response_present", isinstance(athena_response, dict), type(athena_response), failures)
    sections = athena_response.get("ui_sections") or []
    player_header = next((s for s in sections if s.get("section_type") == "player_profile_header"), None)
    check("player_header_section", isinstance(player_header, dict), player_header, failures)
    identity = ((player_header or {}).get("data") or {}).get("identity") or {}
    check("player_identity_name", identity.get("full_name") == "Auston Matthews", identity, failures)
    check("player_identity_jersey_number", identity.get("jersey_number") == "34", identity, failures)
    check("player_identity_team", identity.get("team") == "Toronto Maple Leafs", identity, failures)
    check("player_identity_position", identity.get("position") == "C", identity, failures)
    check("assessment_badge_available", "ELITE" in (identity.get("assessment_badges") or []), identity.get("assessment_badges"), failures)
    stat_boxes = ((player_header or {}).get("data") or {}).get("stat_boxes") or []
    labels = {box.get("label") for box in stat_boxes}
    check("current_stat_boxes", {"Goals", "Assists", "Points", "P/GP", "+/-"}.issubset(labels), labels, failures)
    evidence_panel = next((s for s in sections if s.get("section_type") == "expandable_evidence_panel"), None)
    check("evidence_panel_hidden_by_default", isinstance(evidence_panel, dict) and evidence_panel.get("default_open") is False, evidence_panel, failures)

    normalized = build_athena_response({"intent": "public_team_profile", "title": "Toronto Maple Leafs", "public_comment": "Executive summary."})
    check("generic_response_sections", normalized.ui_sections[-1].section_type == "expandable_evidence_panel", [s.section_type for s in normalized.ui_sections], failures)

    print("-" * 64)
    if failures:
        print("Overall status: FAIL")
        print(f"Failed: {len(failures)}")
        return 1
    print("Overall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
