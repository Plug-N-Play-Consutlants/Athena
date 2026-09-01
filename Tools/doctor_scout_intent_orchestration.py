"""Doctor for Scout Intent & Response Orchestration Foundation."""
from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_VERSION, RELEASE_NAME
from Scout.conversation.orchestration import ORCHESTRATION_VERSION, orchestration_diagnostics, scout_intent_plan

ROOT = Path(__file__).resolve().parents[1]


def check(label: str, condition: bool, detail: object, failures: list[str]) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}: {detail}")
    if not condition:
        failures.append(label)


def main() -> int:
    failures: list[str] = []
    print("Scout Intent Orchestration Doctor")
    print("=" * 64)
    required = [
        "Scout/conversation/orchestration.py",
        "Scout/conversation/router.py",
        "Tests/validate_scout_intent_orchestration.py",
        "Tools/doctor_scout_intent_orchestration.py",
    ]
    check("version_at_least_0_5_6_3_0", ATHENA_VERSION >= "0.5.6.3.0", ATHENA_VERSION, failures)
    check("release_name", RELEASE_NAME in {"Scout Intent Orchestration Foundation", "Scout Context Isolation Hotfix", "Workspace Runtime State Tolerance Hotfix", "Experience Layer Foundation", "Player Experience Foundation", "Player Experience Rendering Hotfix", "Player Experience Contract Hotfix", "Scout Orchestration Release Gate Hotfix", "Experience Gate Alignment Hotfix", "Player Experience Content Mapping Hotfix", "Player Experience Refinement", "Foundational Governance and Module Adaptivity", "Foundational Governance Cleanup Tolerance Hotfix", "Adaptive Investigation Strategy Foundation", "Adaptive Investigation Runtime Integration"}, RELEASE_NAME, failures)
    check("orchestration_version", ORCHESTRATION_VERSION >= "0.5.6.3.0", ORCHESTRATION_VERSION, failures)
    for rel in required:
        check(f"required_file:{rel}", (ROOT / rel).exists(), rel, failures)
    router_text = (ROOT / "Scout/conversation/router.py").read_text(encoding="utf-8")
    check("router_imports_orchestration", "scout_orchestrated_answer" in router_text, "Scout/conversation/router.py", failures)
    check("router_uses_orchestration_before_recent_events", router_text.find("orchestration_plan = scout_intent_plan") < router_text.find("is_recent_event_query(raw_question)"), "orchestration precedes legacy recent-event route", failures)
    diagnostics = orchestration_diagnostics()
    check("diagnostics_routes_available", len(diagnostics.get("routes", [])) >= 10, diagnostics, failures)
    plan = scout_intent_plan("Compare Connor McDavid and Nathan MacKinnon. Which player would you build a franchise around today, and why?", "public")
    check("comparison_plan", plan is not None and plan.route == "public_player_comparison", plan, failures)
    print("-" * 64)
    if failures:
        print("Overall status: FAIL")
        return 1
    print("Overall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
