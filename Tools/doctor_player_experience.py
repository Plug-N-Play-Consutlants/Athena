"""Doctor for Epic 6B Player Experience."""
from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_VERSION, RELEASE_NAME
from Experience.player import PLAYER_EXPERIENCE_VERSION, build_player_experience_section


def report(label: str, ok: bool, detail: object) -> bool:
    print(f"[{'PASS' if ok else 'FAIL'}] {label}: {detail}")
    return ok


def main() -> int:
    print("Player Experience Doctor")
    print("=" * 64)
    checks = []
    checks.append(report("version", ATHENA_VERSION >= "0.6.2.0.2", ATHENA_VERSION))
    checks.append(report("release_name", RELEASE_NAME in {"Experience Layer Foundation", "Player Experience Foundation", "Player Experience Rendering Hotfix", "Player Experience Contract Hotfix", "Scout Orchestration Release Gate Hotfix", "Experience Gate Alignment Hotfix", "Player Experience Content Mapping Hotfix", "Player Experience Refinement", "Foundational Governance and Module Adaptivity", "Foundational Governance Cleanup Tolerance Hotfix", "Adaptive Investigation Strategy Foundation", "Adaptive Investigation Runtime Integration"}, RELEASE_NAME))
    checks.append(report("player_experience_version", PLAYER_EXPERIENCE_VERSION >= "0.6.2.0.2", PLAYER_EXPERIENCE_VERSION))
    section = build_player_experience_section({
        "intent": "public_player_profile",
        "title": "Connor McDavid",
        "confidence": 0.91,
        "cards": [
            {"label": "Team", "value": "Edmonton Oilers"},
            {"label": "Position", "value": "C"},
            {"label": "Jersey Number", "value": "97"},
            {"label": "Career Tier", "value": "Elite"},
            {"label": "Goals", "value": "32"},
            {"label": "Assists", "value": "75"},
            {"label": "Points", "value": "107"},
            {"label": "P/GP", "value": "1.40"},
            {"label": "+/-", "value": "+25"},
        ],
    })
    identity = section.data.get("identity", {})
    checks.append(report("section_type", section.section_type == "player_experience", section.section_type))
    checks.append(report("jersey_number", identity.get("jersey_number") == "97", identity))
    checks.append(report("badges", "Elite" in identity.get("assessment_badges", []), identity.get("assessment_badges")))
    checks.append(report("tabs", [child.title for child in section.children] == ["Analysis", "Stats"], [child.title for child in section.children]))
    print("-" * 64)
    if all(checks):
        print("Overall status: PASS")
        return 0
    print("Overall status: FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
