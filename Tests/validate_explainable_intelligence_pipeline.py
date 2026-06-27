"""Validation for Athena v0.5.5.1.0 Explainable Intelligence Pipeline."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    CHECKS.append((name, bool(condition), detail))


def main() -> int:
    from Core.version import ATHENA_VERSION, RELEASE_NAME
    from Intelligence.Explainability import (
        EXPLAINABLE_INTELLIGENCE_VERSION,
        EvidenceBundle,
        EvidenceItem,
        ReasoningStep,
        ReasoningTrace,
        ExplainabilityResult,
    )
    from Intelligence.Confidence import CONFIDENCE_PROPAGATION_VERSION, propagate_confidence
    from Intelligence.Pipeline import EXPLAINABLE_PIPELINE_VERSION, execute_explainable_intelligence, studio_explainability_diagnostics
    from Intelligence.Foundation import capability_matrix, seed_intelligence_registry
    from Knowledge.Intelligence.Routing.multi_sport_router import route_multi_sport_query, studio_route_diagnostics

    version_tuple = tuple(map(int, ATHENA_VERSION.split(".")))
    check("version", version_tuple >= (0, 5, 5, 1, 0), ATHENA_VERSION)
    check("release family", bool(RELEASE_NAME), RELEASE_NAME)
    check("explainability version", EXPLAINABLE_INTELLIGENCE_VERSION == "0.5.5.1.0", EXPLAINABLE_INTELLIGENCE_VERSION)
    check("pipeline version", EXPLAINABLE_PIPELINE_VERSION == "0.5.5.1.0", EXPLAINABLE_PIPELINE_VERSION)
    check("confidence version", CONFIDENCE_PROPAGATION_VERSION == "0.5.5.1.0", CONFIDENCE_PROPAGATION_VERSION)

    evidence = EvidenceBundle(
        knowledge=(EvidenceItem("knowledge_graph", "Knowledge Evidence", "sample", 0.7),),
        events=(EvidenceItem("event_intelligence", "Event Evidence", "sample", 0.65),),
    )
    trace = ReasoningTrace((ReasoningStep("sample", "Sample Step", detail="deterministic"),))
    report = propagate_confidence(0.7, evidence, trace)
    check("confidence report", 0.5 <= report.score <= 0.95 and report.label in {"medium", "high"}, str(report.to_dict()))

    result = execute_explainable_intelligence("Compare Auston Matthews vs Connor McDavid in the NHL")
    payload = result.to_dict()
    check("pipeline returns ExplainabilityResult", isinstance(result, ExplainabilityResult), str(type(result)))
    check("reasoning trace generated", payload["reasoning"]["step_count"] >= 5, str(payload["reasoning"]))
    check("evidence bundle generated", payload["evidence"]["source_counts"]["knowledge"] >= 1, str(payload["evidence"]["source_counts"]))
    check("modules selected", "player_assessment" in payload["modules"], str(payload["modules"]))
    check("confidence propagated", payload["confidence"]["score"] > 0.4 and payload["confidence"]["label"] in {"low", "medium", "high"}, str(payload["confidence"]))
    check("public context guardrail visible", any("Blocked context" in item for item in payload["limitations"]), str(payload["limitations"]))

    event_result = execute_explainable_intelligence("Summarize Blue Jays injuries")
    check("event context explanation", "event_assessment" in event_result.modules and event_result.evidence.source_counts()["events"] >= 1, str(event_result.to_dict()["evidence"]["source_counts"]))

    diagnostics = studio_explainability_diagnostics()
    check("Studio explainability diagnostics", diagnostics["panel"] == "explainable_intelligence" and diagnostics["status"] == "pass", str(diagnostics.keys()))
    route_diag = studio_route_diagnostics()
    check("route diagnostics include explainability", route_diag.get("explainability", {}).get("panel") == "explainable_intelligence", str(route_diag.keys()))

    # Prior sprint guardrails.
    registry = seed_intelligence_registry()
    check("foundation registry preserved", registry.stats()["modules"] >= 10, str(registry.stats()))
    check("capability matrix preserved", capability_matrix()["status"] == "pass", str(capability_matrix()["registry"]))
    route = route_multi_sport_query("Tell me about the Toronto Raptors")
    check("routing preserved", route.sport == "basketball" and route.intelligence_modules, str(route.to_dict()))

    studio = (ROOT / "Tools" / "athena_studio.py").read_text(encoding="utf-8")
    check("Studio exposes explainability tools", "show_explainability_dashboard" in studio and "validate_explainable_intelligence_pipeline" in studio, "Studio integration")

    failed = [row for row in CHECKS if not row[1]]
    print("Explainable Intelligence Pipeline Validation")
    print("=" * 64)
    for name, ok, detail in CHECKS:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"Overall status: {'PASS' if not failed else 'FAIL'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
