"""Doctor for Epic 6A Experience Layer foundation."""
from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_VERSION, RELEASE_NAME
from Experience import ATHENA_RESPONSE_SCHEMA_VERSION, EXPERIENCE_LAYER_VERSION, PlayerIdentity
from Experience.renderer import build_athena_response


def report(label: str, passed: bool, detail: object) -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {label}: {detail}")
    return passed


def main() -> int:
    print("Experience Layer Foundation Doctor")
    print("=" * 64)
    checks = []
    checks.append(report("version", ATHENA_VERSION >= "0.6.1.0.0", ATHENA_VERSION))
    checks.append(report("release", RELEASE_NAME in {"Experience Layer Foundation", "Player Experience Foundation", "Player Experience Rendering Hotfix", "Player Experience Contract Hotfix", "Scout Orchestration Release Gate Hotfix", "Experience Gate Alignment Hotfix", "Player Experience Content Mapping Hotfix", "Player Experience Refinement", "Foundational Governance and Module Adaptivity", "Foundational Governance Cleanup Tolerance Hotfix", "Adaptive Investigation Strategy Foundation", "Adaptive Investigation Runtime Integration"}, RELEASE_NAME))
    checks.append(report("schema", ATHENA_RESPONSE_SCHEMA_VERSION == "athena_response_v1", ATHENA_RESPONSE_SCHEMA_VERSION))
    checks.append(report("layer_version", EXPERIENCE_LAYER_VERSION >= "0.6.1.0.0", EXPERIENCE_LAYER_VERSION))
    identity = PlayerIdentity(full_name="Sample Player", jersey_number="34", team="Sample Team", position="C")
    checks.append(report("jersey_number_first_class", identity.jersey_number == "34", identity))
    response = build_athena_response({"intent": "public_player_profile", "title": "Sample Player", "public_comment": "Sample summary.", "player_number": "34"})
    sections = [section.section_type for section in response.ui_sections]
    checks.append(report("render_sections", "player_profile_header" in sections and "expandable_evidence_panel" in sections, sections))
    print("-" * 64)
    if all(checks):
        print("Overall status: PASS")
        return 0
    print("Overall status: FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
